Clazz.load(["java.util.Enumeration"], "java.util.StringTokenizer", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.string = null;
this.delimiters = null;
this.returnDelimiters = false;
this.position = 0;
Clazz.instantialize(this, arguments);}, java.util, "StringTokenizer", null, java.util.Enumeration);
Clazz.makeConstructor(c$, 
function(string, delimiters, returnDelimiters){
{
switch (arguments.length) {
case 1: delimiters = " \t\n\r\f";
case 2: returnDelimiters = false;
}
}if (string == null) throw  new NullPointerException();
this.string = string;
this.delimiters = delimiters;
this.returnDelimiters = returnDelimiters;
this.position = 0;
}, "~S,~S,~B");
Clazz.defineMethod(c$, "countTokens", 
function(){
var count = 0;
var inToken = false;
for (var i = this.position, length = this.string.length; i < length; i++) {
if (this.delimiters.indexOf(this.string.charAt(i), 0) >= 0) {
if (this.returnDelimiters) count++;
if (inToken) {
count++;
inToken = false;
}} else {
inToken = true;
}}
if (inToken) count++;
return count;
});
Clazz.overrideMethod(c$, "hasMoreElements", 
function(){
return this.hasMoreTokens();
});
Clazz.defineMethod(c$, "hasMoreTokens", 
function(){
var length = this.string.length;
if (this.position < length) {
if (this.returnDelimiters) return true;
for (var i = this.position; i < length; i++) if (this.delimiters.indexOf(this.string.charAt(i), 0) == -1) return true;

}return false;
});
Clazz.overrideMethod(c$, "nextElement", 
function(){
return this.nextToken();
});
Clazz.defineMethod(c$, "nextToken", 
function(){
{
(arguments.length == 1) && (this.delimiters = arguments[0]);
}var i = this.position;
var length = this.string.length;
if (i < length) {
if (this.returnDelimiters) {
if (this.delimiters.indexOf(this.string.charAt(this.position), 0) >= 0) return String.valueOf(this.string.charAt(this.position++));
for (this.position++; this.position < length; this.position++) if (this.delimiters.indexOf(this.string.charAt(this.position), 0) >= 0) return this.string.substring(i, this.position);

return this.string.substring(i);
}while (i < length && this.delimiters.indexOf(this.string.charAt(i), 0) >= 0) i++;

this.position = i;
if (i < length) {
for (this.position++; this.position < length; this.position++) if (this.delimiters.indexOf(this.string.charAt(this.position), 0) >= 0) return this.string.substring(i, this.position);

return this.string.substring(i);
}}throw  new java.util.NoSuchElementException();
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
