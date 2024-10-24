Clazz.load(["java.io.Closeable"], "java.io.Reader", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.lock = null;
this.skipBuffer = String.fromCharCode(null);
Clazz.instantialize(this, arguments);}, java.io, "Reader", null, java.io.Closeable);
Clazz.makeConstructor(c$, 
function(lock){
if (lock == null) {
throw  new NullPointerException();
}this.lock = lock;
}, "~O");
Clazz.defineMethod(c$, "skip", 
function(n){
if (n < 0) throw  new IllegalArgumentException("skip value is negative");
var nn = Math.min(n, 8192);
{
if ((this.skipBuffer == null) || (this.skipBuffer.length < nn)) this.skipBuffer =  Clazz.newCharArray (nn, '\0');
var r = n;
while (r > 0) {
var nc = this.read(this.skipBuffer, 0, Math.min(r, nn));
if (nc == -1) break;
r -= nc;
}
return n - r;
}}, "~N");
Clazz.defineMethod(c$, "ready", 
function(){
return false;
});
Clazz.defineMethod(c$, "markSupported", 
function(){
return false;
});
Clazz.defineMethod(c$, "mark", 
function(readAheadLimit){
throw  new java.io.IOException("mark() not supported");
}, "~N");
Clazz.defineMethod(c$, "reset", 
function(){
throw  new java.io.IOException("reset() not supported");
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
