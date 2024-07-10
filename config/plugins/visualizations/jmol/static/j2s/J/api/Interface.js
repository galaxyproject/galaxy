Clazz.declarePackage("J.api");
Clazz.load(null, "J.api.Interface", ["JU.Logger"], function(){
var c$ = Clazz.declareType(J.api, "Interface", null);
c$.getInterface = Clazz.defineMethod(c$, "getInterface", 
function(name, vwr, state){
try {
var x = Clazz._4Name(name);
return (x == null ? null : x.newInstance());
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.error("Interface.java Error creating instance for " + name + ": \n" + e);
return null;
} else {
throw e;
}
}
}, "~S,JV.Viewer,~S");
c$.getOption = Clazz.defineMethod(c$, "getOption", 
function(className, vwr, state){
return J.api.Interface.getInterface("J." + className, vwr, state);
}, "~S,JV.Viewer,~S");
c$.getUtil = Clazz.defineMethod(c$, "getUtil", 
function(name, vwr, state){
return J.api.Interface.getInterface("JU." + name, vwr, state);
}, "~S,JV.Viewer,~S");
c$.getSymmetry = Clazz.defineMethod(c$, "getSymmetry", 
function(vwr, state){
return J.api.Interface.getInterface("JS.Symmetry", vwr, state);
}, "JV.Viewer,~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
