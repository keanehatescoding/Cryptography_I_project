function downloadFile(index) {
	const file = encryptedFiles[index];
	const blob = new Blob([file.decrypted_data]);
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = file.filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

function showStatus(message, type) {
	statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
}

function getPrivateKeyFile() {
	return new Promise((resolve) => {
		privateKeyPicker.onchange = (e) => {
			resolve(e.target.files[0]);
		};
		privateKeyPicker.click();
	});
}

async function importPrivateKey(pem) {
	let pemContents = pem.replace(/-----BEGIN [^-]+-----|-----END [^-]+-----|\s+/g, '');
	if (!pemContents) throw new Error("Invalid PEM format");

	try {
		const binaryDer = base64ToArrayBuffer(pemContents);
		return await crypto.subtle.importKey(
			'pkcs8',
			binaryDer,
			{ name: 'RSA-OAEP', hash: 'SHA-256' },
			false,
			['decrypt']
		);
	} catch {
		console.error('Private Key Import Error:', error);
		throw new Error('Failed to import private key. Ensure it is a valid PKCS8 format RSA-OAEP key.');
	}
}

function base64ToArrayBuffer(base64) {
	const binary = atob(base64);
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) {
		bytes[i] = binary.charCodeAt(i);
	}
	return bytes.buffer;
}
let privateKey = null;
const loadKeyBtn = document.getElementById('loadKeyBtn');
const privateKeyPicker = document.getElementById('privateKeyPicker');
const statusDiv = document.getElementById('status');
const filesContainer = document.getElementById('filesContainer');
let encryptedFiles = [];

// Load files on page load
loadFiles();

loadKeyBtn.addEventListener('click', async () => {
	try {
		const keyFile = await getPrivateKeyFile();
		const keyPem = await keyFile.text();
		privateKey = await importPrivateKey(keyPem);

		showStatus('Private key loaded successfully! Decrypting files...', 'success');
		loadKeyBtn.textContent = 'Private Key Loaded ✓';
		loadKeyBtn.disabled = true;

		// Decrypt all files
		await decryptAllFiles();

	} catch (error) {
		showStatus('Error loading private key: ' + error.message, 'error');
		console.error(error);
	}
});

async function loadFiles() {
	try {
		filesContainer.innerHTML = '<div class="loading">Loading files...</div>';

		const response = await fetch('/check_files');
		const data = await response.json();

		if (!data.success) {
			throw new Error(data.error || 'Failed to load files');
		}

		encryptedFiles = data.files;

		if (encryptedFiles.length === 0) {
			filesContainer.innerHTML = '<div class="status info">No files received yet.</div>';
			return;
		}

		showStatus(`Found ${encryptedFiles.length} encrypted file(s). Load your private key to decrypt them.`, 'info');
		renderFiles();

	} catch (error) {
		showStatus('Error loading files: ' + error.message, 'error');
		console.error(error);
	}
}

function renderFiles() {
	filesContainer.innerHTML = '';

	encryptedFiles.forEach((file, index) => {
		const card = document.createElement('div');
		card.className = 'file-card';
		card.id = `file-${index}`;

		const uploadDate = new Date(file.uploaded_at).toLocaleString();
		const isDecrypted = file.decrypted_content !== undefined;

		card.innerHTML = `
                    <div class="file-header">
                        <div class="file-name">${file.filename}</div>
                        <span class="${isDecrypted ? 'decrypted-badge' : 'encrypted-badge'}">
                            ${isDecrypted ? 'DECRYPTED' : 'ENCRYPTED'}
                        </span>
                    </div>
                    <div class="file-meta">
                        From: <strong>${file.sender}</strong> | 
                        Received: ${uploadDate}
                    </div>
                    ${isDecrypted ? `
                        <div class="file-content" id="content-${index}">${file.decrypted_content}</div>
                        <div class="file-actions">
                            <button class="btn btn-success" onclick="downloadFile(${index})">Download</button>
                        </div>
                    ` : `
                        <div class="file-content">🔒 File is encrypted. Load your private key to decrypt.</div>
                    `}
                `;

		filesContainer.appendChild(card);
	});
}

async function decryptAllFiles() {
	for (let i = 0; i < encryptedFiles.length; i++) {
		await decryptFile(i);
	}
	showStatus('All files decrypted successfully!', 'success');
}

async function decryptFile(index) {
	const file = encryptedFiles[index];

	try {
		// Decrypt AES key and IV
		const encryptedKey = base64ToArrayBuffer(file.encrypted_key);
		const encryptedIv = base64ToArrayBuffer(file.encrypted_iv);

		const decryptedKey = await crypto.subtle.decrypt(
			{ name: 'RSA-OAEP' },
			privateKey,
			encryptedKey
		);

		const decryptedIv = await crypto.subtle.decrypt(
			{ name: 'RSA-OAEP' },
			privateKey,
			encryptedIv
		);

		const aesKey = await crypto.subtle.importKey(
			'raw',
			decryptedKey,
			{ name: 'AES-CBC' },
			false,
			['decrypt']
		);

		const iv = new Uint8Array(decryptedIv);
		if (iv.length !== 16) {
			throw new Error("Invalid IV length after decryption");
		}

		// Fetch encrypted file content
		const fileResponse = await fetch(`/get_encrypted_file/${file.stored_file}`);
		const fileData = await fileResponse.json();

		if (!fileData.success) {
			throw new Error(fileData.error || 'Failed to fetch file');
		}

		const encryptedFileData = base64ToArrayBuffer(fileData.encrypted_data);

		// Decrypt file content
		const decryptedData = await crypto.subtle.decrypt(
			{ name: 'AES-CBC', iv },
			aesKey,
			encryptedFileData
		);

		// Convert to text (assuming text file)
		const decoder = new TextDecoder();
		const decryptedText = decoder.decode(decryptedData);

		// Store decrypted content
		encryptedFiles[index].decrypted_content = decryptedText;
		encryptedFiles[index].decrypted_data = decryptedData;

		// Re-render files
		renderFiles();

	} catch (error) {
		console.error(`Error decrypting file ${index}:`, error);
		encryptedFiles[index].decrypted_content = `❌ Decryption failed: ${error.message}`;
		renderFiles();
	}
}
