Clazz.declarePackage("java.util.zip");
Clazz.load(["com.jcraft.jzlib.Deflater"], "java.util.zip.Deflater", null, function(){
var c$ = Clazz.declareType(java.util.zip, "Deflater", com.jcraft.jzlib.Deflater);
Clazz.makeConstructor(c$, 
function(compressionLevel){
if (compressionLevel != 2147483647) this.init(compressionLevel, 0, false);
}, "~N");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
