var cookie_name = "genetrack_ui"
var now = new Date();
now.setTime(now.getTime() + 365 * 24 * 60 * 60 * 1000);

// this toggles between none and block
function toggle(name){
	var elem = get(name)
	if (elem) {
		if (elem.style.display=="none"){
			elem.style.display="block"
			setCookie(cookie_name, name, now)
		} else {
			elem.style.display="none"
			setCookie(cookie_name, '', now)
		}
		
	}
}

function main(){
	//executed upon main body load
	var value = getCookie(cookie_name);
	toggle(	value )		
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
