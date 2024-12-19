Clazz.declarePackage("JU");
Clazz.load(["JU.DataReader"], "JU.StringDataReader", ["java.io.StringReader"], function(){
var c$ = Clazz.declareType(JU, "StringDataReader", JU.DataReader);
Clazz.makeConstructor(c$, 
function(data){
Clazz.superConstructor(this, JU.StringDataReader, [ new java.io.StringReader(data)]);
}, "~S");
Clazz.overrideMethod(c$, "setData", 
function(data){
return  new JU.StringDataReader(data);
}, "~O");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
