Clazz.load(["java.io.Closeable"], "java.io.InputStream", null, function(){
var c$ = Clazz.declareType(java.io, "InputStream", null, java.io.Closeable);
Clazz.defineMethod(c$, "read", 
function(b, off, len){
if (b == null) {
throw  new NullPointerException();
} else if (off < 0 || len < 0 || len > b.length - off) {
throw  new IndexOutOfBoundsException();
} else if (len == 0) {
return 0;
}var c = this.readByteAsInt();
if (c == -1) {
return -1;
}b[off] = c;
var i = 1;
try {
for (; i < len; i++) {
c = this.readByteAsInt();
if (c == -1) {
break;
}b[off + i] = c;
}
} catch (ee) {
if (Clazz.exceptionOf(ee,"java.io.IOException")){
} else {
throw ee;
}
}
return i;
}, "~A,~N,~N");
Clazz.defineMethod(c$, "skip", 
function(n){
var remaining = n;
var nr;
if (java.io.InputStream.skipBuffer == null) java.io.InputStream.skipBuffer =  Clazz.newByteArray (2048, 0);
var localSkipBuffer = java.io.InputStream.skipBuffer;
if (n <= 0) {
return 0;
}while (remaining > 0) {
nr = this.read(localSkipBuffer, 0, Math.min(2048, remaining));
if (nr < 0) {
break;
}remaining -= nr;
}
return n - remaining;
}, "~N");
Clazz.defineMethod(c$, "available", 
function(){
return 0;
});
Clazz.overrideMethod(c$, "close", 
function(){
});
Clazz.defineMethod(c$, "mark", 
function(readlimit){
}, "~N");
Clazz.defineMethod(c$, "reset", 
function(){
throw  new java.io.IOException("mark/reset not supported");
});
Clazz.defineMethod(c$, "markSupported", 
function(){
return false;
});
Clazz.defineMethod(c$, "resetStream", 
function(){
});
c$.skipBuffer = null;
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
