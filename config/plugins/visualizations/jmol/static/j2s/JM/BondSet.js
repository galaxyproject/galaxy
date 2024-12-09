Clazz.declarePackage("JM");
Clazz.load(["JU.BS"], "JM.BondSet", ["JU.BSUtil"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.associatedAtoms = null;
Clazz.instantialize(this, arguments);}, JM, "BondSet", JU.BS);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JM.BondSet, []);
});
c$.newBS = Clazz.defineMethod(c$, "newBS", 
function(bs){
var b =  new JM.BondSet();
JU.BSUtil.copy2(bs, b);
return b;
}, "JU.BS");
Clazz.defineMethod(c$, "getAssociatedAtoms", 
function(ms){
if (this.associatedAtoms == null) this.associatedAtoms = ms.getAtomIndices(ms.getAtoms(1677721602, this));
return this.associatedAtoms;
}, "JM.ModelSet");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
