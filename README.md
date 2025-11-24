# Cryptography_I_Project 🚀 - Secure File Messenger

**Secure File Messenger** is a proof-of-concept (PoC) web application built as part of a Cryptography I unit. It enables end-to-end encrypted file sharing between users, ensuring that sensitive files remain private, even from the server.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Configuration](#configuration)
4. [Usage](#usage)
5. [Architecture & Design](#architecture--design)
6. [Cryptographic Flow](#cryptographic-flow)
7. [Security Considerations](#security-considerations)
8. [Limitations / Known Issues](#limitations--known-issues)
9. [Contributing](#contributing)
10. [License](#license)
11. [Acknowledgments](#acknowledgments)
12. [Contact](#Contact)

---

## Overview

Secure File Messenger is a full-stack web application allowing users to securely share files via end-to-end encryption. Built for a Cryptography I course, its main goal is to demonstrate practical cryptographic primitives (asymmetric and symmetric encryption) in a working app.

All cryptographic operations happen **client-side** (in the browser) using the Web Crypto API — so private keys, plaintext files, and symmetric keys never leave the user’s device.

---

## Features

🔐 Security

- **End-to-End Encryption**: Files are encrypted client-side with AES-256-GCM.
- **RSA-OAEP Key wrapping**: AES keys are securely wrapped using 4096-bit RSA with OAEP padding
- **Double-Wrapping**: AES keys are encrypted twice (once for sender, once for recipient) and stored securely in MongoDB.
- **User Authentication**: Secure login/registration with SQLite backend.
- **Zero Server Knowledge**: Server only stores ciphertext and encrypted keys; no access to sensitive data
- **Key Reusability**: AES keys are reused per sender-recipient pair to minimize expensive RSA operations

👤 User Experience

- **Secure Authentication**: User registration and login with SQLite-backed session management
- **Intuitive Interface**: Clean, responsive UI built with TailwindCSS
- **Easy File Sharing**: Simple workflow to encrypt, send, and decrypt files
- **Inbox Management**: View all received files with one-click decryption

🏗️ Technical

- **Browser-Based Crypto**: All encryption/decryption handled by Web Crypto API
- **Hybrid Architecture**: Flask backend for routing, MongoDB for encrypted storage
- **Modern Tooling**: Uses uv for fast, reliable dependency management

---

## Getting Started

### Prerequisites

- **Python 3.8+**
- **MongoDB 6.0+**(with mongosh for setup)
- The **uv** package manager (https://github.com/astral-sh/uv)
- **Git**

### Installation

1. Install uv (if you don’t already have it):

- macOS/Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

```

- Windows

```Powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Clone the repo and install dependencies using uv:

```bash
# Clone the project
git clone https://github.com/keanehatescoding/Cryptography_I_project.git
cd Cryptography_I_project
```

3. Install dependencies (reads pyproject.toml or requirements.txt)

```bash
uv sync
```

4. Set Up Environmental Variables:

Create a .env in the root directory

```text
SECRET_KEY=your_flask_secret_key_here  # Generate with: python -c "import secrets; print(secrets.token_hex(16))"
SQLALCHEMY_DATABASE_URI=sqlite:///users.db  # Or your preferred SQLite path
PORT=5000  # Default port
MONGO_URI=mongodb://localhost:27017/  # Default local MongoDB
```

Generate a secure SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

5.Set up MongoDB Start MongoDB service:

```bash
# Linux
sudo systemctl start mongod

# macOS (with Homebrew)
brew services start mongodb-community
```

Initialize MongoDB Collections:

```bash
mongosh
```

In the Mongo shell

```mongocli
use file_db
db.createCollection("aes_keys")
db.createCollection("encrypted_aes_keys")
exit
```

8. Create private and public keys

```
cd certs
openssl genrsa -out key.pem 4096
openssl rsa -in key.pem -pubout -out cert.pem
```

9. Run the Application

```bash
cd src
uv run main.py
   # Or: python server.py
   # Or: flask run

```

The server will start at https://localhost:5000. Open it in a modern browser (Chrome/Firefox recommended for Web Crypto support).

---

## Usage

- Start the backend
- Open the UI in the browser

1. Register a New Account

- Navigate to /register and create your credentials. Your RSA keypair will be automatically generated in your browser.

2. Login

- Go to /login to access your account.

3. Send a File

- Visit /send_file
- Select a recipient from the dropdown
- Choose a file to upload
- Click "Send" — the file is encrypted in your browser before transmission

4. Check Your Inbox

- Navigate to /inbox
- View all received files
- Click on any file to decrypt and download it

---

## Architecture

### Technology Stack

#### Frontend

- HTML5 + Jinja2 templates
- TailwindCSS for styling
- Vanilla JavaScript + Web Crypto API

#### Backend:

- Flask (Python) for API routes and session management
- WTForms for input validation
- SQLAlchemy ORM

#### Databases:

- **SQLite**: User accounts and sessions.
- **MongoDB**: Encrypted files (.enc) and wrapped AES keys.

Storage:
Public keys: uploads/public*keys/*.pub
Encrypted files: storage/encrypted*files/*.enc

---

Storage Layout

```
Cryptography_I_project/
├── server.py               # Flask application entry point
├── models.py               # SQLAlchemy database models
├── forms.py                # WTForms definitions
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JavaScript, assets
├── uploads/publickeys/     # User RSA public keys (.pub)
├── storage/encryptedfiles/ # Encrypted files (.enc)
├── .env                    # Environment configuration
└── users.db                # SQLite database
```

---

## Cryptographic Flow

### 1. Key Generation

- Private key: Stored in client's browser (never sent to server)
- Public key: Uploaded to server at uploads/publickeys/<username>.pub

### 2. File Encryption(Sender):

- Check if an AES-256 key already exists for this sender/recipient pair
- If not, create a new AES key
- Encrypt the file client-side with AES-GCM → produces ciphertext, nonce, and auth tag
- Wrap AES key with recipient's RSA public key
- Wrap AES key with sender's RSA public key (To be able to reuse this key)
- Upload ciphertext and both wrapped keys to server
- If there is already an AES-GCM key
- Prompt for the sender's private key
- Decrypt the encrypted AES-GCM key using the private key
- Encrypt the file using
- Encrypt the file client-side with AES-GCM → produces ciphertext, nonce, and auth tag
- Upload the ciphertext to the server

#### 3. File Decryption(Recipeint)

- Retrieve encrypted file(s) and wrapped AES key from server
- Unwrap AES key using recipient's RSA private key which your will be prompted
- Decrypt file using unwrapped AES key
- Download plaintext file

---

## Important Security Notes

### Security Considerations

This is a PoC project — not recommended for production use without additional security hardening

Security Considerations
Strengths

- ✅ True end-to-end encryption with client-side crypto
- ✅ Server never sees plaintext data or private keys
- ✅ Use of modern, vetted algorithms (AES-GCM, RSA-OAEP)
- ✅ Key reuse strategy reduces computational overhead

---

### Limitations / Known Issues

This is a proof-of-concept, not ready for production use.

- ⚠️ No key rotation or revocation mechanism
- ⚠️ Session management could be strengthened
- ⚠️ No protection against traffic analysis or metadata leakage
- ⚠️ File size limits not enforced
- ⚠️ Browser Dependency: Requires modern browser with Web Crypto API support
- ⚠️ No Mobile App: Web-only interface
- ⚠️ No File Preview: Files must be fully decrypted before viewing
- ⚠️ Key Management: No automated key rotation or expiration

---

## Contributing

This is an educational project, but contributions are welcome! If you'd like to improve the code:

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add some amazing feature')
4. Write some test(if applicable)
5. Push to the branch (git push origin feature/amazing-feature)
6. **Submit a Pull Request** with a clear description of what you changed and why

Some ideas for contribution:

- Implement key recovery / backup mechanism

- Add client-side UI improvements (progress bar, drag & drop file upload)
- Add better error handling and validation

- Unit tests for cryptographic functions

- Add logging / audit trail for file operations

## Please follow the existing code style. If you want to propose a large feature (e.g., key revocation, file expiry), open an issue first so we can discuss.

## License

This project is licensed under the GPL-2.0 License.
Make sure to respect this license when using or contributing.

---

## Acknowledgments

- Inspired by common cryptography course assignments and secure file-sharing designs.
- Thanks to the authors and maintainers of the Web Crypto API.
- Based on Python + Flask tutorials, and cryptographic best practices.

---

## Contact

For questions or feedback, please open an issue on GitHub.

⚠️ Disclaimer: This is a proof-of-concept educational project. While it implements real cryptographic primitives, it has not undergone a professional security audit and should not be used for protecting truly sensitive information in production environments.
