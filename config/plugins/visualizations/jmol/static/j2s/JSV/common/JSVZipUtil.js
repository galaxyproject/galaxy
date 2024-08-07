Clazz.declarePackage("JSV.common");
Clazz.load(["JSV.api.JSVZipInterface"], "JSV.common.JSVZipUtil", ["java.util.zip.GZIPInputStream", "JSV.common.JSVZipFileSequentialReader"], function(){
var c$ = Clazz.declareType(JSV.common, "JSVZipUtil", null, JSV.api.JSVZipInterface);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "newGZIPInputStream", 
function(bis){
return  new java.util.zip.GZIPInputStream(bis, 512);
}, "java.io.InputStream");
Clazz.overrideMethod(c$, "newJSVZipFileSequentialReader", 
function($in, subFileList, startCode){
return  new JSV.common.JSVZipFileSequentialReader().set($in, subFileList, startCode);
}, "java.io.InputStream,~A,~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
