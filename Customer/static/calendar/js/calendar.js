// Array of max days in month in a year and in a leap year
const monthMaxDays	= [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const monthMaxDaysLeap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
//const monthList = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const monthList = ['01', '02','03','04','05','06','07','08','09','10','11','12'];
const hideSelectTags = [];

function getRealYear(dateObj) {
	return (dateObj.getYear() % 100) + (((dateObj.getYear() % 100) < 39) ? 2000 : 1900);
}

function getDaysPerMonth(month, year) {
	const curDate = new Date();
	const curYear = getRealYear(curDate);
	/*
	Check for leap year. These are some conditions to check year is leap year or not...
	1.Years evenly divisible by four are normally leap years, except for...
	2.Years also evenly divisible by 100 are not leap years, except for...
	3.Years also evenly divisible by 400 are leap years.
	*/
	if ((year % 4) == 0) {

		if ((year % 100) == 0 && (year % 400) != 0) { return monthMaxDays[month]; }

		return monthMaxDaysLeap[month];
	}

	return monthMaxDays[month];
}

function createCalender(year, month, day) {
	 // current Date
	const curDate = new Date();
	const curDay = curDate.getDate();
	const curMonth = curDate.getMonth();
	const curYear = getRealYear(curDate);
	// alert(document.getElementById('selectYear').options.length);

	 // if a date already exists, we calculate some values here
	if (!year) {
		var year = curYear;
		var month = curMonth;
	}


	let yearFound = 0;
	for (let i = 0; i < document.getElementById('selectYear').options.length; i++) {
		if (document.getElementById('selectYear').options[i].value == year) {
			document.getElementById('selectYear').selectedIndex = i;
			yearFound = true;
			break;
		}
	}
	if (!yearFound) {
		document.getElementById('selectYear').selectedIndex = 0;
		year = document.getElementById('selectYear').options[0].value;
	}
	document.getElementById('selectMonth').selectedIndex = month;

	 // first day of the month.
	const fristDayOfMonthObj = new Date(year, month, 1);
	const firstDayOfMonth = fristDayOfMonthObj.getDay();

	continu		= true;
	firstRow	= true;
	let x	= 0;
	var d	= 0;
	const trs = [];
	let ti = 0;
	while (d <= getDaysPerMonth(month, year)) {
		if (firstRow) {
			trs[ti] = document.createElement('TR');
			if (firstDayOfMonth > 0) {
				while (x < firstDayOfMonth) {
					trs[ti].appendChild(document.createElement('TD'));
					x++;
				}
			}
			firstRow = false;
			var d = 1;
		}
		if (x % 7 == 0) {
			ti++;
			trs[ti] = document.createElement('TR');
		}
		if (day && d == day) {
			var setID = 'calenderChoosenDay';
			var styleClass = 'choosenDay';
			var setTitle = 'this day is currently selected';
		}  else {
			var setID = false;
			var styleClass = 'normalDay';
			var setTitle = false;
		}
		const td = document.createElement('TD');
		td.className = styleClass;
		if (setID) {
			td.id = setID;
		}
		if (setTitle) {
			td.title = setTitle;
		}
		td.onmouseover = new Function('highLiteDay(this)');
		td.onmouseout = new Function('deHighLiteDay(this)');

		if (targetEl) { td.onclick = new Function(`pickDate(${year}, ${month}, ${d})`); } else { td.style.cursor = 'default'; }
		td.appendChild(document.createTextNode(d));
		trs[ti].appendChild(td);
		x++;
		d++;
	}

	return trs;
}

function showCalender(elPos, tgtEl) {
	targetEl = false;
	if (document.getElementById(tgtEl)) {
		targetEl = document.getElementById(tgtEl);
	} else
	if (document.forms[0].elements[tgtEl]) {
		targetEl = document.forms[0].elements[tgtEl];
	}

	const calTable = document.getElementById('calenderTable');

	var positions = [0, 0];
	var positions = getParentOffset(elPos, positions);
	calTable.style.left = `${positions[0]}px`;
	calTable.style.top = `${positions[1]}px`;

	calTable.style.display = 'block';

	const matchDate = new RegExp('^([0-9]{4})-([0-9]{2})-([0-9]{2})$');
	const m = matchDate.exec(targetEl.value);

	if (m == null) {
		 const selectedDate = dateSplit(tgtEl);
		if(selectedDate)
			trs = createCalender(selectedDate['year'], selectedDate['month'], selectedDate['day']);
		else
			trs = createCalender(false, false, false);
		showCalenderBody(trs);
	} else {
		if (m[1].substr(0, 1) == 0) { m[1] = m[1].substr(1, 1); }
		if (m[2].substr(0, 1) == 0) { m[2] = m[2].substr(1, 1); }
		m[2] -= 1;
		trs = createCalender(m[1], m[2], m[3]);
		showCalenderBody(trs);
	}

	hideSelect(document.body, 1);
}

function dateSplit(tgtEl){
	const elem = document.getElementById(tgtEl);
	if(elem && elem.value){
		const arr = elem.value.split('-');
		return {
			day : arr[2],
			month:monthList.indexOf(arr[1]),
			year:arr[0],
		}
	}
	return null;
}

function showCalenderBody(trs) {
	const calTBody = document.getElementById('calender');
	while (calTBody.childNodes[0]) {
		calTBody.removeChild(calTBody.childNodes[0]);
	}
	for (const i in trs) {
		calTBody.appendChild(trs[i]);
	}
}
function setYears(sy, ey) {
	 // current Date
	const curDate = new Date();
	const curYear = getRealYear(curDate);

	if (ey)
	{
		endYear = curYear;
	}
	// alert(sy);
	// /alert(ey);
	document.getElementById('selectYear').options.length = 0;
	let j = 0;
	for (y = curYear; y >= sy; y--) {
		document.getElementById('selectYear')[j++] = new Option(y, y);
	}
}
function hideSelect(el, superTotal) {
	if (superTotal >= 100) {
		return;
	}

	const totalChilds = el.childNodes.length;
	for (let c = 0; c < totalChilds; c++) {
		const thisTag = el.childNodes[c];
		if (thisTag.tagName == 'SELECT') {
			if (thisTag.id != 'selectMonth' && thisTag.id != 'selectYear') {
				const calenderEl = document.getElementById('calenderTable');
				var positions = [0, 0];
				var positions = getParentOffset(thisTag, positions);	// nieuw
				const thisLeft	= positions[0];
				const thisRight	= positions[0] + thisTag.offsetWidth;
				const thisTop	= positions[1];
				const thisBottom	= positions[1] + thisTag.offsetHeight;
				const calLeft	= calenderEl.offsetLeft;
				const calRight	= calenderEl.offsetLeft + calenderEl.offsetWidth;
				const calTop	= calenderEl.offsetTop;
				const calBottom	= calenderEl.offsetTop + calenderEl.offsetHeight;

				if (
					(
						/* check if it overlaps horizontally */
						(thisLeft >= calLeft && thisLeft <= calRight)
							||						(thisRight <= calRight && thisRight >= calLeft)
							||						(thisLeft <= calLeft && thisRight >= calRight)
					)
						&&					(
						/* check if it overlaps vertically */
							(thisTop >= calTop && thisTop <= calBottom)
							||						(thisBottom <= calBottom && thisBottom >= calTop)
							||						(thisTop <= calTop && thisBottom >= calBottom)
						)
				) {
					hideSelectTags[hideSelectTags.length] = thisTag;
					thisTag.style.display = 'none';
				}
			}
		} else if (thisTag.childNodes.length > 0) {
			hideSelect(thisTag, (superTotal + 1));
		}
	}
}
function closeCalender() {
	for (let i = 0; i < hideSelectTags.length; i++) {
		hideSelectTags[i].style.display = 'block';
	}
	hideSelectTags.length = 0;
	document.getElementById('calenderTable').style.display = 'none';
}
function highLiteDay(el) {
	el.className = 'hlDay';
}
function deHighLiteDay(el) {
	if (el.id == 'calenderToDay') {
	 	el.className = 'toDay';
	 } else if (el.id == 'calenderChoosenDay') {
		 el.className = 'choosenDay';
	 } else {
		 el.className = 'normalDay';
	 }
}
function pickDate(year, month, day) {
	month++;
	day	= day < 10 ? `0${day}` : day;

	const monthFrmt = monthList[month-1];
	month	= month < 10 ? `0${month}` : month;

	if (!targetEl) {
		alert('target for date is not set yet');
	} else {
		targetEl.value = `${year}-${monthFrmt}-${day}`;
		if(targetEl.id === 'fromDate'){
			document.getElementById('inp-fromDate').value = `${year}-${month}-${day}`;
		}else if(targetEl.id ==='toDate'){
			document.getElementById('inp-toDate').value =  `${year}-${month}-${day}`;
		}
		closeCalender();
	}
}
function getParentOffset(el, positions) {
	positions[0] += el.offsetLeft;
	positions[1] += el.offsetTop;
//	if (el.offsetParent) { positions = getParentOffset(el.offsetParent, positions); }
	return positions;
}