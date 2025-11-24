const form = document.getElementById('sendFileForm');
const privateKeyPicker = document.getElementById('privateKeyPicker');

// // Add this helper function at the top of send_file.js
function showStatus(message, type = 'info') {
	const statusDiv = document.getElementById('status');
	statusDiv.textContent = message;
	statusDiv.className = type + ' show';
	statusDiv.classList.remove('hidden');

	if (type === 'success') {
		setTimeout(() => {
			statusDiv.classList.add('hidden');
		}, 5000);
	}
}

function arrayBufferToBase64(buffer) {
	return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}
function base64ToArrayBuffer(base64) {
	const binary = atob(base64);
	return Uint8Array.from(binary, c => c.charCodeAt(0)).buffer;
}
function pemToArrayBuffer(pem) {
	const base64 = pem.replace(/-----BEGIN[^-]*-----/g, '')
		.replace(/-----END[^-]*-----/g, '')
		.replace(/\s+/g, '');
	const binaryString = atob(base64);
	const bytes = new Uint8Array(binaryString.length);
	for (let i = 0; i < binaryString.length; i++) {
		bytes[i] = binaryString.charCodeAt(i);
	}
	return bytes.buffer;
}
async function importPublicKey(pem) {
	const der = pemToArrayBuffer(pem);
	return crypto.subtle.importKey("spki", der, { name: "RSA-OAEP", hash: "SHA-256" }, false, ["encrypt"]);
}
async function importPrivateKey(pem) {
	const der = pemToArrayBuffer(pem);
	return crypto.subtle.importKey("pkcs8", der, { name: "RSA-OAEP", hash: "SHA-256" }, false, ["decrypt"]);
}
function getPrivateKeyFile() {
	return new Promise((resolve) => {
		privateKeyPicker.onchange = (e) => resolve(e.target.files[0]);
		privateKeyPicker.click();
	});
}

// MAIN FORM SUBMIT
form.addEventListener('submit', async e => {
	e.preventDefault();
	const submitBtn = form.querySelector('[type="submit"]');
	if (submitBtn) submitBtn.disabled = true;

	const recipient = form.recipient.value.trim();
	const file = form.file.files[0];
	if (!file) {
		showStatus("Please select a file", "error");
		if (submitBtn) submitBtn.disabled = false;
		return;
	}

	try {
		// STEP 1: Get or create double-wrapped reusable key
		const resp = await fetch(`/get_reusable_aes_key?recipient=${encodeURIComponent(recipient)}`);
		if (!resp.ok) {
			if (resp.status === 500) {
				throw new Error(`Recipient "${recipient}" not found. Please check the username.`);
			}
			throw new Error(`Server error: ${resp.status} ${resp.statusText}`);
		}
		// Check content type before parsing
		const contentType = resp.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			throw new Error(`Recipient "${recipient}" not found or invalid response from server.`);
		}
		const data = await resp.json();

		let wrappedForSenderB64;
		let wrappedForRecipientB64;
		let aesKey; // Will hold the actual AES key

		if (data.exists) {
			// KEY EXISTS: Need to decrypt our wrapped copy with private key
			wrappedForSenderB64 = data.wrapped_for_sender;
			wrappedForRecipientB64 = data.wrapped_for_recipient;

			// Prompt for private key to unwrap
			const privFile = await getPrivateKeyFile();
			const privPem = await privFile.text();
			const privKey = await importPrivateKey(privPem);

			const ourWrapped = base64ToArrayBuffer(wrappedForSenderB64);
			const rawAesKey = await crypto.subtle.decrypt({ name: "RSA-OAEP" }, privKey, ourWrapped);

			aesKey = await crypto.subtle.importKey(
				"raw", rawAesKey, { name: "AES-GCM" }, false, ["encrypt"]
			);

		} else {
			// NEW KEY: Generate fresh AES key (no private key needed!)
			aesKey = await crypto.subtle.generateKey(
				{ name: "AES-GCM", length: 256 },
				true,
				["encrypt"]
			);
			const rawKey = await crypto.subtle.exportKey("raw", aesKey);

			// Fetch both public keys
			const [recPubRes, senderPubRes] = await Promise.all([
				fetch(`/uploads/public_keys/${encodeURIComponent(recipient)}.pub`),
				fetch(`/uploads/public_keys/${current_user_username}.pub`)
			]);

			if (!recPubRes.ok) throw new Error(`Recipient ${recipient} has no public key, Are you sure they exist?`);
			if (!senderPubRes.ok) throw new Error("You must upload your public key first");

			const [recPubKey, senderPubKey] = await Promise.all([
				importPublicKey(await recPubRes.text()),
				importPublicKey(await senderPubRes.text())
			]);

			// Wrap the key for both parties
			const [encRec, encSender] = await Promise.all([
				crypto.subtle.encrypt({ name: "RSA-OAEP" }, recPubKey, rawKey),
				crypto.subtle.encrypt({ name: "RSA-OAEP" }, senderPubKey, rawKey)
			]);

			wrappedForRecipientB64 = arrayBufferToBase64(encRec);
			wrappedForSenderB64 = arrayBufferToBase64(encSender);

			// Publish the wrapped keys
			await fetch("/publish_reusable_aes_key", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					recipient,
					wrapped_for_sender: wrappedForSenderB64,
					wrapped_for_recipient: wrappedForRecipientB64
				})
			});
		}

		// STEP 2: Encrypt file with AES key (whether new or decrypted)
		const nonce = crypto.getRandomValues(new Uint8Array(12));
		const encryptedFile = await crypto.subtle.encrypt(
			{ name: "AES-GCM", iv: nonce },
			aesKey,
			await file.arrayBuffer()
		);

		// STEP 3: Send
		const sendResp = await fetch("/send_file", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				recipient,
				filename: file.name,
				encrypted_file: arrayBufferToBase64(encryptedFile),
				wrapped_key_for_recipient: wrappedForRecipientB64,
				nonce: arrayBufferToBase64(nonce)
			})
		});

		const result = await sendResp.json();
		if (result.success) {
			showStatus("File sent successfully!", "success");
			form.reset();
		} else {
			throw new Error(result.error || "Send failed");
		}

	} catch (err) {
		console.error(err);
		showStatus("Error: " + err.message, "error");

	} finally {
		if (submitBtn) submitBtn.disabled = false;
	}
});
