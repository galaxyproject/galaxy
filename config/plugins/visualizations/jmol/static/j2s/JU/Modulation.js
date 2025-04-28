Clazz.declarePackage("JU");
Clazz.load(null, "JU.Modulation", ["java.util.Hashtable", "JU.AU", "$.PT", "JU.Escape", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.qCoefs = null;
this.a1 = 0;
this.a2 = 0;
this.center = 0;
this.left = 0;
this.right = 0;
this.order = 0;
this.axis = '\0';
this.type = '\0';
this.params = null;
this.utens = null;
this.delta2 = 0;
Clazz.instantialize(this, arguments);}, JU, "Modulation", null);
Clazz.makeConstructor(c$, 
function(axis, type, params, utens, qCoefs){
JU.Logger.info("MOD create " + JU.Escape.e(qCoefs) + " axis=" + axis + " type=" + type + " params=" + JU.Escape.e(params) + " utens=" + utens);
this.axis = axis;
this.type = type;
this.utens = utens;
this.params = params;
this.qCoefs = qCoefs;
switch ((type).charCodeAt(0)) {
case 109:
case 102:
case 111:
case 117:
this.a1 = params[0];
this.a2 = params[1];
break;
case 108:
case 76:
this.a1 = params[2];
this.order = Clazz.doubleToInt(params[3]);
this.calcLegendre(this.order);
case 116:
case 115:
case 99:
this.center = params[0];
this.delta2 = params[1] / 2;
if (this.delta2 > 0.5) this.delta2 = 0.5;
this.left = this.center - this.delta2;
this.right = this.center + this.delta2;
if (this.left < 0) this.left += 1;
if (this.right > 1) this.right -= 1;
if (this.left >= this.right && this.left - this.right < 0.01) this.left = this.right + 0.01;
if (this.a1 == 0) {
this.a1 = params[2] / this.delta2;
}break;
}
}, "~S,~S,~A,~S,~A");
Clazz.defineMethod(c$, "apply", 
function(ms, t){
var v = 0;
var nt = 0;
var isSpin = false;
for (var i = this.qCoefs.length; --i >= 0; ) nt += this.qCoefs[i] * t[i][0];

switch ((this.type).charCodeAt(0)) {
case 109:
isSpin = true;
case 102:
case 111:
case 117:
var theta = 6.283185307179586 * nt;
if (this.a1 != 0) v += this.a1 * Math.sin(theta);
if (this.a2 != 0) v += this.a2 * Math.cos(theta);
if (JU.Logger.debuggingHigh) JU.Logger.info("MOD " + ms.id + " " + t[0][0] + " " + JU.Escape.e(this.qCoefs) + " axis=" + this.axis + " v=" + v + " csin,ccos=" + this.a1 + "," + this.a2 + " / theta=" + theta);
break;
case 76:
case 108:
ms.occAbsolute = true;
nt -= Math.floor(nt);
if (!this.range(nt)) {
ms.vOcc = 0;
return;
}ms.vOcc = 1;
var x = (nt - this.center) / this.delta2;
x = ((x + 1) % 2) + (x < -1 ? 1 : -1);
var xp = 1;
var p = JU.Modulation.legendre[this.order];
var i = 0;
var n = p.length;
while (true) {
v += p[i] * xp;
if (++i == n) break;
xp *= x;
}
v *= this.a1;
break;
case 99:
ms.occAbsolute = true;
ms.vOcc = (this.range(nt - Math.floor(nt)) ? 1 : 0);
return;
case 116:
isSpin = true;
case 115:
ms.occAbsolute = true;
nt -= Math.floor(nt);
if (!this.range(nt)) {
ms.vOcc = 0;
return;
}ms.vOcc = 1;
if (this.left > this.right) {
if (nt < this.left && this.left < this.center) nt += 1;
 else if (nt > this.right && this.right > this.center) nt -= 1;
}v = this.a1 * (nt - this.center);
break;
}
if (isSpin) {
var f = ms.axesLengths;
if (f == null) System.out.println("Modulation.java axis error");
switch ((this.axis).charCodeAt(0)) {
case 120:
ms.mxyz.x += v / f[0];
break;
case 121:
ms.mxyz.y += v / f[1];
break;
case 122:
ms.mxyz.z += v / f[2];
break;
}
} else {
switch ((this.axis).charCodeAt(0)) {
case 120:
ms.x += v;
break;
case 121:
ms.y += v;
break;
case 122:
ms.z += v;
break;
case 85:
ms.addUTens(this.utens, v);
break;
default:
if (Float.isNaN(ms.vOcc)) ms.vOcc = 0;
ms.vOcc += v;
}
}}, "JU.ModulationSet,~A");
Clazz.defineMethod(c$, "range", 
function(x4){
return (this.left < this.right ? this.left <= x4 && x4 <= this.right : this.left <= x4 || x4 <= this.right);
}, "~N");
Clazz.defineMethod(c$, "getInfo", 
function(){
var info =  new java.util.Hashtable();
info.put("type", "" + this.type + this.axis);
info.put("params", this.params);
info.put("qCoefs", this.qCoefs);
if (this.utens != null) info.put("Utens", this.utens);
return info;
});
Clazz.defineMethod(c$, "calcLegendre", 
function(m){
var n = JU.Modulation.legendre.length;
if (n > m) return;
m += 3;
var l = JU.AU.newDouble2(m + 1);
for (var i = 0; i < n; i++) l[i] = JU.Modulation.legendre[i];

for (; n <= m; n++) {
var p = l[n] =  Clazz.newDoubleArray (n + 1, 0);
for (var i = 0; i < n; i++) {
p[i + 1] = (2 * n - 1) * l[n - 1][i] / n;
if (i < n - 1) p[i] += (1 - n) * l[n - 2][i] / n;
}
}
JU.Modulation.legendre = l;
}, "~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return "[Modulation " + this.type + " " + JU.PT.toJSON(null, this.params) + "]";
});
c$.legendre =  Clazz.newArray(-1, [ Clazz.newDoubleArray(-1, [1]),  Clazz.newDoubleArray(-1, [0, 1])]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
