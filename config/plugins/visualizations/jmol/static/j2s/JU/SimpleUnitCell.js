Clazz.declarePackage("JU");
Clazz.load(["JV.Viewer"], "JU.SimpleUnitCell", ["JU.AU", "$.M4", "$.P3", "$.P4", "$.PT", "$.V3", "JU.Escape"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.unitCellParams = null;
this.slop = 0;
this.matrixCartesianToFractional = null;
this.matrixFractionalToCartesian = null;
this.matrixCtoFNoOffset = null;
this.matrixFtoCNoOffset = null;
this.volume = 0;
this.dimension = 3;
this.fractionalOrigin = null;
this.na = 0;
this.nb = 0;
this.nc = 0;
this.a = 0;
this.b = 0;
this.c = 0;
this.alpha = 0;
this.beta = 0;
this.gamma = 0;
this.cosAlpha = 0;
this.sinAlpha = 0;
this.cosBeta = 0;
this.sinBeta = 0;
this.cosGamma = 0;
this.sinGamma = 0;
this.cA_ = 0;
this.cB_ = 0;
this.a_ = 0;
this.b_ = 0;
this.c_ = 0;
Clazz.instantialize(this, arguments);}, JU, "SimpleUnitCell", null);
Clazz.prepareFields (c$, function(){
this.slop = (JV.Viewer.isHighPrecision ? 1.0E-12 : 1.0E-4);
});
Clazz.makeConstructor(c$, 
function(){
this.fractionalOrigin =  new JU.P3();
});
Clazz.defineMethod(c$, "getPrecision", 
function(){
return this.slop;
});
Clazz.defineMethod(c$, "setPrecision", 
function(slop){
this.unitCellParams[26] = this.slop = (!Float.isNaN(slop) ? slop : !Float.isNaN(this.unitCellParams[26]) ? this.unitCellParams[26] : JV.Viewer.isHighPrecision ? 1.0E-12 : 1.0E-4);
}, "~N");
Clazz.defineMethod(c$, "isSupercell", 
function(){
return (this.na > 1 || this.nb > 1 || this.nc > 1);
});
c$.isValid = Clazz.defineMethod(c$, "isValid", 
function(parameters){
return (parameters != null && (parameters[0] > 0 || parameters.length > 14 && !Float.isNaN(parameters[14])));
}, "~A");
c$.newA = Clazz.defineMethod(c$, "newA", 
function(params){
var c =  new JU.SimpleUnitCell();
c.init(params);
return c;
}, "~A");
c$.getDimensionFromParams = Clazz.defineMethod(c$, "getDimensionFromParams", 
function(params){
return (params[0] <= 0 ? 3 : params[1] < 0 ? 1 : params[2] < 0 ? 2 : 3);
}, "~A");
Clazz.defineMethod(c$, "init", 
function(params){
if (params == null) params =  Clazz.newFloatArray(-1, [1, 1, 1, 90, 90, 90]);
if (!JU.SimpleUnitCell.isValid(params)) return;
this.unitCellParams = JU.SimpleUnitCell.newParams(params, NaN);
var rotateHex = false;
this.dimension = JU.SimpleUnitCell.getDimensionFromParams(params);
this.a = params[0];
this.b = params[1];
this.c = params[2];
this.alpha = params[3];
this.beta = params[4];
this.gamma = params[5];
if (this.gamma == -1 && this.c > 0) {
rotateHex = true;
this.gamma = 120;
}if (params.length > 26) {
if (Float.isNaN(params[26])) {
params[26] = this.slop;
} else {
this.slop = params[26];
}}var fa = this.na = Math.max(1, params.length > 24 && !Float.isNaN(params[22]) ? Clazz.floatToInt(params[22]) : 1);
var fb = this.nb = Math.max(1, params.length > 24 && !Float.isNaN(params[23]) ? Clazz.floatToInt(params[23]) : 1);
var fc = this.nc = Math.max(1, params.length > 24 && !Float.isNaN(params[24]) ? Clazz.floatToInt(params[24]) : 1);
if (params.length > 25 && !Float.isNaN(params[25])) {
var fScale = params[25];
if (fScale > 0) {
fa *= fScale;
fb *= fScale;
fc *= fScale;
}} else {
fa = fb = fc = 1;
}if (this.a <= 0 && this.c <= 0) {
var va = JU.SimpleUnitCell.newV(params, 6);
var vb = JU.SimpleUnitCell.newV(params, 9);
var vc = JU.SimpleUnitCell.newV(params, 12);
this.setABC(va, vb, vc);
if (this.c < 0) {
var n = JU.AU.arrayCopyF(params, -1);
if (this.b < 0) {
vb.set(0, 0, 1);
vb.cross(vb, va);
if (vb.length() < 0.001) vb.set(0, 1, 0);
vb.normalize();
n[9] = vb.x;
n[10] = vb.y;
n[11] = vb.z;
}if (this.c < 0) {
vc.cross(va, vb);
vc.normalize();
n[12] = vc.x;
n[13] = vc.y;
n[14] = vc.z;
}params = n;
}}this.a *= fa;
if (this.b <= 0) {
this.b = this.c = 1;
} else if (this.c <= 0) {
this.c = 1;
this.b *= fb;
} else {
this.b *= fb;
this.c *= fc;
}this.setCellParams();
if (params.length > 21 && !Float.isNaN(params[21])) {
var scaleMatrix =  Clazz.newFloatArray (16, 0);
for (var i = 0; i < 16; i++) {
var f;
switch (i % 4) {
case 0:
f = fa;
break;
case 1:
f = fb;
break;
case 2:
f = fc;
break;
default:
f = 1;
break;
}
scaleMatrix[i] = params[6 + i] * f;
}
this.matrixCartesianToFractional = JU.M4.newA16(scaleMatrix);
this.matrixCartesianToFractional.getTranslation(this.fractionalOrigin);
this.matrixFractionalToCartesian = JU.M4.newM4(this.matrixCartesianToFractional).invert();
if (params[0] == 1) this.setParamsFromMatrix();
} else if (params.length > 14 && !Float.isNaN(params[14])) {
var m = this.matrixFractionalToCartesian =  new JU.M4();
m.setColumn4(0, params[6] * fa, params[7] * fa, params[8] * fa, 0);
m.setColumn4(1, params[9] * fb, params[10] * fb, params[11] * fb, 0);
m.setColumn4(2, params[12] * fc, params[13] * fc, params[14] * fc, 0);
if (params.length > 17 && !Float.isNaN(params[17])) {
m.setColumn4(3, params[15], params[16], params[17], 1);
} else {
m.setColumn4(3, 0, 0, 0, 1);
}this.matrixCartesianToFractional = JU.M4.newM4(this.matrixFractionalToCartesian).invert();
} else {
var m = this.matrixFractionalToCartesian =  new JU.M4();
if (rotateHex) {
m.setColumn4(0, (-this.b * this.cosGamma), (-this.b * this.sinGamma), 0, 0);
m.setColumn4(1, (-this.b * this.cosGamma), (this.b * this.sinGamma), 0, 0);
} else {
m.setColumn4(0, this.a, 0, 0, 0);
m.setColumn4(1, (this.b * this.cosGamma), (this.b * this.sinGamma), 0, 0);
}m.setColumn4(2, (this.c * this.cosBeta), (this.c * (this.cosAlpha - this.cosBeta * this.cosGamma) / this.sinGamma), (this.volume / (this.a * this.b * this.sinGamma)), 0);
m.setColumn4(3, 0, 0, 0, 1);
this.matrixCartesianToFractional = JU.M4.newM4(this.matrixFractionalToCartesian).invert();
}this.matrixCtoFNoOffset = this.matrixCartesianToFractional;
this.matrixFtoCNoOffset = this.matrixFractionalToCartesian;
}, "~A");
c$.newV = Clazz.defineMethod(c$, "newV", 
function(p, i){
return JU.V3.new3(p[i++], p[i++], p[i]);
}, "~A,~N");
c$.newParams = Clazz.defineMethod(c$, "newParams", 
function(params, slop){
var p =  Clazz.newFloatArray (27, 0);
var n = params.length;
for (var i = 0; i < 27; i++) p[i] = (i < n ? params[i] : NaN);

if (n < 27) p[26] = slop;
return p;
}, "~A,~N");
c$.addVectors = Clazz.defineMethod(c$, "addVectors", 
function(params){
var c = JU.SimpleUnitCell.newA(params);
var m = c.matrixFractionalToCartesian;
for (var i = 0; i < 9; i++) params[6 + i] = m.getElement(i % 3, Clazz.doubleToInt(i / 3));

}, "~A");
Clazz.defineMethod(c$, "setParamsFromMatrix", 
function(){
var va = JU.V3.new3(1, 0, 0);
var vb = JU.V3.new3(0, 1, 0);
var vc = JU.V3.new3(0, 0, 1);
this.matrixFractionalToCartesian.rotate(va);
this.matrixFractionalToCartesian.rotate(vb);
this.matrixFractionalToCartesian.rotate(vc);
this.setABC(va, vb, vc);
this.setCellParams();
});
Clazz.defineMethod(c$, "setABC", 
function(va, vb, vc){
JU.SimpleUnitCell.fillParams(va, vb, vc, this.unitCellParams);
var p = this.unitCellParams;
this.a = p[0];
this.b = p[1];
this.c = p[2];
this.alpha = p[3];
this.beta = p[4];
this.gamma = p[5];
}, "JU.V3,JU.V3,JU.V3");
c$.fillParams = Clazz.defineMethod(c$, "fillParams", 
function(va, vb, vc, p){
if (va == null) {
va = JU.SimpleUnitCell.newV(p, 6);
vb = JU.SimpleUnitCell.newV(p, 9);
vc = JU.SimpleUnitCell.newV(p, 12);
}var a = va.length();
var b = vb.length();
var c = vc.length();
if (a == 0) return;
if (b == 0) b = c = -1;
 else if (c == 0) c = -1;
p[0] = a;
p[1] = b;
p[2] = c;
p[3] = (b < 0 || c < 0 ? 90 : vb.angle(vc) / 0.017453292519943295);
p[4] = (c < 0 ? 90 : va.angle(vc) / 0.017453292519943295);
p[5] = (b < 0 ? 90 : va.angle(vb) / 0.017453292519943295);
}, "JU.V3,JU.V3,JU.V3,~A");
Clazz.defineMethod(c$, "setCellParams", 
function(){
this.cosAlpha = Math.cos(0.017453292519943295 * this.alpha);
this.sinAlpha = Math.sin(0.017453292519943295 * this.alpha);
this.cosBeta = Math.cos(0.017453292519943295 * this.beta);
this.sinBeta = Math.sin(0.017453292519943295 * this.beta);
this.cosGamma = Math.cos(0.017453292519943295 * this.gamma);
this.sinGamma = Math.sin(0.017453292519943295 * this.gamma);
var unitVolume = Math.sqrt(this.sinAlpha * this.sinAlpha + this.sinBeta * this.sinBeta + this.sinGamma * this.sinGamma + 2.0 * this.cosAlpha * this.cosBeta * this.cosGamma - 2);
this.volume = this.a * this.b * this.c * unitVolume;
this.cA_ = (this.cosAlpha - this.cosBeta * this.cosGamma) / this.sinGamma;
this.cB_ = unitVolume / this.sinGamma;
this.a_ = this.b * this.c * this.sinAlpha / this.volume;
this.b_ = this.a * this.c * this.sinBeta / this.volume;
this.c_ = this.a * this.b * this.sinGamma / this.volume;
});
Clazz.defineMethod(c$, "getFractionalOrigin", 
function(){
return this.fractionalOrigin;
});
Clazz.defineMethod(c$, "toSupercell", 
function(fpt){
fpt.x /= this.na;
fpt.y /= this.nb;
fpt.z /= this.nc;
return fpt;
}, "JU.P3");
Clazz.defineMethod(c$, "toCartesian", 
function(pt, ignoreOffset){
if (this.matrixFractionalToCartesian != null) (ignoreOffset ? this.matrixFtoCNoOffset : this.matrixFractionalToCartesian).rotTrans(pt);
}, "JU.T3,~B");
Clazz.defineMethod(c$, "toFractionalM", 
function(m){
if (this.matrixCartesianToFractional == null) return;
m.mul(this.matrixFractionalToCartesian);
m.mul2(this.matrixCartesianToFractional, m);
}, "JU.M4");
Clazz.defineMethod(c$, "toFractional", 
function(pt, ignoreOffset){
if (this.matrixCartesianToFractional == null) return;
(ignoreOffset ? this.matrixCtoFNoOffset : this.matrixCartesianToFractional).rotTrans(pt);
}, "JU.T3,~B");
Clazz.defineMethod(c$, "isPolymer", 
function(){
return (this.dimension == 1);
});
Clazz.defineMethod(c$, "isSlab", 
function(){
return (this.dimension == 2);
});
Clazz.defineMethod(c$, "getUnitCellParams", 
function(){
return this.unitCellParams;
});
Clazz.defineMethod(c$, "getUnitCellAsArray", 
function(vectorsOnly){
var m = this.matrixFractionalToCartesian;
return (vectorsOnly ?  Clazz.newFloatArray(-1, [m.m00, m.m10, m.m20, m.m01, m.m11, m.m21, m.m02, m.m12, m.m22]) :  Clazz.newFloatArray(-1, [this.a, this.b, this.c, this.alpha, this.beta, this.gamma, m.m00, m.m10, m.m20, m.m01, m.m11, m.m21, m.m02, m.m12, m.m22, this.dimension, this.volume]));
}, "~B");
Clazz.defineMethod(c$, "getInfo", 
function(infoType){
switch (infoType) {
case 0:
return this.a;
case 1:
return this.b;
case 2:
return this.c;
case 3:
return this.alpha;
case 4:
return this.beta;
case 5:
return this.gamma;
case 6:
return this.dimension;
case 7:
return (JU.SimpleUnitCell.isHexagonal(this.unitCellParams) ? 1 : 0);
case 8:
return (JU.SimpleUnitCell.isRhombohedral(this.unitCellParams) ? 1 : 0);
}
return NaN;
}, "~N");
c$.getReciprocal = Clazz.defineMethod(c$, "getReciprocal", 
function(abc, ret, scale){
var off = (abc.length == 4 ? 1 : 0);
var rabc =  new Array(4);
rabc[0] = (off == 1 ? JU.P3.newP(abc[0]) :  new JU.P3());
if (scale == 0) scale = (6.283185307179586);
for (var i = 0; i < 3; i++) {
var v = rabc[i + 1] =  new JU.P3();
v.cross(abc[((i + 1) % 3) + off], abc[((i + 2) % 3) + off]);
var vol = abc[i + off].dot(v);
if (scale == -1) scale = Math.sqrt(vol);
v.scale(scale / vol);
}
if (ret == null) return rabc;
for (var i = 0; i < 4; i++) {
ret[i] = rabc[i];
}
return ret;
}, "~A,~A,~N");
c$.setAbc = Clazz.defineMethod(c$, "setAbc", 
function(abcabg, params, ucnew){
if (abcabg != null) {
if (params == null) params =  Clazz.newFloatArray (6, 0);
var tokens = JU.PT.split(abcabg.$replace(',', '='), "=");
if (tokens.length >= 12) for (var i = 0; i < 6; i++) params[i] = JU.PT.parseFloat(tokens[i * 2 + 1]);

}if (ucnew == null) return null;
return JU.SimpleUnitCell.setAbcFromParams(params, ucnew);
}, "~S,~A,~A");
c$.setAbcFromParams = Clazz.defineMethod(c$, "setAbcFromParams", 
function(params, ucnew){
var f = JU.SimpleUnitCell.newA(params).getUnitCellAsArray(true);
ucnew[1].set(f[0], f[1], f[2]);
ucnew[2].set(f[3], f[4], f[5]);
ucnew[3].set(f[6], f[7], f[8]);
return ucnew;
}, "~A,~A");
Clazz.defineMethod(c$, "unitizeDim", 
function(dimension, pt){
switch (dimension) {
case 3:
pt.z = JU.SimpleUnitCell.unitizeX(pt.z, this.slop);
case 2:
pt.y = JU.SimpleUnitCell.unitizeX(pt.y, this.slop);
case 1:
pt.x = JU.SimpleUnitCell.unitizeX(pt.x, this.slop);
}
}, "~N,JU.T3");
c$.unitizeDimRnd = Clazz.defineMethod(c$, "unitizeDimRnd", 
function(dimension, pt, slop){
switch (dimension) {
case 3:
pt.z = JU.SimpleUnitCell.unitizeXRnd(pt.z, slop);
case 2:
pt.y = JU.SimpleUnitCell.unitizeXRnd(pt.y, slop);
case 1:
pt.x = JU.SimpleUnitCell.unitizeXRnd(pt.x, slop);
}
}, "~N,JU.T3,~N");
c$.unitizeX = Clazz.defineMethod(c$, "unitizeX", 
function(x, slop){
x = (x - Math.floor(x));
if (x > 1 - slop || x < slop) x = 0;
return x;
}, "~N,~N");
c$.unitizeXRnd = Clazz.defineMethod(c$, "unitizeXRnd", 
function(x, slop){
x = (x - Math.floor(x));
if (x > 1 - slop || x < slop) x = 0;
return x;
}, "~N,~N");
Clazz.defineMethod(c$, "twelfthsOf", 
function(f){
if (f == 0) return 0;
f = Math.abs(f * 12);
var i = Math.round(f);
return (i <= 12 && Math.abs(f - i) < this.slop * 12 ? i : -1);
}, "~N");
Clazz.defineMethod(c$, "twelfthify", 
function(pt){
switch (this.dimension) {
case 3:
pt.z = this.setTwelfths(pt.z);
case 2:
pt.y = this.setTwelfths(pt.y);
case 1:
pt.x = this.setTwelfths(pt.x);
break;
}
}, "JU.P3");
Clazz.defineMethod(c$, "setTwelfths", 
function(x){
var i = this.twelfthsOf(x);
return (i >= 0 ? i / 12 : x);
}, "~N");
c$.ijkToPoint3f = Clazz.defineMethod(c$, "ijkToPoint3f", 
function(nnn, cell, offset, kcode){
var f = (nnn > 1000000000 ? 1000 : nnn > 1000000 ? 100 : 10);
var f2 = f * f;
offset -= (offset >= 0 ? Clazz.doubleToInt(5 * f / 10) : offset);
cell.x = ((Clazz.doubleToInt(nnn / f2)) % f) + offset;
cell.y = Clazz.doubleToInt((nnn % f2) / f) + offset;
cell.z = (kcode == 0 ? nnn % f : (offset == -500 ? Clazz.doubleToInt(kcode / f) : kcode) % f) + offset;
}, "~N,JU.P3,~N,~N");
c$.ptToIJK = Clazz.defineMethod(c$, "ptToIJK", 
function(pt, scale){
if (pt.x <= 5 && pt.y <= 5 && pt.z <= 5) {
return JU.P4.new4(555, (pt.x + 4) * 100 + (pt.y + 4) * 10 + pt.z + 4, scale, 0);
}var i555 = 1500500500;
return JU.P4.new4(i555, i555 + pt.x * 1000000 + pt.y * 1000 + pt.z, scale, 1500500 + pt.z);
}, "JU.T3,~N");
c$.escapeMultiplier = Clazz.defineMethod(c$, "escapeMultiplier", 
function(pt){
if (Clazz.instanceOf(pt,"JU.P4")) {
var pt4 = pt;
var x = Clazz.doubleToInt(Math.floor(pt4.x / 1000)) * 1000 + Clazz.doubleToInt(Math.floor(pt4.w / 1000)) - 1000;
var y = Clazz.doubleToInt(Math.floor(pt4.y / 1000)) * 1000 + Clazz.doubleToInt(Math.floor(pt4.w)) % 1000;
return "{" + x + " " + y + " " + pt.z + "}";
}return JU.Escape.eP(pt);
}, "JU.T3");
c$.setMinMaxLatticeParameters = Clazz.defineMethod(c$, "setMinMaxLatticeParameters", 
function(dimension, minXYZ, maxXYZ, kcode){
if (maxXYZ.x <= maxXYZ.y && maxXYZ.y >= 555) {
var pt =  new JU.P3();
JU.SimpleUnitCell.ijkToPoint3f(maxXYZ.x, pt, 0, kcode);
minXYZ.x = Clazz.floatToInt(pt.x);
minXYZ.y = Clazz.floatToInt(pt.y);
minXYZ.z = Clazz.floatToInt(pt.z);
JU.SimpleUnitCell.ijkToPoint3f(maxXYZ.y, pt, 1, kcode);
maxXYZ.x = Clazz.floatToInt(pt.x);
maxXYZ.y = Clazz.floatToInt(pt.y);
maxXYZ.z = Clazz.floatToInt(pt.z);
}switch (dimension) {
case 1:
minXYZ.y = 0;
maxXYZ.y = 1;
case 2:
minXYZ.z = 0;
maxXYZ.z = 1;
}
}, "~N,JU.P3i,JU.P3i,~N");
c$.isHexagonal = Clazz.defineMethod(c$, "isHexagonal", 
function(params){
return (JU.SimpleUnitCell.approx0(params[0] - params[1]) && JU.SimpleUnitCell.approx0(params[3] - 90) && JU.SimpleUnitCell.approx0(params[4] - 90) && (JU.SimpleUnitCell.approx0(params[5] - 120) || params[5] == -1));
}, "~A");
c$.isRhombohedral = Clazz.defineMethod(c$, "isRhombohedral", 
function(params){
return (JU.SimpleUnitCell.approx0(params[0] - params[1]) && JU.SimpleUnitCell.approx0(params[1] - params[2]) && !JU.SimpleUnitCell.approx0(params[3] - 90) && JU.SimpleUnitCell.approx0(params[3] - params[4]) && JU.SimpleUnitCell.approx0(params[4] - params[5]));
}, "~A");
c$.approx0 = Clazz.defineMethod(c$, "approx0", 
function(f){
return (Math.abs(f) < 0.001);
}, "~N");
c$.getCellRange = Clazz.defineMethod(c$, "getCellRange", 
function(fset, cellRange){
var t3w = (Clazz.instanceOf(fset,"JU.T4") ? Clazz.floatToInt((fset).w) : 0);
JU.SimpleUnitCell.ijkToPoint3f(Clazz.floatToInt(fset.x), cellRange[0], 0, t3w);
JU.SimpleUnitCell.ijkToPoint3f(Clazz.floatToInt(fset.y), cellRange[1], 1, t3w);
if (fset.z < 0) {
cellRange[0].scale(-1 / fset.z);
cellRange[1].scale(-1 / fset.z);
}return t3w;
}, "JU.T3,~A");
Clazz.overrideMethod(c$, "toString", 
function(){
return "[" + this.a + " " + this.b + " " + this.c + " " + this.alpha + " " + this.beta + " " + this.gamma + "]";
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
