Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.AtomShape"], "J.shape.Halos", ["JU.BSUtil", "$.C"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.colixSelection = 2;
this.bsHighlight = null;
this.colixHighlight = 10;
Clazz.instantialize(this, arguments);}, J.shape, "Halos", J.shape.AtomShape);
Clazz.defineMethod(c$, "initState", 
function(){
this.translucentAllowed = false;
});
Clazz.overrideMethod(c$, "setProperty", 
function(propertyName, value, bs){
if ("translucency" === propertyName) return;
if ("argbSelection" === propertyName) {
this.colixSelection = JU.C.getColix((value).intValue());
return;
}if ("argbHighlight" === propertyName) {
this.colixHighlight = JU.C.getColix((value).intValue());
return;
}if ("highlight" === propertyName) {
this.bsHighlight = value;
return;
}if (propertyName === "deleteModelAtoms") {
JU.BSUtil.deleteBits(this.bsHighlight, bs);
}this.setPropAS(propertyName, value, bs);
}, "~S,~O,JU.BS");
Clazz.overrideMethod(c$, "setModelVisibilityFlags", 
function(bs){
var bsSelected = (this.vwr.getSelectionHalosEnabled() ? this.vwr.bsA() : null);
var atoms = this.ms.at;
for (var i = this.ms.ac; --i >= 0; ) {
if (atoms[i] != null) atoms[i].setShapeVisibility(this.vf, bsSelected != null && bsSelected.get(i) || this.mads != null && this.mads[i] != 0);
}
}, "JU.BS");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
