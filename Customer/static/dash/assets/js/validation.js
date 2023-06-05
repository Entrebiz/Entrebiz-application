function validateForm(id, type, excludeFields = ['middleName','note', 'additionalPage']) {
	let validationType = false;
	let allInputs = [];
	if (type === 'form') allInputs = document.forms[id].elements;
	if (type === 'class') allInputs = document.getElementsByClassName(id);
	const labels = document.querySelectorAll('label');
	for (let j = 0; j < allInputs.length; j += 1) {
		if (!['button', 'submit'].includes(allInputs[j].type) && !excludeFields.includes(allInputs[j].getAttribute('data-name') || allInputs[j].name)) {
			if (allInputs[j].value && allInputs[j].type !== 'file') { // can only set an empty string to a file input value, due to security reasons
				allInputs[j].value = (typeof allInputs[j].value === 'string')
					? allInputs[j].value.trim() : allInputs[j].value;
			}
			if (['', null, undefined].includes(allInputs[j].value)) {
				// showErrorField([allInputs[j]]);
				for (const l in labels) {
					if (labels[l].htmlFor === allInputs[j].id) {
						showErrorField([allInputs[j]], `${labels[l].innerText} is required.`);
					}
				}
				validationType = true;
				// return false;
			}
			const hasMoreThanAscii = !/^[\u0000-\u007f]*$/.test(allInputs[j].value)
			if ( hasMoreThanAscii ) {
				// string has non-ascii characters
				showErrorField([allInputs[j]], 'fancy characters are not allowed');
				validationType = true;
			  }
			if (allInputs[j].type === 'email') {
				allInputs[j].value = allInputs[j].value.toString()
					.toLowerCase();
				if (!validateEmail(allInputs[j].value)) {
				    if (document.getElementById('errorField')) {
						showErrorField([allInputs[j]], 'Please provide a valid email address.');
					} else {
						showErrorField([allInputs[j]], 'Please provide a valid email address.');
					}

					validationType = true;
					// return false;
				}
			}

			if (allInputs[j].name && ((allInputs[j].name === 'phoneNo' && !validatePhone(allInputs[j].value)) || (allInputs[j].name === 'countryCode' && allInputs[j].value == '0'))) {
				const countryCodeElem = document.getElementById('countryCode');
				const phoneNoElem = document.getElementById('phoneNo');
				if ((countryCodeElem.value == '0') && !phoneNoElem.value) {
					showErrorField([countryCodeElem]);
					showErrorField([phoneNoElem], 'Phone number with country code is required.');
					validationType = true;
				} else if (countryCodeElem.value == '0') {
					showErrorField([countryCodeElem], 'Country code is required.');
					validationType = true;
				} else if (!phoneNoElem.value) {
					showErrorField([phoneNoElem], 'Phone number is required.');
					validationType = true;
				}
			}

			if (allInputs[j].name && ((allInputs[j].name === 'validityMonth') || (allInputs[j].name === 'validityYear'))) {
				const validityMonth = document.getElementById('month');
				const validityYear = document.getElementById('year');
				const currentDate = new Date();
				if (validityMonth.value == '' && validityYear.value == '') {
					showErrorField([validityMonth], 'Validity is required.');
					showErrorField([validityYear]);
					validationType = true;
				} else if (validityMonth.value == '') {
					showErrorField([validityMonth], 'Validity month is required.');
					validationType = true;
				} else if (validityYear.value == '') {
					showErrorField([validityYear], 'Validity year is required.');
					validationType = true;
				} else if (validityYear.value === `${currentDate.getUTCFullYear()}`
                    && new Date(`1${validityMonth.value}1999`).getMonth() <= currentDate.getMonth()) {
					showErrorField([validityMonth], 'Verification document expired!');
					validationType = true;
				}
			}

			if (allInputs[j].name && ((allInputs[j].name === 'companyMonth') || (allInputs[j].name === 'companyYear') || (allInputs[j].name === 'companyDay'))) {
				const validityMonth = document.getElementById('month');
				const validityYear = document.getElementById('year');
				const validityDay = document.getElementById('day');
				const elem = document.getElementById('dob');
				if (elem) {
					if (validityMonth.value === '0' && validityYear.value == '0' && validityDay.value == '0') {
						showErrorField([validityDay], '');
						showErrorField([validityMonth], '');
						showErrorField([validityYear], '');
						showErrorField([elem], 'Date of Incorporation is required.');
						validationType = true;
					} else if (validityDay.value == '0') {
						showErrorField([validityDay], '');
						showErrorField([elem], 'valid day is required.');
						validationType = true;
					} else if (validityMonth.value === '0') {
						showErrorField([validityMonth], '');
						showErrorField([elem], 'valid month is required.');
						validationType = true;
					} else if (validityYear.value == '0') {
						showErrorField([validityYear], '');
						showErrorField([elem], 'valid year is required.');
						validationType = true;
					}
				}
			}

			if (allInputs[j].type === 'file') {
				const fileExtension = allInputs[j].value.split('.').pop();
				if (!['jpg', 'jpeg', 'png', 'pdf', 'JPG', 'tiff', 'tif', 'JPEG', 'JPG', 'PDF', 'TIFF'].includes(fileExtension)) {
					showErrorField([allInputs[j]], `.${fileExtension.italics()} files are not allowed.`);
					validationType = true;
					// return false;
				}
			}

			if (allInputs[j].name === 'dob' && allInputs[j].type === 'hidden') {
				const dayElem = document.getElementById('day');
				const monthElem = document.getElementById('month');
				const yearElem = document.getElementById('year');

				if (!dayElem.value && !monthElem.value && !yearElem.value) {
					showErrorField([allInputs[j]], 'Date of Birth is required.');
					showErrorField([dayElem]);
					showErrorField([monthElem]);
					showErrorField([yearElem]);
					showErrorField([allInputs[j]], 'Date of birth is required.');
					validationType = true;
				} else if (!dayElem.value) {
					showErrorField([dayElem], '');
					validationType = true;
				} else if (!monthElem.value) {
					showErrorField([monthElem], '');
					validationType = true;
				} else if (!yearElem.value) {
					showErrorField([yearElem], '');
					validationType = true;
				}
			}
		}
	}
	if (allInputs.password && allInputs.confirmPassword) {
		if (allInputs.password.value !== allInputs.confirmPassword.value) {
			showErrorField([allInputs.password, allInputs.confirmPassword], 'Your passwords does not match.');
			validationType = true;
			// return false;
		}
	}
	if (allInputs.primaryCurrency && allInputs.secondaryCurrency) {
		if (allInputs.primaryCurrency.value === allInputs.secondaryCurrency.value) {
			showErrorField([allInputs.secondaryCurrency], 'Please choose a different currency.');
			// showErrorMsg('Please choose a different currency.');
			validationType = true;
			// return false;
		}
	}
	if (allInputs.firstAmount) {
		if (parseFloat(allInputs.firstAmount.value) <= 0) {
			showErrorField([allInputs.firstAmount], 'Amount should be greater than zero!');
			validationType = true;
			// return false;
		}
		const $balance = document.getElementById('hiddenFirstAccountBalance').innerText;
		if ((allInputs.firstAmount.value) > parseFloat($balance)) {
			showErrorField([allInputs.firstAmount], 'Insufficient balance!');
			validationType = true;
			// return false;
		}
	}
	if (allInputs.Amount) {
		if (parseFloat(allInputs.Amount.value) <= 0) {
			showErrorField([allInputs.Amount], 'Amount should be greater than zero!');
			validationType = true;
			// return false;
		}
	}
	if (allInputs.firstCurrency && allInputs.secondCurrency) {
		if (allInputs.firstCurrency.value === allInputs.secondCurrency.value) {
			showErrorField([allInputs.secondCurrency], 'Please choose a different account.');
			validationType = true;
			// return false;
		}
	}
	if (allInputs.idProof) {
		if (parseFloat(allInputs.idProof.value) === '') {
			showErrorField([allInputs.idProof], 'Select a document!');
			validationType = true;
			// return false;
		}
	}
	if (validationType) return false;

	return true;
}

function showErrorField(fields = [], msg = '') {
	const tempFields = fields;
	for (let f = 0; f < tempFields.length; f += 1) {
		tempFields[f].style.borderColor = 'red';
	}
	if (msg !== '') {
		if (!document.getElementById(`err-${tempFields[0].id}`)) {
			const msgElem = document.createElement('p');
			msgElem.style.color = 'red';
			msgElem.style.fontSize = 'small';
			msgElem.id = `err-${tempFields[0].id}`;
			msgElem.innerText = msg;
            if (tempFields[0].id === 'phoneNo') {
                return tempFields[0].parentElement.parentElement.appendChild(msgElem);
            }
			tempFields[0].parentElement.appendChild(msgElem);
		}
	}
}

function clearErrorMessage(elem) {
	(document.getElementById(`err-${elem.id}`)) && document.getElementById(`err-${elem.id}`).remove();
	if (elem.style.borderColor && elem.style.borderColor === 'red') {
		elem.style.borderColor = null;
	}
}

function validateEmail(email) {
	const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

	return re.test(email);
}

function validatePhone(ph) {
	const re = /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/;

	return re.test(ph);
}

function checkUniqueCurrency(e) {
	const fCurrency = document.getElementById('primaryCurrency');
	const sCurrency = document.getElementById('secondaryCurrency');
	if (fCurrency.value === sCurrency.value) {
		// showErrorMsg('Please choose a different currency.');
		showErrorField([e], 'Please choose a different currency.');

		return false;
	}

	return true;
}

function restrictNumbers(e) {
	const charReg = /^[0-9 -]+$/;
	const inputVal = e.key.toString();
	const inputText = e.target.value;

	if (inputVal === 'Tab' || inputVal === 'Backspace') {
		return true;
	}
	if (!charReg.test(inputVal)) {
		return false;
	}

	return inputText.length <= 15;
}

/**
 * @return {boolean}
 */
function ValidateSize(file) {
	const FileSize = file.files[0].size / 1024 / 1024; // in MB


	// return FileSize <= 10;
	return true
}

function showLoader() {
	if (document.getElementById('loader')) {
		document.getElementById('loader')
			.parentElement
			.classList
			.remove('hide-loader');
	}
}

function hideLoader() {
	if (document.getElementById('loader')) {
		document.getElementById('loader')
			.parentElement
			.classList
			.add('hide-loader');
	}
}

function showSuccessMsg(message) {
	if (message) {
		document.getElementById('errorField').innerHTML = message;
		document.getElementById('errorField').style.color = 'green';
		if (document.getElementById('alertDiv')) {
			// document.getElementById('alertDiv').classList.add('sucessMsgShow');
		}
		if (document.getElementById('alertDiv')) {
			document.getElementById('alertDiv').style.display = 'block';
			document.getElementById('alertDiv').classList.add('alert-box-warning');
			// document.getElementById('alertDiv').scrollIntoView();
		}
		setTimeout(() => {
			document.getElementById('errorField').innerHTML = '';
			// document.getElementById('alertDiv').classList.remove('sucessMsgShow');
			if (document.getElementById('alertDiv')) {
				document.getElementById('alertDiv').classList.remove('alert-box-warning');
				document.getElementById('alertDiv').style.display = 'none';
			}
		}, 5000);
	}
}


function showErrorMsg(message) {
	document.getElementById('errorField').innerHTML = message;
	if (document.getElementById('alertDiv')) {
		document.getElementById('alertDiv').classList.add('sucessMsgShow');
		document.getElementById('alertDiv').style.display = 'block';
		document.getElementById('alertDiv').scrollIntoView({ block: 'center' });
	}

	setTimeout(() => {
		document.getElementById('errorField').innerHTML = '';
		document.getElementById('alertDiv').classList.remove('sucessMsgShow');
		if (document.getElementById('alertDiv')) {
			document.getElementById('alertDiv').style.display = 'none';
		}
	}, 5000);

	return true;
}

if (document.forms.length) {
	for (let f = 0; f < document.forms.length; f += 1) {
		for (let e = 0; e < document.forms[f].elements.length; e += 1) {
			document.forms[f].elements[e].addEventListener('focus', (event) => {
				if (event.target.style.borderColor && event.target.style.borderColor === 'red') {
					event.target.style.borderColor = null;
				}
				const errMsgSelector = document.getElementById(`err-${event.target.id}`);
				if (errMsgSelector) {
					errMsgSelector.remove();
				}
				if (['day', 'month', 'year'].includes(event.target.id)) {
					document.getElementById('err-dob') && document.getElementById('err-dob').remove();
				}
			});
		}
	}
}

function signUpFieldValidate(e) {
	const regexp =/^[a-zA-Z0-9 !@"?:.,-/]+$/;
	const inputVal = e.key;
	if (inputVal === 'Tab' || inputVal === 'Backspace') {
		return true;
	}

	return regexp.test(inputVal);
}

function signUpFieldValidateOnchange(elem) {
	const field = elem.parentElement.childNodes[1].innerText;
	const regexp = /^[a-zA-Z0-9 !@"?:.,-/]+$/;
	let inputVal;
	if (elem.id != 'middleName') inputVal = (elem.value);
	((elem.id != 'middleName') && (inputVal === '')) && showErrorField([elem], `${field} is required`);
	if (inputVal === 'Tab' || inputVal === 'Backspace') return true;
	if (elem.value && (!regexp.test(inputVal))) {
		showErrorField([elem], 'Single quotes are not allowed');
	}
}

let intervalField = 0;
let startDate;
startDate = new Date();
startDate.setMinutes(startDate.getMinutes() + 10);
setTimerField(true);
function setTimerField(flag) {
	const localData = {};
	let statusFlag = false;
	if (flag) {
		if (document.getElementById('timerShow')) {
			intervalField = setInterval(async () => {
				localData.now = new Date();
				localData.distance = startDate - localData.now;
				localData.minutes = Math.floor((localData.distance % (1000 * 60 * 60)) / (1000 * 60));
				localData.seconds = Math.floor((localData.distance % (1000 * 60)) / 1000);
				document.getElementById('timerShow').innerHTML = `${localData.minutes}m ${localData.seconds}s `;
				if (localData.distance > 0) {
					return;
				}
				clearInterval(intervalField);
				document.getElementById('timerShow').innerHTML = 'EXPIRED';
				window.location.href = '/logout';
				statusFlag = true;
			}, 1000);
		}
	} else {
		clearInterval(intervalField);
	}
}
document.addEventListener('click', () => {
	startDate = new Date();
	startDate.setMinutes(startDate.getMinutes() + 10);
	setTimerField(true);
});

function checkNonAsciiCharacters(elem) {
	const hasMoreThanAscii = !/^[\u0000-\u007f]*$/.test(elem.value)
	if ( hasMoreThanAscii ) {
		// string has non-ascii characters
		showErrorField([elem], 'fancy characters are not allowed');
	  }
}

function removeSpace(e, id) {
	var value = document.getElementById(id).value;
	if (/\s/g.test(value)){
		var space_removed_val = value.replace(/\s+/g, '');
		document.getElementById(id).value = space_removed_val;
	}
	
}