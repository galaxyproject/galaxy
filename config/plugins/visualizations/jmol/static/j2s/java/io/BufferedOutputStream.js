Clazz.load(["java.io.FilterOutputStream"], "java.io.BufferedOutputStream", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.buf = null;
this.count = 0;
Clazz.instantialize(this, arguments);}, java.io, "BufferedOutputStream", java.io.FilterOutputStream);
Clazz.makeConstructor(c$, 
function(out){
Clazz.superConstructor (this, java.io.BufferedOutputStream, []);
this.jzSetFOS(out);
this.buf =  Clazz.newByteArray (8192, 0);
}, "java.io.OutputStream");
Clazz.makeConstructor(c$, 
function(out, size){
Clazz.superConstructor (this, java.io.BufferedOutputStream, []);
this.jzSetFOS(out);
if (size <= 0) {
throw  new IllegalArgumentException(("K0058"));
}this.buf =  Clazz.newByteArray (size, 0);
}, "java.io.OutputStream,~N");
Clazz.overrideMethod(c$, "flush", 
function(){
if (this.count > 0) {
this.out.write(this.buf, 0, this.count);
}this.count = 0;
this.out.flush();
});
Clazz.defineMethod(c$, "write", 
function(buffer, offset, length){
if (buffer == null) {
throw  new NullPointerException(("K0047"));
}if (offset < 0 || offset > buffer.length - length || length < 0) {
throw  new ArrayIndexOutOfBoundsException(("K002f"));
}if (this.count == 0 && length >= this.buf.length) {
this.out.write(buffer, offset, length);
return;
}var available = this.buf.length - this.count;
if (length < available) {
available = length;
}if (available > 0) {
System.arraycopy(buffer, offset, this.buf, this.count, available);
this.count += available;
}if (this.count == this.buf.length) {
this.out.write(this.buf, 0, this.buf.length);
this.count = 0;
if (length > available) {
offset += available;
available = length - available;
if (available >= this.buf.length) {
this.out.write(buffer, offset, available);
} else {
System.arraycopy(buffer, offset, this.buf, this.count, available);
this.count += available;
}}}}, "~A,~N,~N");
Clazz.defineMethod(c$, "write", 
function(oneByte){
if (this.count == this.buf.length) {
this.out.write(this.buf, 0, this.count);
this.count = 0;
}this.buf[this.count++] = oneByte;
}, "~N");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
