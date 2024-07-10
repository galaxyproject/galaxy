Clazz.declarePackage("JS");
Clazz.load(["JU.M3", "$.V3"], "JS.PointGroup", ["java.util.Hashtable", "JU.Lst", "$.P3", "$.PT", "$.Quat", "$.SB", "J.bspt.Bspt", "JU.BSUtil", "$.Escape", "$.Logger", "$.Point3fi"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.isAtoms = false;
this.drawInfo = null;
this.info = null;
this.textInfo = null;
this.iter = null;
this.drawType = "";
this.drawIndex = 0;
this.scale = NaN;
this.nAxes = null;
this.axes = null;
this.nAtoms = 0;
this.radius = 0;
this.distanceTolerance = 0.25;
this.distanceTolerance2 = 0;
this.linearTolerance = 8;
this.cosTolerance = 0.99;
this.name = "C_1?";
this.principalAxis = null;
this.principalPlane = null;
this.convention = 0;
this.vTemp = null;
this.centerAtomIndex = -1;
this.haveInversionCenter = false;
this.center = null;
this.points = null;
this.elements = null;
this.atomMap = null;
this.bsAtoms = null;
this.haveVibration = false;
this.localEnvOnly = false;
this.$isLinear = false;
this.sppa = 0;
this.maxAtoms = 250;
this.maxElement = 0;
this.eCounts = null;
this.nOps = 0;
if (!Clazz.isClassDefined("JS.PointGroup.Operation")) {
JS.PointGroup.$PointGroup$Operation$ ();
}
Clazz.instantialize(this, arguments);}, JS, "PointGroup", null);
Clazz.prepareFields (c$, function(){
this.nAxes =  Clazz.newIntArray (JS.PointGroup.maxAxis, 0);
this.axes =  new Array(JS.PointGroup.maxAxis);
this.vTemp =  new JU.V3();
});
Clazz.makeConstructor(c$, 
function(isHM){
this.convention = (isHM ? 1 : 0);
}, "~B");
Clazz.defineMethod(c$, "getName", 
function(){
return this.getConventionalName(this.name);
});
Clazz.defineMethod(c$, "getHermannMauguinName", 
function(){
return JS.PointGroup.getHMfromSFName(this.name);
});
Clazz.defineMethod(c$, "getConventionalName", 
function(name){
return (this.convention == 1 ? JS.PointGroup.getHMfromSFName(name) : name);
}, "~S");
c$.getPointGroup = Clazz.defineMethod(c$, "getPointGroup", 
function(pgLast, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly, isHM, sppa){
var pg =  new JS.PointGroup(isHM);
if (distanceTolerance <= 0) {
distanceTolerance = 0.01;
}if (linearTolerance <= 0) {
linearTolerance = 0.5;
}if (maxAtoms <= 0) maxAtoms = 250;
pg.distanceTolerance = distanceTolerance;
pg.distanceTolerance2 = distanceTolerance * distanceTolerance;
pg.linearTolerance = linearTolerance;
pg.maxAtoms = maxAtoms;
pg.isAtoms = (bsAtoms != null);
pg.bsAtoms = (pg.isAtoms ? bsAtoms : JU.BSUtil.newBitSet2(0, atomset.length));
pg.haveVibration = haveVibration;
pg.center = center;
pg.localEnvOnly = localEnvOnly;
pg.sppa = sppa;
if (JU.Logger.debugging) pgLast = null;
return (pg.set(pgLast, atomset) ? pg : pgLast);
}, "JS.PointGroup,JU.T3,~A,JU.BS,~B,~N,~N,~N,~B,~B,~N");
Clazz.defineMethod(c$, "isEqual", 
function(pg){
if (pg == null) return false;
if (this.convention != pg.convention || this.linearTolerance != pg.linearTolerance || this.distanceTolerance != pg.distanceTolerance || this.nAtoms != pg.nAtoms || this.localEnvOnly != pg.localEnvOnly || this.haveVibration != pg.haveVibration || this.bsAtoms == null ? pg.bsAtoms != null : !this.bsAtoms.equals(pg.bsAtoms)) return false;
for (var i = 0; i < this.nAtoms; i++) {
if (this.elements[i] != pg.elements[i] || !this.points[i].equals(pg.points[i])) return false;
}
return true;
}, "JS.PointGroup");
Clazz.defineMethod(c$, "set", 
function(pgLast, atomset){
this.cosTolerance = (Math.cos(this.linearTolerance / 180 * 3.141592653589793));
if (!this.getPointsAndElements(atomset)) {
JU.Logger.error("Too many atoms for point group calculation");
this.name = "point group not determined -- ac > " + this.maxAtoms + " -- select fewer atoms and try again.";
return true;
}this.getElementCounts();
if (this.haveVibration) {
var atomVibs =  new Array(this.points.length);
for (var i = this.points.length; --i >= 0; ) {
atomVibs[i] = JU.P3.newP(this.points[i]);
var v = (this.points[i]).getVibrationVector();
if (v != null) atomVibs[i].add(v);
}
this.points = atomVibs;
}if (this.isEqual(pgLast)) return false;
try {
this.findInversionCenter();
this.$isLinear = this.isLinear(this.points);
if (this.$isLinear) {
if (this.haveInversionCenter) {
this.name = "D(infinity)h";
} else {
this.name = "C(infinity)v";
}this.vTemp.sub2(this.points[1], this.points[0]);
this.addAxis(16, this.vTemp);
this.principalAxis = this.axes[16][0];
if (this.haveInversionCenter) {
this.axes[0] =  new Array(1);
this.principalPlane = this.axes[0][this.nAxes[0]++] = Clazz.innerTypeInstance(JS.PointGroup.Operation, this, null, this.vTemp);
}return true;
}this.axes[0] =  new Array(15);
var nPlanes = 0;
this.findCAxes();
nPlanes = this.findPlanes();
this.findAdditionalAxes(nPlanes);
var n = this.getHighestOrder();
if (this.nAxes[17] > 1) {
if (this.nAxes[19] > 1) {
if (this.haveInversionCenter) {
this.name = "Ih";
} else {
this.name = "I";
}} else if (this.nAxes[18] > 1) {
if (this.haveInversionCenter) {
this.name = "Oh";
} else {
this.name = "O";
}} else {
if (nPlanes > 0) {
if (this.haveInversionCenter) {
this.name = "Th";
} else {
this.name = "Td";
}} else {
this.name = "T";
}}} else {
if (n < 2) {
if (nPlanes == 1) {
this.name = "Cs";
return true;
}if (this.haveInversionCenter) {
this.name = "Ci";
return true;
}this.name = "C1";
} else if ((n % 2) == 1 && this.nAxes[16] > 0 || (n % 2) == 0 && this.nAxes[16] > 1) {
this.principalAxis = this.setPrincipalAxis(n, nPlanes);
if (nPlanes == 0) {
if (n < 14) {
this.name = "S" + n;
} else {
this.name = "D" + (n - 14);
}} else {
if (n < 14) n = Clazz.doubleToInt(n / 2);
 else n -= 14;
if (nPlanes == n) {
this.name = "D" + n + "d";
} else {
this.name = "D" + n + "h";
}}} else if (nPlanes == 0) {
this.principalAxis = this.axes[n][0];
if (n < 14) {
this.name = "S" + n;
} else {
this.name = "C" + (n - 14);
}} else if (nPlanes == n - 14) {
this.principalAxis = this.axes[n][0];
this.name = "C" + nPlanes + "v";
} else {
this.principalAxis = this.axes[n < 14 ? n + 14 : n][0];
this.principalPlane = this.axes[0][0];
if (n < 14) n /= 2;
 else n -= 14;
this.name = "C" + n + "h";
}}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
this.name = "??";
} else {
throw e;
}
} finally {
JU.Logger.info("Point group found: " + this.name);
}
return true;
}, "JS.PointGroup,~A");
Clazz.defineMethod(c$, "setPrincipalAxis", 
function(n, nPlanes){
var principalPlane = this.setPrincipalPlane(n, nPlanes);
if (nPlanes == 0 && n < 14 || this.nAxes[n] == 1) {
return this.axes[n][0];
}if (principalPlane == null) return null;
for (var i = 0; i < this.nAxes[16]; i++) if (this.isParallel(principalPlane.normalOrAxis, this.axes[16][i].normalOrAxis)) {
if (i != 0) {
var o = this.axes[16][0];
this.axes[16][0] = this.axes[16][i];
this.axes[16][i] = o;
}return this.axes[16][0];
}
return null;
}, "~N,~N");
Clazz.defineMethod(c$, "setPrincipalPlane", 
function(n, nPlanes){
if (nPlanes == 1) return this.principalPlane = this.axes[0][0];
if (nPlanes == 0 || nPlanes == n - 14) return null;
for (var i = 0; i < nPlanes; i++) for (var j = 0, nPerp = 0; j < nPlanes; j++) if (this.isPerpendicular(this.axes[0][i].normalOrAxis, this.axes[0][j].normalOrAxis) && ++nPerp > 2) {
if (i != 0) {
var o = this.axes[0][0];
this.axes[0][0] = this.axes[0][i];
this.axes[0][i] = o;
}return this.principalPlane = this.axes[0][0];
}

return null;
}, "~N,~N");
Clazz.defineMethod(c$, "getPointsAndElements", 
function(atomset){
var ac = this.bsAtoms.cardinality();
if (this.isAtoms && ac > this.maxAtoms) return false;
this.points =  new Array(ac);
this.elements =  Clazz.newIntArray (ac, 0);
if (ac == 0) return true;
var atomIndexMax = 0;
for (var i = this.bsAtoms.nextSetBit(0); i >= 0; i = this.bsAtoms.nextSetBit(i + 1)) {
var p = atomset[i];
if (Clazz.instanceOf(p,"JU.Node")) atomIndexMax = Math.max(atomIndexMax, (p).i);
}
this.atomMap =  Clazz.newIntArray (atomIndexMax + 1, 0);
this.nAtoms = 0;
var needCenter = (this.center == null);
if (needCenter) this.center =  new JU.P3();
var bspt =  new J.bspt.Bspt(3, 0);
for (var i = this.bsAtoms.nextSetBit(0); i >= 0; i = this.bsAtoms.nextSetBit(i + 1), this.nAtoms++) {
var p = atomset[i];
if (Clazz.instanceOf(p,"JU.Node")) {
var bondIndex = (this.localEnvOnly ? 1 : 1 + Math.max(3, (p).getCovalentBondCount()));
this.elements[this.nAtoms] = (p).getElementNumber() * bondIndex;
this.atomMap[(p).i] = this.nAtoms + 1;
} else {
var newPt =  new JU.Point3fi();
newPt.setT(p);
newPt.i = -1 - this.nAtoms;
if (Clazz.instanceOf(p,"JU.Point3fi")) this.elements[this.nAtoms] = Math.max(0, (p).sD);
p = newPt;
}bspt.addTuple(p);
if (needCenter) this.center.add(p);
this.points[this.nAtoms] = p;
}
this.iter = bspt.allocateCubeIterator();
if (needCenter) this.center.scale(1 / this.nAtoms);
for (var i = this.nAtoms; --i >= 0; ) {
var r2 = this.center.distanceSquared(this.points[i]);
if (this.isAtoms && r2 < this.distanceTolerance2) this.centerAtomIndex = i;
this.radius = Math.max(this.radius, r2);
}
this.radius = Math.sqrt(this.radius);
if (this.radius < 1.5 && this.distanceTolerance > 0.15) {
this.distanceTolerance = this.radius / 10;
this.distanceTolerance2 = this.distanceTolerance * this.distanceTolerance;
System.out.println("PointGroup calculation adjusting distanceTolerance to " + this.distanceTolerance);
}return true;
}, "~A");
Clazz.defineMethod(c$, "findInversionCenter", 
function(){
this.haveInversionCenter = this.checkOperation(null, this.center, -1);
if (this.haveInversionCenter) {
this.axes[1] =  new Array(1);
this.axes[1][0] = Clazz.innerTypeInstance(JS.PointGroup.Operation, this, null);
}});
Clazz.defineMethod(c$, "checkOperation", 
function(q, center, iOrder){
var pt =  new JU.P3();
var nFound = 0;
var isInversion = (iOrder < 14);
out : for (var n = this.points.length, i = n; --i >= 0 && nFound < n; ) {
if (i == this.centerAtomIndex) continue;
var a1 = this.points[i];
var e1 = this.elements[i];
if (q != null) {
pt.sub2(a1, center);
q.transform2(pt, pt).add(center);
} else {
pt.setT(a1);
}if (isInversion) {
this.vTemp.sub2(center, pt);
pt.scaleAdd2(2, this.vTemp, pt);
}if ((q != null || isInversion) && pt.distanceSquared(a1) < this.distanceTolerance2) {
nFound++;
continue;
}this.iter.initialize(pt, this.distanceTolerance, false);
while (this.iter.hasMoreElements()) {
var a2 = this.iter.nextElement();
if (a2 === a1) continue;
var j = this.getPointIndex((a2).i);
if (this.centerAtomIndex >= 0 && j == this.centerAtomIndex || j >= this.elements.length || this.elements[j] != e1) continue;
if (pt.distanceSquared(a2) < this.distanceTolerance2) {
nFound++;
continue out;
}}
return false;
}
return true;
}, "JU.Quat,JU.T3,~N");
Clazz.defineMethod(c$, "getPointIndex", 
function(j){
return (j < 0 ? -j : this.atomMap[j]) - 1;
}, "~N");
Clazz.defineMethod(c$, "isLinear", 
function(atoms){
var v1 = null;
if (atoms.length < 2) return false;
for (var i = atoms.length; --i >= 0; ) {
if (i == this.centerAtomIndex) continue;
if (v1 == null) {
v1 =  new JU.V3();
v1.sub2(atoms[i], this.center);
v1.normalize();
this.vTemp.setT(v1);
continue;
}this.vTemp.sub2(atoms[i], this.center);
this.vTemp.normalize();
if (!this.isParallel(v1, this.vTemp)) return false;
}
return true;
}, "~A");
Clazz.defineMethod(c$, "isParallel", 
function(v1, v2){
return (Math.abs(v1.dot(v2)) >= this.cosTolerance);
}, "JU.V3,JU.V3");
Clazz.defineMethod(c$, "isPerpendicular", 
function(v1, v2){
return (Math.abs(v1.dot(v2)) <= 1 - this.cosTolerance);
}, "JU.V3,JU.V3");
Clazz.defineMethod(c$, "getElementCounts", 
function(){
for (var i = this.points.length; --i >= 0; ) {
var e1 = this.elements[i];
if (e1 > this.maxElement) this.maxElement = e1;
}
this.eCounts =  Clazz.newIntArray (++this.maxElement, 0);
for (var i = this.points.length; --i >= 0; ) this.eCounts[this.elements[i]]++;

});
Clazz.defineMethod(c$, "findCAxes", 
function(){
var v1 =  new JU.V3();
var v2 =  new JU.V3();
var v3 =  new JU.V3();
for (var i = this.points.length; --i >= 0; ) {
if (i == this.centerAtomIndex) continue;
var a1 = this.points[i];
var e1 = this.elements[i];
for (var j = this.points.length; --j > i; ) {
var a2 = this.points[j];
if (this.elements[j] != e1) continue;
v1.sub2(a1, this.center);
v2.sub2(a2, this.center);
v1.normalize();
v2.normalize();
if (this.isParallel(v1, v2)) {
this.getAllAxes(v1);
continue;
}if (this.nAxes[16] < JS.PointGroup.axesMaxN[16]) {
v3.ave(a1, a2);
v3.sub(this.center);
this.getAllAxes(v3);
}var order = (6.283185307179586 / v1.angle(v2));
var iOrder = Clazz.doubleToInt(Math.floor(order + 0.01));
var isIntegerOrder = (order - iOrder <= 0.02);
if (!isIntegerOrder || (iOrder = iOrder + 14) >= JS.PointGroup.maxAxis) continue;
if (this.nAxes[iOrder] < JS.PointGroup.axesMaxN[iOrder]) {
v3.cross(v1, v2);
this.checkAxisOrder(iOrder, v3, this.center);
}}
}
var vs =  new Array(this.nAxes[16] * 2);
for (var i = 0; i < vs.length; i++) vs[i] =  new JU.V3();

var n = 0;
for (var i = 0; i < this.nAxes[16]; i++) {
vs[n++].setT(this.axes[16][i].normalOrAxis);
vs[n].setT(this.axes[16][i].normalOrAxis);
vs[n++].scale(-1);
}
for (var i = vs.length; --i >= 2; ) for (var j = i; --j >= 1; ) for (var k = j; --k >= 0; ) {
v3.add2(vs[i], vs[j]);
v3.add(vs[k]);
if (v3.length() < 1) continue;
this.checkAxisOrder(17, v3, this.center);
}


var nMin = 2147483647;
var iMin = -1;
for (var i = 0; i < this.maxElement; i++) {
if (this.eCounts[i] < nMin && this.eCounts[i] > 2) {
nMin = this.eCounts[i];
iMin = i;
}}
out : for (var i = 0; i < this.points.length - 2; i++) if (this.elements[i] == iMin) for (var j = i + 1; j < this.points.length - 1; j++) if (this.elements[j] == iMin) for (var k = j + 1; k < this.points.length; k++) if (this.elements[k] == iMin) {
v1.sub2(this.points[i], this.points[j]);
v2.sub2(this.points[i], this.points[k]);
v1.normalize();
v2.normalize();
v3.cross(v1, v2);
this.getAllAxes(v3);
v1.add2(this.points[i], this.points[j]);
v1.add(this.points[k]);
v1.normalize();
if (!this.isParallel(v1, v3)) this.getAllAxes(v1);
if (this.nAxes[19] == JS.PointGroup.axesMaxN[19]) break out;
}


vs =  new Array(this.maxElement);
for (var i = this.points.length; --i >= 0; ) {
var e1 = this.elements[i];
if (vs[e1] == null) vs[e1] =  new JU.V3();
 else if (this.haveInversionCenter) continue;
vs[e1].add(this.points[i]);
}
if (!this.haveInversionCenter) for (var i = 0; i < this.maxElement; i++) if (vs[i] != null) vs[i].scale(1 / this.eCounts[i]);

for (var i = 0; i < this.maxElement; i++) if (vs[i] != null) for (var j = 0; j < this.maxElement; j++) {
if (i == j || vs[j] == null) continue;
if (this.haveInversionCenter) v1.cross(vs[i], vs[j]);
 else v1.sub2(vs[i], vs[j]);
this.checkAxisOrder(16, v1, this.center);
}

return this.getHighestOrder();
});
Clazz.defineMethod(c$, "getAllAxes", 
function(v3){
for (var o = 16; o < JS.PointGroup.maxAxis; o++) if (this.nAxes[o] < JS.PointGroup.axesMaxN[o]) this.checkAxisOrder(o, v3, this.center);

}, "JU.V3");
Clazz.defineMethod(c$, "getHighestOrder", 
function(){
var n = 0;
for (n = 14; --n > 1 && this.nAxes[n] == 0; ) {
}
if (n > 1) return (n + 14 < JS.PointGroup.maxAxis && this.nAxes[n + 14] > 0 ? n + 14 : n);
for (n = JS.PointGroup.maxAxis; --n > 1 && this.nAxes[n] == 0; ) {
}
return n;
});
Clazz.defineMethod(c$, "checkAxisOrder", 
function(iOrder, v, center){
switch (iOrder) {
case 22:
if (this.nAxes[17] > 0) return false;
case 20:
case 18:
if (this.nAxes[19] > 0) return false;
break;
case 17:
if (this.nAxes[22] > 0) return false;
break;
case 19:
if (this.nAxes[18] > 0 || this.nAxes[20] > 0 || this.nAxes[22] > 0) return false;
break;
case 16:
break;
}
v.normalize();
if (this.haveAxis(iOrder, v)) return false;
var q = JS.PointGroup.getQuaternion(v, iOrder);
if (!this.checkOperation(q, center, iOrder)) return false;
this.addAxis(iOrder, v);
switch (iOrder) {
case 16:
this.checkAxisOrder(4, v, center);
break;
case 17:
this.checkAxisOrder(3, v, center);
if (this.haveInversionCenter) this.addAxis(6, v);
break;
case 18:
this.addAxis(16, v);
this.checkAxisOrder(4, v, center);
this.checkAxisOrder(8, v, center);
break;
case 19:
this.checkAxisOrder(5, v, center);
if (this.haveInversionCenter) this.addAxis(10, v);
break;
case 20:
this.addAxis(16, v);
this.addAxis(17, v);
this.checkAxisOrder(3, v, center);
this.checkAxisOrder(6, v, center);
this.checkAxisOrder(12, v, center);
break;
case 22:
this.addAxis(16, v);
this.addAxis(18, v);
break;
}
return true;
}, "~N,JU.V3,JU.T3");
Clazz.defineMethod(c$, "addAxis", 
function(iOrder, v){
if (this.haveAxis(iOrder, v)) return;
if (this.axes[iOrder] == null) this.axes[iOrder] =  new Array(JS.PointGroup.axesMaxN[iOrder]);
this.axes[iOrder][this.nAxes[iOrder]++] = Clazz.innerTypeInstance(JS.PointGroup.Operation, this, null, v, iOrder);
}, "~N,JU.V3");
Clazz.defineMethod(c$, "haveAxis", 
function(iOrder, v){
if (this.nAxes[iOrder] == JS.PointGroup.axesMaxN[iOrder]) {
return true;
}if (this.nAxes[iOrder] > 0) for (var i = this.nAxes[iOrder]; --i >= 0; ) {
if (this.isParallel(v, this.axes[iOrder][i].normalOrAxis)) return true;
}
return false;
}, "~N,JU.V3");
Clazz.defineMethod(c$, "findPlanes", 
function(){
var pt =  new JU.P3();
var v1 =  new JU.V3();
var v2 =  new JU.V3();
var v3 =  new JU.V3();
var nPlanes = 0;
var haveAxes = (this.getHighestOrder() > 1);
for (var i = this.points.length; --i >= 0; ) {
if (i == this.centerAtomIndex) continue;
var a1 = this.points[i];
var e1 = this.elements[i];
for (var j = this.points.length; --j > i; ) {
if (haveAxes && this.elements[j] != e1) continue;
var a2 = this.points[j];
pt.add2(a1, a2);
pt.scale(0.5);
v1.sub2(a1, this.center);
v2.sub2(a2, this.center);
v1.normalize();
v2.normalize();
if (!this.isParallel(v1, v2)) {
v3.cross(v1, v2);
v3.normalize();
nPlanes = this.getPlane(v3);
}v3.sub2(a2, a1);
v3.normalize();
nPlanes = this.getPlane(v3);
if (nPlanes == JS.PointGroup.axesMaxN[0]) return nPlanes;
}
}
if (haveAxes) for (var i = 16; i < JS.PointGroup.maxAxis; i++) for (var j = 0; j < this.nAxes[i]; j++) nPlanes = this.getPlane(this.axes[i][j].normalOrAxis);


return nPlanes;
});
Clazz.defineMethod(c$, "getPlane", 
function(v3){
if (!this.haveAxis(0, v3) && this.checkOperation(JU.Quat.newVA(v3, 180), this.center, -1)) this.axes[0][this.nAxes[0]++] = Clazz.innerTypeInstance(JS.PointGroup.Operation, this, null, v3);
return this.nAxes[0];
}, "JU.V3");
Clazz.defineMethod(c$, "findAdditionalAxes", 
function(nPlanes){
var planes = this.axes[0];
var Cn = 0;
if (nPlanes > 1 && ((Cn = nPlanes + 14) < JS.PointGroup.maxAxis) && this.nAxes[Cn] == 0) {
this.vTemp.cross(planes[0].normalOrAxis, planes[1].normalOrAxis);
if (!this.checkAxisOrder(Cn, this.vTemp, this.center) && nPlanes > 2) {
this.vTemp.cross(planes[1].normalOrAxis, planes[2].normalOrAxis);
this.checkAxisOrder(Cn - 1, this.vTemp, this.center);
}}if (this.nAxes[16] == 0 && nPlanes > 2) {
for (var i = 0; i < nPlanes - 1; i++) {
for (var j = i + 1; j < nPlanes; j++) {
this.vTemp.add2(planes[1].normalOrAxis, planes[2].normalOrAxis);
this.checkAxisOrder(16, this.vTemp, this.center);
}
}
}}, "~N");
c$.getQuaternion = Clazz.defineMethod(c$, "getQuaternion", 
function(v, iOrder){
return JU.Quat.newVA(v, (iOrder < 14 ? 180 : 0) + (iOrder == 0 ? 0 : Clazz.doubleToInt(360 / (iOrder % 14))));
}, "JU.V3,~N");
Clazz.defineMethod(c$, "getInfo", 
function(modelIndex, drawID, asInfo, type, index, scaleFactor){
var asDraw = (drawID != null);
this.info = (asInfo ?  new java.util.Hashtable() : null);
var v =  new JU.V3();
var op;
if (scaleFactor == 0) scaleFactor = 1;
this.scale = scaleFactor;
var nType =  Clazz.newIntArray (4, 2, 0);
for (var i = 1; i < JS.PointGroup.maxAxis; i++) for (var j = this.nAxes[i]; --j >= 0; ) nType[this.axes[i][j].type][0]++;


var sb =  new JU.SB().append("# ").appendI(this.nAtoms).append(" atoms\n");
var name = this.getConventionalName(this.name);
if (asDraw) {
drawID = "draw " + drawID;
var haveType = (type != null && type.length > 0);
this.drawType = type = (haveType ? type : "");
this.drawIndex = index;
var anyProperAxis = (type.equalsIgnoreCase(this.getConventionalName("Cn")));
var anyImproperAxis = (type.equalsIgnoreCase(this.getConventionalName("Sn")));
sb.append("set perspectivedepth off;\n");
var m = "_" + modelIndex + "_";
if (!haveType) sb.append(drawID + "pg0").append(m).append("* delete;draw pgva").append(m).append("* delete;draw pgvp").append(m).append("* delete;");
if (!haveType || type.equalsIgnoreCase("Ci")) sb.append(drawID + "pg0").append(m).append(this.haveInversionCenter ? "inv " : " ").append(JU.Escape.eP(this.center)).append(this.haveInversionCenter ? "\"i\";\n" : ";\n");
var offset = 0.1;
for (var i = 2; i < JS.PointGroup.maxAxis; i++) {
if (i == 14) offset = 0.1;
if (this.nAxes[i] == 0) continue;
var sglabel = (!this.$isLinear ? this.axes[i][0].getLabel(false) : "C_infinity");
var label = (!this.$isLinear ? this.axes[i][0].getLabel(true) : "C_infinity");
offset += 0.25;
var scale = scaleFactor * 1.05 * this.radius + offset * 80 / this.sppa;
var isProper = (i >= 14);
if (!haveType || type.equalsIgnoreCase(label) || anyProperAxis && isProper || anyImproperAxis && !isProper) for (var j = 0; j < this.nAxes[i]; j++) {
if (index > 0 && j + 1 != index) continue;
op = this.axes[i][j];
v.add2(op.normalOrAxis, this.center);
sb.append(drawID + "pgva").append(m).append(sglabel).append("_").appendI(j + 1).append(" width 0.05 scale ").appendF(op.type == 2 ? -scale : scale).append(" ").append(JU.Escape.eP(v));
v.scaleAdd2(-2, op.normalOrAxis, v);
var isPA = (!this.$isLinear && this.principalAxis != null && op.index == this.principalAxis.index);
sb.append(JU.Escape.eP(v)).append("\"").append(label).append(isPA ? "" : "").append("\" color ").append(isPA ? "red" : op.type == 2 ? "blue" : "orange").append(";\n");
}
}
if (!haveType || type.equalsIgnoreCase(this.getConventionalName("Cs"))) {
for (var j = 0; j < this.nAxes[0]; j++) {
if (index > 0 && j + 1 != index) continue;
op = this.axes[0][j];
sb.append(drawID + "pgvp").append(m).appendI(j + 1).append("disk scale ").appendF(scaleFactor * this.radius * 2).append(" CIRCLE PLANE ").append(JU.Escape.eP(this.center));
v.add2(op.normalOrAxis, this.center);
sb.append(JU.Escape.eP(v)).append(" color translucent yellow;\n");
v.add2(op.normalOrAxis, this.center);
sb.append(drawID + "pgvp").append(m).appendI(j + 1).append("ring width 0.05 scale ").appendF(scaleFactor * this.radius * 2).append(" arc ").append(JU.Escape.eP(v));
v.scaleAdd2(-2, op.normalOrAxis, v);
sb.append(JU.Escape.eP(v));
v.add3(0.011, 0.012, 0.013);
sb.append(JU.Escape.eP(v)).append("{0 360 0.5} color ").append(this.principalPlane != null && op.index == this.principalPlane.index ? "red" : "blue").append(";\n");
}
}sb.append("# name=").append(name);
sb.append(", n" + this.getConventionalName("Ci") + "=").appendI(this.haveInversionCenter ? 1 : 0);
sb.append(", n" + this.getConventionalName("Cs") + "=").appendI(this.nAxes[0]);
sb.append(", n" + this.getConventionalName("Cn") + "=").appendI(nType[1][0]);
sb.append(", n" + this.getConventionalName("Sn") + "=").appendI(nType[2][0]);
sb.append(": ");
for (var i = JS.PointGroup.maxAxis; --i >= 2; ) if (this.nAxes[i] > 0) {
var axisName = this.getConventionalName((i < 14 ? "S" : "C") + (i % 14));
sb.append(" n").append(axisName);
sb.append("=").appendI(this.nAxes[i]);
}
sb.append(";\n");
sb.append("print '" + name + "';\n");
this.drawInfo = sb.toString();
if (JU.Logger.debugging) JU.Logger.info(this.drawInfo);
return this.drawInfo;
}var n = 0;
var nTotal = 1;
var nElements = 0;
var ctype = (this.haveInversionCenter ? this.getConventionalName("Ci") : "center");
if (this.haveInversionCenter) {
nTotal++;
nElements++;
}if (asInfo) {
if (this.center != null) {
this.info.put(ctype, this.center);
if (this.haveInversionCenter) this.info.put("center", this.center);
this.info.put(ctype, this.center);
}} else {
sb.append("\n\n").append(name).append("\t").append(ctype).append("\t").append(JU.Escape.eP(this.center));
}for (var i = JS.PointGroup.maxAxis; --i >= 0; ) {
if (this.nAxes[i] > 0) {
n = JS.PointGroup.nUnique[i];
var label = this.axes[i][0].getLabel(true);
var sglabel = this.axes[i][0].getLabel(false);
if (asInfo) this.info.put("n" + sglabel, Integer.$valueOf(this.nAxes[i]));
 else sb.append("\n\n").append(name).append("\tn").append(label).append("\t").appendI(this.nAxes[i]).append("\t").appendI(n);
n *= this.nAxes[i];
nTotal += n;
nElements += this.nAxes[i];
nType[this.axes[i][0].type][1] += n;
var vinfo = (asInfo ?  new JU.Lst() : null);
var minfo = (asInfo ?  new JU.Lst() : null);
for (var j = 0; j < this.nAxes[i]; j++) {
var aop = this.axes[i][j];
if (asInfo) {
vinfo.addLast(aop.normalOrAxis);
minfo.addLast(aop.getM3());
} else {
sb.append("\n").append(name).append("\t").append(sglabel).append("_").appendI(j + 1).append("\t").appendO(aop.normalOrAxis);
}}
if (asInfo) {
this.info.put(sglabel, vinfo);
this.info.put(sglabel + "_m", minfo);
}}}
if (!asInfo) {
sb.append("\n");
sb.append("\n").append(name).append("\ttype\tnElements\tnUnique");
sb.append("\n").append(name).append("\t" + this.getConventionalName("E") + "\t  1\t  1");
n = (this.haveInversionCenter ? 1 : 0);
sb.append("\n").append(name).append("\t" + this.getConventionalName("Ci") + "\t  ").appendI(n).append("\t  ").appendI(n);
sb.append("\n").append(name).append("\t" + this.getConventionalName("Cs") + "\t");
JU.PT.rightJustify(sb, "    ", this.nAxes[0] + "\t");
JU.PT.rightJustify(sb, "    ", this.nAxes[0] + "\n");
sb.append(name).append("\t" + this.getConventionalName("Cn") + "\t");
JU.PT.rightJustify(sb, "    ", nType[1][0] + "\t");
JU.PT.rightJustify(sb, "    ", nType[1][1] + "\n");
sb.append(name).append("\t" + this.getConventionalName("Sn") + "\t");
JU.PT.rightJustify(sb, "    ", nType[2][0] + "\t");
JU.PT.rightJustify(sb, "    ", nType[2][1] + "\n");
sb.append(name).append("\t\tTOTAL\t");
JU.PT.rightJustify(sb, "    ", nTotal + "\n");
return (this.textInfo = sb.toString());
}this.info.put("name", this.name);
this.info.put("hmName", this.getHermannMauguinName());
this.info.put("nAtoms", Integer.$valueOf(this.nAtoms));
this.info.put("nTotal", Integer.$valueOf(nTotal));
this.info.put("nElements", Integer.$valueOf(nElements));
this.info.put("nCi", Integer.$valueOf(this.haveInversionCenter ? 1 : 0));
if (this.haveInversionCenter) this.info.put("Ci_m", JU.M3.newM3(JS.PointGroup.mInv));
this.info.put("nCs", Integer.$valueOf(this.nAxes[0]));
this.info.put("nCn", Integer.$valueOf(nType[1][0]));
this.info.put("nSn", Integer.$valueOf(nType[2][0]));
this.info.put("distanceTolerance", Float.$valueOf(this.distanceTolerance));
this.info.put("linearTolerance", Float.$valueOf(this.linearTolerance));
this.info.put("points", this.points);
this.info.put("detail", sb.toString().$replace('\n', ';'));
if (this.principalAxis != null && this.principalAxis.index > 0) this.info.put("principalAxis", this.principalAxis.normalOrAxis);
if (this.principalPlane != null && this.principalPlane.index > 0) this.info.put("principalPlane", this.principalPlane.normalOrAxis);
return this.info;
}, "~N,~S,~B,~S,~N,~N");
Clazz.defineMethod(c$, "isDrawType", 
function(type, index, scale){
return (this.drawInfo != null && this.drawType.equals(type == null ? "" : type) && this.drawIndex == index && this.scale == scale);
}, "~S,~N,~N");
c$.getHMfromSFName = Clazz.defineMethod(c$, "getHMfromSFName", 
function(name){
if (JS.PointGroup.htSFToHM == null) {
JS.PointGroup.htSFToHM =  new java.util.Hashtable();
var syms = JS.PointGroup.SF2HM;
JS.PointGroup.addNames("E", "1");
JS.PointGroup.addNames("Ci", "-1");
JS.PointGroup.addNames("Cn", "n");
JS.PointGroup.addNames("Sn", "-n");
for (var i = 0; i < syms.length; i++) {
var list = syms[i].$plit(",");
var sym = list[0];
if (list.length == 2) {
JS.PointGroup.addNames(sym, list[1]);
continue;
}var type = sym.substring(0, 1);
var ext = sym.substring(2, sym.length);
for (var n = 1; n < 13; n++) {
var val = list[n];
if (val.length > 0) {
JS.PointGroup.addNames(type + n + ext, val);
System.out.println(type + n + ext + "\t" + val);
}}
if (list.length == 14) {
JS.PointGroup.addNames(type + "\u221e" + ext, list[13]);
}}
}var hm = JS.PointGroup.htSFToHM.get(name);
return (hm == null ? name : hm);
}, "~S");
c$.addNames = Clazz.defineMethod(c$, "addNames", 
function(sch, hm){
JS.PointGroup.htSFToHM.put(sch, hm);
JS.PointGroup.htSFToHM.put(hm, sch);
}, "~S,~S");
c$.$PointGroup$Operation$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.type = 0;
this.order = 0;
this.index = 0;
this.normalOrAxis = null;
this.typeOrder = 0;
this.mat = null;
Clazz.instantialize(this, arguments);}, JS.PointGroup, "Operation", null);
Clazz.makeConstructor(c$, 
function(){
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = 3;
this.order = 1;
this.typeOrder = 1;
if (JU.Logger.debugging) JU.Logger.debug("new operation -- " + JS.PointGroup.typeNames[this.type]);
});
Clazz.makeConstructor(c$, 
function(v, i){
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = (i < 14 ? 2 : 1);
this.typeOrder = i;
this.order = i % 14;
this.normalOrAxis = JU.Quat.newVA(v, 180).getNormal();
if (JU.Logger.debugging) JU.Logger.debug("new operation -- " + (this.order == i ? "S" : "C") + this.order + " " + this.normalOrAxis);
}, "JU.V3,~N");
Clazz.makeConstructor(c$, 
function(v){
if (v == null) return;
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = 0;
this.normalOrAxis = JU.Quat.newVA(v, 180).getNormal();
if (JU.Logger.debugging) JU.Logger.debug("new operation -- plane " + this.normalOrAxis);
}, "JU.V3");
Clazz.defineMethod(c$, "getLabel", 
function(conventional){
var s;
switch (this.type) {
case 0:
s = "Cs";
break;
case 2:
s = "S" + this.order;
break;
default:
s = "C" + this.order;
break;
}
return (conventional ? this.b$["JS.PointGroup"].getConventionalName(s) : s);
}, "~B");
Clazz.defineMethod(c$, "getM3", 
function(){
if (this.mat != null) return this.mat;
var m = JU.M3.newM3(JS.PointGroup.getQuaternion(this.normalOrAxis, this.typeOrder).getMatrix());
if (this.type == 0 || this.type == 2) m.mul(JS.PointGroup.mInv);
this.cleanMatrix(m);
return this.mat = m;
});
Clazz.defineMethod(c$, "cleanMatrix", 
function(m){
for (var i = 0; i < 3; i++) for (var j = 0; j < 3; j++) m.setElement(i, j, this.approx0(m.getElement(i, j)));


}, "JU.M3");
Clazz.defineMethod(c$, "approx0", 
function(v){
return (v > 1e-15 || v < -1.0E-15 ? v : 0);
}, "~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return this.getLabel(false) + " " + this.normalOrAxis;
});
/*eoif4*/})();
};
c$.axesMaxN =  Clazz.newIntArray(-1, [15, 0, 0, 1, 3, 1, 10, 0, 1, 0, 6, 0, 1, 0, 0, 0, 15, 10, 6, 6, 10, 0, 1]);
c$.nUnique =  Clazz.newIntArray(-1, [1, 0, 0, 2, 2, 4, 2, 0, 4, 0, 4, 0, 4, 0, 0, 0, 1, 2, 2, 4, 2, 0, 4]);
c$.maxAxis = JS.PointGroup.axesMaxN.length;
c$.typeNames =  Clazz.newArray(-1, ["plane", "proper axis", "improper axis", "center of inversion"]);
c$.mInv = JU.M3.newA9( Clazz.newFloatArray(-1, [-1, 0, 0, 0, -1, 0, 0, 0, -1]));
c$.SF2HM = ("Cn,1,2,3,4,5,6,7,8,9,10,11,12|Cnv,m,2m,3m,4mm,5m,6mm,7m,8mm,9m,10mm,11m,12mm,\u221em|Sn,,-1,-6,-4,(-10),-3,(-14),-8,(-18),-5,(-22),(-12)|Cnh,m,2/m,-6,4/m,-10,6/m,-14,8/m,-18,10/m,-22,12/m|Dn,,222,32,422,52,622,72,822,92,(10)22,(11)2,(12)22|Dnd,,-42m,-3m,-82m,-5m,(-12)2m,-7m,(-16)2m,-9m,(-20)2m,(-11)m,(-24)2m|Dnh,,mmm,-6m2,4/mmm,(-10)m2,6/mmm,(-14)m2,8/mmm,(-18)m2,10/mmm,(-22)m2,12/mmm,\u221e/mm|Ci,-1|Cs,m|T,23|Th,m-3|Td,-43m|O,432|Oh,m-3m").$plit("\\|");
c$.htSFToHM = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
