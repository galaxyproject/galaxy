Clazz.declarePackage("JM");
Clazz.load(["JM.Bond"], "JM.HBond", ["JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.energy = 0;
Clazz.instantialize(this, arguments);}, JM, "HBond", JM.Bond);
Clazz.makeConstructor(c$, 
function(atom1, atom2, order, mad, colix, energy){
Clazz.superConstructor(this, JM.HBond, [atom1, atom2, order, mad, colix]);
this.energy = energy;
if (JU.Logger.debugging) JU.Logger.debug("HBond energy = " + energy + " #" + this.getIdentity());
}, "JM.Atom,JM.Atom,~N,~N,~N,~N");
Clazz.overrideMethod(c$, "getEnergy", 
function(){
return this.energy;
});
c$.calcEnergy = Clazz.defineMethod(c$, "calcEnergy", 
function(distAH, distCH, distCD, distAD){
var energy = Math.round(-27888.0 / distAH - -27888.0 / distAD + -27888.0 / distCD - -27888.0 / distCH);
return energy;
}, "~N,~N,~N,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
