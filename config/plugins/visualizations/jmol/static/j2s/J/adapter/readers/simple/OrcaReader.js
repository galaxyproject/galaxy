Clazz.declarePackage("J.adapter.readers.simple");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.simple.OrcaReader", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.chargeTag = null;
this.atomCount = 0;
this.xyzBohr = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.simple, "OrcaReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.chargeTag = (this.checkAndRemoveFilterKey("CHARGE=LOW") ? "LOEW" : "MULL");
});
Clazz.overrideMethod(c$, "checkLine", 
function(){
if (this.line.startsWith("! Bohrs")) {
this.xyzBohr = true;
return true;
}if (this.line.startsWith("* xyz") || this.line.startsWith("*xyz")) {
this.processInputFile();
this.continuing = false;
return false;
}if (this.line.indexOf("CARTESIAN COORDINATES (ANG") >= 0) {
this.processCoordinates();
return true;
}if (this.line.indexOf("ATOMIC CHARGES") >= 0 && this.line.indexOf(this.chargeTag) >= 0) {
this.processAtomicCharges();
return true;
}if (this.line.startsWith("Total Energy")) {
this.processEnergyLine();
return true;
}return true;
});
Clazz.defineMethod(c$, "processEnergyLine", 
function(){
var tokens = this.getTokens();
this.asc.setAtomSetEnergy(tokens[3], Float.parseFloat(tokens[3]));
});
Clazz.defineMethod(c$, "processInputFile", 
function(){
while (this.rd() != null) {
while (this.line.trim().length == 0 || this.line.startsWith("#")) {
this.rd();
}
if (this.line.indexOf("*") >= 0) break;
var tokens = this.getTokens();
var a = this.addAtomXYZSymName(tokens, 1, tokens[0], null);
if (this.xyzBohr) a.scale(0.5291772);
}
});
Clazz.defineMethod(c$, "processCoordinates", 
function(){
this.asc.newAtomSet();
this.baseAtomIndex = this.asc.ac;
this.rd();
while (this.rd() != null) {
var tokens = this.getTokens();
if (tokens.length != 4) break;
this.addAtomXYZSymName(tokens, 1, tokens[0], null);
}
if (this.baseAtomIndex == 0) this.atomCount = this.asc.ac;
});
Clazz.defineMethod(c$, "processAtomicCharges", 
function(){
this.rd();
for (var i = 0; i < this.atomCount; i++) {
this.rd();
this.asc.atoms[i + this.baseAtomIndex].partialCharge = Float.parseFloat(this.line.substring(this.line.indexOf(":") + 1));
}
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
