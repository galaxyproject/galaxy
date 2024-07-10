Clazz.declarePackage("J.adapter.readers.xtal");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.xtal.ShelxReader", ["JU.AU", "$.PT", "J.adapter.smarter.Atom", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.sfacElementSymbols = null;
this.isCmdf = false;
this.tokens = null;
this.altloc = '\0';
this.isCentroSymmetric = false;
this.haveXYZ = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xtal, "ShelxReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.setFractionalCoordinates(true);
});
Clazz.overrideMethod(c$, "checkLine", 
function(){
var lineLength;
while ((lineLength = (this.line = this.line.trim()).length) > 0 && this.line.charAt(lineLength - 1) == '=') this.line = this.line.substring(0, lineLength - 1) + this.rd();

this.tokens = this.getTokens();
if (this.tokens.length == 0) return true;
var command = this.tokens[0].toUpperCase();
if (command.equals("TITL")) {
if (!this.doGetModel(++this.modelNumber, null)) return this.checkLastModel();
this.sfacElementSymbols = null;
this.applySymmetryAndSetTrajectory();
this.setFractionalCoordinates(true);
this.asc.newAtomSet();
this.asc.setAtomSetName(this.line.substring(4).trim());
return true;
}if (command.equals("NOTE")) {
this.isCmdf = true;
return true;
}if (!this.doProcessLines || lineLength < 3) return true;
if (";ZERR;DISP;UNIT;LAUE;REM;MORE;TIME;HKLF;OMIT;SHEL;BASF;TWIN;EXTI;SWAT;HOPE;MERG;SPEC;RESI;MOVE;ANIS;AFIX;HFIX;FRAG;FEND;EXYZ;EXTI;EADP;EQIV;CONN;BIND;FREE;DFIX;DANG;BUMP;SAME;SADI;CHIV;FLAT;DELU;SIMU;DEFS;ISOR;NCSY;SUMP;L.S.;CGLS;BLOC;DAMP;STIR;WGHT;FVAR;BOND;CONF;MPLA;RTAB;HTAB;LIST;ACTA;SIZE;TEMP;WPDB;FMAP;GRID;PLAN;MOLE;".indexOf(";" + command + ";") >= 0) return true;
for (var i = J.adapter.readers.xtal.ShelxReader.supportedRecordTypes.length; --i >= 0; ) if (command.equals(J.adapter.readers.xtal.ShelxReader.supportedRecordTypes[i])) {
this.processSupportedRecord(i);
return true;
}
if (!this.isCmdf) this.assumeAtomRecord();
return true;
});
Clazz.defineMethod(c$, "processSupportedRecord", 
function(recordIndex){
switch (recordIndex) {
case 0:
case 9:
break;
case 1:
this.cell();
break;
case 2:
this.setSpaceGroupName(JU.PT.parseTrimmedAt(this.line, 4));
break;
case 3:
this.parseSfacRecord();
break;
case 4:
this.parseLattRecord();
break;
case 5:
this.parseSymmRecord();
break;
case 6:
this.isCmdf = true;
break;
case 7:
this.isCmdf = true;
this.processCmdfAtoms();
break;
case 8:
this.processPartRecord();
break;
}
}, "~N");
Clazz.defineMethod(c$, "processPartRecord", 
function(){
var part = this.parseIntStr(this.tokens[1]);
this.altloc = String.fromCharCode(part == 0 ? 0 : 48 + part);
});
Clazz.defineMethod(c$, "parseLattRecord", 
function(){
var latt = this.parseIntStr(this.tokens[1]);
this.isCentroSymmetric = (latt > 0);
if (latt == 1 || latt == -1) return;
this.asc.getXSymmetry().setLatticeParameter(latt);
});
Clazz.defineMethod(c$, "parseSymmRecord", 
function(){
if (!this.haveXYZ) {
this.setSymmetryOperator("x,y,z");
this.haveXYZ = true;
}this.setSymmetryOperator(this.line.substring(4).trim());
});
Clazz.defineMethod(c$, "cell", 
function(){
var ioff = this.tokens.length - 6;
if (ioff == 2) this.asc.setInfo("wavelength", Float.$valueOf(this.parseFloatStr(this.tokens[1])));
for (var ipt = 0; ipt < 6; ipt++) this.setUnitCellItem(ipt, this.parseFloatStr(this.tokens[ipt + ioff]));

});
Clazz.defineMethod(c$, "parseSfacRecord", 
function(){
var allElementSymbols = true;
for (var i = this.tokens.length; allElementSymbols && --i >= 1; ) {
var token = this.tokens[i];
allElementSymbols = J.adapter.readers.xtal.ShelxReader.isValidElementSymbolNoCaseSecondChar(token);
}
var sfacTokens = JU.PT.getTokens(this.line.substring(4));
if (allElementSymbols) this.parseSfacElementSymbols(sfacTokens);
 else this.parseSfacCoefficients(sfacTokens);
});
Clazz.defineMethod(c$, "parseSfacElementSymbols", 
function(sfacTokens){
if (this.sfacElementSymbols == null) {
this.sfacElementSymbols = sfacTokens;
} else {
var oldCount = this.sfacElementSymbols.length;
var tokenCount = sfacTokens.length;
this.sfacElementSymbols = JU.AU.arrayCopyS(this.sfacElementSymbols, oldCount + tokenCount);
for (var i = tokenCount; --i >= 0; ) this.sfacElementSymbols[oldCount + i] = sfacTokens[i];

}}, "~A");
Clazz.defineMethod(c$, "parseSfacCoefficients", 
function(sfacTokens){
var a1 = this.parseFloatStr(sfacTokens[1]);
var a2 = this.parseFloatStr(sfacTokens[3]);
var a3 = this.parseFloatStr(sfacTokens[5]);
var a4 = this.parseFloatStr(sfacTokens[7]);
var c = this.parseFloatStr(sfacTokens[9]);
var z = Math.round(a1 + a2 + a3 + a4 + c);
var elementSymbol = J.adapter.smarter.AtomSetCollectionReader.getElementSymbol(z);
var oldCount = 0;
if (this.sfacElementSymbols == null) {
this.sfacElementSymbols =  new Array(1);
} else {
oldCount = this.sfacElementSymbols.length;
this.sfacElementSymbols = JU.AU.arrayCopyS(this.sfacElementSymbols, oldCount + 1);
this.sfacElementSymbols[oldCount] = elementSymbol;
}this.sfacElementSymbols[oldCount] = elementSymbol;
}, "~A");
Clazz.defineMethod(c$, "assumeAtomRecord", 
function(){
var x = NaN;
var y = NaN;
var z = NaN;
var occ = 1;
var elementIndex = -1;
var atomName = null;
try {
atomName = this.tokens[0];
elementIndex = this.parseIntStr(this.tokens[1]) - 1;
x = this.parseFloatStr(this.tokens[2]) % 10;
y = this.parseFloatStr(this.tokens[3]) % 10;
z = this.parseFloatStr(this.tokens[4]) % 10;
occ = this.parseFloatStr(this.tokens[5]) % 10;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
if (Float.isNaN(x) || Float.isNaN(y) || Float.isNaN(z)) {
JU.Logger.error("skipping line " + this.line);
return;
}var atom = this.asc.addNewAtom();
atom.atomName = atomName;
atom.foccupancy = occ;
var isQPeak = atomName.startsWith("Q");
if (isQPeak) {
atom.elementSymbol = "Xx";
} else if (this.sfacElementSymbols != null && elementIndex >= 0 && elementIndex < this.sfacElementSymbols.length) {
atom.elementSymbol = this.sfacElementSymbols[elementIndex];
}this.setAtomCoordXYZ(atom, x, y, z);
atom.altLoc = this.altloc;
if (this.tokens.length == 12) {
var data =  Clazz.newFloatArray (8, 0);
data[0] = this.parseFloatStr(this.tokens[6]);
data[1] = this.parseFloatStr(this.tokens[7]);
data[2] = this.parseFloatStr(this.tokens[8]);
data[3] = this.parseFloatStr(this.tokens[11]);
data[4] = this.parseFloatStr(this.tokens[10]);
data[5] = this.parseFloatStr(this.tokens[9]);
for (var i = 0; i < 6; i++) if (Float.isNaN(data[i])) {
JU.Logger.error("Bad anisotropic Uij data: " + this.line);
return;
}
this.asc.setAnisoBorU(atom, data, 8);
}});
Clazz.defineMethod(c$, "processCmdfAtoms", 
function(){
while (this.rd() != null && this.line.length > 10) {
this.tokens = this.getTokens();
this.addAtomXYZSymName(this.tokens, 2, this.getSymbol(this.tokens[0]), this.tokens[1]);
}
});
Clazz.defineMethod(c$, "getSymbol", 
function(sym){
if (sym == null) return "Xx";
var len = sym.length;
if (len < 2) return sym;
var ch1 = sym.charAt(1);
if (ch1 >= 'a' && ch1 <= 'z') return sym.substring(0, 2);
return "" + sym.charAt(0);
}, "~S");
c$.isValidElementSymbolNoCaseSecondChar = Clazz.defineMethod(c$, "isValidElementSymbolNoCaseSecondChar", 
function(str){
if (str == null) return false;
var length = str.length;
if (length == 0) return false;
var chFirst = str.charAt(0);
if (length == 1) return J.adapter.smarter.Atom.isValidSym1(chFirst);
if (length > 2) return false;
var chSecond = str.charAt(1);
return J.adapter.smarter.Atom.isValidSymNoCase(chFirst, chSecond);
}, "~S");
Clazz.overrideMethod(c$, "applySymmetryAndSetTrajectory", 
function(){
if (this.isCentroSymmetric && !this.ignoreFileSymmetryOperators) {
this.asc.getXSymmetry().getSymmetry().addInversion();
this.isCentroSymmetric = false;
}this.applySymTrajASCR();
});
c$.supportedRecordTypes =  Clazz.newArray(-1, ["TITL", "CELL", "SPGR", "SFAC", "LATT", "SYMM", "NOTE", "ATOM", "PART", "END"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
