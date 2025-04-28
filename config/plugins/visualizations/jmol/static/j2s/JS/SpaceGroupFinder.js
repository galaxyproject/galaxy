Clazz.declarePackage("JS");
Clazz.load(["JU.P3"], "JS.SpaceGroupFinder", ["JU.BS", "$.Lst", "$.M4", "$.PT", "JS.SpaceGroup", "$.Symmetry", "$.SymmetryOperation", "$.UnitCell", "JU.BSUtil", "JV.FileManager"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.uc = null;
this.sg = null;
this.cartesians = null;
this.atoms = null;
this.nAtoms = 0;
this.xyzList = null;
this.unitCellParams = null;
this.slop = 0;
this.isAssign = false;
this.isUnknown = false;
this.$checkSupercell = false;
this.isSupercell = false;
this.asString = false;
this.bsPoints0 = null;
this.bsAtoms = null;
this.targets = null;
this.origin = null;
this.oabc = null;
this.scaling = null;
this.pTemp = null;
this.isg = 0;
if (!Clazz.isClassDefined("JS.SpaceGroupFinder.SGAtom")) {
JS.SpaceGroupFinder.$SpaceGroupFinder$SGAtom$ ();
}
Clazz.instantialize(this, arguments);}, JS, "SpaceGroupFinder", null);
Clazz.prepareFields (c$, function(){
this.pTemp =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "findSpaceGroup", 
function(vwr, atoms0, xyzList0, unitCellParams, origin, oabc0, uci, flags){
this.vwr = vwr;
this.xyzList = xyzList0;
this.unitCellParams = unitCellParams;
this.origin = origin;
this.oabc = oabc0;
this.uc = uci;
this.isAssign = ((flags & 2) != 0);
this.$checkSupercell = ((flags & 8) != 0);
this.asString = ((flags & 1) != 0);
var setFromScratch = ((flags & 4) != 0);
var slop0 = this.uc.getPrecision();
this.slop = (!Double.isNaN(slop0) ? slop0 : unitCellParams != null && unitCellParams.length > 26 ? unitCellParams[26] : false ? 1.0E-12 : 1.0E-4);
this.cartesians = vwr.ms.at;
this.bsPoints0 =  new JU.BS();
if (this.xyzList == null || this.isAssign) {
this.bsAtoms = JU.BSUtil.copy(atoms0);
this.nAtoms = this.bsAtoms.cardinality();
}this.targets = JU.BS.newN(this.nAtoms);
this.scaling = JU.P3.new3(1, 1, 1);
var name;
var basis;
this.isUnknown = true;
var isITA = (this.xyzList != null && this.xyzList.toUpperCase().startsWith("ITA/"));
var isHall = (this.xyzList != null && !isITA && (this.xyzList.startsWith("[") || this.xyzList.startsWith("Hall:")));
if (isITA || this.isAssign && isHall) {
this.isUnknown = false;
if (isITA) {
this.xyzList = JU.PT.rep(this.xyzList.substring(4), " ", "");
} else if (this.xyzList.startsWith("Hall:")) {
this.xyzList = this.xyzList.substring(5);
} else {
this.xyzList = JU.PT.replaceAllCharacters(this.xyzList, "[]", "");
}this.sg = this.setITA(isHall);
if (this.sg == null) return null;
name = this.sg.getName();
} else if (this.oabc != null || isHall) {
name = this.xyzList;
this.sg = JS.SpaceGroup.createSpaceGroupN(name);
this.isUnknown = (this.sg == null);
if (isHall && !this.isUnknown) return this.sg.dumpInfoObj();
} else if (JS.SpaceGroup.isXYZList(this.xyzList)) {
this.sg = JS.SpaceGroup.findSpaceGroupFromXYZ(this.xyzList);
if (this.sg != null) return this.sg.dumpInfoObj();
}if (setFromScratch) {
if (this.sg == null && (this.sg = JS.SpaceGroup.determineSpaceGroupNA(this.xyzList, unitCellParams)) == null && (this.sg = JS.SpaceGroup.createSpaceGroupN(this.xyzList)) == null) return null;
basis =  new JU.BS();
name = this.sg.asString();
if (this.oabc == null) {
var userDefined = (unitCellParams.length == 6);
this.uc = JS.SpaceGroupFinder.setSpaceGroupAndUnitCell(this.sg, unitCellParams, null, userDefined);
this.oabc = this.uc.getUnitCellVectors();
if (origin != null) this.oabc[0].setT(origin);
} else {
this.uc = JS.SpaceGroupFinder.setSpaceGroupAndUnitCell(this.sg, null, this.oabc, false);
this.uc.transformUnitCell(uci.replaceTransformMatrix(null));
}} else {
var ret = this.findGroupByOperations();
if (!this.isAssign || !(Clazz.instanceOf(ret,"JS.SpaceGroup"))) return ret;
this.sg = ret;
name = this.sg.asString();
basis = JU.BSUtil.copy(this.bsAtoms);
for (var i = this.targets.nextSetBit(0); i >= 0; i = this.targets.nextSetBit(i + 1)) basis.clear(this.atoms[i].index);

var nb = basis.cardinality();
var msg = name + (atoms0 == null ? "" : "\nbasis is " + nb + " atom" + (nb == 1 ? "" : "s") + ": " + basis);
System.out.println(msg);
if (this.asString) return msg;
}var map = this.sg.dumpInfoObj();
if (this.uc != null) System.out.println("unitcell is " + this.uc.getUnitCellInfo(true));
if (!this.isAssign) {
var bs1 = JU.BS.copy(this.bsPoints0);
bs1.andNot(this.targets);
this.dumpBasis(JS.SpaceGroupFinder.bsGroupOps[this.isg], bs1, this.bsPoints0);
}map.put("name", name);
map.put("basis", basis);
if (this.isSupercell) map.put("supercell", this.scaling);
this.oabc[1].scale(1 / this.scaling.x);
this.oabc[2].scale(1 / this.scaling.y);
this.oabc[3].scale(1 / this.scaling.z);
map.put("unitcell", this.oabc);
if (this.isAssign) map.put("sg", this.sg);
return map;
}, "JV.Viewer,JU.BS,~S,~A,JU.T3,~A,J.api.SymmetryInterface,~N");
Clazz.defineMethod(c$, "setITA", 
function(isHall){
var name = null;
var sgdata = null;
var pt = this.xyzList.lastIndexOf(":");
var hasTransform = (pt > 0 && this.xyzList.indexOf(",") > pt);
var isJmolCode = (pt > 0 && !hasTransform);
var transform = null;
var clegId = null;
if (hasTransform) {
name = transform = this.uc.staticCleanTransform(this.xyzList.substring(pt + 1));
this.xyzList = this.xyzList.substring(0, pt);
clegId = this.xyzList + ":" + transform;
if (transform.equals("a,b,c")) {
transform = null;
hasTransform = false;
}}pt = this.xyzList.indexOf(".");
if (pt > 0 && (hasTransform || isJmolCode)) {
this.xyzList = this.xyzList.substring(0, pt);
pt = -1;
}var itano = this.xyzList;
var isITADotSetting = (pt > 0);
if (!isJmolCode && !isHall && !hasTransform && !isITADotSetting && JU.PT.parseInt(itano) != -2147483648) this.xyzList += ".1";
var genPos;
var setting = null;
var itaIndex = this.xyzList;
if (isHall) {
genPos = this.uc.getSpaceGroupInfoObj("nameToXYZList", "Hall:" + this.xyzList, false, false);
if (genPos == null) return null;
} else {
name = (hasTransform ? transform : itaIndex);
this.sg = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(hasTransform ? clegId : itaIndex);
var o = this.uc.getSpaceGroupJSON(this.vwr, "ITA", itaIndex, 0);
if (o == null || (typeof(o)=='string')) {
return null;
}sgdata = o;
if (isJmolCode || hasTransform) {
var its = sgdata.get("its");
if (its == null) return null;
sgdata = null;
for (var i = 0, c = its.size(); i < c; i++) {
setting = its.get(i);
if (name.equals(setting.get(hasTransform ? "trm" : "jmolId"))) {
sgdata = setting;
break;
}}
if (sgdata == null || !sgdata.containsKey("jmolId")) {
if (isJmolCode) {
return null;
}setting = null;
if (sgdata != null) transform = sgdata.get("trm");
hasTransform = true;
sgdata = its.get(0);
} else {
setting = null;
hasTransform = false;
transform = null;
}} else {
name = sgdata.get("jmolId");
}genPos = sgdata.get("gp");
}if (this.sg != null && transform == null) {
this.sg = JS.SpaceGroup.createITASpaceGroup(genPos, this.sg);
return this.sg;
}this.sg = JS.SpaceGroup.transformSpaceGroup(null, this.sg, genPos, (hasTransform ? transform : null), (hasTransform ?  new JU.M4() : null));
if (this.sg == null) return null;
name = "";
if (this.sg.itaNumber.equals("0")) {
if (transform == null) {
transform = sgdata.get("trm");
var hm = sgdata.get("hm");
this.sg.setHMSymbol(hm);
}name = null;
System.out.println("SpaceGroupFinder: new setting: " + this.sg.asString());
}return this.sg;
}, "~B");
Clazz.defineMethod(c$, "findGroupByOperations", 
function(){
var bsOps =  new JU.BS();
var bsGroups =  new JU.BS();
var n = 0;
var nChecked = 0;
try {
if (this.isUnknown) {
if (JS.SpaceGroupFinder.bsOpGroups == null) JS.SpaceGroupFinder.loadData(this.vwr, this);
} else {
bsGroups.set(0);
}if (this.xyzList != null) {
if (this.isUnknown) {
var ret = this.getGroupsWithOps(this.xyzList, this.unitCellParams, this.isAssign);
if (!this.isAssign || ret == null) return ret;
this.sg = ret;
}if (this.oabc == null) this.uc.setUnitCellFromParams(this.unitCellParams, false, this.slop);
}var uc0 = this.uc;
if (this.oabc == null) {
this.oabc = this.uc.getUnitCellVectors();
this.uc = this.uc.getUnitCellMultiplied();
if (this.origin != null && !this.origin.equals(this.uc.getCartesianOffset())) {
this.oabc[0].setT(this.origin);
this.uc.setCartesianOffset(this.origin);
}} else {
this.uc.getUnitCell(this.oabc, false, "finder");
}if (this.isUnknown) this.filterGroups(bsGroups, this.uc.getUnitCellParams());
 else if (this.nAtoms == 0) {
return this.sg;
}if (this.bsAtoms != null) {
this.atoms =  new Array(this.bsAtoms.cardinality());
System.out.println("bsAtoms = " + this.bsAtoms);
for (var p = 0, i = this.bsAtoms.nextSetBit(0); i >= 0; i = this.bsAtoms.nextSetBit(i + 1), p++) {
var a = this.cartesians[i];
var type = a.getAtomicAndIsotopeNumber();
(this.atoms[p] = Clazz.innerTypeInstance(JS.SpaceGroupFinder.SGAtom, this, null, type, i, a.getAtomName(), a.getOccupancy100())).setT(this.toFractional(a, this.uc));
}
}var bsPoints = JU.BSUtil.newBitSet2(0, this.nAtoms);
this.nAtoms = bsPoints.cardinality();
uc0 = this.uc;
if (this.nAtoms > 0) {
for (var i = bsPoints.nextSetBit(0); i >= 0; i = bsPoints.nextSetBit(i + 1)) {
this.uc.unitize(this.atoms[i]);
}
this.removeDuplicates(bsPoints);
if (this.$checkSupercell) {
this.uc = this.checkSupercell(this.vwr, this.uc, bsPoints, 1, this.scaling);
this.uc = this.checkSupercell(this.vwr, this.uc, bsPoints, 2, this.scaling);
this.uc = this.checkSupercell(this.vwr, this.uc, bsPoints, 3, this.scaling);
this.isSupercell = (this.uc !== uc0);
if (this.isSupercell) {
if (this.scaling.x != 1) System.out.println("supercell found; a scaled by 1/" + this.scaling.x);
if (this.scaling.y != 1) System.out.println("supercell found; b scaled by 1/" + this.scaling.y);
if (this.scaling.z != 1) System.out.println("supercell found; c scaled by 1/" + this.scaling.z);
}}}n = bsPoints.cardinality();
this.bsAtoms =  new JU.BS();
var newAtoms =  new Array(n);
for (var p = 0, i = bsPoints.nextSetBit(0); i >= 0; i = bsPoints.nextSetBit(i + 1)) {
var a = this.atoms[i];
newAtoms[p++] = a;
if (this.isSupercell) {
a.setT(this.toFractional(this.cartesians[a.index], this.uc));
this.uc.unitize(a);
}this.bsAtoms.set(this.atoms[i].index);
}
this.atoms = newAtoms;
this.nAtoms = n;
bsPoints.clearAll();
bsPoints.setBits(0, this.nAtoms);
this.bsPoints0 = JU.BS.copy(bsPoints);
var temp1 = JU.BS.newN(JS.SpaceGroupFinder.OP_COUNT);
var targeted = JU.BS.newN(this.nAtoms);
bsOps.setBits(1, this.sg == null ? JS.SpaceGroupFinder.OP_COUNT : this.sg.getOperationCount());
if (this.nAtoms == 0) {
bsGroups.clearBits(1, JS.SpaceGroupFinder.GROUP_COUNT);
bsOps.clearAll();
}var uncheckedOps = JU.BS.newN(JS.SpaceGroupFinder.OP_COUNT);
var opsChecked = JU.BS.newN(JS.SpaceGroupFinder.OP_COUNT);
opsChecked.set(0);
var hasC1 = false;
for (var iop = bsOps.nextSetBit(1); iop > 0 && !bsGroups.isEmpty(); iop = bsOps.nextSetBit(iop + 1)) {
var op = (this.sg == null ? JS.SpaceGroupFinder.getOp(iop) : this.sg.getOperation(iop));
if (this.sg == null) {
System.out.println("\nChecking operation " + iop + " " + JS.SpaceGroupFinder.opXYZ[iop]);
System.out.println("bsGroups = " + bsGroups);
System.out.println("bsOps = " + bsOps);
nChecked++;
}var isOK = true;
bsPoints.clearAll();
bsPoints.or(this.bsPoints0);
targeted.clearAll();
for (var i = bsPoints.nextSetBit(0); i >= 0; i = bsPoints.nextSetBit(i + 1)) {
bsPoints.clear(i);
var j = this.findEquiv(this.uc, iop, op, i, bsPoints, this.pTemp, true);
if (j < 0 && this.sg == null) {
System.out.println("failed op " + iop + " for atom " + i + " " + this.atoms[i].name + " " + this.atoms[i] + " looking for " + this.pTemp + "\n" + op);
isOK = false;
break;
}if (j >= 0 && i != j) {
targeted.set(j);
}}
if (this.sg == null) {
var myGroups = JS.SpaceGroupFinder.bsOpGroups[iop];
bsOps.clear(iop);
opsChecked.set(iop);
if (isOK) {
if (iop == 1) hasC1 = true;
this.targets.or(targeted);
bsGroups.and(myGroups);
temp1.setBits(1, JS.SpaceGroupFinder.OP_COUNT);
for (var i = bsGroups.nextSetBit(0); i >= 0; i = bsGroups.nextSetBit(i + 1)) {
temp1.and(JS.SpaceGroupFinder.bsGroupOps[i]);
}
uncheckedOps.or(temp1);
bsOps.andNot(temp1);
} else {
bsGroups.andNot(myGroups);
temp1.clearAll();
for (var i = bsGroups.nextSetBit(0); i >= 0; i = bsGroups.nextSetBit(i + 1)) {
temp1.or(JS.SpaceGroupFinder.bsGroupOps[i]);
}
bsOps.and(temp1);
}} else {
this.targets.or(targeted);
}}
if (this.sg == null) {
n = bsGroups.cardinality();
if (n == 0) {
bsGroups.set(hasC1 ? 1 : 0);
n = 1;
if (hasC1 && !this.asString) {
uncheckedOps.clearAll();
uncheckedOps.set(1);
opsChecked.clearAll();
this.targets.clearAll();
bsPoints.or(this.bsPoints0);
}}this.isg = bsGroups.nextSetBit(0);
if (n == 1) {
if (this.isg > 0) {
opsChecked.and(JS.SpaceGroupFinder.bsGroupOps[this.isg]);
uncheckedOps.and(JS.SpaceGroupFinder.bsGroupOps[this.isg]);
uncheckedOps.andNot(opsChecked);
uncheckedOps.or(JS.SpaceGroupFinder.bsGroupOps[this.isg]);
uncheckedOps.clear(0);
bsPoints.or(this.bsPoints0);
bsPoints.andNot(this.targets);
if (!this.checkBasis(this.uc, uncheckedOps, bsPoints, this.targets)) {
this.isg = 0;
}}if (this.isg == 0) this.targets.clearAll();
}}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
bsGroups.clearAll();
} else {
throw e;
}
}
if (this.sg == null) {
System.out.println("checked " + nChecked + " operations; now " + n + " " + bsGroups + " " + bsOps);
for (var i = bsGroups.nextSetBit(0); i >= 0; i = bsGroups.nextSetBit(i + 1)) {
System.out.println(JS.SpaceGroup.nameToGroup.get(JS.SpaceGroupFinder.groupNames[i]));
}
if (n != 1) return null;
this.sg = JS.SpaceGroup.nameToGroup.get(JS.SpaceGroupFinder.groupNames[this.isg]);
}return this.sg;
});
c$.setSpaceGroupAndUnitCell = Clazz.defineMethod(c$, "setSpaceGroupAndUnitCell", 
function(sg, params, oabc, allowSame){
var sym =  new JS.Symmetry();
sym.setSpaceGroupTo(sg);
if (oabc == null) {
var newParams =  Clazz.newFloatArray (6, 0);
if (!JS.UnitCell.createCompatibleUnitCell(sg, params, newParams, allowSame)) {
newParams = params;
}sym.setUnitCellFromParams(newParams, false, NaN);
} else {
sym.getUnitCell(oabc, false, "modelkit");
}return sym;
}, "JS.SpaceGroup,~A,~A,~B");
Clazz.defineMethod(c$, "removeDuplicates", 
function(bs){
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var a = this.atoms[i];
for (var j = bs.nextSetBit(0); j < i; j = bs.nextSetBit(j + 1)) {
var b = this.atoms[j];
if (a.typeAndOcc == b.typeAndOcc && a.distanceSquared(b) < 1.96E-6) {
bs.clear(i);
break;
}}
}
}, "JU.BS");
Clazz.defineMethod(c$, "dumpBasis", 
function(ops, bs1, bsPoints){
}, "JU.BS,JU.BS,JU.BS");
Clazz.defineMethod(c$, "checkBasis", 
function(uc, uncheckedOps, bsPoints, targets){
var n = uncheckedOps.cardinality();
if (n == 0) return true;
var bs =  new JU.BS();
bs.or(bsPoints);
System.out.println("finishing check for basis for " + n + " operations");
for (var iop = uncheckedOps.nextSetBit(0); iop >= 0; iop = uncheckedOps.nextSetBit(iop + 1)) {
bs.or(bsPoints);
var op = JS.SpaceGroupFinder.getOp(iop);
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var j = this.findEquiv(uc, -1, op, i, bs, this.pTemp, false);
if (j < 0) return false;
if (i != j) {
j = Math.max(i, j);
targets.set(j);
bs.clear(j);
}}
}
return true;
}, "J.api.SymmetryInterface,JU.BS,JU.BS,JU.BS");
Clazz.defineMethod(c$, "filterGroups", 
function(bsGroups, params){
var isOrtho = false;
var isTet = false;
var isTri = false;
var isRhombo = false;
var isCubic = false;
var absame = this.approx001(params[0] - params[1]);
var bcsame = this.approx001(params[1] - params[2]);
if (params[3] == 90) {
if (params[4] == 90) {
if (absame && params[0] != params[1]) System.out.println("OHOH");
isTri = (absame && this.approx001(params[5] - 120));
if (params[5] == 90) {
isCubic = (absame && params[1] == params[2]);
isTet = (!isCubic && absame);
isOrtho = (!isCubic && !isTet);
}}} else if (absame && bcsame && this.approx001(params[3] - params[4]) && this.approx001(params[4] - params[5])) {
isRhombo = true;
}bsGroups.setBits(0, 2);
var i0 = 2;
var i = 2;
while (true) {
i = JS.SpaceGroupFinder.scanTo(i, "16");
if (!isOrtho && !isTet && !isTri && !isRhombo && !isCubic) break;
i = JS.SpaceGroupFinder.scanTo(i, "75");
if (!isTet && !isTri && !isRhombo && !isCubic) break;
i = JS.SpaceGroupFinder.scanTo(i, "143");
if (!isTri && !isRhombo && !isCubic) break;
i0 = i;
for (; ; i++) {
var g = JS.SpaceGroupFinder.groupNames[i];
if (g.indexOf(":r") >= 0) {
if (!isRhombo) continue;
bsGroups.set(i);
}if (g.startsWith("195")) {
if (isRhombo) return;
break;
}}
if (!isCubic) break;
bsGroups.setBits(2, i0);
i0 = i;
i = JS.SpaceGroupFinder.GROUP_COUNT;
break;
}
bsGroups.setBits(i0, i);
}, "JU.BS,~A");
Clazz.defineMethod(c$, "approx001", 
function(d){
return Math.abs(d) < 0.001;
}, "~N");
c$.scanTo = Clazz.defineMethod(c$, "scanTo", 
function(i, num){
num = "000" + num;
num = num.substring(num.length - 3);
for (; ; i++) {
if (JS.SpaceGroupFinder.groupNames[i].startsWith(num)) break;
}
return i;
}, "~N,~S");
Clazz.defineMethod(c$, "getGroupsWithOps", 
function(xyzList, unitCellParams, isAssign){
var groups =  new JU.BS();
if (unitCellParams == null) {
groups.setBits(0, JS.SpaceGroupFinder.GROUP_COUNT);
} else {
this.filterGroups(groups, unitCellParams);
}var sgo = null;
if (!JS.SpaceGroup.isXYZList(xyzList)) {
sgo = JS.SpaceGroup.determineSpaceGroupNA(xyzList, unitCellParams);
if (sgo == null) return null;
sgo.checkHallOperators();
var tableNo = ("00" + sgo.jmolId);
var pt = tableNo.indexOf(":");
tableNo = tableNo.substring((pt < 0 ? tableNo.length : pt) - 3);
for (var i = 0; i < JS.SpaceGroupFinder.GROUP_COUNT; i++) if (JS.SpaceGroupFinder.groupNames[i].equals(tableNo)) return (groups.get(i) ? sgo : null);

return null;
}var isEqual = xyzList.indexOf("&") < 0 || isAssign;
var ops = JU.PT.split(JU.PT.trim(xyzList.trim().$replace('&', ';'), ";="), ";");
for (var j = ops.length; --j >= 0; ) {
var xyz = ops[j];
if (xyz == null) return "?" + ops[j] + "?";
xyz = JS.SymmetryOperation.getJmolCanonicalXYZ(xyz);
for (var i = JS.SpaceGroupFinder.opXYZ.length; --i >= 0; ) {
if (JS.SpaceGroupFinder.opXYZ[i].equals(xyz)) {
groups.and(JS.SpaceGroupFinder.bsOpGroups[i]);
break;
}if (i == 0) groups.clearAll();
}
}
if (groups.isEmpty()) {
return (isAssign ? JS.SpaceGroup.createSpaceGroupN(xyzList) : null);
}if (isEqual) {
for (var n = ops.length, i = groups.nextSetBit(0); i >= 0; i = groups.nextSetBit(i + 1)) {
if (JS.SpaceGroupFinder.bsGroupOps[i].cardinality() == n) {
if (isAssign) {
return JS.SpaceGroup.createSpaceGroupN(JS.SpaceGroupFinder.groupNames[i]);
}return JS.SpaceGroup.getInfo(null, JS.SpaceGroupFinder.groupNames[i], unitCellParams, true, false);
}}
return null;
}var ret =  new Array(groups.cardinality());
for (var p = 0, i = groups.nextSetBit(0); i >= 0; i = groups.nextSetBit(i + 1)) {
ret[p++] = JS.SpaceGroupFinder.groupNames[i];
}
return ret;
}, "~S,~A,~B");
Clazz.defineMethod(c$, "toFractional", 
function(a, uc){
this.pTemp.setT(a);
uc.toFractional(this.pTemp, false);
return this.pTemp;
}, "JM.Atom,J.api.SymmetryInterface");
c$.getOp = Clazz.defineMethod(c$, "getOp", 
function(iop){
var op = JS.SpaceGroupFinder.ops[iop];
if (op == null) {
JS.SpaceGroupFinder.ops[iop] = op =  new JS.SymmetryOperation(null, iop, false);
op.setMatrixFromXYZ(JS.SpaceGroupFinder.opXYZ[iop], 0, false);
op.doFinalize();
}return op;
}, "~N");
Clazz.defineMethod(c$, "checkSupercell", 
function(vwr, uc, bsPoints, abc, scaling){
if (bsPoints.isEmpty()) return uc;
var minF = 2147483647;
var maxF = -2147483648;
var counts =  Clazz.newIntArray (101, 0);
var nAtoms = bsPoints.cardinality();
for (var i = bsPoints.nextSetBit(0); i >= 0; i = bsPoints.nextSetBit(i + 1)) {
var a = this.atoms[i];
var type = a.typeAndOcc;
var b;
var f;
for (var j = bsPoints.nextSetBit(0); j >= 0; j = bsPoints.nextSetBit(j + 1)) {
if (j == i || (b = this.atoms[j]).typeAndOcc != type) continue;
this.pTemp.sub2(b, a);
switch (abc) {
case 1:
if (this.approx0(f = this.pTemp.x) || !this.approx0(this.pTemp.y) || !this.approx0(this.pTemp.z)) continue;
break;
case 2:
if (this.approx0(f = this.pTemp.y) || !this.approx0(this.pTemp.x) || !this.approx0(this.pTemp.z)) continue;
break;
default:
case 3:
if (this.approx0(f = this.pTemp.z) || !this.approx0(this.pTemp.x) || !this.approx0(this.pTemp.y)) continue;
break;
}
var n = this.approxInt(1 / f);
if (n == 0 || Clazz.doubleToInt(nAtoms / n) != 1 * nAtoms / n || n > 100) continue;
if (n > maxF) maxF = n;
if (n < minF) minF = n;
counts[n]++;
}
}
var n = maxF;
while (n >= minF) {
if (counts[n] > 0 && counts[n] == Clazz.doubleToInt((n - 1) * nAtoms / n)) {
break;
}--n;
}
if (n < minF) return uc;
var oabc = uc.getUnitCellVectors();
oabc[abc].scale(1 / n);
switch (abc) {
case 1:
scaling.x = n;
break;
case 2:
scaling.y = n;
break;
case 3:
scaling.z = n;
break;
}
(uc =  new JS.Symmetry()).getUnitCell(oabc, false, "scaled");
var f = 0;
for (var i = bsPoints.nextSetBit(0); i >= 0; i = bsPoints.nextSetBit(i + 1)) {
switch (abc) {
case 1:
f = this.approxInt(n * this.atoms[i].x);
break;
case 2:
f = this.approxInt(n * this.atoms[i].y);
break;
case 3:
f = this.approxInt(n * this.atoms[i].z);
break;
}
if (f != 0) {
this.atoms[i] = null;
bsPoints.clear(i);
}}
nAtoms = bsPoints.cardinality();
return uc;
}, "JV.Viewer,JS.Symmetry,JU.BS,~N,JU.P3");
Clazz.defineMethod(c$, "approx0", 
function(f){
return (Math.abs(f) < this.slop);
}, "~N");
Clazz.defineMethod(c$, "approxInt", 
function(finv){
var i = Clazz.floatToInt(finv + this.slop);
return (this.approx0(finv - i) ? i : 0);
}, "~N");
Clazz.defineMethod(c$, "findEquiv", 
function(uc, iop, op, i, bsPoints, pt, andClear){
var a = this.atoms[i];
pt.setT(a);
op.rotTrans(pt);
uc.unitize(pt);
if (pt.distanceSquared(a) == 0) {
return i;
}var testiop = -99;
var type = a.typeAndOcc;
var name = a.name;
for (var j = this.nAtoms; --j >= 0; ) {
var b = this.atoms[j];
if (b.typeAndOcc != type) continue;
var d = b.distance(pt);
if (d * d < 1.96E-6 || (1 - d) * (1 - d) < 1.96E-6 && this.latticeShift(pt, b)) {
if (andClear) {
j = Math.max(i, j);
if (i != j) bsPoints.clear(j);
}return j;
}}
return -1;
}, "J.api.SymmetryInterface,~N,JS.SymmetryOperation,~N,JU.BS,JU.P3,~B");
Clazz.defineMethod(c$, "latticeShift", 
function(a, b){
var is1 = (this.approx0(Math.abs(a.x - b.x) - 1) || this.approx0(Math.abs(a.y - b.y) - 1) || this.approx0(Math.abs(a.z - b.z) - 1));
if (is1) {
}return is1;
}, "JU.P3,JU.P3");
c$.main = Clazz.defineMethod(c$, "main", 
function(args){
if (JS.SpaceGroupFinder.loadData(null,  new JS.SpaceGroupFinder())) System.out.println("OK");
}, "~A");
c$.loadData = Clazz.defineMethod(c$, "loadData", 
function(vwr, me){
try {
JS.SpaceGroupFinder.groupNames = JS.SpaceGroupFinder.getList(vwr, me, null, "sggroups_ordered.txt");
JS.SpaceGroupFinder.GROUP_COUNT = JS.SpaceGroupFinder.groupNames.length;
JS.SpaceGroupFinder.opXYZ = JS.SpaceGroupFinder.getList(vwr, me, null, "sgops_ordered.txt");
JS.SpaceGroupFinder.OP_COUNT = JS.SpaceGroupFinder.opXYZ.length;
var map = JS.SpaceGroupFinder.getList(vwr, me,  new Array(JS.SpaceGroupFinder.OP_COUNT), "sgmap.txt");
JS.SpaceGroupFinder.bsGroupOps =  new Array(JS.SpaceGroupFinder.GROUP_COUNT);
JS.SpaceGroupFinder.bsOpGroups =  new Array(JS.SpaceGroupFinder.OP_COUNT);
for (var j = 0; j < JS.SpaceGroupFinder.GROUP_COUNT; j++) JS.SpaceGroupFinder.bsGroupOps[j] = JU.BS.newN(JS.SpaceGroupFinder.OP_COUNT);

for (var i = 0; i < JS.SpaceGroupFinder.OP_COUNT; i++) {
var m = map[i];
var n = m.length;
JS.SpaceGroupFinder.bsOpGroups[i] = JU.BS.newN(JS.SpaceGroupFinder.GROUP_COUNT);
for (var j = 0; j < n; j++) {
if (m.charAt(j) == '1') {
JS.SpaceGroupFinder.bsGroupOps[j].set(i);
JS.SpaceGroupFinder.bsOpGroups[i].set(j);
}}
}
JS.SpaceGroupFinder.ops =  new Array(JS.SpaceGroupFinder.OP_COUNT);
return true;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
return false;
} else {
throw e;
}
} finally {
if (JS.SpaceGroupFinder.rdr != null) try {
JS.SpaceGroupFinder.rdr.close();
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
} else {
throw e;
}
}
}
}, "JV.Viewer,~O");
c$.getList = Clazz.defineMethod(c$, "getList", 
function(vwr, me, list, fileName){
JS.SpaceGroupFinder.rdr = JV.FileManager.getBufferedReaderForResource(vwr, me, "JS/", "sg/" + fileName);
if (list == null) {
var l =  new JU.Lst();
var line;
while ((line = JS.SpaceGroupFinder.rdr.readLine()) != null) {
if (line.length > 0) {
l.addLast(line);
}}
l.toArray(list =  new Array(l.size()));
} else {
for (var i = 0; i < list.length; i++) list[i] = JS.SpaceGroupFinder.rdr.readLine();

}JS.SpaceGroupFinder.rdr.close();
return list;
}, "JV.Viewer,~O,~A,~S");
c$.$SpaceGroupFinder$SGAtom$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.typeAndOcc = 0;
this.index = 0;
this.name = null;
Clazz.instantialize(this, arguments);}, JS.SpaceGroupFinder, "SGAtom", JU.P3);
Clazz.makeConstructor(c$, 
function(type, index, name, occupancy){
Clazz.superConstructor (this, JS.SpaceGroupFinder.SGAtom, []);
this.typeAndOcc = type + 1000 * occupancy;
this.index = index;
this.name = name;
}, "~N,~N,~S,~N");
/*eoif4*/})();
};
c$.GROUP_COUNT = 0;
c$.OP_COUNT = 0;
c$.bsOpGroups = null;
c$.bsGroupOps = null;
c$.groupNames = null;
c$.opXYZ = null;
c$.ops = null;
c$.rdr = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
