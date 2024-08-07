Clazz.declarePackage("J.adapter.readers.xtal");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.xtal.XcrysdenReader", ["JU.PT"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.nAtoms = 0;
this.animation = false;
this.unitCellData = null;
this.animationStep = 0;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xtal, "XcrysdenReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.prepareFields (c$, function(){
this.unitCellData =  Clazz.newFloatArray (9, 0);
});
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.setFractionalCoordinates(false);
this.doApplySymmetry = true;
});
Clazz.overrideMethod(c$, "checkLine", 
function(){
if (this.line.startsWith("ATOMS")) {
this.doApplySymmetry = false;
return this.readCoordinates();
}if (this.line.contains("ANIMSTEP")) {
this.animation = true;
} else if (this.line.contains("PRIMVEC")) {
this.readUnitCell();
} else if (this.line.contains("PRIMCOORD")) {
return this.readCoordinates();
}return true;
});
Clazz.defineMethod(c$, "readUnitCell", 
function(){
this.setSymmetry();
this.fillFloatArray(null, 0, this.unitCellData);
this.setUnitCell();
});
Clazz.defineMethod(c$, "setUnitCell", 
function(){
this.addExplicitLatticeVector(0, this.unitCellData, 0);
this.addExplicitLatticeVector(1, this.unitCellData, 3);
this.addExplicitLatticeVector(2, this.unitCellData, 6);
});
Clazz.defineMethod(c$, "setSymmetry", 
function(){
this.applySymmetryAndSetTrajectory();
this.asc.newAtomSet();
this.setSpaceGroupName("P1");
this.setFractionalCoordinates(false);
});
Clazz.defineMethod(c$, "readCoordinates", 
function(){
if (this.doApplySymmetry) {
var atomStr = JU.PT.getTokens(this.rd());
this.nAtoms = Integer.parseInt(atomStr[0]);
} else {
this.nAtoms = 2147483647;
}this.setFractionalCoordinates(false);
var counter = 0;
while (counter < this.nAtoms && this.rd() != null) {
var tokens = this.getTokens();
var an = JU.PT.parseInt(tokens[0]);
if (an < 0) {
break;
}this.line = null;
this.addAtomXYZSymName(tokens, 1, null, J.adapter.smarter.AtomSetCollectionReader.getElementSymbol(an));
counter++;
}
this.asc.setAtomSetName(this.animation ? "Structure " + (++this.animationStep) : "Initial coordinates");
if (this.line != null) this.setSymmetry();
return (this.line == null);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
