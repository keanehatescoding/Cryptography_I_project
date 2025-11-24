async function checkifKeyExists(username) {
	try {
		const enc_keys = await fetch("http://localhost:5000/enc_keys" + username);
		const enc_keys_json = await enc_keys.json()
		const enc_key = enc_keys_json.find(username)
		return enc_key;
	} catch (error) {
		console.error(e)
	}
}
form.addEventListener("submit", async (e) => {
	let username = document.getElementById("username")
	const file = document.getElementById("file")
	const private_key = document.getElementById("file")
	if (username === '' || username.value == null) {
		alert("Please enter a valid username")
		return;
	}
	if (file.file[0] == null || private_key.file[1] == null) {
		alert("Please enter a valid file")
		return;
	}
	const enc_key = await checkifKeyExists(username.vlaue)
	if (enc_key) {

		let [FileHadle] = await window.showOpenFilePicker(multiple = False);
		let fileData = await fileHandle.getfile();
	} else {

		alert("Enter a password")
		fetch("http://localhost:5000/post_key/" + username
	}
}
