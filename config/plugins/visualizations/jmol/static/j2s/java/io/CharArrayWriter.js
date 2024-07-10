Clazz.load(["java.io.Writer"], "java.io.CharArrayWriter", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.buf = null;
this.count = 0;
Clazz.instantialize(this, arguments);}, java.io, "CharArrayWriter", java.io.Writer);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, java.io.CharArrayWriter);
this.buf =  Clazz.newCharArray (32, '\0');
this.lock = this.buf;
});
Clazz.makeConstructor(c$, 
function(initialSize){
Clazz.superConstructor(this, java.io.CharArrayWriter);
if (initialSize >= 0) {
this.buf =  Clazz.newCharArray (initialSize, '\0');
this.lock = this.buf;
} else {
throw  new IllegalArgumentException(("K005e"));
}}, "~N");
Clazz.overrideMethod(c$, "close", 
function(){
});
Clazz.defineMethod(c$, "expand", 
function(i){
if (this.count + i <= this.buf.length) {
return;
}var newbuf =  Clazz.newCharArray (this.buf.length + (2 * i), '\0');
System.arraycopy(this.buf, 0, newbuf, 0, this.count);
this.buf = newbuf;
}, "~N");
Clazz.overrideMethod(c$, "flush", 
function(){
});
Clazz.defineMethod(c$, "reset", 
function(){
{
this.count = 0;
}});
Clazz.defineMethod(c$, "size", 
function(){
{
return this.count;
}});
Clazz.defineMethod(c$, "toCharArray", 
function(){
{
var result =  Clazz.newCharArray (this.count, '\0');
System.arraycopy(this.buf, 0, result, 0, this.count);
return result;
}});
Clazz.overrideMethod(c$, "toString", 
function(){
{
return  String.instantialize(this.buf, 0, this.count);
}});
Clazz.defineMethod(c$, "write", 
function(c, offset, len){
if (0 <= offset && offset <= c.length && 0 <= len && len <= c.length - offset) {
{
this.expand(len);
System.arraycopy(c, offset, this.buf, this.count, len);
this.count += len;
}} else {
throw  new IndexOutOfBoundsException();
}}, "~A,~N,~N");
Clazz.defineMethod(c$, "write", 
function(oneChar){
{
this.expand(1);
this.buf[this.count++] = String.fromCharCode(oneChar);
}}, "~N");
Clazz.defineMethod(c$, "write", 
function(str, offset, len){
if (str == null) {
throw  new NullPointerException(("K0047"));
}if (0 <= offset && offset <= str.length && 0 <= len && len <= str.length - offset) {
{
this.expand(len);
str.getChars(offset, offset + len, this.buf, this.count);
this.count += len;
}} else {
throw  new StringIndexOutOfBoundsException();
}}, "~S,~N,~N");
Clazz.defineMethod(c$, "writeTo", 
function(out){
{
out.write(this.buf, 0, this.count);
}}, "java.io.Writer");
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
