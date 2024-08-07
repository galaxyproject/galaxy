Clazz.declarePackage("java.util.zip");
Clazz.load(["com.jcraft.jzlib.InflaterInputStream"], "java.util.zip.InflaterInputStream", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.inf = null;
Clazz.instantialize(this, arguments);}, java.util.zip, "InflaterInputStream", com.jcraft.jzlib.InflaterInputStream);
Clazz.makeConstructor(c$, 
function($in, inflater, size){
Clazz.superConstructor(this, java.util.zip.InflaterInputStream, [$in, inflater, size, true]);
this.inf = inflater;
}, "java.io.InputStream,java.util.zip.Inflater,~N");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
