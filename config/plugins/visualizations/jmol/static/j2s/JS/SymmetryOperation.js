Clazz.declarePackage("JS");
Clazz.load(["JU.M4", "$.P3"], "JS.SymmetryOperation", ["java.util.Hashtable", "JU.Lst", "$.Matrix", "$.Measure", "$.P4", "$.PT", "$.SB", "$.V3", "JS.UnitCell", "JU.BoxInfo", "$.Logger", "$.Parser"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.xyzOriginal = null;
this.xyzCanonical = null;
this.xyz = null;
this.doNormalize = true;
this.isFinalized = false;
this.opId = 0;
this.centering = null;
this.info = null;
this.opType = -1;
this.opOrder = 0;
this.opTrans = null;
this.opGlide = null;
this.opPoint = null;
this.opPoint2 = null;
this.opAxis = null;
this.opPlane = null;
this.opIsCCW = null;
this.isIrrelevant = false;
this.iCoincident = 0;
this.myLabels = null;
this.modDim = 0;
this.linearRotTrans = null;
this.rsvs = null;
this.isBio = false;
this.sigma = null;
this.number = 0;
this.subsystemCode = null;
this.timeReversal = 0;
this.unCentered = false;
this.isCenteringOp = false;
this.magOp = 2147483647;
this.divisor = 12;
this.opX = null;
this.opAxisCode = null;
this.opIsLong = false;
Clazz.instantialize(this, arguments);}, JS, "SymmetryOperation", JU.M4);
Clazz.makeConstructor(c$, 
function(op, id, doNormalize){
Clazz.superConstructor (this, JS.SymmetryOperation, []);
this.doNormalize = doNormalize;
if (op == null) {
this.opId = id;
return;
}this.xyzOriginal = op.xyzOriginal;
this.xyz = op.xyz;
this.divisor = op.divisor;
this.opId = op.opId;
this.modDim = op.modDim;
this.myLabels = op.myLabels;
this.number = op.number;
this.linearRotTrans = op.linearRotTrans;
this.sigma = op.sigma;
this.subsystemCode = op.subsystemCode;
this.timeReversal = op.timeReversal;
this.setMatrix(false);
if (!op.isFinalized) this.doFinalize();
}, "JS.SymmetryOperation,~N,~B");
Clazz.defineMethod(c$, "getOpName", 
function(opMode){
if (this.opType == -1) this.setOpTypeAndOrder();
switch (this.opType) {
case 0:
return "I";
case 1:
return "Trans" + JS.SymmetryOperation.op48(this.opTrans);
case 2:
return "Rot" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + this.opIsCCW;
case 4:
return "Inv" + JS.SymmetryOperation.op48(this.opPoint);
case 8:
return (opMode == 0 ? "" : "Plane") + this.opPlane;
case 3:
return (opMode == 0 ? "S" + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) : "Screw" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + JS.SymmetryOperation.op48(this.opTrans) + this.opIsCCW);
case 6:
return "Nbar" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + this.opIsCCW;
case 9:
return (opMode == 0 ? "" : "Glide") + this.opPlane + (opMode == 2 ? JS.SymmetryOperation.op48(this.opTrans) : "");
}
System.out.println("SymmetryOperation REJECTED TYPE FOR " + this);
return "";
}, "~N");
Clazz.defineMethod(c$, "getOpTitle", 
function(){
if (this.opType == -1) this.setOpTypeAndOrder();
switch (this.opType) {
case 0:
return "identity ";
case 1:
return "translation " + JS.SymmetryOperation.opFrac(this.opTrans);
case 2:
return "rotation " + this.opOrder;
case 4:
return "inversion center " + JS.SymmetryOperation.opFrac(this.opPoint);
case 8:
return "reflection ";
case 3:
return "screw rotation " + this.opOrder + (this.opIsCCW == null ? "" : this.opIsCCW === Boolean.TRUE ? "(+) " : "(-) ") + JS.SymmetryOperation.opFrac(this.opTrans);
case 6:
return this.opOrder + "-bar " + (this.opIsCCW == null ? "" : this.opIsCCW === Boolean.TRUE ? "(+) " : "(-) ") + JS.SymmetryOperation.opFrac(this.opPoint);
case 9:
return "glide reflection " + JS.SymmetryOperation.opFrac(this.opTrans);
}
return "";
});
c$.opFrac = Clazz.defineMethod(c$, "opFrac", 
function(p){
return "{" + JS.SymmetryOperation.opF(p.x) + " " + JS.SymmetryOperation.opF(p.y) + " " + JS.SymmetryOperation.opF(p.z) + "}";
}, "JU.T3");
c$.opF = Clazz.defineMethod(c$, "opF", 
function(x){
if (x == 0) return "0";
var neg = (x < 0);
if (neg) {
x = -x;
}var n = 0;
if (x >= 1) {
n = Clazz.floatToInt(x);
x -= n;
}var n48 = Math.round(x * 48);
if (JU.PT.approx(n48 / 48 - x, 1000) != 0) return "" + JU.PT.approx(x, 1000);
var div;
if (n48 % 48 == 0) {
div = 1;
} else if (n48 % 24 == 0) {
div = 2;
} else if (n48 % 16 == 0) {
div = 3;
} else if (n48 % 12 == 0) {
div = 4;
} else if (n48 % 8 == 0) {
div = 6;
} else if (n48 % 6 == 0) {
div = 8;
} else if (n48 % 4 == 0) {
div = 12;
} else if (n48 % 3 == 0) {
div = 16;
} else if (n48 % 2 == 0) {
div = 24;
} else {
div = 48;
}return (neg ? "-" : "") + (n * div + Clazz.doubleToInt(n48 * div / 48)) + (div == 1 ? "" : "/" + div);
}, "~N");
c$.op48 = Clazz.defineMethod(c$, "op48", 
function(p){
if (p == null) {
System.err.println("SymmetryOperation.op48 null");
return "(null)";
}return "{" + Math.round(p.x * 48) + " " + Math.round(p.y * 48) + " " + Math.round(p.z * 48) + "}";
}, "JU.T3");
Clazz.defineMethod(c$, "setSigma", 
function(subsystemCode, sigma){
this.subsystemCode = subsystemCode;
this.sigma = sigma;
}, "~S,JU.Matrix");
Clazz.defineMethod(c$, "setGamma", 
function(isReverse){
var n = 3 + this.modDim;
var a = (this.rsvs =  new JU.Matrix(null, n + 1, n + 1)).getArray();
var t =  Clazz.newDoubleArray (n, 0);
var pt = 0;
for (var i = 0; i < n; i++) {
for (var j = 0; j < n; j++) a[i][j] = this.linearRotTrans[pt++];

t[i] = (isReverse ? -1 : 1) * this.linearRotTrans[pt++];
}
a[n][n] = 1;
if (isReverse) this.rsvs = this.rsvs.inverse();
for (var i = 0; i < n; i++) a[i][n] = t[i];

a = this.rsvs.getSubmatrix(0, 0, 3, 3).getArray();
for (var i = 0; i < 3; i++) for (var j = 0; j < 4; j++) this.setElement(i, j, (j < 3 ? a[i][j] : t[i]));


this.setElement(3, 3, 1);
}, "~B");
Clazz.defineMethod(c$, "doFinalize", 
function(){
JS.SymmetryOperation.div12(this, this.divisor);
if (this.modDim > 0) {
var a = this.rsvs.getArray();
for (var i = a.length - 1; --i >= 0; ) a[i][3 + this.modDim] = JS.SymmetryOperation.finalizeD(a[i][3 + this.modDim], this.divisor);

}this.isFinalized = true;
});
c$.div12 = Clazz.defineMethod(c$, "div12", 
function(op, divisor){
op.m03 = JS.SymmetryOperation.finalizeF(op.m03, divisor);
op.m13 = JS.SymmetryOperation.finalizeF(op.m13, divisor);
op.m23 = JS.SymmetryOperation.finalizeF(op.m23, divisor);
return op;
}, "JU.M4,~N");
c$.finalizeF = Clazz.defineMethod(c$, "finalizeF", 
function(m, divisor){
if (divisor == 0) {
if (m == 0) return 0;
var n = Clazz.floatToInt(m);
return ((n >> 8) * 1 / (n & 255));
}return m / divisor;
}, "~N,~N");
c$.finalizeD = Clazz.defineMethod(c$, "finalizeD", 
function(m, divisor){
if (divisor == 0) {
if (m == 0) return 0;
var n = Clazz.doubleToInt(m);
return ((n >> 8) * 1 / (n & 255));
}return m / divisor;
}, "~N,~N");
Clazz.defineMethod(c$, "getXyz", 
function(normalized){
return (normalized && this.modDim == 0 || this.xyzOriginal == null ? this.xyz : this.xyzOriginal);
}, "~B");
Clazz.defineMethod(c$, "getxyzTrans", 
function(t){
var m = JU.M4.newM4(this);
m.add(t);
return JS.SymmetryOperation.getXYZFromMatrix(m, false, false, false);
}, "JU.T3");
Clazz.defineMethod(c$, "dumpInfo", 
function(){
return "\n" + this.xyz + "\ninternal matrix representation:\n" + this.toString();
});
c$.dumpSeitz = Clazz.defineMethod(c$, "dumpSeitz", 
function(s, isCanonical){
var sb =  new JU.SB();
var r =  Clazz.newFloatArray (4, 0);
for (var i = 0; i < 3; i++) {
s.getRow(i, r);
sb.append("[\t");
for (var j = 0; j < 3; j++) sb.appendI(Clazz.floatToInt(r[j])).append("\t");

var trans = r[3];
trans *= (trans == Clazz.floatToInt(trans) ? 4 : 48);
sb.append(JS.SymmetryOperation.twelfthsOf(isCanonical ? JS.SymmetryOperation.normalizeTwelfths(trans / 48, 48, true) : Clazz.floatToInt(trans))).append("\t]\n");
}
return sb.toString();
}, "JU.M4,~B");
Clazz.defineMethod(c$, "setMatrixFromXYZ", 
function(xyz, modDim, allowScaling){
if (xyz == null) return false;
this.xyzOriginal = xyz;
this.divisor = JS.SymmetryOperation.setDivisor(xyz);
xyz = xyz.toLowerCase();
this.setModDim(modDim);
var isReverse = false;
var halfOrLess = true;
if (xyz.startsWith("!")) {
if (xyz.startsWith("!nohalf!")) {
halfOrLess = false;
xyz = xyz.substring(8);
this.xyzOriginal = xyz;
} else {
isReverse = false;
xyz = xyz.substring(1);
}}if (xyz.indexOf("xyz matrix:") == 0) {
this.xyz = xyz;
JU.Parser.parseStringInfestedFloatArray(xyz, null, this.linearRotTrans);
return this.setFromMatrix(null, isReverse);
}if (xyz.indexOf("[[") == 0) {
xyz = xyz.$replace('[', ' ').$replace(']', ' ').$replace(',', ' ');
JU.Parser.parseStringInfestedFloatArray(xyz, null, this.linearRotTrans);
for (var i = this.linearRotTrans.length; --i >= 0; ) if (Float.isNaN(this.linearRotTrans[i])) return false;

this.setMatrix(isReverse);
this.isFinalized = true;
this.isBio = (xyz.indexOf("bio") >= 0);
this.xyz = (this.isBio ? (this.xyzOriginal = Clazz.superCall(this, JS.SymmetryOperation, "toString", [])) : JS.SymmetryOperation.getXYZFromMatrix(this, false, false, false));
return true;
}if (modDim == 0 && xyz.indexOf("x4") >= 0) {
for (var i = 14; --i >= 4; ) {
if (xyz.indexOf("x" + i) >= 0) {
this.setModDim(i - 3);
break;
}}
}var mxyz = null;
if (xyz.endsWith("m")) {
this.timeReversal = (xyz.indexOf("-m") >= 0 ? -1 : 1);
allowScaling = true;
} else if (xyz.indexOf("mz)") >= 0) {
var pt = xyz.indexOf("(");
mxyz = xyz.substring(pt + 1, xyz.length - 1);
xyz = xyz.substring(0, pt);
allowScaling = false;
}var strOut = JS.SymmetryOperation.getMatrixFromString(this, xyz, this.linearRotTrans, allowScaling, halfOrLess, true);
if (strOut == null) return false;
this.xyzCanonical = strOut;
if (mxyz != null) {
var isProper = (JU.M4.newA16(this.linearRotTrans).determinant3() == 1);
this.timeReversal = (((xyz.indexOf("-x") < 0) == (mxyz.indexOf("-mx") < 0)) == isProper ? 1 : -1);
}this.setMatrix(isReverse);
this.xyz = (isReverse ? JS.SymmetryOperation.getXYZFromMatrix(this, true, false, false) : this.doNormalize ? strOut : xyz);
if (this.timeReversal != 0) this.xyz += (this.timeReversal == 1 ? ",m" : ",-m");
if (JU.Logger.debugging) JU.Logger.debug("" + this);
return true;
}, "~S,~N,~B");
c$.setDivisor = Clazz.defineMethod(c$, "setDivisor", 
function(xyz){
var pt = xyz.indexOf('/');
var len = xyz.length;
while (pt > 0 && pt < len - 1) {
var c = xyz.charAt(pt + 1);
if ("2346".indexOf(c) < 0 || pt < len - 2 && Character.isDigit(xyz.charAt(pt + 2))) {
return 0;
}pt = xyz.indexOf('/', pt + 1);
}
return 12;
}, "~S");
Clazz.defineMethod(c$, "setModDim", 
function(dim){
var n = (dim + 4) * (dim + 4);
this.modDim = dim;
if (dim > 0) this.myLabels = JS.SymmetryOperation.labelsXn;
this.linearRotTrans =  Clazz.newFloatArray (n, 0);
}, "~N");
Clazz.defineMethod(c$, "setMatrix", 
function(isReverse){
if (this.linearRotTrans.length > 16) {
this.setGamma(isReverse);
} else {
this.setA(this.linearRotTrans);
if (isReverse) {
var p3 = JU.P3.new3(this.m03, this.m13, this.m23);
this.invert();
this.rotate(p3);
p3.scale(-1);
this.setTranslation(p3);
}}}, "~B");
Clazz.defineMethod(c$, "setFromMatrix", 
function(offset, isReverse){
var v = 0;
var pt = 0;
this.myLabels = (this.modDim == 0 ? JS.SymmetryOperation.labelsXYZ : JS.SymmetryOperation.labelsXn);
var rowPt = 0;
var n = 3 + this.modDim;
for (var i = 0; rowPt < n; i++) {
if (Float.isNaN(this.linearRotTrans[i])) return false;
v = this.linearRotTrans[i];
if (Math.abs(v) < 0.00001) v = 0;
var isTrans = ((i + 1) % (n + 1) == 0);
if (isTrans) {
var denom = (this.divisor == 0 ? (Clazz.floatToInt(v)) & 255 : this.divisor);
if (denom == 0) denom = 12;
v = JS.SymmetryOperation.finalizeF(v, this.divisor);
if (offset != null) {
if (pt < offset.length) v += offset[pt++];
}v = JS.SymmetryOperation.normalizeTwelfths(((v < 0 ? -1 : 1) * Math.abs(v * denom) / denom), denom, this.doNormalize);
if (this.divisor == 0) v = JS.SymmetryOperation.toDivisor(v, denom);
rowPt++;
}this.linearRotTrans[i] = v;
}
this.linearRotTrans[this.linearRotTrans.length - 1] = this.divisor;
this.setMatrix(isReverse);
this.isFinalized = (offset == null);
this.xyz = JS.SymmetryOperation.getXYZFromMatrix(this, true, false, false);
return true;
}, "~A,~B");
c$.getMatrixFromXYZ = Clazz.defineMethod(c$, "getMatrixFromXYZ", 
function(xyz, v, halfOrLess){
if (v == null) v =  Clazz.newFloatArray (16, 0);
xyz = JS.SymmetryOperation.getMatrixFromString(null, xyz, v, false, halfOrLess, true);
if (xyz == null) return null;
var m =  new JU.M4();
m.setA(v);
return JS.SymmetryOperation.div12(m, JS.SymmetryOperation.setDivisor(xyz));
}, "~S,~A,~B");
c$.getJmolCanonicalXYZ = Clazz.defineMethod(c$, "getJmolCanonicalXYZ", 
function(xyz){
try {
return JS.SymmetryOperation.getMatrixFromString(null, xyz, null, false, true, true);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "~S");
c$.getMatrixFromString = Clazz.defineMethod(c$, "getMatrixFromString", 
function(op, xyz, linearRotTrans, allowScaling, halfOrLess, retString){
var isDenominator = false;
var isDecimal = false;
var isNegative = false;
xyz = JU.PT.rep(xyz, "[bio[", "");
var modDim = (op == null ? 0 : op.modDim);
var nRows = 4 + modDim;
var divisor = (op == null ? JS.SymmetryOperation.setDivisor(xyz) : op.divisor);
var doNormalize = halfOrLess && (op == null ? !xyz.startsWith("!") : op.doNormalize);
var dimOffset = (modDim > 0 ? 3 : 0);
if (linearRotTrans != null) {
var n = linearRotTrans.length - 1;
for (var i = n; --i >= 0; ) linearRotTrans[i] = 0;

linearRotTrans[n] = 1;
}var transPt = xyz.indexOf(';') + 1;
if (transPt != 0) {
allowScaling = true;
if (transPt == xyz.length) xyz += "0,0,0";
}var rotPt = -1;
var myLabels = (op == null || modDim == 0 ? null : op.myLabels);
if (myLabels == null) myLabels = JS.SymmetryOperation.labelsXYZ;
xyz = xyz.toLowerCase() + ",";
xyz = xyz.$replace('(', ',');
if (modDim > 0) xyz = JS.SymmetryOperation.replaceXn(xyz, modDim + 3);
var xpt = 0;
var tpt0 = 0;
var rowPt = 0;
var ch;
var iValue = 0;
var denom = 0;
var numer = 0;
var decimalMultiplier = 1;
var strT = "";
var strOut = (retString ? "" : null);
var ret =  Clazz.newIntArray (1, 0);
var len = xyz.length;
for (var i = 0; i < len; i++) {
switch ((ch = xyz.charAt(i)).charCodeAt(0)) {
case 59:
break;
case 39:
case 32:
case 123:
case 125:
case 33:
continue;
case 45:
isNegative = true;
continue;
case 43:
isNegative = false;
continue;
case 47:
denom = 0;
isDenominator = true;
continue;
case 120:
case 121:
case 122:
case 97:
case 98:
case 99:
case 100:
case 101:
case 102:
case 103:
case 104:
tpt0 = rowPt * nRows;
var ipt = (ch >= 'x' ? ch.charCodeAt(0) - 120 : ch.charCodeAt(0) - 97 + dimOffset);
xpt = tpt0 + ipt;
var val = (isNegative ? -1 : 1);
if (allowScaling && iValue != 0) {
if (linearRotTrans != null) linearRotTrans[xpt] = iValue;
val = Clazz.floatToInt(iValue);
iValue = 0;
} else if (linearRotTrans != null) {
linearRotTrans[xpt] = val;
}if (strOut != null) strT += JS.SymmetryOperation.plusMinus(strT, val, myLabels[ipt], false);
break;
case 44:
if (transPt != 0) {
if (transPt > 0) {
rotPt = i;
i = transPt - 1;
transPt = -i;
iValue = 0;
denom = 0;
continue;
}transPt = i + 1;
i = rotPt;
}iValue = JS.SymmetryOperation.normalizeTwelfths(iValue, denom == 0 ? 12 : divisor == 0 ? denom : divisor, doNormalize);
if (linearRotTrans != null) linearRotTrans[tpt0 + nRows - 1] = (divisor == 0 && denom > 0 ? iValue = JS.SymmetryOperation.toDivisor(numer, denom) : iValue);
if (strOut != null) {
strT += JS.SymmetryOperation.xyzFraction12(iValue, (divisor == 0 ? denom : divisor), false, halfOrLess);
strOut += (strOut === "" ? "" : ",") + strT;
}if (rowPt == nRows - 2) return (retString ? strOut : "ok");
iValue = 0;
numer = 0;
denom = 0;
strT = "";
tpt0 += 4;
if (rowPt++ > 2 && modDim == 0) {
JU.Logger.warn("Symmetry Operation? " + xyz);
return null;
}break;
case 46:
isDecimal = true;
decimalMultiplier = 1;
continue;
case 48:
if (!isDecimal && divisor == 12 && (isDenominator || !allowScaling)) continue;
default:
var ich = ch.charCodeAt(0) - 48;
if (ich >= 0 && ich <= 9) {
if (isDecimal) {
decimalMultiplier /= 10;
if (iValue < 0) isNegative = true;
iValue += decimalMultiplier * ich * (isNegative ? -1 : 1);
continue;
}if (isDenominator) {
ret[0] = i;
denom = JU.PT.parseIntNext(xyz, ret);
if (denom < 0) return null;
i = ret[0] - 1;
if (iValue == 0) {
if (linearRotTrans != null) linearRotTrans[xpt] /= denom;
} else {
numer = Clazz.floatToInt(iValue);
iValue /= denom;
}} else {
iValue = iValue * 10 + (isNegative ? -1 : 1) * ich;
isNegative = false;
}} else {
JU.Logger.warn("symmetry character?" + ch);
}}
isDecimal = isDenominator = isNegative = false;
}
return null;
}, "JS.SymmetryOperation,~S,~A,~B,~B,~B");
c$.replaceXn = Clazz.defineMethod(c$, "replaceXn", 
function(xyz, n){
for (var i = n; --i >= 0; ) xyz = JU.PT.rep(xyz, JS.SymmetryOperation.labelsXn[i], JS.SymmetryOperation.labelsXnSub[i]);

return xyz;
}, "~S,~N");
c$.toDivisor = Clazz.defineMethod(c$, "toDivisor", 
function(numer, denom){
var n = Clazz.floatToInt(numer);
if (n != numer) {
var f = numer - n;
denom = Clazz.floatToInt(Math.abs(denom / f));
n = Clazz.floatToInt(Math.abs(numer) / f);
}return ((n << 8) + denom);
}, "~N,~N");
c$.xyzFraction12 = Clazz.defineMethod(c$, "xyzFraction12", 
function(n12ths, denom, allPositive, halfOrLess){
if (n12ths == 0) return "";
var n = n12ths;
if (denom != 12) {
var $in = Clazz.floatToInt(n);
denom = ($in & 255);
n = $in >> 8;
}var half = (Clazz.doubleToInt(denom / 2));
if (allPositive) {
while (n < 0) n += denom;

} else if (halfOrLess) {
while (n > half) n -= denom;

while (n < -half) n += denom;

}var s = (denom == 12 ? JS.SymmetryOperation.twelfthsOf(n) : n == 0 ? "0" : n + "/" + denom);
return (s.charAt(0) == '0' ? "" : n > 0 ? "+" + s : s);
}, "~N,~N,~B,~B");
c$.twelfthsOf = Clazz.defineMethod(c$, "twelfthsOf", 
function(n12ths){
var str = "";
if (n12ths < 0) {
n12ths = -n12ths;
str = "-";
}var m = 12;
var n = Math.round(n12ths);
if (Math.abs(n - n12ths) > 0.01) {
var f = n12ths / 12;
var max = 20;
for (m = 3; m < max; m++) {
var fm = f * m;
n = Math.round(fm);
if (Math.abs(n - fm) < 0.01) break;
}
if (m == max) return str + f;
} else {
if (n == 12) return str + "1";
if (n < 12) return str + JS.SymmetryOperation.twelfths[n % 12];
switch (n % 12) {
case 0:
return str + Clazz.doubleToInt(n / 12);
case 2:
case 10:
m = 6;
break;
case 3:
case 9:
m = 4;
break;
case 4:
case 8:
m = 3;
break;
case 6:
m = 2;
break;
default:
break;
}
n = (Clazz.doubleToInt(n * m / 12));
}return str + n + "/" + m;
}, "~N");
c$.plusMinus = Clazz.defineMethod(c$, "plusMinus", 
function(strT, x, sx, allowFractions){
var a;
return (x == 0 ? "" : (x < 0 ? "-" : strT.length == 0 ? "" : "+") + (x == 1 || x == -1 ? "" : (a = Math.abs(x)) < 1 && allowFractions ? JS.SymmetryOperation.twelfthsOf(a * 12) : "" + Clazz.floatToInt(a))) + sx;
}, "~S,~N,~S,~B");
c$.normalizeTwelfths = Clazz.defineMethod(c$, "normalizeTwelfths", 
function(iValue, divisor, doNormalize){
iValue *= divisor;
var half = Clazz.doubleToInt(divisor / 2);
if (doNormalize) {
while (iValue > half) iValue -= divisor;

while (iValue <= -half) iValue += divisor;

}return iValue;
}, "~N,~N,~B");
c$.getXYZFromMatrix = Clazz.defineMethod(c$, "getXYZFromMatrix", 
function(mat, is12ths, allPositive, halfOrLess){
return JS.SymmetryOperation.getXYZFromMatrixFrac(mat, is12ths, allPositive, halfOrLess, false);
}, "JU.M4,~B,~B,~B");
c$.getXYZFromMatrixFrac = Clazz.defineMethod(c$, "getXYZFromMatrixFrac", 
function(mat, is12ths, allPositive, halfOrLess, allowFractions){
var str = "";
var op = (Clazz.instanceOf(mat,"JS.SymmetryOperation") ? mat : null);
if (op != null && op.modDim > 0) return JS.SymmetryOperation.getXYZFromRsVs(op.rsvs.getRotation(), op.rsvs.getTranslation(), is12ths);
var row =  Clazz.newFloatArray (4, 0);
var denom = Clazz.floatToInt(mat.getElement(3, 3));
if (denom == 1) denom = 12;
 else mat.setElement(3, 3, 1);
for (var i = 0; i < 3; i++) {
var lpt = (i < 3 ? 0 : 3);
mat.getRow(i, row);
var term = "";
for (var j = 0; j < 3; j++) {
var x = row[j];
if (JS.SymmetryOperation.approx(x) != 0) {
term += JS.SymmetryOperation.plusMinus(term, x, JS.SymmetryOperation.labelsXYZ[j + lpt], allowFractions);
}}
if ((is12ths ? row[3] : JS.SymmetryOperation.approx(row[3])) != 0) {
var f = JS.SymmetryOperation.xyzFraction12((is12ths ? row[3] : row[3] * denom), denom, allPositive, halfOrLess);
if (term === "") f = (f.charAt(0) == '+' ? f.substring(1) : f);
term += f;
}str += "," + (term === "" ? "0" : term);
}
return str.substring(1);
}, "JU.M4,~B,~B,~B,~B");
Clazz.defineMethod(c$, "rotateAxes", 
function(vectors, unitcell, ptTemp, mTemp){
var vRot =  new Array(3);
this.getRotationScale(mTemp);
for (var i = vectors.length; --i >= 0; ) {
ptTemp.setT(vectors[i]);
unitcell.toFractional(ptTemp, true);
mTemp.rotate(ptTemp);
unitcell.toCartesian(ptTemp, true);
vRot[i] = JU.V3.newV(ptTemp);
}
return vRot;
}, "~A,JS.UnitCell,JU.P3,JU.M3");
c$.fcoord = Clazz.defineMethod(c$, "fcoord", 
function(p, sep){
return JS.SymmetryOperation.opF(p.x) + sep + JS.SymmetryOperation.opF(p.y) + sep + JS.SymmetryOperation.opF(p.z);
}, "JU.T3,~S");
c$.approx = Clazz.defineMethod(c$, "approx", 
function(f){
return JU.PT.approx(f, 100);
}, "~N");
c$.approx6 = Clazz.defineMethod(c$, "approx6", 
function(f){
return JU.PT.approx(f, 1000000);
}, "~N");
c$.getXYZFromRsVs = Clazz.defineMethod(c$, "getXYZFromRsVs", 
function(rs, vs, is12ths){
var ra = rs.getArray();
var va = vs.getArray();
var d = ra.length;
var s = "";
for (var i = 0; i < d; i++) {
s += ",";
for (var j = 0; j < d; j++) {
var r = ra[i][j];
if (r != 0) {
s += (r < 0 ? "-" : s.endsWith(",") ? "" : "+") + (Math.abs(r) == 1 ? "" : "" + Math.abs(r)) + "x" + (j + 1);
}}
s += JS.SymmetryOperation.xyzFraction12(Clazz.doubleToInt(va[i][0] * (is12ths ? 1 : 12)), 12, false, true);
}
return JU.PT.rep(s.substring(1), ",+", ",");
}, "JU.Matrix,JU.Matrix,~B");
Clazz.defineMethod(c$, "toString", 
function(){
return (this.rsvs == null ? Clazz.superCall(this, JS.SymmetryOperation, "toString", []) : Clazz.superCall(this, JS.SymmetryOperation, "toString", []) + " " + this.rsvs.toString());
});
Clazz.defineMethod(c$, "getMagneticOp", 
function(){
return (this.magOp == 2147483647 ? this.magOp = Clazz.floatToInt(this.determinant3() * this.timeReversal) : this.magOp);
});
Clazz.defineMethod(c$, "setTimeReversal", 
function(magRev){
this.timeReversal = magRev;
if (this.xyz.indexOf("m") >= 0) this.xyz = this.xyz.substring(0, this.xyz.indexOf("m"));
if (magRev != 0) {
this.xyz += (magRev == 1 ? ",m" : ",-m");
}}, "~N");
Clazz.defineMethod(c$, "getCentering", 
function(){
if (!this.isFinalized) this.doFinalize();
if (this.centering == null && !this.unCentered) {
if (this.modDim == 0 && this.m00 == 1 && this.m11 == 1 && this.m22 == 1 && this.m01 == 0 && this.m02 == 0 && this.m10 == 0 && this.m12 == 0 && this.m20 == 0 && this.m21 == 0 && (this.m03 != 0 || this.m13 != 0 || this.m23 != 0)) {
this.isCenteringOp = true;
this.centering = JU.V3.new3(this.m03, this.m13, this.m23);
} else {
this.unCentered = true;
this.centering = null;
}}return this.centering;
});
Clazz.defineMethod(c$, "fixMagneticXYZ", 
function(m, xyz, addMag){
if (this.timeReversal == 0) return xyz;
var pt = xyz.indexOf("m");
pt -= Clazz.doubleToInt((3 - this.timeReversal) / 2);
xyz = (pt < 0 ? xyz : xyz.substring(0, pt));
if (!addMag) return xyz + (this.timeReversal > 0 ? " +1" : " -1");
var m2 = JU.M4.newM4(m);
m2.m03 = m2.m13 = m2.m23 = 0;
if (this.getMagneticOp() < 0) m2.scale(-1);
xyz += "(" + JU.PT.rep(JU.PT.rep(JU.PT.rep(JS.SymmetryOperation.getXYZFromMatrix(m2, false, false, false), "x", "mx"), "y", "my"), "z", "mz") + ")";
return xyz;
}, "JU.M4,~S,~B");
Clazz.defineMethod(c$, "getInfo", 
function(){
if (this.info == null) {
this.info =  new java.util.Hashtable();
this.info.put("xyz", this.xyz);
if (this.centering != null) this.info.put("centering", this.centering);
this.info.put("index", Integer.$valueOf(this.number - 1));
this.info.put("isCenteringOp", Boolean.$valueOf(this.isCenteringOp));
if (this.linearRotTrans != null) this.info.put("linearRotTrans", this.linearRotTrans);
this.info.put("modulationDimension", Integer.$valueOf(this.modDim));
this.info.put("matrix", JU.M4.newM4(this));
if (this.magOp != 3.4028235E38) this.info.put("magOp", Float.$valueOf(this.magOp));
this.info.put("id", Integer.$valueOf(this.opId));
this.info.put("timeReversal", Integer.$valueOf(this.timeReversal));
if (this.xyzOriginal != null) this.info.put("xyzOriginal", this.xyzOriginal);
}return this.info;
});
c$.normalizeOperationToCentroid = Clazz.defineMethod(c$, "normalizeOperationToCentroid", 
function(dim, m, fracPts, i0, n){
if (n <= 0) return;
var x = 0;
var y = 0;
var z = 0;
if (JS.SymmetryOperation.atomTest == null) JS.SymmetryOperation.atomTest =  new JU.P3();
for (var i = i0, i2 = i + n; i < i2; i++) {
m.rotTrans2(fracPts[i], JS.SymmetryOperation.atomTest);
x += JS.SymmetryOperation.atomTest.x;
y += JS.SymmetryOperation.atomTest.y;
z += JS.SymmetryOperation.atomTest.z;
}
x /= n;
y /= n;
z /= n;
while (x < -0.001 || x >= 1.001) {
m.m03 += (x < 0 ? 1 : -1);
x += (x < 0 ? 1 : -1);
}
if (dim > 1) while (y < -0.001 || y >= 1.001) {
m.m13 += (y < 0 ? 1 : -1);
y += (y < 0 ? 1 : -1);
}
if (dim > 2) while (z < -0.001 || z >= 1.001) {
m.m23 += (z < 0 ? 1 : -1);
z += (z < 0 ? 1 : -1);
}
}, "~N,JU.M4,~A,~N,~N");
c$.getLatticeCentering = Clazz.defineMethod(c$, "getLatticeCentering", 
function(ops){
var list =  new JU.Lst();
for (var i = 0; i < ops.length; i++) {
var c = (ops[i] == null ? null : ops[i].getCentering());
if (c != null) list.addLast(JU.P3.newP(c));
}
return list;
}, "~A");
Clazz.defineMethod(c$, "getOpIsCCW", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opIsCCW;
});
Clazz.defineMethod(c$, "getOpType", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opType;
});
Clazz.defineMethod(c$, "getOpOrder", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opOrder;
});
Clazz.defineMethod(c$, "getOpPoint", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opPoint;
});
Clazz.defineMethod(c$, "getOpAxis", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opAxis;
});
Clazz.defineMethod(c$, "getOpPoint2", 
function(){
return this.opPoint2;
});
Clazz.defineMethod(c$, "getOpTrans", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return (this.opTrans == null ? (this.opTrans =  new JU.V3()) : this.opTrans);
});
c$.opGet3code = Clazz.defineMethod(c$, "opGet3code", 
function(m){
var c = 0;
var row =  Clazz.newFloatArray (4, 0);
for (var r = 0; r < 3; r++) {
m.getRow(r, row);
for (var i = 0; i < 3; i++) {
switch (Clazz.floatToInt(row[i])) {
case 1:
c |= (i + 1) << ((2 - r) << 3);
break;
case -1:
c |= (0x10 + i + 1) << ((2 - r) << 3);
break;
}
}
}
return c;
}, "JU.M4");
c$.opGet3x = Clazz.defineMethod(c$, "opGet3x", 
function(m){
if (m.m22 != 0) return JS.SymmetryOperation.x;
var c = JS.SymmetryOperation.opGet3code(m);
for (var i = 0; i < 8; i++) if (c == JS.SymmetryOperation.C3codes[i]) {
if (JS.SymmetryOperation.xneg == null) {
JS.SymmetryOperation.xneg = JU.V3.newV(JS.SymmetryOperation.x);
JS.SymmetryOperation.xneg.scale(-1);
}return JS.SymmetryOperation.xneg;
}
return JS.SymmetryOperation.x;
}, "JU.M4");
Clazz.defineMethod(c$, "setOpTypeAndOrder", 
function(){
this.clearOp();
var det = Math.round(this.determinant3());
var trace = Math.round(this.m00 + this.m11 + this.m22);
var order = 0;
var angle = 0;
var px = JS.SymmetryOperation.x;
switch (trace) {
case 3:
if (JS.SymmetryOperation.hasTrans(this)) {
this.opType = 1;
this.opTrans =  new JU.V3();
this.getTranslation(this.opTrans);
this.opOrder = 2;
} else {
this.opType = 0;
this.opOrder = 1;
}return;
case -3:
this.opType = 4;
order = 2;
break;
default:
order = trace * det + 3;
if (order == 5) order = 6;
if (det > 0) {
this.opType = 2;
angle = Clazz.doubleToInt(Math.acos((trace - 1) / 2) * 180 / 3.141592653589793);
if (angle == 120) {
if (this.opX == null) this.opX = JS.SymmetryOperation.opGet3x(this);
px = this.opX;
}} else {
if (order == 2) {
this.opType = 8;
} else {
this.opType = 6;
if (order == 3) order = 6;
angle = Clazz.doubleToInt(Math.acos((-trace - 1) / 2) * 180 / 3.141592653589793);
if (angle == 120) {
if (this.opX == null) this.opX = JS.SymmetryOperation.opGet3x(this);
px = this.opX;
}}}break;
}
this.opOrder = order;
var m4 =  new JU.M4();
var p1 =  new JU.P3();
var p2 = JU.P3.newP(px);
m4.setM4(this);
var p1sum =  new JU.P3();
var p2sum = JU.P3.newP(p2);
var p2odd =  new JU.P3();
var p2even = JU.P3.newP(p2);
var p21 =  new JU.P3();
for (var i = 1; i < order; i++) {
m4.mul(this);
this.rotTrans(p1);
this.rotTrans(p2);
if (i == 1) p21.setT(p2);
p1sum.add(p1);
p2sum.add(p2);
if (this.opType == 6) {
if (i % 2 == 0) {
p2even.add(p2);
} else {
p2odd.add(p2);
}}}
this.opTrans =  new JU.V3();
m4.getTranslation(this.opTrans);
this.opTrans.scale(1 / order);
var d = JS.SymmetryOperation.approx6(this.opTrans.length());
this.opPoint =  new JU.P3();
var v = null;
var isOK = true;
switch (this.opType) {
case 4:
p2sum.add2(p2, px);
p2sum.scale(0.5);
this.opPoint = JU.P3.newP(JS.SymmetryOperation.opClean6(p2sum));
isOK = JS.SymmetryOperation.checkOpPoint(this.opPoint);
break;
case 6:
p2odd.scale(2 / order);
p2even.scale(2 / order);
v = JU.V3.newVsub(p2odd, p2even);
v.normalize();
this.opAxis = JS.SymmetryOperation.opClean6(v);
p1sum.add2(p2odd, p2even);
p2sum.scale(1 / order);
this.opPoint.setT(JS.SymmetryOperation.opClean6(p2sum));
isOK = JS.SymmetryOperation.checkOpPoint(this.opPoint);
if (angle != 180) {
p2.cross(px, p2);
this.opIsCCW = Boolean.$valueOf(p2.dot(v) < 0);
}break;
case 2:
v = JU.V3.newVsub(p2sum, p1sum);
v.normalize();
this.opAxis = JS.SymmetryOperation.opClean6(v);
p1sum.scale(1 / order);
p1.setT(p1sum);
if (d > 0) {
p1sum.sub(this.opTrans);
}this.opPoint.setT(p1sum);
JS.SymmetryOperation.opClean6(this.opPoint);
if (angle != 180) {
p2.cross(px, p2);
this.opIsCCW = Boolean.$valueOf(p2.dot(v) < 0);
}isOK = new Boolean (isOK & JS.SymmetryOperation.checkOpAxis(p1, (d == 0 ? this.opAxis : this.opTrans), p1sum,  new JU.V3(),  new JU.V3(), null)).valueOf();
if (isOK) {
this.opPoint.setT(p1sum);
if (JS.SymmetryOperation.checkOpAxis(this.opPoint, this.opAxis, p2,  new JU.V3(),  new JU.V3(), this.opPoint)) {
this.opPoint2 = JU.P3.newP(p2);
}if (d > 0) {
p1sum.scaleAdd2(0.5, this.opTrans, this.opPoint);
isOK = JS.SymmetryOperation.checkOpPoint(p1sum);
if (this.opPoint2 != null) {
p1sum.scaleAdd2(0.5, this.opTrans, this.opPoint2);
if (!JS.SymmetryOperation.checkOpPoint(p1sum)) this.opPoint2 = null;
}if (v.dot(p1) < 0) {
isOK = false;
}}}break;
case 8:
p1.sub(this.opTrans);
p1.scale(0.5);
this.opPoint.setT(p1);
p21.sub(this.opTrans);
this.opAxis = JU.V3.newVsub(p21, px);
p2.scaleAdd2(0.5, this.opAxis, px);
this.opAxis.normalize();
this.opPlane =  new JU.P4();
p1.set(px.x + 1.1, px.y + 1.7, px.z + 2.1);
p1.scale(0.5);
this.rotTrans(p1);
p1.sub(this.opTrans);
p1.scaleAdd2(0.5, px, p1);
p1.scale(0.5);
v =  new JU.V3();
isOK = JS.SymmetryOperation.checkOpPlane(this.opPoint, p1, p2, this.opPlane, v,  new JU.V3());
JS.SymmetryOperation.opClean6(this.opPlane);
if (JS.SymmetryOperation.approx6(this.opPlane.w) == 0) this.opPlane.w = 0;
JS.SymmetryOperation.approx6Pt(this.opAxis);
JS.SymmetryOperation.normalizePlane(this.opPlane);
break;
}
if (d > 0) {
JS.SymmetryOperation.opClean6(this.opTrans);
var dmax = 1;
if (this.opType == 8) {
if (this.opTrans.z == 0 && this.opTrans.lengthSquared() == 1.25 || this.opTrans.z == 0.5 && this.opTrans.lengthSquared() == 1.5) {
dmax = 1.25;
this.opIsLong = true;
} else {
dmax = 0.78;
}this.opGlide = JU.V3.newV(this.opTrans);
this.fixNegTrans(this.opGlide);
if (this.opGlide.length() == 0) this.opGlide = null;
if ((this.opTrans.x == 1 || this.opTrans.y == 1 || this.opTrans.z == 1) && this.m22 == -1) isOK = false;
} else {
if (this.opTrans.z == 0 && this.opTrans.lengthSquared() == 1.25) {
dmax = 1.25;
this.opIsLong = true;
}}this.opType |= 1;
if (Math.abs(JS.SymmetryOperation.approx(this.opTrans.x)) >= dmax || Math.abs(JS.SymmetryOperation.approx(this.opTrans.y)) >= dmax || Math.abs(JS.SymmetryOperation.approx(this.opTrans.z)) >= dmax) {
isOK = false;
}} else {
this.opTrans = null;
}if (!isOK) {
this.isIrrelevant = true;
}});
Clazz.defineMethod(c$, "fixNegTrans", 
function(t){
t.x = JS.SymmetryOperation.normHalf(t.x);
t.y = JS.SymmetryOperation.normHalf(t.y);
t.z = JS.SymmetryOperation.normHalf(t.z);
}, "JU.V3");
c$.normalizePlane = Clazz.defineMethod(c$, "normalizePlane", 
function(plane){
JS.SymmetryOperation.approx6Pt(plane);
plane.w = JS.SymmetryOperation.approx6(plane.w);
if (plane.w > 0 || plane.w == 0 && (plane.x < 0 || plane.x == 0 && plane.y < 0 || plane.y == 0 && plane.z < 0)) {
plane.scale4(-1);
}JS.SymmetryOperation.opClean6(plane);
plane.w = JS.SymmetryOperation.approx6(plane.w);
}, "JU.P4");
c$.isCoaxial = Clazz.defineMethod(c$, "isCoaxial", 
function(v){
return (Math.abs(JS.SymmetryOperation.approx(v.x)) == 1 || Math.abs(JS.SymmetryOperation.approx(v.y)) == 1 || Math.abs(JS.SymmetryOperation.approx(v.z)) == 1);
}, "JU.T3");
Clazz.defineMethod(c$, "clearOp", 
function(){
if (!this.isFinalized) this.doFinalize();
this.isIrrelevant = false;
this.opTrans = null;
this.opPoint = this.opPoint2 = null;
this.opPlane = null;
this.opIsCCW = null;
this.opIsLong = false;
});
c$.hasTrans = Clazz.defineMethod(c$, "hasTrans", 
function(m4){
return (JS.SymmetryOperation.approx6(m4.m03) != 0 || JS.SymmetryOperation.approx6(m4.m13) != 0 || JS.SymmetryOperation.approx6(m4.m23) != 0);
}, "JU.M4");
c$.checkOpAxis = Clazz.defineMethod(c$, "checkOpAxis", 
function(pt, axis, ptRet, t1, t2, ptNot){
if (JS.SymmetryOperation.opPlanes == null) {
JS.SymmetryOperation.opPlanes = JU.BoxInfo.getBoxFacesFromOABC(null);
}var map = JU.BoxInfo.faceOrder;
var f = (ptNot == null ? 1 : -1);
for (var i = 0; i < 6; i++) {
var p = JU.Measure.getIntersection(pt, axis, JS.SymmetryOperation.opPlanes[map[i]], ptRet, t1, t2);
if (p != null && JS.SymmetryOperation.checkOpPoint(p) && axis.dot(t1) * f < 0 && (ptNot == null || JS.SymmetryOperation.approx(ptNot.distance(p) - 0.5) >= 0)) {
return true;
}}
return false;
}, "JU.P3,JU.V3,JU.P3,JU.V3,JU.V3,JU.P3");
c$.opClean6 = Clazz.defineMethod(c$, "opClean6", 
function(t){
if (JS.SymmetryOperation.approx6(t.x) == 0) t.x = 0;
if (JS.SymmetryOperation.approx6(t.y) == 0) t.y = 0;
if (JS.SymmetryOperation.approx6(t.z) == 0) t.z = 0;
return t;
}, "JU.T3");
c$.checkOpPoint = Clazz.defineMethod(c$, "checkOpPoint", 
function(pt){
return JS.SymmetryOperation.checkOK(pt.x, 0) && JS.SymmetryOperation.checkOK(pt.y, 0) && JS.SymmetryOperation.checkOK(pt.z, 0);
}, "JU.T3");
c$.checkOK = Clazz.defineMethod(c$, "checkOK", 
function(p, a){
return (a != 0 || JS.SymmetryOperation.approx(p) >= 0 && JS.SymmetryOperation.approx(p) <= 1);
}, "~N,~N");
c$.checkOpPlane = Clazz.defineMethod(c$, "checkOpPlane", 
function(p1, p2, p3, plane, vtemp1, vtemp2){
JU.Measure.getPlaneThroughPoints(p1, p2, p3, vtemp1, vtemp2, plane);
var pts = JU.BoxInfo.unitCubePoints;
var nPos = 0;
var nNeg = 0;
for (var i = 8; --i >= 0; ) {
var d = JU.Measure.getPlaneProjection(pts[i], plane, p1, vtemp1);
switch (Clazz.floatToInt(Math.signum(JS.SymmetryOperation.approx6(d)))) {
case 1:
if (nNeg > 0) return true;
nPos++;
break;
case 0:
break;
case -1:
if (nPos > 0) return true;
nNeg++;
}
}
return !(nNeg == 8 || nPos == 8);
}, "JU.P3,JU.P3,JU.P3,JU.P4,JU.V3,JU.V3");
c$.getAdditionalOperations = Clazz.defineMethod(c$, "getAdditionalOperations", 
function(ops){
var n = ops.length;
var lst =  new JU.Lst();
var xyzLst =  new JU.SB();
var mapPlanes =  new java.util.Hashtable();
var vTemp =  new JU.V3();
for (var i = 0; i < n; i++) {
var op = ops[i];
lst.addLast(op);
var s = op.getOpName(1);
xyzLst.append(s).appendC(';');
if ((op.getOpType() & 8) != 0) JS.SymmetryOperation.addCoincidentMap(mapPlanes, op, 8, vTemp);
 else if (op.getOpType() == 3) JS.SymmetryOperation.addCoincidentMap(mapPlanes, op, 3, null);
}
for (var i = 1; i < n; i++) {
ops[i].addOps(xyzLst, lst, mapPlanes, n, i, vTemp);
}
return lst.toArray( new Array(lst.size()));
}, "~A");
Clazz.defineMethod(c$, "addOps", 
function(xyzList, lst, mapCoincident, n0, isym, vTemp){
var t0 =  new JU.V3();
this.getTranslation(t0);
var isPlane = ((this.getOpType() & 8) == 8);
var isScrew = (this.getOpType() == 3);
var t =  new JU.V3();
var opTemp = null;
for (var i = 3; --i >= -3; ) {
for (var j = 3; --j >= -3; ) {
for (var k = 3; --k >= -3; ) {
if (opTemp == null) opTemp =  new JS.SymmetryOperation(null, 0, false);
t.set(i, j, k);
if (this.checkOpSimilar(t, vTemp)) continue;
if (opTemp.opCheckAdd(this, t0, n0, t, xyzList, lst, isym + 1)) {
if (isPlane) JS.SymmetryOperation.addCoincidentMap(mapCoincident, opTemp, 8, vTemp);
 else if (isScrew) JS.SymmetryOperation.addCoincidentMap(mapCoincident, opTemp, 3, null);
opTemp = null;
}}
}
}
}, "JU.SB,JU.Lst,java.util.Map,~N,~N,JU.V3");
c$.addCoincidentMap = Clazz.defineMethod(c$, "addCoincidentMap", 
function(mapCoincident, op, opType, vTemp){
if (op.isIrrelevant) return;
var s = op.getOpName(0);
var l = mapCoincident.get(s);
op.iCoincident = 0;
var isRotation = (opType == 3);
if (l == null) {
mapCoincident.put(s, l =  new JU.Lst());
} else if (isRotation) {
if (op.opOrder == 6) {
for (var i = l.size(); --i >= 0; ) {
var op1 = l.get(i);
if (!op1.isIrrelevant) switch (op1.opOrder) {
case 3:
op1.isIrrelevant = true;
break;
case 6:
break;
}
}
}op.iCoincident = 1;
} else {
var op0 = null;
for (var i = l.size(); --i >= 0; ) {
op0 = l.get(i);
if (op.opGlide != null && op0.opGlide != null) {
vTemp.sub2(op.opGlide, op0.opGlide);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.add2(op.opGlide, op0.opGlide);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.add2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}} else if (op.opGlide == null && op0.opGlide == null) {
vTemp.add2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.sub2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}}}
if (op0.iCoincident == 0) {
op.iCoincident = 1;
op0.iCoincident = -1;
} else {
op.iCoincident = -op0.iCoincident;
}}l.addLast(op);
}, "java.util.Map,JS.SymmetryOperation,~N,JU.V3");
Clazz.defineMethod(c$, "checkOpSimilar", 
function(t, vTemp){
switch (this.getOpType() & -2) {
default:
return false;
case 0:
return true;
case 2:
return (JS.SymmetryOperation.approx6(t.dot(this.opAxis) - t.length()) == 0);
case 8:
vTemp.cross(t, this.opAxis);
return (JS.SymmetryOperation.approx6(vTemp.length()) == 0 ? false : JS.SymmetryOperation.approx6(t.dot(this.opAxis)) == 0);
}
}, "JU.V3,JU.V3");
Clazz.defineMethod(c$, "opCheckAdd", 
function(opThis, t0, n0, t, xyzList, lst, itno){
this.setM4(opThis);
var t1 = JU.V3.newV(t);
t1.add(t0);
this.setTranslation(t1);
this.isFinalized = true;
this.setOpTypeAndOrder();
if (this.isIrrelevant || this.opType == 0 || this.opType == 1) return false;
var s = this.getOpName(1) + ";";
if ((this.opType & 8) == 0 && xyzList.indexOf(s) >= 0) {
return false;
}xyzList.append(s);
lst.addLast(this);
this.isFinalized = true;
this.xyz = JS.SymmetryOperation.getXYZFromMatrix(this, false, false, false);
return true;
}, "JS.SymmetryOperation,JU.V3,~N,JU.V3,JU.SB,JU.Lst,~N");
c$.approx6Pt = Clazz.defineMethod(c$, "approx6Pt", 
function(pt){
if (pt != null) {
pt.x = JS.SymmetryOperation.approx6(pt.x);
pt.y = JS.SymmetryOperation.approx6(pt.y);
pt.z = JS.SymmetryOperation.approx6(pt.z);
}}, "JU.T3");
c$.normalize12ths = Clazz.defineMethod(c$, "normalize12ths", 
function(vtrans){
vtrans.x = JU.PT.approx(vtrans.x, 12);
vtrans.y = JU.PT.approx(vtrans.y, 12);
vtrans.z = JU.PT.approx(vtrans.z, 12);
}, "JU.V3");
Clazz.defineMethod(c$, "getCode", 
function(){
if (this.opAxisCode != null) {
return this.opAxisCode;
}var t = this.getOpName(2).charAt(0);
var o = this.opOrder;
var ccw = (this.opIsCCW == null ? 0 : this.opIsCCW === Boolean.TRUE ? 1 : 2);
var g = "";
var m = "";
switch ((t).charCodeAt(0)) {
case 71:
t = JS.SymmetryOperation.getGlideFromTrans(this.opTrans, this.opPlane);
case 80:
if (!JS.SymmetryOperation.isCoaxial(this.opAxis)) {
t = (t == 'P' ? 'p' : String.fromCharCode(t.charCodeAt(0) - 32));
}break;
case 83:
var d = this.opTrans.length();
if (this.opIsCCW != null && (d < (d > 1 ? 6 : 0.5)) == (this.opIsCCW === Boolean.TRUE)) t = 'w';
break;
case 82:
if (!JS.SymmetryOperation.isCoaxial(this.opAxis)) {
t = 'o';
}if (this.opPoint.length() == 0) t = (t == 'o' ? 'q' : 'Q');
break;
default:
break;
}
var s = g + m + t + "." + (String.fromCharCode(48 + o)) + "." + ccw + ".";
return this.opAxisCode = s;
});
c$.getGlideFromTrans = Clazz.defineMethod(c$, "getGlideFromTrans", 
function(ftrans, ax1){
var fx = Math.abs(JS.SymmetryOperation.approx(ftrans.x * 12));
var fy = Math.abs(JS.SymmetryOperation.approx(ftrans.y * 12));
var fz = Math.abs(JS.SymmetryOperation.approx(ftrans.z * 12));
if (fx == 9) fx = 3;
if (fy == 9) fy = 3;
if (fz == 9) fz = 3;
var nonzero = 3;
if (fx == 0) nonzero--;
if (fy == 0) nonzero--;
if (fz == 0) nonzero--;
var sum = Clazz.floatToInt(fx + fy + fz);
switch (nonzero) {
default:
case 1:
return (fx != 0 ? 'a' : fy != 0 ? 'b' : 'c');
case 2:
switch (sum) {
case 6:
return 'd';
case 12:
var n = JU.P3.newP(ax1);
n.normalize();
if (JS.SymmetryOperation.approx(n.x + n.y + n.z) == 1) return 'n';
}
break;
case 3:
switch (sum) {
case 9:
return 'd';
case 18:
return 'n';
}
break;
}
return 'g';
}, "JU.T3,JU.T3");
c$.rotateAndTranslatePoint = Clazz.defineMethod(c$, "rotateAndTranslatePoint", 
function(m, src, ta, tb, tc, dest){
m.rotTrans2(src, dest);
dest.add3(ta, tb, tc);
}, "JU.M4,JU.P3,~N,~N,~N,JU.P3");
c$.transformStr = Clazz.defineMethod(c$, "transformStr", 
function(xyz, trm, trmInv, t, v, centering, targetCentering, normalize, allowFractions){
if (trmInv == null) {
trmInv = JU.M4.newM4(trm);
trmInv.invert();
}if (t == null) t =  new JU.M4();
if (v == null) v =  Clazz.newFloatArray (16, 0);
var op = JS.SymmetryOperation.getMatrixFromXYZ(xyz, v, true);
if (centering != null) op.add(centering);
t.setM4(trmInv);
t.mul(op);
if (trm != null) t.mul(trm);
if (targetCentering != null) op.add(targetCentering);
if (normalize) {
t.getColumn(3, v);
for (var i = 0; i < 3; i++) {
v[i] = v[i] % 1;
}
t.setColumnA(3, v);
}return JS.SymmetryOperation.getXYZFromMatrixFrac(t, false, true, false, allowFractions);
}, "~S,JU.M4,JU.M4,JU.M4,~A,JU.T3,JU.T3,~B,~B");
c$.transformXyzT = Clazz.defineMethod(c$, "transformXyzT", 
function(xyz, transform){
return (JS.SymmetryOperation.transformStr(xyz, JS.UnitCell.toTrm(transform, null), null, null, null, null, null, true, false));
}, "~S,~S");
c$.stringToMatrix = Clazz.defineMethod(c$, "stringToMatrix", 
function(xyz){
var divisor = JS.SymmetryOperation.setDivisor(xyz);
var a =  Clazz.newFloatArray (16, 0);
JS.SymmetryOperation.getMatrixFromString(null, xyz, a, true, false, false);
return JS.SymmetryOperation.div12(JU.M4.newA16(a), divisor);
}, "~S");
c$.getTransformABC = Clazz.defineMethod(c$, "getTransformABC", 
function(transform, normalize){
if (transform == null) return "a,b,c";
var t = transform;
var m = JU.M4.newM4(t);
var tr =  new JU.V3();
m.getTranslation(tr);
tr.scale(-1);
m.add(tr);
m.transpose();
var s = JS.SymmetryOperation.getXYZFromMatrixFrac(m, false, true, false, true).$replace('x', 'a').$replace('y', 'b').$replace('z', 'c');
if (tr.lengthSquared() < 1e-12) return s;
tr.scale(-1);
return s + ";" + (normalize ? JS.SymmetryOperation.norm3(tr) : JS.SymmetryOperation.opF(tr.x) + "," + JS.SymmetryOperation.opF(tr.y) + "," + JS.SymmetryOperation.opF(tr.z));
}, "~O,~B");
c$.norm3 = Clazz.defineMethod(c$, "norm3", 
function(tr){
return JS.SymmetryOperation.norm(tr.x) + "," + JS.SymmetryOperation.norm(tr.y) + "," + JS.SymmetryOperation.norm(tr.z);
}, "JU.T3");
c$.norm = Clazz.defineMethod(c$, "norm", 
function(d){
return JS.SymmetryOperation.opF(JS.SymmetryOperation.normHalf(d));
}, "~N");
c$.normHalf = Clazz.defineMethod(c$, "normHalf", 
function(d){
while (d <= -0.5) {
d += 1;
}
while (d > 0.5) {
d -= 1;
}
return d;
}, "~N");
c$.toPoint = Clazz.defineMethod(c$, "toPoint", 
function(xyz, p){
if (p == null) p =  new JU.P3();
var s = JU.PT.split(xyz, ",");
p.set(JU.PT.parseFloatFraction(s[0]), JU.PT.parseFloatFraction(s[1]), JU.PT.parseFloatFraction(s[2]));
return p;
}, "~S,JU.P3");
c$.atomTest = null;
c$.twelfths =  Clazz.newArray(-1, ["0", "1/12", "1/6", "1/4", "1/3", "5/12", "1/2", "7/12", "2/3", "3/4", "5/6", "11/12"]);
c$.labelsXYZ =  Clazz.newArray(-1, ["x", "y", "z"]);
c$.labelsXn =  Clazz.newArray(-1, ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13"]);
c$.labelsXnSub =  Clazz.newArray(-1, ["x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]);
c$.x = JU.P3.new3(3.141592653589793, 2.718281828459045, (8.539734222673566));
c$.C3codes =  Clazz.newIntArray(-1, [0x031112, 0x121301, 0x130112, 0x021311, 0x130102, 0x020311, 0x031102, 0x120301]);
c$.xneg = null;
c$.opPlanes = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
