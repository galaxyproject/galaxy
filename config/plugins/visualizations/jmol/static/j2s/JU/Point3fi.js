Clazz.declarePackage("JU");
Clazz.load(["JU.P3"], "JU.Point3fi", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.mi = -1;
this.i = 0;
this.sX = 0;
this.sY = 0;
this.sZ = 0;
this.sD = -1;
Clazz.instantialize(this, arguments);}, JU, "Point3fi", JU.P3, Cloneable);
Clazz.defineMethod(c$, "copy", 
function(){
try {
return this.clone();
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
