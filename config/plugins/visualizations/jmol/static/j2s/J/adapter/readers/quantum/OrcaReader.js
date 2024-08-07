Clazz.declarePackage("J.adapter.readers.quantum");
Clazz.load(["J.adapter.readers.quantum.MOReader"], "J.adapter.readers.quantum.OrcaReader", ["java.util.Hashtable", "JU.AU", "$.Lst", "$.PT", "J.adapter.readers.quantum.BasisFunctionReader", "J.quantum.QS", "JU.Escape", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.chargeTag = null;
this.atomCount = 0;
this.xyzBohr = false;
this.moModelSet = 0;
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum, "OrcaReader", J.adapter.readers.quantum.MOReader);
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
this.processAtoms();
return true;
}if (this.line.indexOf("ATOMIC CHARGES") >= 0 && this.line.indexOf(this.chargeTag) >= 0) {
this.processAtomicCharges();
return true;
}if (this.line.startsWith("Total Energy")) {
this.processEnergyLine();
return true;
}if (this.line.indexOf("BASIS SET IN INPUT FORMAT") == 0) {
this.processBasis();
}if (this.line.trim().equals("MOLECULAR ORBITALS")) {
this.processMolecularOrbitals();
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
Clazz.defineMethod(c$, "processAtoms", 
function(){
this.modelNumber++;
if (!this.doGetModel(this.modelNumber, null)) return;
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
Clazz.defineMethod(c$, "processBasis", 
function(){
if (this.shells != null) return;
this.shells =  new JU.Lst();
var gdata =  new JU.Lst();
var doSphericalF = true;
var doSphericalD = true;
this.calculationType = "5D7F";
var basisLines =  new java.util.Hashtable();
this.rd();
while (this.discardLinesUntilContains2("#", "-----").indexOf("#") >= 0) {
var element = this.line.substring(this.line.indexOf(":") + 1).trim();
var lines =  new JU.Lst();
basisLines.put(element, lines);
this.rd();
while (this.rd().indexOf("end;") < 0) {
if (this.line.length > 10) this.line = this.line.substring(4);
lines.addLast(this.getTokens());
}
}
for (var ac = 0; ac < this.atomCount; ac++) {
var lines = basisLines.get(this.asc.atoms[ac].elementSymbol);
for (var j = 0; j < lines.size(); ) {
var tokens = lines.get(j++);
this.shellCount++;
var slater =  Clazz.newIntArray (4, 0);
slater[0] = ac + 1;
var oType = tokens[0];
if (doSphericalF && oType.indexOf("F") >= 0 || doSphericalD && oType.indexOf("D") >= 0) slater[1] = J.adapter.readers.quantum.BasisFunctionReader.getQuantumShellTagIDSpherical(oType);
 else slater[1] = J.adapter.readers.quantum.BasisFunctionReader.getQuantumShellTagID(oType);
var nGaussians = this.parseIntStr(tokens[1]);
slater[2] = this.gaussianCount + 1;
slater[3] = nGaussians;
if (this.debugging) JU.Logger.debug("Slater " + this.shells.size() + " " + JU.Escape.eAI(slater));
this.shells.addLast(slater);
this.gaussianCount += nGaussians;
for (var i = 0; i < nGaussians; i++) {
tokens = lines.get(j++);
if (this.debugging) JU.Logger.debug("Gaussians " + (i + 1) + " " + JU.Escape.eAS(tokens, true));
gdata.addLast(tokens);
}
}
}
this.gaussians = JU.AU.newFloat2(this.gaussianCount);
for (var i = 0; i < this.gaussianCount; i++) {
var tokens = gdata.get(i);
this.gaussians[i] =  Clazz.newFloatArray (tokens.length, 0);
for (var j = 0; j < tokens.length; j++) this.gaussians[i][j] = this.parseFloatStr(tokens[j]);

}
JU.Logger.info(this.shellCount + " slater shells read");
JU.Logger.info(this.gaussianCount + " gaussian primitives read");
});
Clazz.defineMethod(c$, "processMolecularOrbitals", 
function(){
if (this.shells == null) return;
var mos = JU.AU.createArrayOfHashtable(6);
var data = JU.AU.createArrayOfArrayList(6);
var nThisLine = 0;
this.rd();
var labels =  new JU.Lst();
while (this.rd() != null && this.line.indexOf("----") < 0) {
if (this.line.length == 0) continue;
var tokens;
if (this.line.startsWith("          ")) {
this.addMODataOR(nThisLine, labels, data, mos);
labels.clear();
this.rd();
tokens = this.getTokens();
nThisLine = tokens.length;
for (var i = 0; i < nThisLine; i++) {
mos[i] =  new java.util.Hashtable();
data[i] =  new JU.Lst();
mos[i].put("energy", Float.$valueOf(tokens[i]));
}
this.rd();
tokens = this.getTokens();
for (var i = 0; i < nThisLine; i++) {
mos[i].put("occupancy", Float.$valueOf(tokens[i]));
}
this.rd();
continue;
}try {
tokens = this.getTokens();
var type = tokens[tokens.length - nThisLine - 1].substring(1).toUpperCase();
labels.addLast(type);
if (JU.PT.isDigit(type.charAt(0))) type = type.substring(1);
if (!J.quantum.QS.isQuantumBasisSupported(type.charAt(0)) && "XYZ".indexOf(type.charAt(0)) >= 0) type = (type.length == 2 ? "D" : "F") + type;
if (!J.quantum.QS.isQuantumBasisSupported(type.charAt(0))) continue;
tokens = J.adapter.smarter.AtomSetCollectionReader.getStrings(this.line.substring(this.line.length - 10 * nThisLine), nThisLine, 10);
for (var i = 0; i < nThisLine; i++) data[i].addLast(tokens[i]);

} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.error("Error reading Gaussian file Molecular Orbitals at line: " + this.line);
break;
} else {
throw e;
}
}
}
this.addMODataOR(nThisLine, labels, data, mos);
this.setMOData(this.moModelSet != this.asc.atomSetCount);
this.moModelSet = this.asc.atomSetCount;
});
Clazz.defineMethod(c$, "addMODataOR", 
function(nThisLine, labels, data, mos){
if (labels.size() == 0) return;
for (var i = 0; i < labels.size(); i++) {
if (labels.get(i).equals("PZ")) {
for (var j = 0; j < nThisLine; j++) {
var d = data[j];
var s = d.removeItemAt(i);
d.add(i + 2, s);
}
}}
this.addMOData(nThisLine, data, mos);
}, "~N,JU.Lst,~A,~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
