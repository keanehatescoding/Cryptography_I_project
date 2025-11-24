async function getPK(username) {
	try {
		res = await fetch("http://localhost:5000/" + username + ".pub");
		if (!res.ok) {
			alert("Unable to retrieve " + username + "'s public key");
			throw new Error(`Response status: ${response.status}`);
		}
		const pk = await res.text();
		return pk;
	} catch (error) {
		console.error("Error fetching public key" + error);
	}
}
// Convert PEM format to ArrayBuffer
function pemToArrayBuffer(pem) {
	const b64 = pem.replace(/-----.*-----/g, "").replace(/\s/g, "");
	const binary = atob(b64);
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) {
		bytes[i] = binary.charCodeAt(i);
	}
	return bytes.buffer;
}
// Import public key into Web Crypto
async function importPublicKey(pem) {
	const binaryDer = pemToArrayBuffer(pem);
	return await window.crypto.subtle.importKey(
		"spki",
		binaryDer,
		{
			name: "RSA-OAEP",
			hash: "SHA-256",
		},
		true,
		["encrypt"],
	);
}
// Encrypt file data using RSA public key
async function encryptFileData(publicKey, fileData) {
	return await window.crypto.subtle.encrypt(
		{
			name: "RSA-OAEP",
		},
		publicKey,
		fileData,
	);
}
document.getElementById("encrypt").addEventListener("click", async () => {
	const username = document.getElementById("username").value;
	const AES_key = document.getElementById("secret_key").value;
	if (!username || !AES_key) {
		alert("Please provide both username and file.");
		return;
	}
	if (AES_key.length < 8) {
		alert("Please provide a key which is atleast 8 digits long");
		return;
	}
	if (AES_key.length > 64) {
		alert("Key is too large");
		return;
	}

	const pk = await getPK(username);
	const publicKey = await importPublicKey(pk);
	const fileData = await AES_key.arrayBuffer();

	// Encrypt
	const encryptedData = await encryptFileData(publicKey, fileData);

	// Convert to base64 for display or transmission
	const b64Encrypted_AES_key = btoa(
		String.fromCharCode(...new Uint8Array(encryptedData)),
	);

	try {
		const response = await fetch("https://localhost:5000/messages/", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			// Set the FormData instance as the request body
			body: JSON.stringify({
				username: username,
				message: b64Encrypted_AES_key,
			}),
		});
		console.log(await response.json());
		console.log("Server response:", result);
		alert("File encrypted and sent successfully!");
	} catch (e) {
		console.error("Error sending file" + e);
	}
});
