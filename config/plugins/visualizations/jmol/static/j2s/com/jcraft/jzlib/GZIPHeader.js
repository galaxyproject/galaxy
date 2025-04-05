Clazz.declarePackage("com.jcraft.jzlib");
Clazz.load(null, "com.jcraft.jzlib.GZIPHeader", ["com.jcraft.jzlib.ZStream"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.text = false;
this.fhcrc = false;
this.time = 0;
this.xflags = 0;
this.os = 255;
this.extra = null;
this.name = null;
this.comment = null;
this.hcrc = 0;
this.crc = 0;
this.done = false;
this.mtime = 0;
Clazz.instantialize(this, arguments);}, com.jcraft.jzlib, "GZIPHeader", null, Cloneable);
Clazz.defineMethod(c$, "setModifiedTime", 
function(mtime){
this.mtime = mtime;
}, "~N");
Clazz.defineMethod(c$, "getModifiedTime", 
function(){
return this.mtime;
});
Clazz.defineMethod(c$, "setOS", 
function(os){
if ((0 <= os && os <= 13) || os == 255) this.os = os;
 else throw  new IllegalArgumentException("os: " + os);
}, "~N");
Clazz.defineMethod(c$, "getOS", 
function(){
return this.os;
});
Clazz.defineMethod(c$, "setName", 
function(name){
this.name = com.jcraft.jzlib.ZStream.getBytes(name);
}, "~S");
Clazz.defineMethod(c$, "getName", 
function(){
if (this.name == null) return "";
try {
return  String.instantialize(this.name, "ISO-8859-1");
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.UnsupportedEncodingException")){
throw  new InternalError(e.toString());
} else {
throw e;
}
}
});
Clazz.defineMethod(c$, "setComment", 
function(comment){
this.comment = com.jcraft.jzlib.ZStream.getBytes(comment);
}, "~S");
Clazz.defineMethod(c$, "getComment", 
function(){
if (this.comment == null) return "";
try {
return  String.instantialize(this.comment, "ISO-8859-1");
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.UnsupportedEncodingException")){
throw  new InternalError(e.toString());
} else {
throw e;
}
}
});
Clazz.defineMethod(c$, "setCRC", 
function(crc){
this.crc = crc;
}, "~N");
Clazz.defineMethod(c$, "getCRC", 
function(){
return this.crc;
});
Clazz.defineMethod(c$, "put", 
function(d){
var flag = 0;
if (this.text) {
flag |= 1;
}if (this.fhcrc) {
flag |= 2;
}if (this.extra != null) {
flag |= 4;
}if (this.name != null) {
flag |= 8;
}if (this.comment != null) {
flag |= 16;
}var xfl = 0;
if (d.level == 1) {
xfl |= 4;
} else if (d.level == 9) {
xfl |= 2;
}d.put_short(0x8b1f);
d.put_byteB(8);
d.put_byteB(flag);
d.put_byteB(this.mtime);
d.put_byteB((this.mtime >> 8));
d.put_byteB((this.mtime >> 16));
d.put_byteB((this.mtime >> 24));
d.put_byteB(xfl);
d.put_byteB(this.os);
if (this.extra != null) {
d.put_byteB(this.extra.length);
d.put_byteB((this.extra.length >> 8));
d.put_byte(this.extra, 0, this.extra.length);
}if (this.name != null) {
d.put_byte(this.name, 0, this.name.length);
d.put_byteB(0);
}if (this.comment != null) {
d.put_byte(this.comment, 0, this.comment.length);
d.put_byteB(0);
}}, "com.jcraft.jzlib.Deflate");
Clazz.defineMethod(c$, "clone", 
function(){
var gheader = Clazz.superCall(this, com.jcraft.jzlib.GZIPHeader, "clone", []);
var tmp;
if (gheader.extra != null) {
tmp =  Clazz.newByteArray (gheader.extra.length, 0);
System.arraycopy(gheader.extra, 0, tmp, 0, tmp.length);
gheader.extra = tmp;
}if (gheader.name != null) {
tmp =  Clazz.newByteArray (gheader.name.length, 0);
System.arraycopy(gheader.name, 0, tmp, 0, tmp.length);
gheader.name = tmp;
}if (gheader.comment != null) {
tmp =  Clazz.newByteArray (gheader.comment.length, 0);
System.arraycopy(gheader.comment, 0, tmp, 0, tmp.length);
gheader.comment = tmp;
}return gheader;
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
