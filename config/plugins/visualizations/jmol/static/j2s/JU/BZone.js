Clazz.declarePackage("JU");
Clazz.load(["JU.P3"], "JU.BZone", ["java.util.Hashtable", "JU.Lst", "$.Measure", "$.P4", "$.V3", "J.bspt.PointIterator", "JU.TempArray"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.ret = null;
this.bz = null;
this.id = null;
this.index = 0;
this.color = null;
this.center = null;
this.subzones = null;
this.newLatticePts = null;
this.newPlanes = null;
this.volume = 0;
Clazz.instantialize(this, arguments);}, JU, "BZone", null);
Clazz.prepareFields (c$, function(){
this.ret =  new Array(1);
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "createBZ", 
function(vwr, n, array, isK, id, scale, foffset, offset){
var bz =  new JU.BZone.BZ(vwr, id, n);
bz.createAllZones(scale, foffset, offset);
}, "JV.Viewer,~N,~A,~B,~S,~N,~N,JU.P3");
Clazz.defineMethod(c$, "create", 
function(zonePrev){
this.getNewLatticePoints();
this.getSubzones(zonePrev);
for (var i = 0; i < this.subzones.size(); i++) {
var subzone = this.subzones.get(i);
if (subzone.getPmeshes()) subzone.createSubzonePolyhedron(this.id);
}
this.finalizeZone();
}, "JU.BZone");
Clazz.defineMethod(c$, "getSubzones", 
function(zonePrev){
this.subzones =  new JU.Lst();
if (this.index == 1) {
 new JU.BZone.Subzone(this, "", 1);
return;
}var len = zonePrev.id.length;
for (var i = 0; i < zonePrev.subzones.size(); i++) {
var prev = zonePrev.subzones.get(i);
var id = prev.id.substring(len);
var isZone2 = (zonePrev.index == 1);
for (var j = (isZone2 ? 0 : 1); j < prev.planes.size(); j++) {
if (!isZone2 && JU.BZone.within(1.0E-4, prev.faceCenters.get(j), this.bz.bzFaceCenters).size() > 1) continue;
var subzone =  new JU.BZone.Subzone(this, id, isZone2 ? j + 1 : j);
subzone.addPlanes(prev.planes, prev.latticePts, j);
subzone.addPlanes(prev.planesUnused, prev.ptsUnused, -1);
subzone.addPlanes(this.newPlanes, this.newLatticePts, -1);
}
}
}, "JU.BZone");
Clazz.defineMethod(c$, "getNewLatticePoints", 
function(){
this.newLatticePts =  new JU.Lst();
this.newPlanes =  new JU.Lst();
var unusedPts =  new JU.Lst();
var unusedLatticePts =  new JU.Lst();
for (var i = 0; i < this.bz.bzPlanePts.size(); i++) {
var p = this.bz.bzPlanePts.get(i);
var center = JU.P3.newP(p);
center.scale(0.5);
var radius = 0.501 * p.length();
var inSphere = JU.BZone.within(radius, center, this.bz.bzPlanePts);
var al;
if (inSphere.size() == 1) {
al = this.newLatticePts;
this.newPlanes.addLast(JU.BZone.newLatticePlane(p, 1, this.bz.bzGamma));
} else {
unusedPts.addLast(p);
al = unusedLatticePts;
}al.addLast(this.bz.bzLatticePts.get(i));
}
this.bz.bzPlanePts = unusedPts;
this.bz.bzLatticePts = unusedLatticePts;
});
c$.newLatticePlane = Clazz.defineMethod(c$, "newLatticePlane", 
function(pt2, f, bzGamma){
var norm = JU.V3.newVsub(pt2, bzGamma);
var pt3 =  new JU.P3();
pt3.scaleAdd2(f, norm, bzGamma);
norm.normalize();
var plane =  new JU.P4();
JU.Measure.getPlaneThroughPoint(pt3, norm, plane);
return plane;
}, "JU.P3,~N,JU.P3");
c$.within = Clazz.defineMethod(c$, "within", 
function(radius, center, pts){
var ret =  new JU.Lst();
var r2 = radius * radius;
for (var i = 0, n = pts.size(); i < n; i++) {
var pt = pts.get(i);
if (center.distanceSquared(pt) < r2) ret.addLast(pt);
}
return ret;
}, "~N,JU.P3,JU.Lst");
Clazz.defineMethod(c$, "finalizeZone", 
function(){
this.volume = 0;
for (var i = this.subzones.size(); --i >= 0; ) {
var subzone = this.subzones.get(i);
if (subzone.isValid) {
this.volume += subzone.volume;
if (subzone.volume < 0.05) {
System.out.println("draw id d" + subzone.id + " points " + JU.BZone.esc(subzone.faceCenters) + ";draw id " + "dc" + subzone.id + " width 0.1 color red " + subzone.center);
}} else {
this.subzones.removeItemAt(i);
}}
});
c$.esc = Clazz.defineMethod(c$, "esc", 
function(pts){
var s = "[";
var sep = "";
for (var i = pts.size(); --i >= 0; ) {
s += sep + pts.get(i).toString();
sep = " ";
}
return s + "]";
}, "JU.Lst");
Clazz.defineMethod(c$, "drawHKL", 
function(vwr, id, plane, pts){
this.bz =  new JU.BZone.BZ(vwr, id, -2);
this.bz.drawMillerPlanes(plane, pts);
}, "JV.Viewer,~S,JU.P4,~A");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.h = 0;
this.k = 0;
this.l = 0;
Clazz.instantialize(this, arguments);}, JU.BZone, "BZPoint", JU.P3);
Clazz.makeConstructor(c$, 
function(h, k, l){
Clazz.superConstructor (this, JU.BZone.BZPoint, []);
this.h = h;
this.k = k;
this.l = l;
}, "~N,~N,~N");
Clazz.defineMethod(c$, "toString", 
function(){
return "[" + this.h + " " + this.k + " " + this.l + "] " + Clazz.superCall(this, JU.BZone.BZPoint, "toString", []);
});
Clazz.defineMethod(c$, "hkl", 
function(){
return "{" + this.h + " " + this.k + " " + this.l + "}";
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.offset = null;
this.vwr = null;
this.pmeshBox = null;
this.b1 = null;
this.b2 = null;
this.b3 = null;
this.wedgePlanes = null;
this.bzGamma = null;
this.bzLatticePts = null;
this.bzFaceCenters = null;
this.bzPlanePts = null;
this.explodeOffset = 0;
this.scale = 0;
this.id = null;
this.n = 0;
this.isWignerSeitz = false;
this.centerOffset = null;
Clazz.instantialize(this, arguments);}, JU.BZone, "BZ", null);
Clazz.prepareFields (c$, function(){
this.bzGamma =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(vwr, id, n){
this.vwr = vwr;
if (n == -2) {
if (id == null) id = "hkl";
} else if (n == -1) {
this.isWignerSeitz = true;
n = 1;
if (id == null) id = "pws";
} else {
if (id == null) id = "pbz";
}this.n = n;
this.id = id;
}, "JV.Viewer,~S,~N");
Clazz.defineMethod(c$, "createAllZones", 
function(scale, explodeOffset, offset){
if (this.isWignerSeitz) {
this.isWignerSeitz = true;
this.offset = offset;
} else {
if (this.n > 1) this.explodeOffset = explodeOffset;
this.scale = scale;
}var wasPrecise = this.vwr.getBoolean(603979831);
this.vwr.setBooleanPropertyTok("floatPrecision", 603979831, true);
this.initializeBZ(this.n);
var cmd = "";
var volume1 = 0;
var zone = null;
for (var i = 1; i <= this.n; i++) {
var prev = zone;
zone =  new JU.BZone();
zone.bz = this;
zone.index = i;
zone.id = this.id + "_" + i + "_";
zone.color = JU.BZone.bzColors[(i - 1) % JU.BZone.bzColors.length];
zone.create(prev);
if (i == 1) {
volume1 = zone.volume;
}if (!this.isWignerSeitz) this.vwr.showString("Brillouin Zone " + zone.index + " volume = " + Math.round(zone.volume / volume1 * 1000) / 1000 + " subzones:" + zone.subzones.size() + " new k-points:" + zone.newLatticePts.size(), false);
if (i > 1 && explodeOffset == 0) cmd += "polyhedra id " + this.id + (i - 1) + "_* delete;";
}
if (!this.isWignerSeitz) {
}this.cmd(cmd + ";restore unitcell _bz;");
this.vwr.setBooleanPropertyTok("floatPrecision", 603979831, wasPrecise);
}, "~N,~N,JU.P3");
Clazz.defineMethod(c$, "initializeBZ", 
function(n){
this.centerOffset = this.vwr.getCurrentUnitCell().getCartesianOffset();
if (this.offset != null) this.offset.add(this.centerOffset);
 else this.offset = JU.P3.newP(this.centerOffset);
if (this.offset.length() == 0) this.offset = null;
this.bzLatticePts =  new JU.Lst();
this.bzPlanePts =  new JU.Lst();
this.bzFaceCenters =  new JU.Lst();
var cmd = "save unitcell _bz;";
if (this.isWignerSeitz) {
cmd += "unitcell conventional;unitcell primitive;";
} else {
if (n == 0) n = 1;
if (Float.isNaN(this.scale)) this.scale = -1;
cmd += "unitcell conventional;unitcell 'reciprocal' " +  new Float(this.scale).toString() + ";";
}cmd += "polyhedra " + this.id + "* delete;";
this.cmd(cmd);
this.pmeshBox =  Clazz.newArray(-1, [this.newCartesian(-2, -2, -2,  new JU.P3()), this.newCartesian(2, 2, 2,  new JU.P3())]);
var abc =  Clazz.newFloatArray(-1, [(this.b1 = this.newCartesian(1, 0, 0,  new JU.P3())).length(), (this.b2 = this.newCartesian(0, 1, 0,  new JU.P3())).length(), (this.b3 = this.newCartesian(0, 0, 1,  new JU.P3())).length()]);
var abcmax = Math.max(abc[0], Math.max(abc[1], abc[2]));
var minmax =  Clazz.newIntArray (3, 3, 0);
for (var i = 0; i < 3; i++) {
var m = Clazz.floatToInt((n + 1) * abcmax / abc[i]);
minmax[i] =  Clazz.newIntArray(-1, [-m, m]);
}
var pts =  new JU.Lst();
for (var h = minmax[0][0]; h <= minmax[0][1]; h++) {
for (var k = minmax[1][0]; k <= minmax[1][1]; k++) {
for (var l = minmax[2][0]; l <= minmax[2][1]; l++) {
if (h != 0 || k != 0 || l != 0) {
var lppt =  new JU.BZone.BZPoint(h, k, l);
this.newCartesian(h, k, l, lppt);
pts.addLast(JU.P3.newP(lppt));
this.bzLatticePts.addLast(lppt);
var ppt = JU.P3.newP(lppt);
ppt.scale(0.5);
this.bzPlanePts.addLast(ppt);
}}
}
}
}, "~N");
Clazz.defineMethod(c$, "newCartesian", 
function(h, k, l, ret){
ret.x = h;
ret.y = k;
ret.z = l;
this.vwr.toCartesian(ret, true);
return ret;
}, "~N,~N,~N,JU.P3");
Clazz.defineMethod(c$, "cmd", 
function(cmd){
try {
this.vwr.eval.runScript(cmd);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
}, "~S");
Clazz.defineMethod(c$, "createPMesh", 
function(pid, plane){
this.vwr.shm.setShapeProperties(29, [ Clazz.newArray(-1, ["init", "cmd"]),  Clazz.newArray(-1, ["thisID", pid]),  Clazz.newArray(-1, ["newObject", null]),  Clazz.newArray(-1, ["fileType", "Pmesh"]),  Clazz.newArray(-1, ["silent", null]),  Clazz.newArray(-1, ["resolution", Float.$valueOf(0.001)]),  Clazz.newArray(-1, ["boundingBox", this.pmeshBox]),  Clazz.newArray(-1, ["plane", plane]),  Clazz.newArray(-1, ["nomap", Float.$valueOf(0)]),  Clazz.newArray(-1, ["hidden", Boolean.TRUE]),  Clazz.newArray(-1, ["finalize", "cmd"]),  Clazz.newArray(-1, ["clear", null])]);
}, "~S,JU.P4");
Clazz.defineMethod(c$, "slab", 
function(pid, plane){
if (plane == null) {
if (this.wedgePlanes != null) {
for (var n = this.wedgePlanes.length, w = 0; w < n; w++) {
if (!this.slab(pid, this.wedgePlanes[w])) return false;
}
}return true;
}this.vwr.shm.setShapePropertyBs(29, "slab", JU.TempArray.getSlabObjectType(134217750, plane, false, null), null);
var a = this.getProperty(pid, "area");
return (a != null && a[0] != 0);
}, "~S,JU.P4");
Clazz.defineMethod(c$, "clearPMesh", 
function(pid){
this.vwr.setShapeProperty(29, "clear", null);
this.vwr.setShapeProperty(29, "delete", pid);
}, "~S");
Clazz.defineMethod(c$, "getProperty", 
function(name, key){
var data =  new Array(3);
data[0] = name;
this.vwr.shm.getShapePropertyData(29, "index", data);
if (data[1] != null && !key.equals("index")) {
var index = (data[1]).intValue();
data[1] = this.vwr.shm.getShapePropertyIndex(29, key.intern(), index);
}return data[1];
}, "~S,~S");
Clazz.defineMethod(c$, "addPolyhedron", 
function(subzone, pts){
if (this.offset != null) {
subzone.center.add(this.offset);
for (var i = pts.length; --i >= 0; ) pts[i].add(this.offset);

}var info =  new java.util.Hashtable();
info.put("id", subzone.id);
info.put("center", subzone.center);
var lst =  new JU.Lst();
for (var i = 0, n = pts.length; i < n; i++) lst.addLast(pts[i]);

info.put("vertices", lst);
info.put("faces", subzone.faceIndices);
if (subzone.index > 1 && this.explodeOffset != 0) info.put("explodeOffset", Float.$valueOf(this.explodeOffset * (subzone.index - 1)));
info.put("color", subzone.color);
info.put("volume", Float.$valueOf(0));
this.vwr.setShapeProperty(21, "init", Boolean.TRUE);
this.vwr.setShapeProperty(21, "info", info);
this.vwr.setShapeProperty(21, "generate", null);
this.vwr.setShapeProperty(21, "init", Boolean.FALSE);
return (info.get("volume")).floatValue();
}, "JU.BZone.Subzone,~A");
Clazz.defineMethod(c$, "drawMillerPlanes", 
function(plane, pts){
this.cmd("draw id " + this.id + "* delete");
var d = Math.abs(plane.w);
if (d == 0) return;
var p = JU.P4.newPt(plane);
p.w = d * 10;
var n = 0;
for (var i = 1; ; i++) {
p.w -= d;
System.out.println(p);
var list = this.vwr.getTriangulator().intersectPlane(p, pts, 0);
if (list == null) {
if (n == 0 && i < 20) continue;
break;
}this.createHKL(this.id + "_" + i, list);
}
}, "JU.P4,~A");
Clazz.defineMethod(c$, "createHKL", 
function(id, list){
this.vwr.shm.setShapeProperties(22, [ Clazz.newArray(-1, ["init", "hkl"]),  Clazz.newArray(-1, ["thisID", id]),  Clazz.newArray(-1, ["points", Integer.$valueOf(0)]),  Clazz.newArray(-1, ["polygon", list]),  Clazz.newArray(-1, ["set", null])]);
}, "~S,JU.Lst");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.zone = null;
this.isValid = false;
this.faces = null;
this.faceIndices = null;
this.faceCenters = null;
this.latticePts = null;
this.planes = null;
this.ptsUnused = null;
this.planesUnused = null;
Clazz.instantialize(this, arguments);}, JU.BZone, "Subzone", JU.BZone);
Clazz.makeConstructor(c$, 
function(zone, id, index){
Clazz.superConstructor (this, JU.BZone.Subzone, []);
this.zone = zone;
this.bz = zone.bz;
this.id = zone.id + id + index + "_";
this.index = index;
this.newLatticePts = zone.newLatticePts;
this.planes = (zone.index == 1 ? zone.newPlanes :  new JU.Lst());
this.latticePts = (zone.index == 1 ? zone.newLatticePts :  new JU.Lst());
this.planesUnused =  new JU.Lst();
this.ptsUnused =  new JU.Lst();
this.faces =  new JU.Lst();
this.faceIndices =  new JU.Lst();
this.faceCenters =  new JU.Lst();
this.volume = 0;
this.color = zone.color;
this.center =  new JU.P3();
zone.subzones.addLast(this);
}, "JU.BZone,~S,~N");
Clazz.defineMethod(c$, "addPlanes", 
function(planes0, pts0, j){
if (j >= 0) {
var pt4 = JU.P4.newPt(planes0.get(j));
pt4.scale4(-1.0);
this.planes.addLast(pt4);
this.latticePts.addLast(pts0.get(j));
}var n = planes0.size();
for (var k = 0; k < n; k++) {
if (k != j) {
this.planes.addLast(planes0.get(k));
this.latticePts.addLast(pts0.get(k));
}}
}, "JU.Lst,JU.Lst,~N");
Clazz.defineMethod(c$, "createSubzonePolyhedron", 
function(id){
id += this.id;
var apts = JU.BZone.Subzone.join(this.faces);
var pts = this.cleanFace(apts);
if (pts.length == 0) return;
this.center = JU.BZone.Subzone.average(pts);
this.faceIndices =  new JU.Lst();
for (var i = 0, n = this.faces.size(); i < n; i++) {
this.faceIndices.addLast(this.cleanFaceIndices(this.faces.get(i), pts));
}
for (var i = this.faceIndices.size(); --i >= 0; ) {
if (this.faceIndices.get(i).length < 3) {
this.faces.removeItemAt(i);
this.faceIndices.removeItemAt(i);
this.faceCenters.removeItemAt(i);
this.planes.removeItemAt(i);
}}
this.volume = this.bz.addPolyhedron(this, pts);
}, "~S");
Clazz.defineMethod(c$, "cleanFaceIndices", 
function(P3s, pts){
J.bspt.PointIterator.withinDistPoints(0, null, pts, P3s, null, this.ret);
return this.ret[0];
}, "~A,~A");
Clazz.defineMethod(c$, "cleanFace", 
function(face){
J.bspt.PointIterator.withinDistPoints(1.0E-4, JU.BZone.ptInner, face, null, null, this.ret);
var l = this.ret[0];
return l.toArray( new Array(l.size()));
}, "~A");
c$.average = Clazz.defineMethod(c$, "average", 
function(face){
var a =  new JU.P3();
for (var i = face.length; --i >= 0; ) a.add(face[i]);

a.scale(1 / face.length);
return a;
}, "~A");
c$.join = Clazz.defineMethod(c$, "join", 
function(faces){
var n = 0;
for (var i = faces.size(); --i >= 0; ) n += faces.get(i).length;

var pts =  new Array(n);
n = 0;
for (var i = faces.size(); --i >= 0; ) {
var face = faces.get(i);
for (var j = face.length; --j >= 0; ) pts[n++] = face[j];

}
return pts;
}, "JU.Lst");
Clazz.defineMethod(c$, "getPmeshes", 
function(){
var nPlanes = this.planes.size();
var planesUsed =  new JU.Lst();
var ptsUsed =  new JU.Lst();
var haveValidPlane = false;
for (var i = 0; i < nPlanes; i++) {
var pid = "f" + this.id + i;
var isValid = true;
this.bz.createPMesh(pid, this.planes.get(i));
for (var j = 0; j < nPlanes; j++) {
if (j == i) {
continue;
}isValid = this.bz.slab(pid, this.planes.get(j));
if (isValid) {
haveValidPlane = true;
} else {
break;
}}
if (isValid) isValid = this.bz.slab(pid, null);
var a = null;
var face = null;
if (isValid) {
face = this.bz.getProperty(pid, "face");
a = JU.BZone.Subzone.average(face);
if (i == 0 && JU.BZone.within(1.0E-4, a, this.bz.bzFaceCenters).size() >= 2) {
isValid = false;
i = nPlanes;
}}if (isValid) {
this.isValid = true;
face = this.cleanFace(face);
this.faces.addLast(face);
this.faceCenters.addLast(a);
this.bz.bzFaceCenters.addLast(a);
planesUsed.addLast(this.planes.get(i));
ptsUsed.addLast(this.latticePts.get(i));
} else if (i < nPlanes) {
this.planesUnused.addLast(this.planes.get(i));
this.ptsUnused.addLast(this.latticePts.get(i));
}this.bz.clearPMesh(pid);
}
this.planes = planesUsed;
this.latticePts = ptsUsed;
if (this.zone.index == 1) {
for (var i = 0; i < ptsUsed.size(); i++) {
var bp = ptsUsed.get(i);
System.out.println("#BZ pt[" + i + "]=" + ptsUsed.get(i));
System.out.println("draw id d" + i + " intersection unitcell hkl " + bp.hkl() + " all;");
}
}return haveValidPlane;
});
/*eoif3*/})();
c$.ptInner = JU.P3.new3(NaN, 0, 0);
c$.bzColors =  Clazz.newArray(-1, ["red", "green", "skyblue", "orange", "yellow", "blue", "violet"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
