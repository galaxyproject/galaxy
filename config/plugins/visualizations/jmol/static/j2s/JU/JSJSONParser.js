Clazz.declarePackage("JU");
Clazz.load(null, "JU.JSJSONParser", ["java.util.Hashtable", "JU.JSONException", "$.Lst", "$.SB"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.str = null;
this.index = 0;
this.len = 0;
this.asHashTable = false;
Clazz.instantialize(this, arguments);}, JU, "JSJSONParser", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "parseMap", 
function(str, asHashTable){
this.index = 0;
this.asHashTable = asHashTable;
this.str = str;
this.len = str.length;
if (this.getChar() != '{') return null;
this.returnChar();
return this.getValue(false);
}, "~S,~B");
Clazz.defineMethod(c$, "parse", 
function(str, asHashTable){
this.index = 0;
this.asHashTable = asHashTable;
this.str = str;
this.len = str.length;
return this.getValue(false);
}, "~S,~B");
Clazz.defineMethod(c$, "next", 
function(){
return (this.index < this.len ? this.str.charAt(this.index++) : '\0');
});
Clazz.defineMethod(c$, "returnChar", 
function(){
this.index--;
});
Clazz.defineMethod(c$, "getChar", 
function(){
for (; ; ) {
var c = this.next();
if (c.charCodeAt(0) == 0 || c > ' ') {
return c;
}}
});
Clazz.defineMethod(c$, "getValue", 
function(isKey){
var i = this.index;
var c = this.getChar();
switch ((c).charCodeAt(0)) {
case 0:
return null;
case 34:
case 39:
return this.getString(c);
case 123:
if (!isKey) return this.getObject();
c = String.fromCharCode( 0);
break;
case 91:
if (!isKey) return this.getArray();
c = String.fromCharCode( 0);
break;
default:
this.returnChar();
while (c >= ' ' && "[,]{:}'\"".indexOf(c) < 0) c = this.next();

this.returnChar();
if (isKey && c != ':') c = String.fromCharCode( 0);
break;
}
if (isKey && c.charCodeAt(0) == 0) throw  new JU.JSONException("invalid key");
var string = this.str.substring(i, this.index).trim();
if (!isKey) {
if (string.equals("true")) {
return Boolean.TRUE;
}if (string.equals("false")) {
return Boolean.FALSE;
}if (string.equals("null")) {
return (this.asHashTable ? string : null);
}}c = string.charAt(0);
if (c >= '0' && c <= '9' || c == '-') try {
if (string.indexOf('.') < 0 && string.indexOf('e') < 0 && string.indexOf('E') < 0) return  new Integer(string);
var d = Float.$valueOf(string);
if (!d.isInfinite() && !d.isNaN()) return d;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
System.out.println("JSON parser cannot parse " + string);
throw  new JU.JSONException("invalid value");
}, "~B");
Clazz.defineMethod(c$, "getString", 
function(quote){
var c;
var sb = null;
var i0 = this.index;
for (; ; ) {
var i1 = this.index;
switch ((c = this.next()).charCodeAt(0)) {
case 0:
case 10:
case 13:
throw this.syntaxError("Unterminated string");
case 92:
switch ((c = this.next()).charCodeAt(0)) {
case 34:
case 39:
case 92:
case 47:
break;
case 98:
c = '\b';
break;
case 116:
c = '\t';
break;
case 110:
c = '\n';
break;
case 102:
c = '\f';
break;
case 114:
c = '\r';
break;
case 117:
var i = this.index;
this.index += 4;
try {
c = String.fromCharCode(Integer.parseInt(this.str.substring(i, this.index), 16));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
throw this.syntaxError("Substring bounds error");
} else {
throw e;
}
}
break;
default:
throw this.syntaxError("Illegal escape.");
}
break;
default:
if (c == quote) return (sb == null ? this.str.substring(i0, i1) : sb.toString());
break;
}
if (this.index > i1 + 1) {
if (sb == null) {
sb =  new JU.SB();
sb.append(this.str.substring(i0, i1));
}}if (sb != null) sb.appendC(c);
}
}, "~S");
Clazz.defineMethod(c$, "getObject", 
function(){
var map = (this.asHashTable ?  new java.util.Hashtable() :  new java.util.HashMap());
var key = null;
switch ((this.getChar()).charCodeAt(0)) {
case 125:
return map;
case 0:
throw  new JU.JSONException("invalid object");
}
this.returnChar();
var isKey = false;
for (; ; ) {
if ((isKey = !isKey) == true) key = this.getValue(true).toString();
 else map.put(key, this.getValue(false));
switch ((this.getChar()).charCodeAt(0)) {
case 125:
return map;
case 58:
if (isKey) continue;
isKey = true;
case 44:
if (!isKey) continue;
default:
throw this.syntaxError("Expected ',' or ':' or '}'");
}
}
});
Clazz.defineMethod(c$, "getArray", 
function(){
var l =  new JU.Lst();
switch ((this.getChar()).charCodeAt(0)) {
case 93:
return l;
case 0:
throw  new JU.JSONException("invalid array");
}
this.returnChar();
var isNull = false;
for (; ; ) {
if (isNull) {
l.addLast(null);
isNull = false;
} else {
l.addLast(this.getValue(false));
}switch ((this.getChar()).charCodeAt(0)) {
case 44:
switch ((this.getChar()).charCodeAt(0)) {
case 93:
return l;
case 44:
isNull = true;
default:
this.returnChar();
}
continue;
case 93:
return l;
default:
throw this.syntaxError("Expected ',' or ']'");
}
}
});
Clazz.defineMethod(c$, "syntaxError", 
function(message){
return  new JU.JSONException(message + " for " + this.str.substring(0, Math.min(this.index, this.len)));
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
