Clazz.declarePackage("J.adapter.readers.quantum");
Clazz.load(["J.adapter.readers.quantum.SlaterReader"], "J.adapter.readers.quantum.AdfReader", ["java.util.Hashtable", "JU.AU", "$.Lst", "$.PT", "J.api.JmolAdapter", "J.quantum.SlaterData", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.htSymmetries = null;
this.vSymmetries = null;
this.energy = null;
this.nXX = 0;
this.symLine = null;
this.isADF = false;
this.lastModel = -1;
if (!Clazz.isClassDefined("J.adapter.readers.quantum.AdfReader.SymmetryData")) {
J.adapter.readers.quantum.AdfReader.$AdfReader$SymmetryData$ ();
}
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum, "AdfReader", J.adapter.readers.quantum.SlaterReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.isADF = true;
});
Clazz.overrideMethod(c$, "checkLine", 
function(){
if (this.line.indexOf("Irreducible Representations, including subspecies") >= 0) {
this.readSymmetries();
return true;
}if (this.line.indexOf("S F O s  ***  (Symmetrized Fragment Orbitals)  ***") >= 0) {
this.readSlaterBasis();
return true;
}if (this.line.indexOf("current energy") >= 0) {
var tokens = JU.PT.getTokens(this.line);
this.energy = tokens[2];
return true;
}if (this.isADF ? this.line.indexOf(" Coordinates (Cartesian)") >= 0 || this.line.indexOf("G E O M E T R Y  ***") >= 0 : this.line.indexOf("Formula:") >= 0) {
if (!this.doGetModel(++this.modelNumber, null)) return this.checkLastModel();
this.readCoordinates();
return true;
}if (this.line.startsWith("Atomic charges")) {
this.readCharges();
return true;
}if (this.line.indexOf(" ======  Eigenvectors (rows) in BAS representation") >= 0) {
if (this.doReadMolecularOrbitals) this.readMolecularOrbitals(JU.PT.getTokens(this.symLine)[1]);
return true;
}if (!this.doProcessLines) {
return true;
}if (this.line.indexOf("Total Bonding Energy:") >= 0) {
var tokens = JU.PT.getTokens(this.line.substring(this.line.indexOf("Total Bonding Energy:")));
var bondingEnergy = tokens[3];
this.asc.setModelInfoForSet("bondingEnergy", Double.$valueOf(bondingEnergy), this.asc.iSet);
this.asc.setAtomSetModelProperty("bondingEnergy", bondingEnergy);
return true;
}if (this.line.indexOf(this.isADF ? "Vibrations" : "Normal Modes") >= 0) {
this.readFrequencies();
return true;
}if (this.line.indexOf(" === ") >= 0) {
this.symLine = this.line;
return true;
}if (this.line.indexOf(" ======  Eigenvectors (rows) in BAS representation") >= 0) {
this.readMolecularOrbitals(JU.PT.getTokens(this.symLine)[1]);
return true;
}if (!this.isADF && this.line.startsWith(" Old frequency:")) {
this.readOldFrequency();
return true;
}return true;
});
Clazz.defineMethod(c$, "readOldFrequency", 
function(){
var tokens = JU.PT.getTokens(this.line);
var frqOld = JU.PT.parseFloat(tokens[2].$replace(",", ""));
var frqNew = JU.PT.parseFloat(tokens[4]);
var finalModel = this.modelNumber + this.vibrationNumber;
for (var i = this.modelNumber; i < finalModel; i++) {
var cname = this.asc.getAtomSetAuxiliaryInfoValue(i, "name");
var frqPrev = cname.$replace(" cm^-1", "");
var frqOldFmt = JU.PT.formatStringF("%.3f", "f", frqOld);
if (frqOldFmt.equals(frqPrev)) {
var frqNewFmt = JU.PT.formatStringF("%.3f", "f", frqNew);
cname += " (now " + frqNewFmt + " cm^-1)";
this.asc.setAtomSetModelPropertyForSet("name", cname, i);
this.asc.setAtomSetModelPropertyForSet("modelName", cname, i);
break;
}}
});
Clazz.defineMethod(c$, "readCoordinates", 
function(){
var isGeometry = (!this.isADF || this.line.indexOf("G E O M E T R Y") >= 0);
this.asc.newAtomSet();
this.lastModel = this.asc.iSet;
var modelName = "model " + String.valueOf(this.modelNumber);
if (this.energy != null) modelName = modelName + " e=" + this.energy + " a.u.";
this.asc.setAtomSetName(modelName);
var startGeomDelimiter = (this.isADF ? "----" : "Index Symbol");
var pt0 = (isGeometry ? 2 : 5);
this.discardLinesUntilContains(startGeomDelimiter);
this.nXX = 0;
var tokens;
while (this.rd() != null && !this.line.startsWith(" -----")) {
tokens = this.getTokens();
if (tokens.length < 5) break;
var symbol = tokens[1];
var name = null;
if (symbol.indexOf(".") >= 0) {
name = symbol;
symbol = symbol.substring(0, symbol.indexOf("."));
}if (J.api.JmolAdapter.getElementNumber(symbol) < 1) this.nXX++;
 else this.addAtomXYZSymName(tokens, pt0, symbol, name);
}
});
Clazz.defineMethod(c$, "readFrequencies", 
function(){
this.rd();
if (!this.isADF) {
this.discardLinesUntilContains("Number of removed rigid");
}while (this.rd() != null) {
this.discardLinesUntilContains2(this.isADF ? "." : "Mode:", "====");
if (this.line == null || this.line.indexOf(".") < 0) return;
var freqdata = this.getTokens();
this.rd();
var iAtom0 = this.asc.ac;
var ac = this.asc.getLastAtomSetAtomCount();
var frequencyCount = (this.isADF ? freqdata.length : 1);
var ignore =  Clazz.newBooleanArray(frequencyCount, false);
for (var i = 0; i < frequencyCount; ++i) {
ignore[i] = !this.doGetVibration(++this.vibrationNumber);
if (ignore[i]) continue;
var frequency = freqdata[this.isADF ? i : 4];
this.asc.cloneLastAtomSet();
this.asc.setAtomSetFrequency(this.vibrationNumber, null, null, frequency, null);
}
this.readLines(this.nXX);
this.fillFrequencyData(iAtom0, ac, ac, ignore, true, 0, 0, null, 0, null);
}
});
Clazz.defineMethod(c$, "readSymmetries", 
function(){
this.vSymmetries =  new JU.Lst();
this.htSymmetries =  new java.util.Hashtable();
this.rd();
var index = 0;
var syms = "";
while (this.rd() != null && this.line.length > 1) syms += this.line;

var tokens = JU.PT.getTokens(syms);
for (var i = 0; i < tokens.length; i++) {
var sd = Clazz.innerTypeInstance(J.adapter.readers.quantum.AdfReader.SymmetryData, this, null, index++, tokens[i]);
this.htSymmetries.put(tokens[i], sd);
this.vSymmetries.addLast(sd);
}
});
Clazz.defineMethod(c$, "readSlaterBasis", 
function(){
if (this.vSymmetries == null) return;
var nBF = 0;
for (var i = 0; i < this.vSymmetries.size(); i++) {
var sd = this.vSymmetries.get(i);
JU.Logger.info(sd.sym);
this.discardLinesUntilContains("=== " + sd.sym + " ===");
if (this.line == null) {
JU.Logger.error("Symmetry slater basis section not found: " + sd.sym);
return;
}sd.nSFO = this.parseIntAt(this.rd(), 15);
sd.nBF = this.parseIntAt(this.rd(), 75);
var funcList = "";
while (this.rd() != null && this.line.length > 1) funcList += this.line;

var tokens = JU.PT.getTokens(funcList);
if (tokens.length != sd.nBF) return;
sd.basisFunctions =  Clazz.newIntArray (tokens.length, 0);
for (var j = tokens.length; --j >= 0; ) {
var n = this.parseIntStr(tokens[j]);
if (n > nBF) nBF = n;
sd.basisFunctions[j] = n - 1;
}
}
this.slaterArray =  new Array(nBF);
this.discardLinesUntilContains("(power of)");
this.readLines(2);
while (this.rd() != null && this.line.length > 3 && this.line.charAt(3) == ' ') {
var data = this.line;
while (this.rd().indexOf("---") < 0) data += this.line;

var tokens = JU.PT.getTokens(data);
var nAtoms = tokens.length - 1;
var atomList =  Clazz.newIntArray (nAtoms, 0);
for (var i = 1; i <= nAtoms; i++) atomList[i - 1] = this.parseIntStr(tokens[i]) - 1;

this.rd();
while (this.line.length >= 10) {
data = this.line;
while (this.rd().length > 35 && this.line.substring(0, 35).trim().length == 0) data += this.line;

tokens = JU.PT.getTokens(data);
var isCore = tokens[0].equals("Core");
var pt = (isCore ? 1 : 0);
var x = this.parseIntStr(tokens[pt++]);
var y = this.parseIntStr(tokens[pt++]);
var z = this.parseIntStr(tokens[pt++]);
var r = this.parseIntStr(tokens[pt++]);
var zeta = this.parseFloatStr(tokens[pt++]);
for (var i = 0; i < nAtoms; i++) {
var ptBF = this.parseIntStr(tokens[pt++]) - 1;
this.slaterArray[ptBF] =  new J.quantum.SlaterData(atomList[i], x, y, z, r, zeta, 1);
this.slaterArray[ptBF].index = ptBF;
}
}
}
});
Clazz.defineMethod(c$, "readMolecularOrbitals", 
function(sym){
var sd = this.htSymmetries.get(sym);
if (sd == null) return;
var ptSym = sd.index;
var isLast = (ptSym == this.vSymmetries.size() - 1);
var n = 0;
var nBF = this.slaterArray.length;
sd.coefs =  Clazz.newFloatArray (sd.nSFO, nBF, 0);
while (n < sd.nBF) {
this.rd();
var nLine = JU.PT.getTokens(this.rd()).length;
this.rd();
sd.mos = JU.AU.createArrayOfHashtable(sd.nSFO);
var data =  new Array(sd.nSFO);
this.fillDataBlock(data, 0);
for (var j = 1; j < nLine; j++) {
var pt = sd.basisFunctions[n++];
for (var i = 0; i < sd.nSFO; i++) sd.coefs[i][pt] = this.parseFloatStr(data[i][j]);

}
}
for (var i = 0; i < sd.nSFO; i++) {
var mo =  new java.util.Hashtable();
mo.put("coefficients", sd.coefs[i]);
mo.put("id", sym + " " + (i + 1));
sd.mos[i] = mo;
}
if (!isLast) return;
var nSym = this.htSymmetries.size();
this.discardLinesUntilContains(nSym == 1 ? "Orbital Energies, per Irrep" : "Orbital Energies, all Irreps");
this.readLines(4);
var pt = (nSym == 1 ? 0 : 1);
if (nSym == 1) sym = this.rd().trim();
while (this.rd() != null && this.line.length > 10) {
this.line = this.line.$replace('(', ' ').$replace(')', ' ');
var tokens = this.getTokens();
var len = tokens.length;
if (nSym > 1) sym = tokens[0];
var moPt = this.parseIntStr(tokens[pt]);
var occ = this.parseFloatStr(tokens[len - 4 + pt]);
var energy = this.parseFloatStr(tokens[len - 2 + pt]);
this.addMo(sym, moPt, occ, energy);
}
var iAtom0 = this.asc.getLastAtomSetAtomIndex();
for (var i = 0; i < nBF; i++) this.slaterArray[i].atomNo += iAtom0 + 1;

this.setSlaters(true);
this.sortOrbitals();
this.setMOs("eV");
}, "~S");
Clazz.defineMethod(c$, "addMo", 
function(sym, moPt, occ, energy){
var sd = this.htSymmetries.get(sym);
if (sd == null) {
for (var entry, $entry = this.htSymmetries.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) if (entry.getKey().startsWith(sym + ":")) {
sd = entry.getValue();
break;
}
if (sd == null) return;
}var mo = sd.mos[moPt - 1];
mo.put("occupancy", Float.$valueOf(occ > 2 ? 2 : occ));
mo.put("energy", Float.$valueOf(energy));
mo.put("symmetry", sd.sym + "_" + moPt);
this.setMO(mo);
}, "~S,~N,~N,~N");
Clazz.defineMethod(c$, "readCharges", 
function(){
if (this.lastModel < 0) return;
this.rd();
this.rd();
var n = this.asc.getAtomSetAtomCount(this.lastModel);
var charges =  Clazz.newFloatArray (n, 0);
for (var i = 0; i < n; i++) {
this.rd();
var tokens = this.getTokens();
var iatom = this.parseIntStr(tokens[0]);
charges[iatom - 1] = this.parseFloatStr(tokens[2]);
}
for (var p = 0, i = this.asc.getAtomSetAtomIndex(this.lastModel); i < this.asc.ac; i++, p = (p + 1) % n) {
this.asc.atoms[i].partialCharge = charges[p];
}
});
c$.$AdfReader$SymmetryData$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.index = 0;
this.sym = null;
this.nSFO = 0;
this.nBF = 0;
this.coefs = null;
this.mos = null;
this.basisFunctions = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum.AdfReader, "SymmetryData", null);
Clazz.makeConstructor(c$, 
function(index, sym){
JU.Logger.info((this.b$["J.adapter.readers.quantum.AdfReader"].isADF ? "ADF" : "AMS") + " reader creating SymmetryData " + sym + " " + index);
this.index = index;
this.sym = sym;
}, "~N,~S");
/*eoif4*/})();
};
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
