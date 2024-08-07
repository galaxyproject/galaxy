Clazz.load(["java.io.Writer"], "java.io.StringWriter", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.buf = null;
Clazz.instantialize(this, arguments);}, java.io, "StringWriter", java.io.Writer);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, java.io.StringWriter);
this.buf = "";
this.lock = this.buf;
});
Clazz.makeConstructor(c$, 
function(initialSize){
Clazz.superConstructor (this, java.io.StringWriter, []);
if (initialSize >= 0) {
this.buf = "";
this.lock = this.buf;
} else {
throw  new IllegalArgumentException();
}}, "~N");
Clazz.overrideMethod(c$, "close", 
function(){
});
Clazz.overrideMethod(c$, "flush", 
function(){
});
Clazz.overrideMethod(c$, "toString", 
function(){
{
return this.buf;
}});
Clazz.defineMethod(c$, "write", 
function(cbuf, offset, count){
if (0 <= offset && offset <= cbuf.length && 0 <= count && count <= cbuf.length - offset) {
{
this.buf +=  String.instantialize(cbuf, offset, count);
}} else {
throw  new IndexOutOfBoundsException();
}}, "~A,~N,~N");
Clazz.defineMethod(c$, "write", 
function(oneChar){
{
this.buf += String.fromCharCode(oneChar);
}}, "~N");
Clazz.defineMethod(c$, "write", 
function(str){
{
this.buf += str;
}}, "~S");
Clazz.defineMethod(c$, "write", 
function(str, offset, count){
var sub = str.substring(offset, offset + count);
{
this.buf += sub;
}}, "~S,~N,~N");
Clazz.defineMethod(c$, "append", 
function(c){
this.write(c.charCodeAt(0));
return this;
}, "~S");
Clazz.defineMethod(c$, "append", 
function(csq){
if (null == csq) {
this.append("null", 0, "null".length);
} else {
this.append(csq, 0, csq.length);
}return this;
}, "CharSequence");
Clazz.defineMethod(c$, "append", 
function(csq, start, end){
if (null == csq) {
csq = "null";
}var output = csq.subSequence(start, end).toString();
this.write(output, 0, output.length);
return this;
}, "CharSequence,~N,~N");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
