Clazz.declarePackage("J.api");
Clazz.load(null, "J.api.JmolAdapter", ["JU.PT", "J.api.JmolViewer", "JU.Elements"], function(){
var c$ = Clazz.declareType(J.api, "JmolAdapter", null);
c$.getElementSymbol = Clazz.defineMethod(c$, "getElementSymbol", 
function(elementNumber){
return JU.Elements.elementSymbolFromNumber(elementNumber);
}, "~N");
c$.getElementNumber = Clazz.defineMethod(c$, "getElementNumber", 
function(elementSymbol){
return JU.Elements.elementNumberFromSymbol(elementSymbol, false);
}, "~S");
c$.getNaturalIsotope = Clazz.defineMethod(c$, "getNaturalIsotope", 
function(elementNumber){
return JU.Elements.getNaturalIsotope(elementNumber);
}, "~N");
c$.getBondingRadius = Clazz.defineMethod(c$, "getBondingRadius", 
function(atomicNumberWithIsotope, charge){
return JU.Elements.getBondingRadius(atomicNumberWithIsotope, charge);
}, "~N,~N");
Clazz.defineMethod(c$, "getAtomSetCollectionFromReaderType", 
function(name, type, bufferedReader, htParams){
var a = this.getAtomSetCollectionReader(name, type, bufferedReader, (J.api.JmolViewer.allocateViewer(null, this)).setLoadParameters(htParams, false));
if ((typeof(a)=='string')) return a;
return this.getAtomSetCollection(a);
}, "~S,~S,~O,java.util.Map");
Clazz.defineMethod(c$, "openBufferedReader", 
function(name, bufferedReader){
return this.getAtomSetCollectionFromReaderType(name, null, bufferedReader, null);
}, "~S,java.io.BufferedReader");
Clazz.defineMethod(c$, "openBufferedReader", 
function(name, bufferedReader, htParams){
return this.getAtomSetCollectionFromReaderType(name, null, bufferedReader, htParams);
}, "~S,java.io.BufferedReader,java.util.Map");
Clazz.defineMethod(c$, "openBufferedReader", 
function(name, type, bufferedReader){
return this.getAtomSetCollectionFromReaderType(name, type, bufferedReader, null);
}, "~S,~S,java.io.BufferedReader");
c$.canonizeAlphaDigit = Clazz.defineMethod(c$, "canonizeAlphaDigit", 
function(ch){
return (JU.PT.isLetterOrDigit(ch) ? ch : '\0');
}, "~S");
c$.canonizeInsertionCode = Clazz.defineMethod(c$, "canonizeInsertionCode", 
function(insertionCode){
return J.api.JmolAdapter.canonizeAlphaDigit(insertionCode);
}, "~S");
c$.canonizeAlternateLocationID = Clazz.defineMethod(c$, "canonizeAlternateLocationID", 
function(altLoc){
return J.api.JmolAdapter.canonizeAlphaDigit(altLoc);
}, "~S");
c$.cellParamNames =  Clazz.newArray(-1, ["_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
