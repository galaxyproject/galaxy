Clazz.declarePackage("JU");
Clazz.load(null, "JU.DF", ["JU.PT", "$.SB"], function(){
var c$ = Clazz.declareType(JU, "DF", null);
c$.setUseNumberLocalization = Clazz.defineMethod(c$, "setUseNumberLocalization", 
function(TF){
JU.DF.useNumberLocalization[0] = (TF ? Boolean.TRUE : Boolean.FALSE);
}, "~B");
c$.formatDecimalDbl = Clazz.defineMethod(c$, "formatDecimalDbl", 
function(value, decimalDigits){
if (decimalDigits == 2147483647 || value == -Infinity || value == Infinity || Double.isNaN(value)) return "" + value;
return JU.DF.formatDecimal(value, decimalDigits);
}, "~N,~N");
c$.formatDecimal = Clazz.defineMethod(c$, "formatDecimal", 
function(value, decimalDigits){
if (value == -Infinity || value == Infinity || Double.isNaN(value)) return "" + value;
if (decimalDigits == 2147483647) return "" + value;
var isNeg = (value < 0);
if (isNeg) value = -value;
var n;
if (decimalDigits < 0) {
decimalDigits = -decimalDigits;
if (decimalDigits > JU.DF.formattingStrings.length) decimalDigits = JU.DF.formattingStrings.length;
if (value == 0) return JU.DF.formattingStrings[decimalDigits - 1] + "E+0";
n = 0;
var d;
if (Math.abs(value) < 1) {
n = 100;
d = value * 1e-100;
} else {
n = -100;
d = value * 1e100;
}var s = ("" + d).toUpperCase();
var i1 = s.indexOf("E");
var sf;
if (i1 < 0) {
sf = "" + value;
} else {
n = JU.PT.parseInt(s.substring(i1 + (s.indexOf("E+") == i1 ? 2 : 1))) + n;
var f = JU.PT.parseFloat(s.substring(0, i1));
sf = JU.DF.formatDecimal(f, decimalDigits - 1);
if (sf.startsWith("10.")) {
sf = JU.DF.formatDecimal(1, decimalDigits - 1);
n++;
}}return (isNeg ? "-" : "") + sf + "E" + (n >= 0 ? "+" : "") + n;
}if (decimalDigits >= JU.DF.formattingStrings.length) decimalDigits = JU.DF.formattingStrings.length - 1;
var s1 = ("" + value).toUpperCase();
var pt = s1.indexOf(".");
if (pt < 0) return (isNeg ? "-" : "") + s1 + JU.DF.formattingStrings[decimalDigits].substring(1);
var pt1 = s1.indexOf("E-");
if (pt1 > 0) {
n = JU.PT.parseInt(s1.substring(pt1 + 1));
s1 = "0." + "0000000000000000000000000000000000000000".substring(0, -n - 1) + s1.substring(0, 1) + s1.substring(2, pt1);
pt = 1;
}pt1 = s1.indexOf("E");
if (pt1 > 0) {
n = JU.PT.parseInt(s1.substring(pt1 + 1));
s1 = s1.substring(0, 1) + s1.substring(2, pt1) + "0000000000000000000000000000000000000000";
s1 = s1.substring(0, n + 1) + "." + s1.substring(n + 1);
pt = s1.indexOf(".");
}var len = s1.length;
var pt2 = decimalDigits + pt + 1;
if (pt2 < len && s1.charAt(pt2) >= '5') {
return JU.DF.formatDecimal((isNeg ? -1 : 1) * (value + JU.DF.formatAdds[decimalDigits]), decimalDigits);
}var s0 = s1.substring(0, (decimalDigits == 0 ? pt : ++pt));
var sb = JU.SB.newS(s0);
if (isNeg && s0.equals("0.") && decimalDigits + 2 <= len && s1.substring(2, 2 + decimalDigits).equals("0000000000000000000000000000000000000000".substring(0, decimalDigits))) isNeg = false;
for (var i = 0; i < decimalDigits; i++, pt++) {
if (pt < len) sb.appendC(s1.charAt(pt));
 else sb.appendC('0');
}
s1 = (isNeg ? "-" : "") + sb;
return (Boolean.TRUE.equals(JU.DF.useNumberLocalization[0]) ? s1 : s1.$replace(',', '.'));
}, "~N,~N");
c$.formatDecimalTrimmed = Clazz.defineMethod(c$, "formatDecimalTrimmed", 
function(x, precision){
var str = JU.DF.formatDecimalDbl(x, precision);
var m = str.length - 1;
var zero = '0';
while (m >= 0 && str.charAt(m) == zero) m--;

return str.substring(0, m + 1);
}, "~N,~N");
c$.formatDecimalTrimmed0 = Clazz.defineMethod(c$, "formatDecimalTrimmed0", 
function(x, precision){
var str = JU.DF.formatDecimalDbl(x, precision);
var m = str.length - 1;
var pt = str.indexOf(".") + 1;
while (m > pt && str.charAt(m) == '0') m--;

return str.substring(0, m + 1);
}, "~N,~N");
c$.formattingStrings =  Clazz.newArray(-1, ["0", "0.0", "0.00", "0.000", "0.0000", "0.00000", "0.000000", "0.0000000", "0.00000000", "0.000000000", "0.0000000000", "0.00000000000", "0.000000000000"]);
c$.formatAdds =  Clazz.newDoubleArray(-1, [0.5, 0.05, 0.005, 0.0005, 0.00005, 0.000005, 0.0000005, 0.00000005, 0.000000005, 0.0000000005, 0.00000000005, 0.000000000005, 0.0000000000005]);
c$.useNumberLocalization =  Clazz.newArray(-1, [Boolean.TRUE]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
