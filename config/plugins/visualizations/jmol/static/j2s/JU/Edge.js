Clazz.declarePackage("JU");
Clazz.load(["java.lang.Enum", "JU.SimpleEdge"], "JU.Edge", ["JU.PT"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.index = -1;
this.order = 0;
Clazz.instantialize(this, arguments);}, JU, "Edge", null, JU.SimpleEdge);
c$.getArgbHbondType = Clazz.defineMethod(c$, "getArgbHbondType", 
function(order){
var argbIndex = ((order & 30720) >> 11);
return JU.Edge.argbsHbondType[argbIndex];
}, "~N");
c$.getBondOrderNumberFromOrder = Clazz.defineMethod(c$, "getBondOrderNumberFromOrder", 
function(order){
order &= 131071;
switch (order) {
case 131071:
case 65535:
return "0";
case 1025:
case 1041:
return "1";
default:
if (JU.Edge.isOrderH(order) || JU.Edge.isAtropism(order) || (order & 256) != 0) return "1";
if ((order & 224) != 0) return (order >> 5) + "." + (order & 0x1F);
return JU.Edge.EnumBondOrder.getNumberFromCode(order);
}
}, "~N");
c$.getCmlBondOrder = Clazz.defineMethod(c$, "getCmlBondOrder", 
function(order){
var sname = JU.Edge.getBondOrderNameFromOrder(order);
switch ((sname.charAt(0)).charCodeAt(0)) {
case 115:
case 100:
case 116:
return "" + sname.toUpperCase().charAt(0);
case 97:
if (sname.indexOf("Double") >= 0) return "D";
 else if (sname.indexOf("Single") >= 0) return "S";
return "aromatic";
case 112:
if (sname.indexOf(" ") >= 0) return sname.substring(sname.indexOf(" ") + 1);
return "partial12";
}
return null;
}, "~N");
c$.getBondOrderNameFromOrder = Clazz.defineMethod(c$, "getBondOrderNameFromOrder", 
function(order){
order &= 131071;
switch (order) {
case 65535:
case 131071:
return "";
case 1025:
return "near";
case 1041:
return "far";
case 32768:
return JU.Edge.EnumBondOrder.STRUT.$$name;
case 1:
return JU.Edge.EnumBondOrder.SINGLE.$$name;
case 2:
return JU.Edge.EnumBondOrder.DOUBLE.$$name;
}
if ((order & 224) != 0) return "partial " + JU.Edge.getBondOrderNumberFromOrder(order);
if (JU.Edge.isOrderH(order)) return JU.Edge.EnumBondOrder.H_REGULAR.$$name;
if ((order & 65537) == 65537) {
var code = JU.Edge.getAtropismCode(order);
return "atropisomer_" + (Clazz.doubleToInt(code / 4)) + (code % 4);
}if ((order & 256) != 0) return JU.Edge.EnumBondOrder.SINGLE.$$name;
return JU.Edge.EnumBondOrder.getNameFromCode(order);
}, "~N");
c$.getAtropismOrder = Clazz.defineMethod(c$, "getAtropismOrder", 
function(nn, mm){
return JU.Edge.getAtropismOrder12(((nn) << 2) + mm);
}, "~N,~N");
c$.getAtropismOrder12 = Clazz.defineMethod(c$, "getAtropismOrder12", 
function(nnmm){
return ((nnmm << 11) | 65537);
}, "~N");
c$.getAtropismCode = Clazz.defineMethod(c$, "getAtropismCode", 
function(order){
return (order >> (11)) & 0xF;
}, "~N");
c$.getAtropismNode = Clazz.defineMethod(c$, "getAtropismNode", 
function(order, a1, isFirst){
var i1 = (order >> (11 + (isFirst ? 0 : 2))) & 3;
return a1.getEdges()[i1 - 1].getOtherNode(a1);
}, "~N,JU.Node,~B");
c$.isAtropism = Clazz.defineMethod(c$, "isAtropism", 
function(order){
return (order & 65537) == 65537;
}, "~N");
c$.isOrderH = Clazz.defineMethod(c$, "isOrderH", 
function(order){
return (order & 30720) != 0 && (order & 65537) == 0;
}, "~N");
c$.getPartialBondDotted = Clazz.defineMethod(c$, "getPartialBondDotted", 
function(order){
return (order & 0x1F);
}, "~N");
c$.getPartialBondOrder = Clazz.defineMethod(c$, "getPartialBondOrder", 
function(order){
return ((order & 131071) >> 5);
}, "~N");
c$.getCovalentBondOrder = Clazz.defineMethod(c$, "getCovalentBondOrder", 
function(order){
if ((order & 1024) != 0) return 1;
if ((order & 1023) == 0) return 0;
order &= 131071;
if ((order & 224) != 0) return JU.Edge.getPartialBondOrder(order);
if ((order & 256) != 0) order &= -257;
if ((order & 0xF8) != 0) order = 1;
return order & 7;
}, "~N");
c$.getBondOrderFromFloat = Clazz.defineMethod(c$, "getBondOrderFromFloat", 
function(fOrder){
switch (Clazz.floatToInt(fOrder * 10)) {
case 10:
return 1;
case 5:
case -10:
return 33;
case 15:
return 515;
case -15:
return 66;
case 20:
return 2;
case 25:
return 97;
case -25:
return 100;
case 30:
return 3;
case 40:
return 4;
}
return 131071;
}, "~N");
c$.getBondOrderFromString = Clazz.defineMethod(c$, "getBondOrderFromString", 
function(s){
if (s.indexOf(' ') < 0) {
if (s.indexOf(".") >= 0) {
s = "partial " + s;
} else {
if (JU.PT.isOneOf(s, ";1;2;3;4;5;6;")) {
return (s.charAt(0)).charCodeAt(0) - 48;
}var order = JU.Edge.EnumBondOrder.getCodeFromName(s);
if (order != 131071 || !s.toLowerCase().startsWith("atropisomer_") || s.length != 14) return order;
try {
order = JU.Edge.getAtropismOrder(Integer.parseInt(s.substring(12, 13)), Integer.parseInt(s.substring(13, 14)));
} catch (e) {
if (Clazz.exceptionOf(e,"NumberFormatException")){
} else {
throw e;
}
}
return order;
}}if (s.toLowerCase().indexOf("partial ") != 0) return 131071;
s = s.substring(8).trim();
return JU.Edge.getPartialBondOrderFromFloatEncodedInt(JU.Edge.getFloatEncodedInt(s));
}, "~S");
c$.getPartialBondOrderFromFloatEncodedInt = Clazz.defineMethod(c$, "getPartialBondOrderFromFloatEncodedInt", 
function(bondOrderInteger){
return (((Clazz.doubleToInt(bondOrderInteger / 1000000)) % 7) << 5) + ((bondOrderInteger % 1000000) & 0x1F);
}, "~N");
c$.getFloatEncodedInt = Clazz.defineMethod(c$, "getFloatEncodedInt", 
function(strDecimal){
var pt = strDecimal.indexOf(".");
if (pt < 1 || strDecimal.charAt(0) == '-' || strDecimal.endsWith(".") || strDecimal.contains(".0")) return 2147483647;
var i = 0;
var j = 0;
if (pt > 0) {
try {
i = Integer.parseInt(strDecimal.substring(0, pt));
if (i < 0) i = -i;
} catch (e) {
if (Clazz.exceptionOf(e,"NumberFormatException")){
i = -1;
} else {
throw e;
}
}
}if (pt < strDecimal.length - 1) try {
j = Integer.parseInt(strDecimal.substring(pt + 1));
} catch (e) {
if (Clazz.exceptionOf(e,"NumberFormatException")){
} else {
throw e;
}
}
i = i * 1000000 + j;
return (i < 0 || i > 2147483647 ? 2147483647 : i);
}, "~S");
Clazz.overrideMethod(c$, "getBondType", 
function(){
return this.order & 131071;
});
Clazz.defineMethod(c$, "setCIPChirality", 
function(c){
}, "~N");
Clazz.defineMethod(c$, "getCIPChirality", 
function(doCalculate){
return "";
}, "~B");
/*if2*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.code = 0;
this.number = null;
this.$$name = null;
Clazz.instantialize(this, arguments);}, JU.Edge, "EnumBondOrder", Enum);
Clazz.makeConstructor(c$, 
function(code, number, name){
this.code = code;
this.number = number;
this.$$name = name;
}, "~N,~S,~S");
c$.getCodeFromName = Clazz.defineMethod(c$, "getCodeFromName", 
function(name){
for (var item, $item = 0, $$item = JU.Edge.EnumBondOrder.values(); $item < $$item.length && ((item = $$item[$item]) || true); $item++) if (item.$$name.equalsIgnoreCase(name)) return item.code;

return 131071;
}, "~S");
c$.getNameFromCode = Clazz.defineMethod(c$, "getNameFromCode", 
function(code){
for (var item, $item = 0, $$item = JU.Edge.EnumBondOrder.values(); $item < $$item.length && ((item = $$item[$item]) || true); $item++) if (item.code == code) return item.$$name;

return "?";
}, "~N");
c$.getNumberFromCode = Clazz.defineMethod(c$, "getNumberFromCode", 
function(code){
for (var item, $item = 0, $$item = JU.Edge.EnumBondOrder.values(); $item < $$item.length && ((item = $$item[$item]) || true); $item++) if (item.code == code) return item.number;

return "?";
}, "~N");
Clazz.defineEnumConstant(c$, "SINGLE", 0, [1, "1", "single"]);
Clazz.defineEnumConstant(c$, "DOUBLE", 1, [2, "2", "double"]);
Clazz.defineEnumConstant(c$, "TRIPLE", 2, [3, "3", "triple"]);
Clazz.defineEnumConstant(c$, "QUADRUPLE", 3, [4, "4", "quadruple"]);
Clazz.defineEnumConstant(c$, "QUINTUPLE", 4, [5, "5", "quintuple"]);
Clazz.defineEnumConstant(c$, "sextuple", 5, [6, "6", "sextuple"]);
Clazz.defineEnumConstant(c$, "AROMATIC", 6, [515, "1.5", "aromatic"]);
Clazz.defineEnumConstant(c$, "STRUT", 7, [32768, "1", "struts"]);
Clazz.defineEnumConstant(c$, "H_REGULAR", 8, [2048, "1", "hbond"]);
Clazz.defineEnumConstant(c$, "PARTIAL01", 9, [33, "0.5", "partial"]);
Clazz.defineEnumConstant(c$, "PARTIAL12", 10, [66, "1.5", "partialDouble"]);
Clazz.defineEnumConstant(c$, "PARTIAL23", 11, [97, "2.5", "partialTriple"]);
Clazz.defineEnumConstant(c$, "PARTIAL32", 12, [100, "2.5", "partialTriple2"]);
Clazz.defineEnumConstant(c$, "AROMATIC_SINGLE", 13, [513, "1", "aromaticSingle"]);
Clazz.defineEnumConstant(c$, "AROMATIC_DOUBLE", 14, [514, "2", "aromaticDouble"]);
Clazz.defineEnumConstant(c$, "ATROPISOMER", 15, [65537, "1", "atropisomer"]);
Clazz.defineEnumConstant(c$, "UNSPECIFIED", 16, [17, "1", "unspecified"]);
/*eoif2*/})();
c$.argbsHbondType =  Clazz.newIntArray(-1, [0xFFFF69B4, 0xFFFFFF00, 0xFFFFFF00, 0xFFFFFFFF, 0xFFFF00FF, 0xFFFF0000, 0xFFFFA500, 0xFF00FFFF, 0xFF00FF00, 0xFFFF8080]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
