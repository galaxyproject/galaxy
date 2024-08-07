Clazz.declarePackage("J.inchi");
Clazz.load(["J.api.JmolInChI"], "J.inchi.InChIJS", ["JU.PT"], function(){
var c$ = Clazz.declareType(J.inchi, "InChIJS", null, J.api.JmolInChI);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "getInchi", 
function(vwr, atoms, molData, options){
if (atoms == null ? molData == null : atoms.isEmpty()) return "";
var ret = "";
try {
if (options == null) options = "";
options = JU.PT.rep(JU.PT.rep(options.$replace('-', ' '), "  ", " ").trim(), " ", " -").toLowerCase();
if (options.length > 0) options = "-" + options;
if (molData == null) molData = vwr.getModelExtract(atoms, false, false, "MOL");
if ((typeof(molData)=='string') && (molData).startsWith("InChI=")) {
{
ret = (Jmol.inchiToInchiKey ? Jmol.inchiToInchiKey(molData) : "");
}return ret;
}var haveKey = (options.indexOf("key") >= 0);
if (haveKey) {
options = options.$replace("inchikey", "key");
}if (options.indexOf("fixedh?") >= 0) {
var fxd = this.getInchi(vwr, atoms, molData, options.$replace('?', ' '));
options = JU.PT.rep(options, "-fixedh?", "");
if (haveKey) options = JU.PT.rep(options, "-key", "");
var inchi = this.getInchi(vwr, atoms, molData, options);
if (fxd != null && fxd.length > inchi.length) inchi = fxd;
return (haveKey ? this.getInchi(vwr, atoms, inchi, "-key") : inchi);
}{
ret = (Jmol.molfileToInChI ? Jmol.molfileToInChI(molData,
options) : "");
}} catch (e) {
{
e = (e.getMessage$ ? e.getMessage$() : e);
}System.err.println("InChIJS exception: " + e);
}
return ret;
}, "JV.Viewer,JU.BS,~O,~S");
{
var wasmPath = "/_WASM";
var es6Path = "/_ES6";
try {
{
var j2sPath = Jmol._applets.master._j2sFullPath;
//
Jmol.inchiPath = j2sPath + wasmPath;
//
var importPath = j2sPath + es6Path;
//
import(importPath + "/molfile-to-inchi.js");
}} catch (t) {
}
}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
