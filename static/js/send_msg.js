const form = document.querySelector('form')
form.addEventListener('submit', handleSubmit)
const username = document.querySelector('form.username')

async function fetchPK() {
	await fetch("http://localhost:5000/get_public_key" + username + ".pub")
}
function handleSubmit(event) {

