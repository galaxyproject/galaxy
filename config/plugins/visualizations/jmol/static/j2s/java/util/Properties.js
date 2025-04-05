Clazz.load(["java.util.Hashtable"], "java.util.Properties", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.builder = null;
this.defaults = null;
Clazz.instantialize(this, arguments);}, java.util, "Properties", java.util.Hashtable);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, java.util.Properties, []);
});
Clazz.makeConstructor(c$, 
function(properties){
this.initHT();
this.defaults = (properties == null ? null : properties);
}, "java.util.Properties");
Clazz.defineMethod(c$, "dumpString", 
function(buffer, string, key){
var i = 0;
if (!key && i < string.length && string.charAt(i) == ' ') {
buffer += ("\\ ");
i++;
}for (; i < string.length; i++) {
var ch = string.charAt(i);
switch ((ch).charCodeAt(0)) {
case 9:
buffer += ("\\t");
break;
case 10:
buffer += ("\\n");
break;
case 12:
buffer += ("\\f");
break;
case 13:
buffer += ("\\r");
break;
default:
if ("\\#!=:".indexOf(ch) >= 0 || (key && ch == ' ')) {
buffer += ('\\');
}if (ch >= ' ' && ch <= '~') {
buffer += (ch);
} else {
var hex = Integer.toHexString(ch.charCodeAt(0));
buffer += ("\\u");
for (var j = 0; j < 4 - hex.length; j++) {
buffer += ("0");
}
buffer += (hex);
}}
}
return buffer;
}, "~S,~S,~B");
Clazz.defineMethod(c$, "getProperty", 
function(name){
var result = this.get(name);
var property = (typeof(result)=='string') ? result : null;
if (property == null && this.defaults != null) {
property = this.defaults.getProperty(name);
}return property;
}, "~S");
Clazz.defineMethod(c$, "getProperty", 
function(name, defaultValue){
var result = this.get(name);
var property = (typeof(result)=='string') ? result : null;
if (property == null && this.defaults != null) {
property = this.defaults.getProperty(name);
}if (property == null) {
return defaultValue;
}return property;
}, "~S,~S");
Clazz.defineMethod(c$, "list", 
function(out){
if (out == null) {
throw  new NullPointerException();
}var buffer = "";
var keys = this.propertyNames();
while (keys.hasMoreElements()) {
var key = keys.nextElement();
buffer += (key);
buffer += ('=');
var property = this.get(key);
var def = this.defaults;
while (property == null) {
property = def.get(key);
def = def.defaults;
}
if (property.length > 40) {
buffer += (property.substring(0, 37));
buffer += ("...");
} else {
buffer += (property);
}out.println(buffer.toString());
buffer = "";
}
}, "java.io.PrintStream");
Clazz.defineMethod(c$, "list", 
function(writer){
if (writer == null) {
throw  new NullPointerException();
}var buffer = "";
var keys = this.propertyNames();
while (keys.hasMoreElements()) {
var key = keys.nextElement();
buffer += (key);
buffer += ('=');
var property = this.get(key);
var def = this.defaults;
while (property == null) {
property = def.get(key);
def = def.defaults;
}
if (property.length > 40) {
buffer += (property.substring(0, 37));
buffer += ("...");
} else {
buffer += (property);
}writer.println(buffer.toString());
buffer = "";
}
}, "java.io.PrintWriter");
Clazz.defineMethod(c$, "load", 
function($in){

}, "java.io.InputStream");
Clazz.defineMethod(c$, "propertyNames", 
function(){
if (this.defaults == null) {
return this.keys();
}var set =  new java.util.Hashtable(this.defaults.size() + this.size());
var keys = this.defaults.propertyNames();
while (keys.hasMoreElements()) {
set.put(keys.nextElement(), set);
}
keys = this.keys();
while (keys.hasMoreElements()) {
set.put(keys.nextElement(), set);
}
return set.keys();
});
Clazz.defineMethod(c$, "save", 
function(out, comment){
try {
this.store(out, comment);
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
} else {
throw e;
}
}
}, "java.io.OutputStream,~S");
Clazz.defineMethod(c$, "setProperty", 
function(name, value){
return this.put(name, value);
}, "~S,~S");
Clazz.defineMethod(c$, "store", 
function(out, comment){

}, "java.io.OutputStream,~S");
Clazz.defineMethod(c$, "loadFromXML", 
function($in){

}, "java.io.InputStream");
Clazz.defineMethod(c$, "storeToXML", 
function(os, comment){

}, "java.io.OutputStream,~S");
Clazz.defineMethod(c$, "storeToXML", 
function(os, comment, encoding){

}, "java.io.OutputStream,~S,~S");
Clazz.defineMethod(c$, "substitutePredefinedEntries", 
function(s){
return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\u0027", "&apos;").replaceAll("\"", "&quot;");
}, "~S");
c$.lineSeparator = null;
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
