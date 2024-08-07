Clazz.declarePackage("J.adapter.readers.xtal");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.xtal.PWmatReader", ["java.util.Hashtable", "JU.Lst", "$.PT", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.nAtoms = 0;
this.haveLattice = false;
this.havePositions = false;
this.haveMagnetic = false;
this.global3 = ";STRESS_MASK;STRESS_EXTERNAL;PTENSOR_EXTERNAL;";
Clazz.instantialize(this, arguments);}, J.adapter.readers.xtal, "PWmatReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.readers.xtal.PWmatReader, []);
});
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.doApplySymmetry = true;
});
Clazz.overrideMethod(c$, "checkLine", 
function(){
if (this.nAtoms == 0) {
this.readComments();
this.setSpaceGroupName("P1");
this.nAtoms = JU.PT.parseInt(this.line);
this.setFractionalCoordinates(true);
return true;
}this.removeComments();
var lc = this.line.toLowerCase().trim();
if (lc.length == 0) return true;
if (!this.haveLattice) {
if (lc.startsWith("lattice")) {
this.readUnitCell();
this.haveLattice = true;
}return true;
}if (!this.havePositions) {
if (lc.startsWith("position")) {
this.readCoordinates();
this.havePositions = true;
}return true;
}if (!this.readDataBlock(lc)) {
this.continuing = false;
}return true;
});
Clazz.defineMethod(c$, "readComments", 
function(){
});
Clazz.defineMethod(c$, "readUnitCell", 
function(){
var unitCellData =  Clazz.newFloatArray (3, 0);
this.addExplicitLatticeVector(0, this.fillFloatArray(this.getLine(), 0, unitCellData), 0);
this.addExplicitLatticeVector(1, this.fillFloatArray(this.getLine(), 0, unitCellData), 0);
this.addExplicitLatticeVector(2, this.fillFloatArray(this.getLine(), 0, unitCellData), 0);
});
Clazz.defineMethod(c$, "readCoordinates", 
function(){
var constraints =  new JU.Lst();
var haveConstraints = true;
var i = 0;
while (i++ < this.nAtoms && this.getLine() != null) {
var tokens = this.getTokens();
var z = Integer.parseInt(tokens[0]);
this.addAtomXYZSymName(tokens, 1, J.adapter.smarter.AtomSetCollectionReader.getElementSymbol(z), null).elementNumber = z;
haveConstraints = (tokens.length >= 7) && haveConstraints;
if (haveConstraints) constraints.addLast( Clazz.newFloatArray(-1, [Float.parseFloat(tokens[4]), Float.parseFloat(tokens[5]), Float.parseFloat(tokens[6])]));
}
var cx =  Clazz.newFloatArray (this.nAtoms, 0);
var cy =  Clazz.newFloatArray (this.nAtoms, 0);
var cz =  Clazz.newFloatArray (this.nAtoms, 0);
var c =  Clazz.newFloatArray(-1, [1, 1, 1]);
for (i = this.nAtoms; --i >= 0; ) {
if (haveConstraints) c = constraints.get(i);
cx[i] = c[0];
cy[i] = c[1];
cz[i] = c[2];
}
this.setVectors("constraints", cx, cy, cz, this.nAtoms);
});
Clazz.defineMethod(c$, "readDataBlock", 
function(name){
name = this.trimPWPropertyNameTo(name, " ([,");
this.getLine();
if (this.line == null) return false;
var tokens = this.getTokens();
switch (tokens.length) {
case 1:
case 2:
case 3:
this.readItems(name, tokens.length - 1, null);
return true;
case 4:
this.readVectors(name, 1, true);
return true;
default:
JU.Logger.error("PWmatReader block " + name.toUpperCase() + " ignored");
return false;
}
}, "~S");
Clazz.defineMethod(c$, "trimPWPropertyNameTo", 
function(name, chars){
for (var i = chars.length; --i >= 0; ) {
var pt = name.indexOf(chars.charAt(i));
if (pt > 0) name = name.substring(0, pt);
}
return name;
}, "~S,~S");
Clazz.defineMethod(c$, "readItems", 
function(name, offset, values){
if (name.equalsIgnoreCase("magnetic")) this.haveMagnetic = true;
var isGlobal = JU.PT.isOneOf(name.toUpperCase(), this.global3);
if (isGlobal) {
var lines =  new Array(3);
lines[0] = this.line;
lines[1] = this.getLine();
lines[2] = this.getLine();
var info = this.asc.getAtomSetAuxiliaryInfo(0);
var data = info.get("globalPWmatData");
if (data == null) info.put("globalPWmatData", data =  new java.util.Hashtable());
data.put(name, lines);
} else {
name = "pwm_" + name;
if (values == null) {
values =  Clazz.newFloatArray (this.nAtoms, 0);
} else {
this.getLine();
}var n = 0;
for (var i = 0; ; ) {
var tokens = this.getTokens();
if ((values[i] = Float.parseFloat(tokens[offset])) != 0) n++;
if (++i == this.nAtoms) break;
this.getLine();
}
this.setProperties(name, values, n);
}}, "~S,~N,~A");
Clazz.defineMethod(c$, "setProperties", 
function(name, values, n){
this.asc.setAtomProperties(name, values, this.asc.iSet, false);
JU.Logger.info("PWmatReader: " + name.toUpperCase() + " processed for " + n + " atoms");
this.appendLoadNote("PWmatReader read property_" + name);
}, "~S,~A,~N");
Clazz.defineMethod(c$, "readVectors", 
function(name, offset, haveLine){
if (!haveLine) this.getLine();
var valuesX =  Clazz.newFloatArray (this.nAtoms, 0);
var valuesY =  Clazz.newFloatArray (this.nAtoms, 0);
var valuesZ =  Clazz.newFloatArray (this.nAtoms, 0);
var n = 0;
for (var i = 0; ; ) {
var tokens = this.getTokens();
if ((((valuesX[i] = Float.parseFloat(tokens[offset])) == 0 ? 0 : 1) | ((valuesY[i] = Float.parseFloat(tokens[offset + 1])) == 0 ? 0 : 1) | ((valuesZ[i] = Float.parseFloat(tokens[offset + 2])) == 0 ? 0 : 1)) != 0) n++;
if (++i == this.nAtoms) break;
this.getLine();
}
this.setVectors(name, valuesX, valuesY, valuesZ, n);
}, "~S,~N,~B");
Clazz.defineMethod(c$, "getLine", 
function(){
this.rd();
return this.removeComments();
});
Clazz.defineMethod(c$, "removeComments", 
function(){
if (this.line != null) {
var pt = this.line.indexOf("#");
if (pt >= 0) {
this.line = this.line.substring(0, pt).trim();
}}return this.line;
});
Clazz.defineMethod(c$, "setVectors", 
function(name, valuesX, valuesY, valuesZ, n){
name = "pwm_" + name;
this.asc.setAtomProperties(name + "_x", valuesX, this.asc.iSet, false);
this.asc.setAtomProperties(name + "_y", valuesY, this.asc.iSet, false);
this.asc.setAtomProperties(name + "_z", valuesZ, this.asc.iSet, false);
JU.Logger.info("PWmatReader: " + name.toUpperCase() + " processed for " + n + " atoms");
this.appendLoadNote("PWmatReader read property_" + name + "_x");
this.appendLoadNote("PWmatReader read property_" + name + "_y");
this.appendLoadNote("PWmatReader read property_" + name + "_z");
if (name.equals("pwm_magnetic_xyz")) {
for (var i = 0; i < this.nAtoms; i++) {
this.asc.addVibrationVector(i, valuesX[i], valuesY[i], valuesZ[i]);
}
this.addJmolScript("vectors 0.2;set vectorscentered");
}}, "~S,~A,~A,~A,~N");
Clazz.defineMethod(c$, "applySymmetryAndSetTrajectory", 
function(){
Clazz.superCall(this, J.adapter.readers.xtal.PWmatReader, "applySymmetryAndSetTrajectory", []);
if (this.nAtoms != this.asc.ac) {
this.nAtoms = this.asc.ac;
var p = this.asc.getAtomSetAuxiliaryInfoValue(this.asc.iSet, "atomProperties");
if (p != null) {
var atoms = this.asc.atoms;
var n = (this.asc.bsAtoms == null ? this.nAtoms : this.asc.bsAtoms.cardinality());
var map = (n == this.nAtoms ? null :  Clazz.newIntArray (this.nAtoms, 0));
if (map != null) {
for (var j = 0, k = 0; j < this.nAtoms; j++) {
if (this.asc.bsAtoms.get(j)) map[j] = k++;
}
}for (var e, $e = p.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var key = e.getKey();
if (key.startsWith("pwm_")) {
var af = e.getValue();
var af2 =  Clazz.newFloatArray (n, 0);
for (var j = 0; j < this.nAtoms; j++) {
af2[map == null ? j : map[j]] = af[atoms[j].atomSite];
}
e.setValue(af2);
}}
}}});
Clazz.overrideMethod(c$, "finalizeSubclassReader", 
function(){
if (!this.haveMagnetic && this.asc.ac > 0) {
this.setProperties("pwm_magnetic",  Clazz.newFloatArray (this.asc.ac, 0), this.nAtoms);
}});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
