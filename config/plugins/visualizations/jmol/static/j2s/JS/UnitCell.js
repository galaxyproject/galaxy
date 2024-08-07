Clazz.declarePackage("JS");
Clazz.load(["JU.SimpleUnitCell", "JU.P3", "JV.JC"], "JS.UnitCell", ["java.util.Hashtable", "JU.AU", "$.Lst", "$.M3", "$.M4", "$.P4", "$.PT", "$.Quat", "$.V3", "J.api.Interface", "JS.Symmetry", "JU.BoxInfo", "$.Escape"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.moreInfo = null;
this.name = "";
this.vertices = null;
this.fractionalOffset = null;
this.allFractionalRelative = false;
this.cartesianOffset = null;
this.unitCellMultiplier = null;
this.unitCellMultiplied = null;
this.f2c = null;
Clazz.instantialize(this, arguments);}, JS, "UnitCell", JU.SimpleUnitCell, Cloneable);
Clazz.prepareFields (c$, function(){
this.cartesianOffset =  new JU.P3();
});
c$.fromOABC = Clazz.defineMethod(c$, "fromOABC", 
function(oabc, setRelative){
var c =  new JS.UnitCell();
if (oabc.length == 3) oabc =  Clazz.newArray(-1, [ new JU.P3(), oabc[0], oabc[1], oabc[2]]);
var parameters =  Clazz.newFloatArray(-1, [-1, 0, 0, 0, 0, 0, oabc[1].x, oabc[1].y, oabc[1].z, oabc[2].x, oabc[2].y, oabc[2].z, oabc[3].x, oabc[3].y, oabc[3].z]);
c.init(parameters);
c.allFractionalRelative = setRelative;
c.initUnitcellVertices();
c.setCartesianOffset(oabc[0]);
return c;
}, "~A,~B");
c$.fromParams = Clazz.defineMethod(c$, "fromParams", 
function(params, setRelative, slop){
var c =  new JS.UnitCell();
c.init(params);
c.initUnitcellVertices();
c.allFractionalRelative = setRelative;
c.setPrecision(slop);
if (params.length > 26) params[26] = slop;
return c;
}, "~A,~B,~N");
c$.cloneUnitCell = Clazz.defineMethod(c$, "cloneUnitCell", 
function(uc){
var ucnew = null;
try {
ucnew = uc.clone();
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
} else {
throw e;
}
}
return ucnew;
}, "JS.UnitCell");
Clazz.defineMethod(c$, "checkDistance", 
function(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset){
var p1 = JU.P3.newP(f1);
this.toCartesian(p1, true);
for (var i = -iRange; i <= iRange; i++) for (var j = -jRange; j <= jRange; j++) for (var k = -kRange; k <= kRange; k++) {
ptOffset.set(f2.x + i, f2.y + j, f2.z + k);
this.toCartesian(ptOffset, true);
var d = p1.distance(ptOffset);
if (dx > 0 ? Math.abs(d - distance) <= dx : d <= distance && d > 0.1) {
ptOffset.set(i, j, k);
return true;
}}


return false;
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz.defineMethod(c$, "checkPeriodic", 
function(pt){
switch (this.dimension) {
case 3:
if (pt.z < -this.slop || pt.z > 1 - this.slop) return false;
case 2:
if (pt.y < -this.slop || pt.y > 1 - this.slop) return false;
case 1:
if (pt.x < -this.slop || pt.x > 1 - this.slop) return false;
}
return true;
}, "JU.P3");
Clazz.defineMethod(c$, "dumpInfo", 
function(isDebug, multiplied){
var m = (multiplied ? this.getUnitCellMultiplied() : this);
if (m !== this) return m.dumpInfo(isDebug, false);
return "a=" + this.a + ", b=" + this.b + ", c=" + this.c + ", alpha=" + this.alpha + ", beta=" + this.beta + ", gamma=" + this.gamma + "\noabc=" + JU.Escape.eAP(this.getUnitCellVectors()) + "\nvolume=" + this.volume + (isDebug ? "\nfractional to cartesian: " + this.matrixFractionalToCartesian + "\ncartesian to fractional: " + this.matrixCartesianToFractional : "");
}, "~B,~B");
Clazz.defineMethod(c$, "fix000", 
function(x){
return (Math.abs(x) < 0.001 ? 0 : x);
}, "~N");
Clazz.defineMethod(c$, "fixFloor", 
function(d){
return (d == 1 ? 0 : d);
}, "~N");
Clazz.defineMethod(c$, "getCanonicalCopy", 
function(scale, withOffset){
var pts = this.getScaledCell(withOffset);
return JU.BoxInfo.getCanonicalCopy(pts, scale);
}, "~N,~B");
Clazz.defineMethod(c$, "getCanonicalCopyTrimmed", 
function(frac, scale){
var pts = this.getScaledCellMult(frac, true);
return JU.BoxInfo.getCanonicalCopy(pts, scale);
}, "JU.P3,~N");
Clazz.defineMethod(c$, "getCartesianOffset", 
function(){
return this.cartesianOffset;
});
Clazz.defineMethod(c$, "getCellWeight", 
function(pt){
var f = 1;
if (pt.x <= this.slop || pt.x >= 1 - this.slop) f /= 2;
if (pt.y <= this.slop || pt.y >= 1 - this.slop) f /= 2;
if (pt.z <= this.slop || pt.z >= 1 - this.slop) f /= 2;
return f;
}, "JU.P3");
Clazz.defineMethod(c$, "getConventionalUnitCell", 
function(latticeType, primitiveToCrystal){
var oabc = this.getUnitCellVectors();
if (!latticeType.equals("P") || primitiveToCrystal != null) this.toFromPrimitive(false, latticeType.charAt(0), oabc, primitiveToCrystal);
return oabc;
}, "~S,JU.M3");
Clazz.defineMethod(c$, "getEquivPoints", 
function(pt, flags, ops, list, i0, n0, dup0){
var fromfractional = (flags.indexOf("fromfractional") >= 0);
var tofractional = (flags.indexOf("tofractional") >= 0);
var packed = (flags.indexOf("packed") >= 0);
if (list == null) list =  new JU.Lst();
var pf = JU.P3.newP(pt);
if (!fromfractional) this.toFractional(pf, true);
var n = list.size();
for (var i = 0, nops = ops.length; i < nops; i++) {
var p = JU.P3.newP(pf);
ops[i].rotTrans(p);
p.x = this.fixFloor(p.x - Math.floor(p.x));
p.y = this.fixFloor(p.y - Math.floor(p.y));
p.z = this.fixFloor(p.z - Math.floor(p.z));
list.addLast(p);
n++;
}
if (packed) {
for (var i = n0; i < n; i++) {
pf.setT(list.get(i));
this.unitizeRnd(pf);
if (pf.x == 0) {
list.addLast(JU.P3.new3(0, pf.y, pf.z));
list.addLast(JU.P3.new3(1, pf.y, pf.z));
if (pf.y == 0) {
list.addLast(JU.P3.new3(1, 1, pf.z));
list.addLast(JU.P3.new3(0, 0, pf.z));
if (pf.z == 0) {
list.addLast(JU.P3.new3(1, 1, 1));
list.addLast(JU.P3.new3(0, 0, 0));
}}}if (pf.y == 0) {
list.addLast(JU.P3.new3(pf.x, 0, pf.z));
list.addLast(JU.P3.new3(pf.x, 1, pf.z));
if (pf.z == 0) {
list.addLast(JU.P3.new3(pf.x, 0, 0));
list.addLast(JU.P3.new3(pf.x, 1, 1));
}}if (pf.z == 0) {
list.addLast(JU.P3.new3(pf.x, pf.y, 0));
list.addLast(JU.P3.new3(pf.x, pf.y, 1));
if (pf.x == 0) {
list.addLast(JU.P3.new3(0, pf.y, 0));
list.addLast(JU.P3.new3(1, pf.y, 1));
}}}
}JS.UnitCell.removeDuplicates(list, i0, dup0, -1);
if (!tofractional) {
for (var i = list.size(); --i >= n0; ) this.toCartesian(list.get(i), true);

}return list;
}, "JU.P3,~S,~A,JU.Lst,~N,~N,~N");
Clazz.defineMethod(c$, "getFractionalOffset", 
function(){
return this.fractionalOffset;
});
Clazz.defineMethod(c$, "getInfo", 
function(){
var m = this.getUnitCellMultiplied();
if (m !== this) return m.getInfo();
var info =  new java.util.Hashtable();
info.put("params", this.unitCellParams);
info.put("oabc", this.getUnitCellVectors());
info.put("volume", Double.$valueOf(this.volume));
info.put("matFtoC", this.matrixFractionalToCartesian);
info.put("matCtoF", this.matrixCartesianToFractional);
return info;
});
Clazz.defineMethod(c$, "getQuaternionRotation", 
function(abc){
var a = JU.V3.newVsub(this.vertices[4], this.vertices[0]);
var b = JU.V3.newVsub(this.vertices[2], this.vertices[0]);
var c = JU.V3.newVsub(this.vertices[1], this.vertices[0]);
var x =  new JU.P3();
var v =  new JU.P3();
var mul = (abc.charAt(0) == '-' ? -1 : 1);
if (mul < 0) abc = abc.substring(1);
var abc0 = abc;
abc = JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(abc, "ab", "A"), "bc", "B"), "ca", "C"), "ba", "D"), "cb", "E"), "ac", "F");
var isFace = !abc0.equals(abc);
var quadrant = (isFace ? 1 : 0);
if (abc.length == 2) {
quadrant = (abc.charAt(1)).charCodeAt(0) - 48;
abc = abc.substring(0, 1);
}var isEven = (quadrant % 2 == 0);
var axis = "abcABCDEF".indexOf(abc);
var v1;
var v2;
var P3;
switch (axis) {
case 7:
mul = -mul;
case 4:
a.cross(c, b);
quadrant = ((5 - quadrant) % 4) + 1;
case 0:
default:
v1 = a;
v2 = c;
P3 = b;
break;
case 8:
mul = -mul;
case 5:
mul = -mul;
b.cross(c, a);
quadrant = ((2 + quadrant) % 4) + 1;
case 1:
v1 = b;
v2 = a;
P3 = c;
mul = -mul;
break;
case 3:
mul = -mul;
case 6:
c.cross(a, b);
if (isEven) quadrant = 6 - quadrant;
case 2:
v1 = c;
v2 = a;
P3 = b;
if (!isFace && quadrant > 0) {
quadrant = 5 - quadrant;
}break;
}
if (quadrant > 0) {
if (mul > 0 != isEven) {
v2 = P3;
v1.scale(-1);
}}switch (quadrant) {
case 0:
default:
case 1:
break;
case 2:
v1.scale(-1);
v2.scale(-1);
break;
case 3:
v2.scale(-1);
break;
case 4:
v1.scale(-1);
break;
}
x.cross(v1, v2);
v.cross(x, v1);
return JU.Quat.getQuaternionFrame(null, v, x).inv();
}, "~S");
Clazz.defineMethod(c$, "getScaledCell", 
function(withOffset){
return this.getScaledCellMult(null, withOffset);
}, "~B");
Clazz.defineMethod(c$, "getScaledCellMult", 
function(mult, withOffset){
var pts =  new Array(8);
var cell0 = null;
var cell1 = null;
var isFrac = (mult != null);
if (!isFrac) mult = this.unitCellMultiplier;
if (withOffset && mult != null && mult.z == 0) {
cell0 =  new JU.P3();
cell1 =  new JU.P3();
JU.SimpleUnitCell.ijkToPoint3f(Clazz.floatToInt(mult.x), cell0, 0, 0);
JU.SimpleUnitCell.ijkToPoint3f(Clazz.floatToInt(mult.y), cell1, 0, 0);
cell1.sub(cell0);
}var scale = (isFrac || mult == null || mult.z == 0 ? 1 : Math.abs(mult.z));
for (var i = 0; i < 8; i++) {
var pt = pts[i] = JU.P3.newP(JU.BoxInfo.unitCubePoints[i]);
if (cell0 != null) {
pts[i].add3(cell0.x + cell1.x * pt.x, cell0.y + cell1.y * pt.y, cell0.z + cell1.z * pt.z);
} else if (isFrac) {
pt.scaleT(mult);
}pts[i].scale(scale);
this.matrixFractionalToCartesian.rotTrans(pt);
if (!withOffset) pt.sub(this.cartesianOffset);
}
return pts;
}, "JU.T3,~B");
Clazz.defineMethod(c$, "getState", 
function(){
var s = "";
if (this.fractionalOffset != null && this.fractionalOffset.lengthSquared() != 0) s += "  unitcell offset " + JU.Escape.eP(this.fractionalOffset) + ";\n";
if (this.unitCellMultiplier != null) s += "  unitcell range " + JU.SimpleUnitCell.escapeMultiplier(this.unitCellMultiplier) + ";\n";
return s;
});
Clazz.defineMethod(c$, "getTensor", 
function(vwr, parBorU){
var t = (J.api.Interface.getUtil("Tensor", vwr, "file"));
if (parBorU[0] == 0 && parBorU[1] == 0 && parBorU[2] == 0) {
var f = parBorU[7];
var eigenValues =  Clazz.newFloatArray(-1, [f, f, f]);
return t.setFromEigenVectors(JS.UnitCell.unitVectors, eigenValues, "iso", "Uiso=" + f, null);
}t.parBorU = parBorU;
var Bcart =  Clazz.newDoubleArray (6, 0);
var ortepType = Clazz.floatToInt(parBorU[6]);
if (ortepType == 12) {
Bcart[0] = parBorU[0] * 19.739208802178716;
Bcart[1] = parBorU[1] * 19.739208802178716;
Bcart[2] = parBorU[2] * 19.739208802178716;
Bcart[3] = parBorU[3] * 19.739208802178716 * 2;
Bcart[4] = parBorU[4] * 19.739208802178716 * 2;
Bcart[5] = parBorU[5] * 19.739208802178716 * 2;
parBorU[7] = (parBorU[0] + parBorU[1] + parBorU[3]) / 3;
} else {
var isFractional = (ortepType == 4 || ortepType == 5 || ortepType == 8 || ortepType == 9);
var cc = 2 - (ortepType % 2);
var dd = (ortepType == 8 || ortepType == 9 || ortepType == 10 ? 19.739208802178716 : ortepType == 4 || ortepType == 5 ? 0.25 : ortepType == 2 || ortepType == 3 ? Math.log(2) : 1);
var B11 = parBorU[0] * dd * (isFractional ? this.a_ * this.a_ : 1);
var B22 = parBorU[1] * dd * (isFractional ? this.b_ * this.b_ : 1);
var B33 = parBorU[2] * dd * (isFractional ? this.c_ * this.c_ : 1);
var B12 = parBorU[3] * dd * (isFractional ? this.a_ * this.b_ : 1) * cc;
var B13 = parBorU[4] * dd * (isFractional ? this.a_ * this.c_ : 1) * cc;
var B23 = parBorU[5] * dd * (isFractional ? this.b_ * this.c_ : 1) * cc;
parBorU[7] = Math.pow(B11 / 19.739208802178716 / this.a_ / this.a_ * B22 / 19.739208802178716 / this.b_ / this.b_ * B33 / 19.739208802178716 / this.c_ / this.c_, 0.3333);
Bcart[0] = this.a * this.a * B11 + this.b * this.b * this.cosGamma * this.cosGamma * B22 + this.c * this.c * this.cosBeta * this.cosBeta * B33 + this.a * this.b * this.cosGamma * B12 + this.b * this.c * this.cosGamma * this.cosBeta * B23 + this.a * this.c * this.cosBeta * B13;
Bcart[1] = this.b * this.b * this.sinGamma * this.sinGamma * B22 + this.c * this.c * this.cA_ * this.cA_ * B33 + this.b * this.c * this.cA_ * this.sinGamma * B23;
Bcart[2] = this.c * this.c * this.cB_ * this.cB_ * B33;
Bcart[3] = 2 * this.b * this.b * this.cosGamma * this.sinGamma * B22 + 2 * this.c * this.c * this.cA_ * this.cosBeta * B33 + this.a * this.b * this.sinGamma * B12 + this.b * this.c * (this.cA_ * this.cosGamma + this.sinGamma * this.cosBeta) * B23 + this.a * this.c * this.cA_ * B13;
Bcart[4] = 2 * this.c * this.c * this.cB_ * this.cosBeta * B33 + this.b * this.c * this.cosGamma * B23 + this.a * this.c * this.cB_ * B13;
Bcart[5] = 2 * this.c * this.c * this.cA_ * this.cB_ * B33 + this.b * this.c * this.cB_ * this.sinGamma * B23;
}return t.setFromThermalEquation(Bcart, JU.Escape.eAF(parBorU));
}, "JV.Viewer,~A");
Clazz.defineMethod(c$, "getUnitCellMultiplied", 
function(){
if (this.unitCellMultiplier == null || this.unitCellMultiplier.z > 0 && this.unitCellMultiplier.z == Clazz.floatToInt(this.unitCellMultiplier.z)) return this;
if (this.unitCellMultiplied == null) {
var pts = JU.BoxInfo.toOABC(this.getScaledCell(true), null);
this.unitCellMultiplied = JS.UnitCell.fromOABC(pts, false);
}return this.unitCellMultiplied;
});
Clazz.defineMethod(c$, "getUnitCellMultiplier", 
function(){
return this.unitCellMultiplier;
});
Clazz.defineMethod(c$, "isStandard", 
function(){
return (this.unitCellMultiplier == null || this.unitCellMultiplier.x == this.unitCellMultiplier.y);
});
Clazz.defineMethod(c$, "getUnitCellVectors", 
function(){
var m = this.matrixFractionalToCartesian;
return  Clazz.newArray(-1, [JU.P3.newP(this.cartesianOffset), JU.P3.new3(this.fix000(m.m00), this.fix000(m.m10), this.fix000(m.m20)), JU.P3.new3(this.fix000(m.m01), this.fix000(m.m11), this.fix000(m.m21)), JU.P3.new3(this.fix000(m.m02), this.fix000(m.m12), this.fix000(m.m22))]);
});
c$.toTrm = Clazz.defineMethod(c$, "toTrm", 
function(transform, trm){
if (trm == null) trm =  new JU.M4();
JS.UnitCell.getMatrixAndUnitCell(null, transform, trm);
return trm;
}, "~S,JU.M4");
c$.getMatrixAndUnitCell = Clazz.defineMethod(c$, "getMatrixAndUnitCell", 
function(uc, def, retMatrix){
if (def == null) def = "a,b,c";
var m;
var pts =  new Array(4);
var pt = pts[0] = JU.P3.new3(0, 0, 0);
pts[1] = JU.P3.new3(1, 0, 0);
pts[2] = JU.P3.new3(0, 1, 0);
pts[3] = JU.P3.new3(0, 0, 1);
var m3 =  new JU.M3();
if (JU.AU.isAD(def)) {
return JU.SimpleUnitCell.setAbcFromParams(def, pts);
}var isString = (typeof(def)=='string');
if (isString) {
var sdef = def;
var strans;
var strans2 = null;
if (sdef.indexOf("a=") == 0) return JU.SimpleUnitCell.setAbc(sdef, null, pts);
var ret =  new Array(1);
var ptc = sdef.indexOf(";");
if (ptc >= 0) {
strans = sdef.substring(ptc + 1).trim();
sdef = sdef.substring(0, ptc);
ret[0] = sdef;
strans2 = JS.UnitCell.fixABC(ret);
if (sdef !== ret[0]) {
sdef = ret[0];
}} else if (sdef.equals("a,b,c")) {
strans = null;
} else {
ret[0] = sdef;
strans = JS.UnitCell.fixABC(ret);
sdef = ret[0];
}sdef += ";0,0,0";
while (sdef.startsWith("!!")) sdef = sdef.substring(2);

var isRev = sdef.startsWith("!");
if (isRev) sdef = sdef.substring(1);
if (sdef.startsWith("r;")) sdef = "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c" + sdef.substring(1);
var symTemp =  new JS.Symmetry();
symTemp.setSpaceGroup(false);
var i = symTemp.addSpaceGroupOperation("=" + sdef, 0);
if (i < 0) return null;
m = symTemp.getSpaceGroupOperation(i);
(m).doFinalize();
var t =  new JU.P3();
JS.UnitCell.addTrans(strans, t);
JS.UnitCell.addTrans(strans2, t);
m.setTranslation(t);
var isABC = (sdef.indexOf("c") >= 0);
if (isABC) {
m.transpose33();
}if (isRev) {
m.invert();
}if (retMatrix != null) {
retMatrix.setM4(m);
}if (uc == null) return pts;
} else if (retMatrix != null || uc == null) {
return null;
} else if (Clazz.instanceOf(def,"JU.M3")) {
m = JU.M4.newMV(def,  new JU.P3());
} else if (Clazz.instanceOf(def,"JU.M4")) {
m = def;
} else {
m = (def)[0];
m.getRotationScale(m3);
m.rotTrans(pt);
uc.toCartesian(pt, false);
for (var i = 1; i < 4; i++) {
m3.rotate(pts[i]);
uc.toCartesian(pts[i], true);
}
return pts;
}m.getRotationScale(m3);
m.getTranslation(pt);
uc.toCartesian(pt, false);
for (var i = 1; i < 4; i++) {
m3.rotate(pts[i]);
uc.toCartesian(pts[i], true);
}
return pts;
}, "JU.SimpleUnitCell,~O,JU.M4");
c$.addTrans = Clazz.defineMethod(c$, "addTrans", 
function(strans, t){
if (strans == null) return;
var atrans = JU.PT.split(strans, ",");
var ftrans =  Clazz.newFloatArray (3, 0);
if (atrans.length == 3) {
for (var j = 0; j < 3; j++) {
var s = atrans[j];
var sfpt = s.indexOf("/");
if (sfpt >= 0) {
ftrans[j] = JU.PT.parseFloat(s.substring(0, sfpt)) / JU.PT.parseFloat(s.substring(sfpt + 1));
} else {
ftrans[j] = JU.PT.parseFloat(s);
}}
}t.add3(ftrans[0], ftrans[1], ftrans[2]);
}, "~S,JU.P3");
c$.fixABC = Clazz.defineMethod(c$, "fixABC", 
function(ret){
var tokens = JU.PT.split(ret[0], ",");
if (tokens.length != 3) return null;
var trans = "";
var abc = "";
var haveT = false;
for (var i = 0; i < 3; i++) {
var a = tokens[i];
var p;
var n = 0;
for (p = a.length; --p >= 0; ) {
var c = a.charAt(p);
switch ((c).charCodeAt(0)) {
default:
if (c >= 'a') p = 0;
break;
case 43:
n = 1;
case 45:
p = -p;
break;
}
}
p = -1 - p;
if (p == 0) {
trans += ",0";
abc += "," + a;
} else {
haveT = true;
trans += "," + a.substring(p + n);
abc += "," + a.substring(0, p);
}}
ret[0] = abc.substring(1);
return (haveT ? trans.substring(1) : null);
}, "~A");
Clazz.defineMethod(c$, "getVertices", 
function(){
return this.vertices;
});
Clazz.defineMethod(c$, "hasOffset", 
function(){
return (this.fractionalOffset != null && this.fractionalOffset.lengthSquared() != 0);
});
Clazz.defineMethod(c$, "initOrientation", 
function(mat){
if (mat == null) return;
var m =  new JU.M4();
m.setToM3(mat);
this.matrixFractionalToCartesian.mul2(m, this.matrixFractionalToCartesian);
this.matrixCartesianToFractional.setM4(this.matrixFractionalToCartesian).invert();
this.initUnitcellVertices();
}, "JU.M3");
Clazz.defineMethod(c$, "initUnitcellVertices", 
function(){
if (this.matrixFractionalToCartesian == null) return;
this.matrixCtoFNoOffset = JU.M4.newM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset = JU.M4.newM4(this.matrixFractionalToCartesian);
this.vertices =  new Array(8);
for (var i = 8; --i >= 0; ) this.vertices[i] = this.matrixFractionalToCartesian.rotTrans2(JU.BoxInfo.unitCubePoints[i],  new JU.P3());

});
Clazz.defineMethod(c$, "isSameAs", 
function(f2c2){
if (f2c2 == null) return false;
var f2c = this.getF2C();
for (var i = 0; i < 3; i++) {
for (var j = 0; j < 4; j++) {
if (!JU.SimpleUnitCell.approx0(f2c[i][j] - f2c2[i][j])) return false;
}
}
return true;
}, "~A");
Clazz.defineMethod(c$, "getF2C", 
function(){
if (this.f2c == null) {
this.f2c =  Clazz.newFloatArray (3, 4, 0);
for (var i = 0; i < 3; i++) this.matrixFractionalToCartesian.getRow(i, this.f2c[i]);

}return this.f2c;
});
Clazz.defineMethod(c$, "isWithinUnitCell", 
function(a, b, c, pt){
switch (this.dimension) {
case 3:
if (pt.z < c - 1 - this.slop || pt.z > c + this.slop) return false;
case 2:
if (pt.y < b - 1 - this.slop || pt.y > b + this.slop) return false;
case 1:
if (pt.x < a - 1 - this.slop || pt.x > a + this.slop) return false;
}
return true;
}, "~N,~N,~N,JU.P3");
Clazz.defineMethod(c$, "setCartesianOffset", 
function(origin){
this.cartesianOffset.setT(origin);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
var wasOffset = this.hasOffset();
this.fractionalOffset = JU.P3.newP(this.cartesianOffset);
this.matrixCartesianToFractional.rotate(this.fractionalOffset);
this.matrixCartesianToFractional.m03 = -this.fractionalOffset.x;
this.matrixCartesianToFractional.m13 = -this.fractionalOffset.y;
this.matrixCartesianToFractional.m23 = -this.fractionalOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4(this.matrixFractionalToCartesian);
}if (!wasOffset && this.fractionalOffset.lengthSquared() == 0) this.fractionalOffset = null;
this.f2c = null;
}, "JU.T3");
Clazz.defineMethod(c$, "setOffset", 
function(pt){
if (pt == null) return;
this.unitCellMultiplied = null;
var pt4 = (Clazz.instanceOf(pt,"JU.T4") ? pt : null);
var w = (pt4 == null ? 1.4E-45 : pt4.w);
var isCell555P4 = (w > 999999);
if (pt4 != null ? w <= 0 || isCell555P4 : pt.x >= 100 || pt.y >= 100) {
this.unitCellMultiplier = (pt.z == 0 && pt.x == pt.y && !isCell555P4 ? null : isCell555P4 ? JU.P4.newPt(pt4) : JU.P3.newP(pt));
this.unitCellMultiplied = null;
if (pt4 == null || pt4.w == 0 || isCell555P4) return;
}if (this.hasOffset() || pt.lengthSquared() > 0) {
this.fractionalOffset = JU.P3.newP(pt);
}this.matrixCartesianToFractional.m03 = -pt.x;
this.matrixCartesianToFractional.m13 = -pt.y;
this.matrixCartesianToFractional.m23 = -pt.z;
this.cartesianOffset.setT(pt);
this.matrixFractionalToCartesian.rotate(this.cartesianOffset);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4(this.matrixFractionalToCartesian);
}this.f2c = null;
}, "JU.T3");
Clazz.defineMethod(c$, "toFromPrimitive", 
function(toPrimitive, type, uc, primitiveToCrystal){
var offset = uc.length - 3;
var mf = null;
if (type == 'r' || primitiveToCrystal == null) {
switch ((type).charCodeAt(0)) {
default:
return false;
case 114:
JU.SimpleUnitCell.getReciprocal(uc, uc, 1);
return true;
case 80:
toPrimitive = true;
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [1, 0, 0, 0, 1, 0, 0, 0, 1]));
break;
case 65:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [1, 0, 0, 0, 0.5, 0.5, 0, -0.5, 0.5]));
break;
case 66:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [0.5, 0, 0.5, 0, 1, 0, -0.5, 0, 0.5]));
break;
case 67:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [0.5, 0.5, 0, -0.5, 0.5, 0, 0, 0, 1]));
break;
case 82:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [0.6666667, -0.33333334, -0.33333334, 0.33333334, 0.33333334, -0.6666667, 0.33333334, 0.33333334, 0.33333334]));
break;
case 73:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [-0.5, .5, .5, .5, -0.5, .5, .5, .5, -0.5]));
break;
case 70:
mf = JU.M3.newA9( Clazz.newFloatArray(-1, [0, 0.5, 0.5, 0.5, 0, 0.5, 0.5, 0.5, 0]));
break;
}
if (!toPrimitive) mf.invert();
} else {
mf = JU.M3.newM3(primitiveToCrystal);
if (toPrimitive) mf.invert();
}for (var i = uc.length; --i >= offset; ) {
var p = uc[i];
this.toFractional(p, true);
mf.rotate(p);
this.toCartesian(p, true);
}
return true;
}, "~B,~S,~A,JU.M3");
Clazz.defineMethod(c$, "toUnitCell", 
function(pt, offset){
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans(pt);
this.unitize(pt);
this.matrixFractionalToCartesian.rotTrans(pt);
} else {
this.matrixCtoFNoOffset.rotTrans(pt);
this.unitize(pt);
pt.add(offset);
this.matrixFtoCNoOffset.rotTrans(pt);
}}, "JU.T3,JU.T3");
Clazz.defineMethod(c$, "toUnitCellRnd", 
function(pt, offset){
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans(pt);
this.unitizeRnd(pt);
this.matrixFractionalToCartesian.rotTrans(pt);
} else {
this.matrixCtoFNoOffset.rotTrans(pt);
this.unitizeRnd(pt);
pt.add(offset);
this.matrixFtoCNoOffset.rotTrans(pt);
}}, "JU.T3,JU.T3");
Clazz.defineMethod(c$, "unitize", 
function(pt){
this.unitizeDim(this.dimension, pt);
}, "JU.T3");
Clazz.defineMethod(c$, "unitizeRnd", 
function(pt){
JU.SimpleUnitCell.unitizeDimRnd(this.dimension, pt, this.slop);
}, "JU.T3");
c$.createCompatibleUnitCell = Clazz.defineMethod(c$, "createCompatibleUnitCell", 
function(sg, params, newParams, allowSame){
if (newParams == null) newParams = params;
var a = params[0];
var b = params[1];
var c = params[2];
var alpha = params[3];
var beta = params[4];
var gamma = params[5];
var n = (sg == null || sg.itaNumber == null ? 0 : JU.PT.parseInt(sg.itaNumber));
var toHex = (n != 0 && JS.UnitCell.isHexagonalSG(n, null));
var isHex = (toHex && JS.UnitCell.isHexagonalSG(-1, params));
var toRhom = (n != 0 && sg.axisChoice == 'r');
var isRhom = (toRhom && JU.SimpleUnitCell.isRhombohedral(params));
if (toHex && isHex || toRhom && isRhom) {
allowSame = true;
}if (n > (allowSame ? 2 : 0)) {
var absame = JU.SimpleUnitCell.approx0(a - b);
var bcsame = JU.SimpleUnitCell.approx0(b - c);
var acsame = JU.SimpleUnitCell.approx0(c - a);
var albesame = JU.SimpleUnitCell.approx0(alpha - beta);
var begasame = JU.SimpleUnitCell.approx0(beta - gamma);
var algasame = JU.SimpleUnitCell.approx0(gamma - alpha);
if (!allowSame) {
if (a > b) {
var d = a;
a = b;
b = d;
}bcsame = JU.SimpleUnitCell.approx0(b - c);
if (bcsame) c = b * 1.5;
absame = JU.SimpleUnitCell.approx0(a - b);
if (absame) b = a * 1.2;
acsame = JU.SimpleUnitCell.approx0(c - a);
if (acsame) c = a * 1.1;
if (JU.SimpleUnitCell.approx0(alpha - 90)) {
alpha = 80;
}if (JU.SimpleUnitCell.approx0(beta - 90)) {
beta = 100;
}if (JU.SimpleUnitCell.approx0(gamma - 90)) {
gamma = 110;
}if (alpha > beta) {
var d = alpha;
alpha = beta;
beta = d;
}albesame = JU.SimpleUnitCell.approx0(alpha - beta);
begasame = JU.SimpleUnitCell.approx0(beta - gamma);
algasame = JU.SimpleUnitCell.approx0(gamma - alpha);
if (albesame) {
beta = alpha * 1.2;
}if (begasame) {
gamma = beta * 1.3;
}if (algasame) {
gamma = alpha * 1.4;
}}if (toHex) {
if (toRhom ? isRhom : isHex) {
} else if (sg.axisChoice == 'r') {
c = b = a;
if (!allowSame && alpha > 85 && alpha < 95) alpha = 80;
gamma = beta = alpha;
} else {
b = a;
alpha = beta = 90;
gamma = 120;
}} else if (n >= 195) {
c = b = a;
alpha = beta = gamma = 90;
} else if (n >= 75) {
b = a;
if (acsame && !allowSame) c = a * 1.5;
alpha = beta = gamma = 90;
} else if (n >= 16) {
alpha = beta = gamma = 90;
} else if (n >= 3) {
switch ((sg.uniqueAxis).charCodeAt(0)) {
case 97:
beta = gamma = 90;
break;
default:
case 98:
alpha = gamma = 90;
break;
case 99:
alpha = beta = 90;
break;
}
}}var isNew = !(a == params[0] && b == params[1] && c == params[2] && alpha == params[3] && beta == params[4] && gamma == params[5]);
newParams[0] = a;
newParams[1] = b;
newParams[2] = c;
newParams[3] = alpha;
newParams[4] = beta;
newParams[5] = gamma;
return isNew;
}, "JS.SpaceGroup,~A,~A,~B");
c$.isHexagonalSG = Clazz.defineMethod(c$, "isHexagonalSG", 
function(n, params){
return (n < 1 ? JU.SimpleUnitCell.isHexagonal(params) : n >= 143 && n <= 194);
}, "~N,~A");
c$.isMonoclinicSG = Clazz.defineMethod(c$, "isMonoclinicSG", 
function(n){
return (n >= 3 && n <= 15);
}, "~N");
c$.isTetragonalSG = Clazz.defineMethod(c$, "isTetragonalSG", 
function(n){
return (n >= 75 && n <= 142);
}, "~N");
c$.isPolarSG = Clazz.defineMethod(c$, "isPolarSG", 
function(n){
return (n == 1 || n >= 3 && n <= 5 || n >= 6 && n <= 9 || n >= 25 && n <= 46 || n >= 75 && n <= 80 || n >= 99 && n <= 110 || n >= 143 && n <= 146 || n >= 156 && n <= 161 || n >= 168 && n <= 173 || n >= 183 && n <= 186);
}, "~N");
c$.removeDuplicates = Clazz.defineMethod(c$, "removeDuplicates", 
function(list, i0, n0, n){
if (n < 0) n = list.size();
for (var i = i0; i < n; i++) {
var p = list.get(i);
for (var j = Math.max(i + 1, n0); j < n; j++) {
if (list.get(j).distanceSquared(p) < 1.96E-6) {
list.removeItemAt(j);
n--;
j--;
}}
}
}, "JU.Lst,~N,~N,~N");
c$.unitVectors =  Clazz.newArray(-1, [JV.JC.axisX, JV.JC.axisY, JV.JC.axisZ]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
