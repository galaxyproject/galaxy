Clazz.load(["java.io.Closeable", "$.Flushable"], "java.io.OutputStream", null, function(){
var c$ = Clazz.declareType(java.io, "OutputStream", null, [java.io.Closeable, java.io.Flushable]);
Clazz.defineMethod(c$, "write", 
function(b, off, len){
if (b == null) {
throw  new NullPointerException();
} else if ((off < 0) || (off > b.length) || (len < 0) || ((off + len) > b.length) || ((off + len) < 0)) {
throw  new IndexOutOfBoundsException();
} else if (len == 0) {
return;
}for (var i = 0; i < len; i++) {
this.writeByteAsInt(b[off + i]);
}
}, "~A,~N,~N");
Clazz.overrideMethod(c$, "flush", 
function(){
});
Clazz.overrideMethod(c$, "close", 
function(){
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
