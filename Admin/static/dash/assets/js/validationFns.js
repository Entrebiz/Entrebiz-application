
function restrictAlphabets(e) {
	const charReg = /^\s*[a-zA-Z0-9\-\s]+\s*$/;
	const regexp = /^\S+$/;
	const inputVal = e.key;
	// const inputText = e.target.value;

	if (inputVal === 'Tab' || inputVal === 'Backspace') {
		return true;
	}

	return regexp.test(inputVal);

	return charReg.test(inputVal);
}

function restrictAmount(e, max) {
	const charReg = /^[0-9]+$/;
	const inputVal = e.key.toString();
	const inputText = e.target.value;

	if ((inputVal === 'Tab') || (inputVal === 'Backspace') || ((inputText.indexOf('.') === -1) && (inputVal === '.'))) {
		return true;
	}
	if (!charReg.test(inputVal)) {
		return false;
	}
	if (max) {
		if (parseFloat(inputText) > parseFloat(max)) {
			return false;
		}
	}

	return true;
}





function validateCompanyFields(e) {
	const charReg = /^[a-zA-Z0-9_.-]+$/;
	const inputVal = e.key.toString();
	const inputText = e.target.value;

	if ((inputVal === 'Tab') || (inputVal === 'Backspace') || ((inputText.indexOf('.') === -1) && (inputVal === '.'))) {
		return true;
	}
	if (!charReg.test(inputVal)) {
		return false;
	}

	return true;
}

function formatAmount(e) {
	if (parseFloat(e.target.value)) {
		e.target.value = e.target.value ? parseFloat(e.target.value).toFixed(2) : '';
	} else {
		e.target.value = '';
	}
}

function formatAccount(e, id) {
	const value = document.getElementById(id).value;
	if (isValidCharacter(value)) {
		showErrorField([document.getElementById(id)], 'Special characters are not allowed');
	}
}


function isValidCharacter(value) {
	const regExp = /^[a-zA-Z0-9 _.-]*$/;
	if (!regExp.test(value)) {
		return true;
	}

	return false;
}

function toCommas(value) {
	return value.toString()
		.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function removeCommas(value) {
	return value.replace(/,/g, '');
}
function myTrim(x) {
	return x.slice(0, x.lastIndexOf(' '));
}

function validateMaxAmount1(e, elem) {
	val = myTrim(document.getElementById('bal_amnt').innerText)
	if (parseFloat(elem.value) > parseFloat(val)) {


		return showErrorField([document.getElementById(elem.id)], 'Insufficient Amount');
	}
	if (parseFloat(elem.value) <= 0) {
		return showErrorField([document.getElementById(elem.id)], 'Amount should be greater than zero!');
	}

	return true;
}

function validatePhone(e, elem) {
	let reg = /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/im;
	if (!elem.value.match(reg)) {

		return showErrorField([document.getElementById(elem.id)], 'Invalid phone number');
	}

	return true;
}

function validateMaxAmount(e, elem) {
	myTrim(document.getElementById('bal_amnt').innerText)
	if (parseFloat(elem.value) > parseFloat(elem.getAttribute('maxValue'))) {

		return showErrorField([document.getElementById(elem.id)], 'Insufficient Amount');
	}
	if (parseFloat(elem.value) <= 0) {
		return showErrorField([document.getElementById(elem.id)], 'Amount should be greater than zero!');
	}

	return true;
}

function restrictOtp(e) {
	const charReg = /^[0-9]+$/;
	const inputVal = e.key.toString();
	const inputText = e.target.value;

	if ((inputVal === 'Tab') || (inputVal === 'Backspace')) {
		return true;
	}
	if (!charReg.test(inputVal)) {
		return false;
	}

	return true;
}



function readImageURL(input) {
	if (input && input.files && input.files.length) {
		const result = ValidateSize(input);
		if (!result) {
			document.getElementById(input.id).value = null;
			document.getElementById(`${input.name}-label`).innerText = '';
			if (!appData.idVerification || !appData.idVerification.documentfilesLength) {
				document.getElementById(input.name).src = '/static/dash/assets/img/upload.png';
				uploadIconShowAndHide(input, 'block');
			} else {
				// showUploadedLabel(input, 'block');
			}
			// showErrorMsg('Maximum file size allowed is 10 MB');
		} else if (input.files && input.files[0]) {
			const reader = new FileReader();
			reader.onload = (e) => {
				if (['application/pdf', 'application/wps-office.pdf'].includes(input.files[0].type)) {
					document.getElementById(input.name).src = '/static/dash/assets/img/pdf2.png';
					// '/assets/img/pdf2.png'
				} else { 
					document.getElementById(input.name).src = e.target.result;
				}
				uploadIconShowAndHide(input, 'none');
			};
			reader.readAsDataURL(input.files[0]);
			document.getElementById(`${input.name}-label`).innerText = 'Document added.';
		}
	} else {
		if (!appData.idVerification || !appData.idVerification.documentfilesLength) {
			uploadIconShowAndHide(input, 'block');
			document.getElementById(input.name).src = '/assets/img/upload.png';
		} else {
			document.getElementById(input.name).src = '';
			showUploadedLabel(input, 'block');
		}
		document.getElementById(input.id).value = null;
		document.getElementById(`${input.name}-label`).innerText = '';
	}
}

function uploadIconShowAndHide(input, value) {
	const children = document.getElementById(input.id).parentNode.childNodes;
	for (let i = 0; i < children.length; i += 1) {
		if (children[i].nodeName === 'LABEL') {
			children[i].style.display = value;
		}
	}
}
function showUploadedLabel(input, value) {
	const children = document.getElementById(input.id).parentNode.childNodes;
	for (let i = 0; i < children.length; i += 1) {
		if (children[i].nodeName === 'LABEL' && children[i].attributes.length === 1) {
			children[i].style.display = value;
		}
	}
}