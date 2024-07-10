Clazz.declarePackage("java.util.zip");
Clazz.load(["com.jcraft.jzlib.DeflaterOutputStream"], "java.util.zip.DeflaterOutputStream", null, function(){
var c$ = Clazz.declareType(java.util.zip, "DeflaterOutputStream", com.jcraft.jzlib.DeflaterOutputStream);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, java.util.zip.DeflaterOutputStream, []);
});
Clazz.makeConstructor(c$, 
function(bos, deflater){
Clazz.superConstructor (this, java.util.zip.DeflaterOutputStream, []);
this.setDOS(bos, deflater);
}, "java.io.ByteArrayOutputStream,java.util.zip.Deflater");
Clazz.defineMethod(c$, "setDOS", 
function(out, deflater){
this.jzSetDOS(out, deflater, 0, true);
}, "java.io.OutputStream,java.util.zip.Deflater");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
