

function removeFromUsersList(divNo) {
	let usersSelector = document.getElementById('users');
	let users = parseAllUsers();
	let email = document.getElementById(`email${divNo}`).value;
	users = users.filter(e => (e.email !== email));
	showUsersList(users);
	usersSelector.value = JSON.stringify(users);
}

function showUsersList(users) {
	let userListContent = '';
	let divCounter = 1;
	let userList = document.getElementById('userLocalList');
	for (let j = 0; j < users.length; j++) {
		userListContent += `<div class="row user-data-row duplicateDiv" id="${'addUserModal' + divCounter}">
			<div class="col-12">
				<button class="btn-default del-btn" type="button" id="${'removeUserBtn' + divCounter}"
						onclick="return removeFromUsersList('${divCounter}');">
					<img src="/assets/img/delete.png" alt=""> Delete
				</button>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'firstName' + divCounter}">First Name</label>
					<input type="text" data-name="firstName" id="${'firstName' + divCounter}" maxlength="50"
						   pattern="[^':]*$"
						 title="Quotes are note allowed"
					value="${users[j].firstName}" class="input-box userField" placeholder="Enter Your First Name" required>
				</div>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'middleName' + divCounter}">Middle Name</label>
					<input type="text" data-name="middleName" id="${'middleName' + divCounter}" maxlength="50"
					pattern="[^':]*$"
					title="Quotes are note allowed"
					value="${users[j].middleName}" class="input-box userField" placeholder="Enter Your Middle Name">
				</div>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'lastName' + divCounter}">Last Name</label>
					<input type="text" data-name="lastName" id="${'lastName' + divCounter}" maxlength="50"
						 pattern="[^':]*$"
						 title="Quotes are note allowed"
					value="${users[j].lastName}" class="input-box userField" placeholder="Enter Your Last Name" required>
				</div>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'email' + divCounter}">Email</label>
					<input type="email" data-name="email" id="${'email' + divCounter}" maxlength="50"
					value="${users[j].email}" class="input-box userField" placeholder="Enter Your Email" required>
				</div>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'userType' + divCounter}">User Type</label>
					<select data-name="userType" id="${'userType' + divCounter}" class="input-box custom-select userField" required>
						<option value="" disabled selected>Select User Type</option>
						
						
						<option value="1" ${(users[j].userType === "1") ? 'selected' : ''}>Director</option>
						
						<option value="2" ${(users[j].userType === "2") ? 'selected' : ''}>Representative</option>
						
						
					</select>
				</div>
			</div>
			<div class="col-lg-4 col-md-6 col-12">
				<div class="user-data-block">
					<label for="${'mainBusinessowner' + divCounter}" class="custom-checbox-hldr">
						<input type="checkbox" name="mainBusinessowner" data-name="mainBusinessowner" value="${users[j].mainBusinessowner}" id="${'mainBusinessowner' + divCounter}"
						class="userField" onchange="checkboxCheckStatus(this);" ${(users[j].mainBusinessowner === '1') ? 'checked' : ''}>
						<span class="checkmark"></span>
						 Ultimate Beneficial Owner
					</label>
				</div>
			</div>
		</div>`;
		divCounter++;
	}
	userList.innerHTML = userListContent;
}

function clearUserInfoFields(userInfo) {
	for (let j = 0; j < userInfo.length; j++) {
		if (userInfo[j].type === 'checkbox')
			userInfo[j].checked = false;
		userInfo[j].value = userInfo[j].getAttribute('data-default');
	}
}

function parseAllUsers() {
	let users = [];
	const usersDivs = document.getElementsByClassName('duplicateDiv');
	for (let i = 0; i < usersDivs.length; i++) {
		const userFields = usersDivs[i].getElementsByClassName('userField');
		let user = {};
		for (let j = 0; j < userFields.length; j++) {
			user[userFields[j].getAttribute('data-name')] = userFields[j].value;
		}
		users.push(user);
	}
	return users;
}
function appendToUsersList(final = false) {
	let usersSelector = document.getElementById('users');
	let userSelector = document.getElementById('user');
	let seen = new Set();
	if (validateForm('userInfo', 'class')) {
		let users = parseAllUsers();
		const userInfo = document.getElementsByClassName('userInfo');
		let user = {};
		for (let j = 0; j < userInfo.length; j++) {
			user[userInfo[j].name] = userInfo[j].value;
		}
		users.push(user);

		/*let array = users.filter((el) => (el.userType == 4));
		if (array.length >= 2) {
				showErrorMsg('Multiple owner allocation not allowed.');
				return false;
		}*/

		let hasDuplicates = users.some((currentObject) => {
			return seen.size === seen.add(currentObject.email).size;
		});

		if (hasDuplicates) {
			showErrorField([userInfo['email']], 'Users with same email is not allowed.');
			// showErrorMsg('Users with same email is not allowed.');
			return false;
		}
		if (final) {
			let mainOwnerUser = users.find(u => {
				return u.mainBusinessowner === '1';
			});
			if (!mainOwnerUser) {
				showErrorMsg('Please add a user as the Ultimate Beneficial Owner');
				return false;
			}
			users.pop();
		} else {
			clearUserInfoFields(userInfo);
		}
		showUsersList(users);
		usersSelector.value = JSON.stringify(users);
		if (final) userSelector.value = JSON.stringify(user);

		return true;
	}
	return false;
}


function createFormDataAndValidate(form) {
	showLoader();
	if (validateFormsub(form, 'form')) {
		if (!appendToUsersList(true)) {
			hideLoader();
			return false;
		}
		let usersSelector = document.getElementById('users');
		let userSelector = document.getElementById('user');
		let users = JSON.parse(usersSelector.value);
		let user = JSON.parse(userSelector.value);
		let existIndex = users.findIndex(u => u.email === user.email);
		if (existIndex > -1) users.splice(existIndex, 1);
		users.push(user);
		usersSelector.value = JSON.stringify(users);
		userSelector.value = '';
		hideLoader();
	} else {
		hideLoader();
		return false;
	}
}



function checkboxCheckStatus(e) {
    let usersSelector = document.getElementById('users');
    let usersLength = JSON.parse(usersSelector.value).length;
    // for (let i = 1; i <= usersLength; i += 1) {
    //     document.getElementById(`mainBusinessowner${i}`).value = 0;
    // }
    document.getElementById('mainOwner-checkbox').value = 0;
    e.value = (+e.checked);
}


function validateFormsub(id, type, excludeFields = ['middleName','note']) {
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
	if (!validationType) 
	{
		document.getElementById("businessForm").submit();
	}

}