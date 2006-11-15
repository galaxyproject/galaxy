var open_ids = []
var cookie_name = "universe_ui"
var now = new Date();
now.setTime(now.getTime() + 365 * 24 * 60 * 60 * 1000);

// 
// cookie management off the web
// http://www.webreference.com/js/column8/property.html
//
function setCookie(name, value, expires, path, domain, secure) {
  var curCookie = name + "=" + escape(value) +
      ((expires) ? "; expires=" + expires.toGMTString() : "") +
      ((path) ? "; path=" + path : "") +
      ((domain) ? "; domain=" + domain : "") +
      ((secure) ? "; secure" : "");
  document.cookie = curCookie;
}

function getCookie(name) {
  var dc = document.cookie;
  var prefix = name + "=";
  var begin = dc.indexOf("; " + prefix);
  if (begin == -1) {
    begin = dc.indexOf(prefix);
    if (begin != 0) return null;
  } else
    begin += 2;
  var end = document.cookie.indexOf(";", begin);
  if (end == -1)
    end = dc.length;
  return unescape(dc.substring(begin + prefix.length, end));
}


function main(){
	init_ids()
	//debugger
	for (i=0; i<len(open_ids); i++){
		value = open_ids[i]
		expand_basic(value)
	}
}

function toggle_value(value) {
	// everything starts out closed
	var found = 0
	var tmp_list = []
	for (i=0; i<len(open_ids); i++){
		id = open_ids[i]
		if ( id == value) {
			found = 1
		} else {
			tmp_list.push(id)
		}
	}
	
	if (found) {
		open_ids = tmp_list
	} else {
		open_ids.push(value)
	}
	
	cookie_value = open_ids.join(':')
	setCookie(cookie_name, cookie_value, now)
}

function init_ids() {  
	var value = getCookie(cookie_name);
	if (value) {
		var items = value.split(":")
		for (i=0; i<len(items); i++){
			id   = items[i]
			elem = get(id)
			if (elem) {
				open_ids.push(id)
			}
		}
	} 
}

 // this expands without the toggle
function expand_basic(name){
	var elem = get(name)
	if (elem) {
		if (elem.style.display=="none"){
			elem.style.display="block"
		} else {
			elem.style.display="none"
		}
	}
}

//this collapses all known open things
function collapse_all(){
	var cur_open = open_ids
	for (var i=0; i<len(cur_open); i++){
		expand(cur_open[i])
	}
}

// this toggles between none and block
function expand(name){
	var elem = get(name)
	if (elem) {
		if (elem.style.display=="none"){
			elem.style.display="block"
		} else {
			elem.style.display="none"
		}
		toggle_value(name)
	}
}


// this toggles between visible and hidden
function show(name){
	var elem = get(name)
    if (elem.style.visibility=="hidden"){
        elem.style.visibility="visible";
    } else {
        elem.style.visibility="hidden";
    }
}

// utility function to get the length of on object 
function len(obj){
	return obj.length;
}

// utility function to get an element by id
function get(name){
	return document.getElementById(name);
}

// pops up a window
function pop_up(url) {
	day = new Date();
	id = day.getTime();
	eval("page" + id + " = window.open(url, '" + id + "', 'toolbar=0,scrollbars=1,location=0,statusbar=1,menubar=0,resizable=1,width=500,height=300');");
}

function frame_up(){
	obj = parent.document.getElementById('inner')
	if (obj) { 
		obj.setAttribute('rows', '30%,70%', 0);
	}
}

function frame_dw(){
	obj = parent.document.getElementById('inner')
	if (obj) { 
		obj.setAttribute('rows', '70%,30%', 0);
	}
}

// Confirm History Delete
function confirm_click(url){
	response = confirm("Are you sure you want to delete this history?")
	if (response != 0)
	{
		location = url
	}
}
