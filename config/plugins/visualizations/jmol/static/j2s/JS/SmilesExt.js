Clazz.declarePackage("JS");
Clazz.load(null, "JS.SmilesExt", ["JU.AU", "$.BS", "$.Lst", "$.M4", "$.Measure", "$.P3", "J.api.Interface", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.e = null;
Clazz.instantialize(this, arguments);}, JS, "SmilesExt", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "init", 
function(se){
this.e = se;
return this;
}, "~O");
Clazz.defineMethod(c$, "getSmilesCorrelation", 
function(bsA, bsB, smiles, ptsA, ptsB, m4, vReturn, asMap, mapSet, center, bestMap, flags){
var tolerance = (mapSet == null ? 0.1 : 3.4028235E38);
try {
if (ptsA == null) {
ptsA =  new JU.Lst();
ptsB =  new JU.Lst();
}var m =  new JU.M4();
var c =  new JU.P3();
var atoms = this.e.vwr.ms.at;
var ac = this.e.vwr.ms.ac;
var sm = this.e.vwr.getSmilesMatcher();
var maps = sm.getCorrelationMaps(smiles, atoms, ac, bsA, flags | 8);
if (maps == null) this.e.evalError(sm.getLastException(), null);
if (maps.length == 0) return NaN;
var mapFirst = maps[0];
for (var i = 0; i < mapFirst.length; i++) ptsA.addLast(atoms[mapFirst[i]]);

maps = sm.getCorrelationMaps(smiles, atoms, ac, bsB, flags);
if (maps == null) this.e.evalError(sm.getLastException(), null);
if (maps.length == 0) return NaN;
JU.Logger.info(maps.length + " mappings found");
if (bestMap || !asMap) {
var lowestStdDev = 3.4028235E38;
var mapBest = null;
for (var i = 0; i < maps.length; i++) {
ptsB.clear();
for (var j = 0; j < maps[i].length; j++) ptsB.addLast(atoms[maps[i][j]]);

J.api.Interface.getInterface("JU.Eigen", this.e.vwr, "script");
var stddev = (ptsB.size() == 1 ? 0 : JU.Measure.getTransformMatrix4(ptsA, ptsB, m, null));
JU.Logger.info("getSmilesCorrelation stddev=" + stddev);
if (vReturn != null) {
if (stddev < tolerance) {
var bs =  new JU.BS();
for (var j = 0; j < maps[i].length; j++) bs.set(maps[i][j]);

vReturn.addLast(bs);
}}if (stddev < lowestStdDev) {
mapBest = maps[i];
if (m4 != null) m4.setM4(m);
if (center != null) center.setT(c);
lowestStdDev = stddev;
}}
if (mapSet != null) {
mapSet[0] = mapFirst;
mapSet[1] = mapBest;
}ptsB.clear();
for (var i = 0; i < mapBest.length; i++) ptsB.addLast(atoms[mapBest[i]]);

return lowestStdDev;
}for (var i = 0; i < maps.length; i++) for (var j = 0; j < maps[i].length; j++) ptsB.addLast(atoms[maps[i][j]]);


} catch (ex) {
if (Clazz.exceptionOf(ex, Exception)){
this.e.evalError(ex.getMessage(), null);
} else {
throw ex;
}
}
return 0;
}, "JU.BS,JU.BS,~S,JU.Lst,JU.Lst,JU.M4,JU.Lst,~B,~A,JU.P3,~B,~N");
Clazz.defineMethod(c$, "getSmilesMatches", 
function(pattern, smiles, bsSelected, bsMatch3D, flags, asOneBitset, firstMatchOnly){
if (pattern.length == 0 || pattern.endsWith("///") || pattern.equals("H") || pattern.equals("H2") || pattern.equals("top") || pattern.equalsIgnoreCase("NOAROMATIC")) {
try {
return this.e.vwr.getSmilesOpt(bsSelected, 0, 0, flags | (pattern.equals("H2") ? 8192 : 0) | (pattern.equals("H") ? 4096 : 0) | (pattern.equals("top") ? 16384 : 0) | (pattern.equalsIgnoreCase("NOAROMATIC") ? 16 : 0), (pattern.endsWith("///") ? pattern : null));
} catch (ex) {
if (Clazz.exceptionOf(ex, Exception)){
this.e.evalError(ex.getMessage(), null);
} else {
throw ex;
}
}
}var b;
if (bsMatch3D == null) {
try {
if (smiles == null) {
b = this.e.vwr.getSubstructureSetArray(pattern, bsSelected, flags);
} else if (pattern.equals("chirality")) {
return this.e.vwr.calculateChiralityForSmiles(smiles);
} else {
var isSmarts = ((flags & 2) == 2);
var ignoreElements = ((flags & 16384) == 16384);
flags = (isSmarts ? 2 : 1) | (firstMatchOnly ? 8 : 0) | (ignoreElements ? 16384 : 0);
if (!((typeof(smiles)=='string'))) {
return this.e.vwr.getSmilesMatcher().hasStructure(pattern, smiles, flags);
}var map = this.e.vwr.getSmilesMatcher().find(pattern, smiles, flags);
if (!asOneBitset) return (!firstMatchOnly ? map : map.length == 0 ?  Clazz.newIntArray (0, 0) : map[0]);
var bs =  new JU.BS();
for (var j = 0; j < map.length; j++) {
var a = map[j];
for (var k = a.length; --k >= 0; ) if (a[k] >= 0) bs.set(a[k]);

}
if (!isSmarts) return  Clazz.newIntArray (bs.cardinality(), 0);
var iarray =  Clazz.newIntArray (bs.cardinality(), 0);
var pt = 0;
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) iarray[pt++] = i;

return iarray;
}} catch (ex) {
if (Clazz.exceptionOf(ex, Exception)){
this.e.evalError(ex.getMessage(), null);
return null;
} else {
throw ex;
}
}
} else {
var vReturn =  new JU.Lst();
var stddev = this.getSmilesCorrelation(bsMatch3D, bsSelected, pattern, null, null, null, vReturn, false, null, null, false, flags);
if (Float.isNaN(stddev)) return (asOneBitset ?  new JU.BS() :  Clazz.newArray(-1, []));
this.e.showString("RMSD " + stddev + " Angstroms");
b = vReturn.toArray( new Array(vReturn.size()));
}if (asOneBitset) {
var bs =  new JU.BS();
for (var j = 0; j < b.length; j++) bs.or(b[j]);

return bs;
}var list =  new JU.Lst();
for (var j = 0; j < b.length; j++) list.addLast(b[j]);

return list;
}, "~S,~O,JU.BS,JU.BS,~N,~B,~B");
Clazz.defineMethod(c$, "getFlexFitList", 
function(bs1, bs2, smiles1, isSmarts){
var mapSet = JU.AU.newInt2(2);
this.getSmilesCorrelation(bs1, bs2, smiles1, null, null, null, null, false, mapSet, null, false, isSmarts ? 2 : 1);
if (mapSet[0] == null) return null;
var bondMap1 = this.e.vwr.ms.getDihedralMap(mapSet[0]);
var bondMap2 = (bondMap1 == null ? null : this.e.vwr.ms.getDihedralMap(mapSet[1]));
if (bondMap2 == null || bondMap2.length != bondMap1.length) return null;
var angles =  Clazz.newFloatArray (bondMap1.length, 3, 0);
var atoms = this.e.vwr.ms.at;
JS.SmilesExt.getTorsions(atoms, bondMap2, angles, 0);
JS.SmilesExt.getTorsions(atoms, bondMap1, angles, 1);
var data =  Clazz.newFloatArray (bondMap1.length * 6, 0);
for (var i = 0, pt = 0; i < bondMap1.length; i++) {
var map = bondMap1[i];
data[pt++] = map[0];
data[pt++] = map[1];
data[pt++] = map[2];
data[pt++] = map[3];
data[pt++] = angles[i][0];
data[pt++] = angles[i][1];
}
return data;
}, "JU.BS,JU.BS,~S,~B");
c$.getTorsions = Clazz.defineMethod(c$, "getTorsions", 
function(atoms, bondMap, diff, pt){
for (var i = bondMap.length; --i >= 0; ) {
var map = bondMap[i];
var v = JU.Measure.computeTorsion(atoms[map[0]], atoms[map[1]], atoms[map[2]], atoms[map[3]], true);
if (pt == 1) {
if (v - diff[i][0] > 180) v -= 360;
 else if (v - diff[i][0] <= -180) v += 360;
}diff[i][pt] = v;
}
}, "~A,~A,~A,~N");
Clazz.defineMethod(c$, "mapPolyhedra", 
function(i1, i2, isSmiles, m){
var ptsA =  new JU.Lst();
var ptsB =  new JU.Lst();
var data;
data =  Clazz.newArray(-1, [Integer.$valueOf(i1), null]);
this.e.getShapePropertyData(21, "syminfo", data);
var p1 = data[1];
data[0] = Integer.$valueOf(i2);
data[1] = null;
this.e.getShapePropertyData(21, "syminfo", data);
var p2 = data[1];
if (p1 == null || p2 == null) return NaN;
var smiles1 = p1.get("polySmiles");
var smiles2 = p2.get("polySmiles");
var map = this.getSmilesMatches(smiles2, smiles1, null, null, isSmiles ? 1 : 16385, false, true);
if (map.length == 0) return NaN;
ptsA.addLast(p1.get("center"));
var a = p1.get("vertices");
for (var i = 0, n = a.length; i < n; i++) ptsA.addLast(a[map[i + 1] - 1]);

ptsB.addLast(p2.get("center"));
a = p2.get("vertices");
for (var i = 0, n = a.length; i < n; i++) ptsB.addLast(a[i]);

J.api.Interface.getInterface("JU.Eigen", this.e.vwr, "script");
return JU.Measure.getTransformMatrix4(ptsA, ptsB, m, null);
}, "~N,~N,~B,JU.M4");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
