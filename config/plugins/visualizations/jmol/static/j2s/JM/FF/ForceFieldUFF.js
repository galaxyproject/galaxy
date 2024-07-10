Clazz.declarePackage("JM.FF");
Clazz.load(["JM.FF.ForceField", "JS.T"], "JM.FF.ForceFieldUFF", ["java.util.Hashtable", "JU.BS", "$.Lst", "$.PT", "JM.FF.CalculationsUFF", "$.FFParam", "JU.Elements", "$.Logger", "JV.JmolAsyncException"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.ffParams = null;
this.bsAromatic = null;
this.is2D = false;
Clazz.instantialize(this, arguments);}, JM.FF, "ForceFieldUFF", JM.FF.ForceField);
Clazz.makeConstructor(c$, 
function(minimizer, isQuick){
Clazz.superConstructor (this, JM.FF.ForceFieldUFF, []);
this.minimizer = minimizer;
if (isQuick) {
this.name = "UFF2D";
this.is2D = true;
this.ffParams = JM.FF.ForceFieldUFF.uff2DParams;
if (this.ffParams == null) JM.FF.ForceFieldUFF.uff2DParams = this.ffParams = this.getParameters();
} else {
this.name = "UFF";
this.ffParams = JM.FF.ForceFieldUFF.uffParams;
if (this.ffParams == null) JM.FF.ForceFieldUFF.uffParams = this.ffParams = this.getParameters();
}}, "JM.Minimizer,~B");
Clazz.overrideMethod(c$, "clear", 
function(){
this.bsAromatic = null;
});
Clazz.overrideMethod(c$, "setModel", 
function(bsElements, elemnoMax){
this.setModelFields();
JU.Logger.info("minimize: setting atom types...");
if (this.ffParams == null || JM.FF.ForceFieldUFF.atomTypes == null && (JM.FF.ForceFieldUFF.atomTypes = this.getAtomTypes()) == null) return false;
this.setAtomTypes(bsElements, elemnoMax);
this.calc =  new JM.FF.CalculationsUFF(this, this.ffParams, this.minAtoms, this.minBonds, this.minAngles, this.minTorsions, this.minimizer.constraints);
return this.calc.setupCalculations();
}, "JU.BS,~N");
Clazz.defineMethod(c$, "setAtomTypes", 
function(bsElements, elemnoMax){
var nTypes = JM.FF.ForceFieldUFF.atomTypes.size();
bsElements.clear(0);
for (var i = 0; i < nTypes; i++) {
var data = JM.FF.ForceFieldUFF.atomTypes.get(i);
var smarts = data[0];
if (smarts == null) continue;
var search = this.getSearch(smarts, elemnoMax, bsElements);
if (bsElements.get(0)) bsElements.clear(0);
 else if (search == null) break;
 else for (var j = this.minimizer.bsAtoms.nextSetBit(0), pt = 0; j < this.minimizer.atoms.length && j >= 0; j = this.minimizer.bsAtoms.nextSetBit(j + 1), pt++) if (search.get(j)) {
this.minAtoms[pt].sType = data[1].intern();
}
}
}, "JU.BS,~N");
Clazz.defineMethod(c$, "getSearch", 
function(smarts, elemnoMax, bsElements){
var search = null;
var len = smarts.length;
search = JM.FF.ForceFieldUFF.tokenTypes[0];
var n = (smarts.charAt(len - 2)).charCodeAt(0) - 48;
var elemNo = 0;
if (n >= 10) n = 0;
var isAromatic = false;
if (smarts.charAt(1) == '#') {
elemNo = JU.PT.parseInt(smarts.substring(2, len - 1));
} else {
var s = smarts.substring(1, (n > 0 ? len - 3 : len - 1));
if (s.equals(s.toLowerCase())) {
s = s.toUpperCase();
isAromatic = true;
}elemNo = JU.Elements.elementNumberFromSymbol(s, false);
}if (elemNo > elemnoMax) return null;
if (!bsElements.get(elemNo)) {
bsElements.set(0);
return null;
}switch ((smarts.charAt(len - 3)).charCodeAt(0)) {
case 68:
search = JM.FF.ForceFieldUFF.tokenTypes[2];
search[6].intValue = n;
break;
case 94:
search = JM.FF.ForceFieldUFF.tokenTypes[4 + (n - 1)];
break;
case 43:
search = JM.FF.ForceFieldUFF.tokenTypes[1];
search[5].intValue = n;
break;
case 45:
search = JM.FF.ForceFieldUFF.tokenTypes[1];
search[5].intValue = -n;
break;
case 65:
search = JM.FF.ForceFieldUFF.tokenTypes[6];
break;
}
search[2].intValue = elemNo;
var v = this.minimizer.vwr.evaluateExpression(search);
if (!(Clazz.instanceOf(v,"JU.BS"))) return null;
var bs = v;
if (isAromatic && bs.nextSetBit(0) >= 0) {
if (this.bsAromatic == null) this.bsAromatic = (bsElements.get(6) ? this.minimizer.vwr.evaluateExpression(JM.FF.ForceFieldUFF.tokenTypes[3]) :  new JU.BS());
bs.and(this.bsAromatic);
}if (JU.Logger.debugging && bs.nextSetBit(0) >= 0) JU.Logger.debug(smarts + " minimize atoms=" + bs);
return bs;
}, "~S,~N,JU.BS");
Clazz.defineMethod(c$, "getParameters", 
function(){
var data =  new java.util.Hashtable();
var resourceName = (this.is2D ? "UFF_2d.txt" : "UFF.txt");
var br = null;
try {
br = this.getBufferedReader(resourceName);
var line;
while ((line = br.readLine()) != null) {
var vs = JU.PT.getTokens(line);
if (vs.length < 13) continue;
if (JU.Logger.debugging) JU.Logger.debug(line);
if (line.substring(0, 5).equals("param")) {
var p =  new JM.FF.FFParam();
data.put(vs[1], p);
p.dVal =  Clazz.newDoubleArray (11, 0);
p.sVal =  new Array(1);
p.sVal[0] = vs[1];
p.dVal[0] = JU.PT.parseFloat(vs[2]);
p.dVal[1] = JU.PT.parseFloat(vs[3]) * 0.017453292519943295;
p.dVal[2] = JU.PT.parseFloat(vs[4]);
p.dVal[3] = JU.PT.parseFloat(vs[5]);
p.dVal[4] = JU.PT.parseFloat(vs[6]);
p.dVal[5] = JU.PT.parseFloat(vs[7]);
p.dVal[6] = JU.PT.parseFloat(vs[8]);
p.dVal[7] = JU.PT.parseFloat(vs[9]);
p.dVal[8] = JU.PT.parseFloat(vs[10]);
p.dVal[9] = JU.PT.parseFloat(vs[11]);
p.dVal[10] = JU.PT.parseFloat(vs[12]);
p.iVal =  Clazz.newIntArray (1, 0);
var coord = (vs[1].length > 2 ? vs[1].charAt(2) : '1');
switch ((coord).charCodeAt(0)) {
case 82:
coord = '2';
break;
default:
coord = '1';
break;
case 49:
case 50:
case 51:
case 52:
case 53:
case 54:
break;
}
p.iVal[0] = coord.charCodeAt(0) - 48;
}}
br.close();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.err.println("Exception " + e.toString() + " in getResource " + resourceName);
try {
br.close();
} catch (ee) {
if (Clazz.exceptionOf(ee, Exception)){
} else {
throw ee;
}
}
return null;
} else {
throw e;
}
}
JU.Logger.info(data.size() + " atom types read from " + resourceName);
return data;
});
Clazz.defineMethod(c$, "getAtomTypes", 
function(){
var types =  new JU.Lst();
var fileName = (this.is2D ? "UFF_2d.txt" : "UFF.txt");
try {
var br = this.getBufferedReader(fileName);
var line;
while ((line = br.readLine()) != null) {
if (line.length > 4 && line.substring(0, 4).equals("atom")) {
var vs = JU.PT.getTokens(line);
var info =  Clazz.newArray(-1, [vs[1], vs[2]]);
types.addLast(info);
}}
br.close();
} catch (e$$) {
if (Clazz.exceptionOf(e$$,"JV.JmolAsyncException")){
var e = e$$;
{
throw  new JV.JmolAsyncException(e.getFileName());
}
} else if (Clazz.exceptionOf(e$$, Exception)){
var e = e$$;
{
System.err.println("Exception " + e.toString() + " in getResource " + fileName);
}
} else {
throw e$$;
}
}
JU.Logger.info(types.size() + " UFF parameters read");
return (types.size() > 0 ? types : null);
});
c$.atomTypes = null;
c$.uff2DParams = null;
c$.uffParams = null;
c$.tokenTypes =  Clazz.newArray(-1, [ Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenAnd, JS.T.n(268440324, 1631586315), JS.T.i(0), JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenAnd, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.i(0), JS.T.tokenRightParen, JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.o(1073741824, "flatring"), JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenAnd, JS.T.tokenLeftParen, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.i(1), JS.T.tokenComma, JS.T.o(4, "triple"), JS.T.tokenRightParen, JS.T.tokenOr, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.i(2), JS.T.tokenComma, JS.T.o(4, "double"), JS.T.tokenRightParen, JS.T.tokenRightParen, JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenAnd, JS.T.o(134217736, "connected"), JS.T.tokenLeftParen, JS.T.i(1), JS.T.tokenComma, JS.T.o(4, "double"), JS.T.tokenRightParen, JS.T.tokenExpressionEnd]),  Clazz.newArray(-1, [JS.T.tokenExpressionBegin, JS.T.n(268440324, 1094715402), JS.T.i(0), JS.T.tokenAnd, JS.T.tokenLeftParen, JS.T.n(268440325, 1094715402), JS.T.i(6), JS.T.tokenOr, JS.T.n(268440325, 1631586315), JS.T.i(0), JS.T.tokenRightParen, JS.T.tokenAnd, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.i(3), JS.T.tokenRightParen, JS.T.tokenAnd, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.tokenConnected, JS.T.tokenLeftParen, JS.T.o(4, "double"), JS.T.tokenRightParen, JS.T.tokenRightParen, JS.T.tokenExpressionEnd])]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
