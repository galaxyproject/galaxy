Clazz.declarePackage("JU");
Clazz.load(["JU.TriangleData"], "JU.Triangulator", ["JU.AU", "$.BS", "$.Lst", "$.Measure", "$.P3", "$.P4", "$.V3"], function(){
var c$ = Clazz.declareType(JU, "Triangulator", JU.TriangleData);
Clazz.defineMethod(c$, "intersectLine", 
function(points, nPoints, ptA, unitVector){
if (nPoints < 0) nPoints = points.length;
var v1 =  new JU.V3();
var v2 =  new JU.V3();
var v3 =  new JU.V3();
var vAB =  new JU.V3();
var pmin = null;
var pmax = null;
var p =  new JU.P3();
var plane =  new JU.P4();
var dmin = 3.4028235E38;
var dmax = -3.4028235E38;
for (var i = 0; i < 12; i++) {
var c = JU.Triangulator.fullCubePolygon[i];
if (i % 2 == 0) {
JU.Measure.getPlaneThroughPoints(points[c[0]], points[c[1]], points[c[2]], v1, v2, plane);
var ret = JU.Measure.getIntersection(ptA, unitVector, plane, p, v1, v3);
if (ret == null) {
i++;
continue;
}vAB.sub2(p, ptA);
}if (JU.Measure.isInTriangle(p, points[c[0]], points[c[1]], points[c[2]], v1, v2, v3)) {
var d = unitVector.dot(vAB);
if (d < dmin) {
dmin = d;
pmin = p;
}if (d > dmax) {
dmax = d;
pmax = p;
}if ((i % 2) == 0) {
i++;
}if (dmax - dmin > 0.01) break;
p =  new JU.P3();
}}
return (pmin == null || (pmax == null || pmin.distance(pmax) < 0.001) && (pmax = pmin) == null ? null :  Clazz.newArray(-1, [pmin, pmax]));
}, "~A,~N,JU.P3,JU.V3");
Clazz.defineMethod(c$, "getCellProjection", 
function(plane, pts){
var vTemp =  new JU.V3();
var d = 0;
var dmax = -3.4028235E38;
var imax = 0;
var newPts =  new Array(8);
for (var i = 0; i < 8; i++) {
d = pts[i].dot(plane);
if (d > dmax) {
dmax = d;
imax = i;
}JU.Measure.getPlaneProjection(pts[i], plane, newPts[i] =  new JU.P3(), vTemp);
}
var t = JU.Triangulator.fullCubeCorners[imax][3];
var polygons = JU.AU.newInt2(6);
for (var p = 0, i = 0; i < 12; i++) {
if ((t & JU.TriangleData.Pwr2[i]) != 0) {
var t1 =  Clazz.newIntArray (4, 0);
var t0 = JU.Triangulator.fullCubePolygon[i];
t1[0] = t0[0];
t1[1] = t0[1];
t1[2] = t0[2];
t1[3] = (t0[0] == imax ? 2 : t0[1] == imax ? 0 : t0[2] == imax ? 1 : 3);
polygons[p++] = t1;
}}
var poly =  new JU.Lst();
poly.addLast(newPts);
poly.addLast(polygons);
return poly;
}, "JU.P4,~A");
Clazz.defineMethod(c$, "intersectPlane", 
function(plane, vertices, flags){
if (flags == -1 && vertices.length == 8) {
return this.getCellProjection(plane, vertices);
}var v =  new JU.Lst();
var edgePoints =  new Array(12);
var insideMask = 0;
var values =  Clazz.newFloatArray (8, 0);
for (var i = 0; i < 8; i++) {
values[i] = plane.x * vertices[i].x + plane.y * vertices[i].y + plane.z * vertices[i].z + plane.w;
if (values[i] < 0) insideMask |= JU.TriangleData.Pwr2[i];
}
var triangles = JU.TriangleData.triangleTable2[insideMask];
if (triangles == null) return null;
for (var i = 0; i < 24; i += 2) {
var v1 = JU.TriangleData.edgeVertexes[i];
var v2 = JU.TriangleData.edgeVertexes[i + 1];
var result = JU.P3.newP(vertices[v2]);
result.sub(vertices[v1]);
result.scale(values[v1] / (values[v1] - values[v2]));
result.add(vertices[v1]);
edgePoints[i >> 1] = result;
}
if (flags == 0) {
var bsPoints =  new JU.BS();
for (var i = 0; i < triangles.length; i++) {
bsPoints.set(triangles[i]);
if (i % 4 == 2) i++;
}
var nPoints = bsPoints.cardinality();
var pts =  new Array(nPoints);
v.addLast(pts);
var list =  Clazz.newIntArray (12, 0);
var ptList = 0;
for (var i = 0; i < triangles.length; i++) {
var pt = triangles[i];
if (bsPoints.get(pt)) {
bsPoints.clear(pt);
pts[ptList] = edgePoints[pt];
list[pt] = ptList++;
}if (i % 4 == 2) i++;
}
var polygons = JU.AU.newInt2(triangles.length >> 2);
v.addLast(polygons);
for (var i = 0; i < triangles.length; i++) polygons[i >> 2] =  Clazz.newIntArray(-1, [list[triangles[i++]], list[triangles[i++]], list[triangles[i++]], triangles[i]]);

return v;
}for (var i = 0; i < triangles.length; i++) {
var pt1 = edgePoints[triangles[i++]];
var pt2 = edgePoints[triangles[i++]];
var pt3 = edgePoints[triangles[i++]];
if ((flags & 1) == 1) v.addLast( Clazz.newArray(-1, [pt1, pt2, pt3]));
if ((flags & 2) == 2) {
var b = triangles[i];
if ((b & 1) == 1) v.addLast( Clazz.newArray(-1, [pt1, pt2]));
if ((b & 2) == 2) v.addLast( Clazz.newArray(-1, [pt2, pt3]));
if ((b & 4) == 4) v.addLast( Clazz.newArray(-1, [pt1, pt3]));
}}
return v;
}, "JU.P4,~A,~N");
c$.fullCubePolygon =  Clazz.newArray(-1, [ Clazz.newIntArray(-1, [0, 4, 5, 3]),  Clazz.newIntArray(-1, [5, 1, 0, 3]),  Clazz.newIntArray(-1, [1, 5, 6, 2]),  Clazz.newIntArray(-1, [6, 2, 1, 3]),  Clazz.newIntArray(-1, [2, 6, 7, 2]),  Clazz.newIntArray(-1, [7, 3, 2, 3]),  Clazz.newIntArray(-1, [3, 7, 4, 2]),  Clazz.newIntArray(-1, [4, 0, 3, 2]),  Clazz.newIntArray(-1, [6, 5, 4, 0]),  Clazz.newIntArray(-1, [4, 7, 6, 0]),  Clazz.newIntArray(-1, [0, 1, 2, 0]),  Clazz.newIntArray(-1, [2, 3, 0, 0])]);
c$.fullCubeCorners =  Clazz.newArray(-1, [ Clazz.newIntArray(-1, [1, 4, 3, 3267]),  Clazz.newIntArray(-1, [0, 2, 5, 3087]),  Clazz.newIntArray(-1, [1, 3, 6, 3132]),  Clazz.newIntArray(-1, [2, 0, 7, 3312]),  Clazz.newIntArray(-1, [0, 5, 7, 963]),  Clazz.newIntArray(-1, [1, 6, 4, 783]),  Clazz.newIntArray(-1, [2, 7, 5, 828]),  Clazz.newIntArray(-1, [3, 4, 6, 1008])]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
