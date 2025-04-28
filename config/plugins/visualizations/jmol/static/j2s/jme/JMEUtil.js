Clazz.declarePackage("jme");
Clazz.load(null, "jme.JMEUtil", ["java.lang.reflect.Array", "java.util.StringTokenizer", "jme.JME"], function(){
var c$ = Clazz.declareType(jme, "JMEUtil", null);
c$.growArray = Clazz.defineMethod(c$, "growArray", 
function(array, newSize){
var newArray = jme.JMEUtil.createArray(newSize);
System.arraycopy(array, 0, newArray, 0, array.length);
return newArray;
}, "~A,~N");
c$.copyArray = Clazz.defineMethod(c$, "copyArray", 
function(array){
var copy =  Clazz.newIntArray (array.length, 0);
System.arraycopy(array, 0, copy, 0, array.length);
return copy;
}, "~A");
c$.growArray = Clazz.defineMethod(c$, "growArray", 
function(array, newSize){
var newArray = jme.JMEUtil.copyOf(array, newSize);
return newArray;
}, "~A,~N");
c$.copyOf = Clazz.defineMethod(c$, "copyOf", 
function(original, newLength){
return jme.JMEUtil.copyOf(original, newLength, original.getClass());
}, "~A,~N");
c$.copyOf = Clazz.defineMethod(c$, "copyOf", 
function(original, newLength, newType){
var copy = (newType === Array) ?  new Array(newLength) : java.lang.reflect.Array.newInstance(newType.getComponentType(), newLength);
System.arraycopy(original, 0, copy, 0, Math.min(original.length, newLength));
return copy;
}, "~A,~N,Class");
c$.growArray = Clazz.defineMethod(c$, "growArray", 
function(array, newSize){
var newArray = jme.JMEUtil.createSArray(newSize);
System.arraycopy(array, 0, newArray, 0, array.length);
return newArray;
}, "~A,~N");
c$.growArray = Clazz.defineMethod(c$, "growArray", 
function(array, newSize){
var newArray = jme.JMEUtil.createDArray(newSize);
System.arraycopy(array, 0, newArray, 0, array.length);
return newArray;
}, "~A,~N");
c$.growArray = Clazz.defineMethod(c$, "growArray", 
function(array, newSize){
var secondarySize = array[0].length;
var newArray = jme.JMEUtil.createArray(newSize, secondarySize);
System.arraycopy(array, 0, newArray, 0, array.length);
return newArray;
}, "~A,~N");
c$.equals = Clazz.defineMethod(c$, "equals", 
function(a1, a2){
if (a1.length == a2.length) {
for (var i = 0; i < a1.length; i++) {
if (a1[i] != a2[i]) {
return false;
}}
return true;
}return false;
}, "~A,~A");
c$.intersection = Clazz.defineMethod(c$, "intersection", 
function(array1, array2){
var common =  Clazz.newIntArray (0, 0);
for (var v1, $v1 = 0, $$v1 = array1; $v1 < $$v1.length && ((v1 = $$v1[$v1]) || true); $v1++) {
if (jme.JMEUtil.contains(array2, v1)) {
common = jme.JMEUtil.growArray(common, common.length + 1);
common[common.length - 1] = v1;
}}
return common;
}, "~A,~A");
c$.contains = Clazz.defineMethod(c$, "contains", 
function(array, v){
for (var each, $each = 0, $$each = array; $each < $$each.length && ((each = $$each[$each]) || true); $each++) {
if (each == v) {
return true;
}}
return false;
}, "~A,~N");
c$.swap = Clazz.defineMethod(c$, "swap", 
function(array, i, j){
var temp = array[j];
array[j] = array[i];
array[i] = temp;
}, "~A,~N,~N");
c$.copyArray = Clazz.defineMethod(c$, "copyArray", 
function(array, n){
var copy =  Clazz.newIntArray (array.length, 0);
System.arraycopy(array, 0, copy, 0, n);
return copy;
}, "~A,~N");
c$.copyArray = Clazz.defineMethod(c$, "copyArray", 
function(array){
var copy =  new Array(array.length);
System.arraycopy(array, 0, copy, 0, array.length);
return copy;
}, "~A");
c$.copyArray = Clazz.defineMethod(c$, "copyArray", 
function(array){
var copy =  Clazz.newDoubleArray (array.length, 0);
System.arraycopy(array, 0, copy, 0, array.length);
return copy;
}, "~A");
c$.createArray = Clazz.defineMethod(c$, "createArray", 
function(size){
return  Clazz.newIntArray (size, 0);
}, "~N");
c$.createSArray = Clazz.defineMethod(c$, "createSArray", 
function(size){
return  new Array(size);
}, "~N");
c$.createDArray = Clazz.defineMethod(c$, "createDArray", 
function(size){
return  Clazz.newDoubleArray (size, 0);
}, "~N");
c$.createLArray = Clazz.defineMethod(c$, "createLArray", 
function(size){
return  Clazz.newLongArray (size, 0);
}, "~N");
c$.createBArray = Clazz.defineMethod(c$, "createBArray", 
function(size){
return  Clazz.newBooleanArray(size, false);
}, "~N");
c$.createArray = Clazz.defineMethod(c$, "createArray", 
function(size1, size2){
return  Clazz.newIntArray (size1, size2, 0);
}, "~N,~N");
c$.isHighDPI = Clazz.defineMethod(c$, "isHighDPI", 
function(){
return false;
});
c$.runAsync = Clazz.defineMethod(c$, "runAsync", 
function(runAsyncCallback){
runAsyncCallback.onSuccess();
}, "jme.JMEUtil.RunAsyncCallback");
c$.generatePrimes = Clazz.defineMethod(c$, "generatePrimes", 
function(n){
var npn;
var pn = jme.JMEUtil.createLArray(n + 2);
var prime = jme.JMEUtil.createArray(100);
var test = 5;
var index = 0;
var num = 0;
var check = true;
prime[0] = 3;
pn[1] = 2;
pn[2] = 3;
npn = 2;
if (n < 3) return pn;
while (test < (prime[num] * prime[num])) {
index = 0;
check = true;
while (check == true && index <= num && test >= (prime[index] * prime[index])) {
if (test % prime[index] == 0) check = false;
 else index++;
}
if (check == true) {
pn[++npn] = test;
if (npn >= n) return pn;
if (num < (prime.length - 1)) {
num++;
prime[num] = test;
}}test += 2;
}
System.err.println("ERROR - Prime Number generator failed !");
return pn;
}, "~N");
c$.nextData = Clazz.defineMethod(c$, "nextData", 
function(st, separator){
while (st.hasMoreTokens()) {
var s = st.nextToken();
if (s.equals(separator)) return " ";
if (!st.nextToken().equals(separator)) {
System.err.println("mol file line separator problem!");
}while (true) {
var c = s.charAt(s.length - 1);
if (c == '|' || c == '\n' || c == '\r') {
s = s.substring(0, s.length - 1);
if (s.length == 0) return " ";
} else {
break;
}}
return s;
}
return null;
}, "java.util.StringTokenizer,~S");
c$.findLineSeparator = Clazz.defineMethod(c$, "findLineSeparator", 
function(molFile){
var st =  new java.util.StringTokenizer(molFile, "\n", true);
if (st.countTokens() > 4) return "\n";
st =  new java.util.StringTokenizer(molFile, "|", true);
if (st.countTokens() > 4) return "|";
System.err.println("Cannot process mol file, use | as line separator !");
return null;
}, "~S");
c$.squareEuclideanDist = Clazz.defineMethod(c$, "squareEuclideanDist", 
function(x1, y1, x2, y2){
var dx = x2 - x1;
var dy = y2 - y1;
return dx * dx + dy * dy;
}, "~N,~N,~N,~N");
c$.dotProduct = Clazz.defineMethod(c$, "dotProduct", 
function(x1, y1, x2, y2){
return x1 * x2 + y1 * y2;
}, "~N,~N,~N,~N");
c$.triangleHeight = Clazz.defineMethod(c$, "triangleHeight", 
function(a, b, c){
var s = (a + b + c) / 2;
var area = Math.sqrt(s * (s - a) * (s - b) * (s - c));
var h = 0;
if (b != 0) {
h = area / b * 2;
}return h;
}, "~N,~N,~N");
c$.compareAngles = Clazz.defineMethod(c$, "compareAngles", 
function(sina, cosa, sinb, cosb){
var qa = 0;
var qb = 0;
if (sina >= 0. && cosa >= 0.) qa = 1;
 else if (sina >= 0. && cosa < 0.) qa = 2;
 else if (sina < 0. && cosa < 0.) qa = 3;
 else if (sina < 0. && cosa >= 0.) qa = 4;
if (sinb >= 0. && cosb >= 0.) qb = 1;
 else if (sinb >= 0. && cosb < 0.) qb = 2;
 else if (sinb < 0. && cosb < 0.) qb = 3;
 else if (sinb < 0. && cosb >= 0.) qb = 4;
if (qa < qb) return 1;
 else if (qa > qb) return -1;
switch (qa) {
case 1:
case 4:
return (sina < sinb ? 1 : -1);
case 2:
case 3:
return (sina > sinb ? 1 : -1);
}
System.err.println("stereowarning #31");
return 0;
}, "~N,~N,~N,~N");
c$.stereoTransformation = Clazz.defineMethod(c$, "stereoTransformation", 
function(t, ref){
var d = 0;
if (ref[0] == t[1]) {
d = t[0];
t[0] = t[1];
t[1] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
} else if (ref[0] == t[2]) {
d = t[2];
t[2] = t[0];
t[0] = d;
d = t[1];
t[1] = t[3];
t[3] = d;
} else if (ref[0] == t[3]) {
d = t[3];
t[3] = t[0];
t[0] = d;
d = t[1];
t[1] = t[2];
t[2] = d;
}if (ref[1] == t[2]) {
d = t[1];
t[1] = t[2];
t[2] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
} else if (ref[1] == t[3]) {
d = t[1];
t[1] = t[3];
t[3] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
}}, "~A,~A");
c$.checkAtomicSymbol = Clazz.defineMethod(c$, "checkAtomicSymbol", 
function(s){
for (var an = 1; an < jme.JME.zlabel.length; an++) {
if (s.equals(jme.JME.zlabel[an])) return an;
}
return 18;
}, "~S");
c$.getSDFDateLine = Clazz.defineMethod(c$, "getSDFDateLine", 
function(version){
var mol = (version + "         ").substring(0, 10);
var cMM;
var cDD;
var cYYYY;
var cHH;
var cmm;
{
var c = new Date(); cMM = c.getMonth(); cDD = c.getDate(); cYYYY =
c.getFullYear(); cHH = c.getHours(); cmm = c.getMinutes();
}mol += jme.JMEUtil.rightJustify("00", "" + (1 + cMM));
mol += jme.JMEUtil.rightJustify("00", "" + cDD);
mol += ("" + cYYYY).substring(2, 4);
mol += jme.JMEUtil.rightJustify("00", "" + cHH);
mol += jme.JMEUtil.rightJustify("00", "" + cmm);
mol += "2D 1   1.00000     0.00000     0";
return mol;
}, "~S");
c$.iformat = Clazz.defineMethod(c$, "iformat", 
function(number, len){
return jme.JMEUtil.rightJustify("        ".substring(0, len), "" + number);
}, "~N,~N");
c$.rightJustify = Clazz.defineMethod(c$, "rightJustify", 
function(s1, s2){
var n = s1.length - s2.length;
return (n == 0 ? s2 : n > 0 ? s1.substring(0, n) + s2 : s1.substring(0, s1.length - 1) + "?");
}, "~S,~S");
c$.fformat = Clazz.defineMethod(c$, "fformat", 
function(number, len, dec){
if (dec == 0) return jme.JMEUtil.iformat(Clazz.doubleToInt(number), len);
if (Math.abs(number) < 0.0009) number = 0.;
var m = Math.pow(10, dec);
number = Math.round(number * m) / m;
var s =  new Double(number).toString();
var dotpos = s.indexOf('.');
if (dotpos < 0) {
s += ".";
dotpos = s.indexOf('.');
}var slen = s.length;
for (var i = 1; i <= dec - slen + dotpos + 1; i++) s += "0";

return (len == 0 ? s : jme.JMEUtil.rightJustify("        ".substring(0, len), s));
}, "~N,~N,~N");
c$.stringHeight = Clazz.defineMethod(c$, "stringHeight", 
function(fm){
return fm.getAscent() - fm.getDescent();
}, "java.awt.FontMetrics");
/*if3*/;(function(){
var c$ = Clazz.declareType(jme.JMEUtil, "GWT", null);
c$.isScript = Clazz.defineMethod(c$, "isScript", 
function(){
return false;
});
c$.log = Clazz.defineMethod(c$, "log", 
function(string){
}, "~S");
/*eoif3*/})();
Clazz.declareInterface(jme.JMEUtil, "RunAsyncCallback");
/*if3*/;(function(){
var c$ = Clazz.declareType(jme.JMEUtil, "JSME_RunAsyncCallback", null, jme.JMEUtil.RunAsyncCallback);
Clazz.overrideMethod(c$, "onFailure", 
function(reason){
}, "Throwable");
/*eoif3*/})();
Clazz.declareInterface(jme.JMEUtil, "RunWhenDataReadyCallback");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
