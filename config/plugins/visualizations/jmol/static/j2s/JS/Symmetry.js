Clazz.declarePackage("JS");
Clazz.load(["J.api.SymmetryInterface"], "JS.Symmetry", ["java.util.Hashtable", "JU.BS", "$.JSJSONParser", "$.Lst", "$.M4", "$.P3", "$.PT", "$.Rdr", "$.SB", "J.api.Interface", "J.bspt.Bspt", "JS.PointGroup", "$.SpaceGroup", "$.SymmetryInfo", "$.SymmetryOperation", "$.UnitCell", "JU.Escape", "$.Logger", "$.SimpleUnitCell", "JV.FileManager"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.spaceGroup = null;
this.unitCell = null;
this.$isBio = false;
this.pointGroup = null;
this.cip = null;
this.symmetryInfo = null;
this.desc = null;
this.transformMatrix = null;
Clazz.instantialize(this, arguments);}, JS, "Symmetry", null, J.api.SymmetryInterface);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "isBio", 
function(){
return this.$isBio;
});
Clazz.overrideMethod(c$, "setPointGroup", 
function(vwr, siLast, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly){
this.pointGroup = JS.PointGroup.getPointGroup(siLast == null ? null : (siLast).pointGroup, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly, vwr.getBoolean(603979956), vwr.getScalePixelsPerAngstrom(false));
return this;
}, "JV.Viewer,J.api.SymmetryInterface,JU.T3,~A,JU.BS,~B,~N,~N,~N,~B");
Clazz.overrideMethod(c$, "getPointGroupName", 
function(){
return this.pointGroup.getName();
});
Clazz.overrideMethod(c$, "getPointGroupInfo", 
function(modelIndex, drawID, asInfo, type, index, scale){
if (drawID == null && !asInfo && this.pointGroup.textInfo != null) return this.pointGroup.textInfo;
 else if (drawID == null && this.pointGroup.isDrawType(type, index, scale)) return this.pointGroup.drawInfo;
 else if (asInfo && this.pointGroup.info != null) return this.pointGroup.info;
return this.pointGroup.getInfo(modelIndex, drawID, asInfo, type, index, scale);
}, "~N,~S,~B,~S,~N,~N");
Clazz.overrideMethod(c$, "setSpaceGroup", 
function(doNormalize){
this.symmetryInfo = null;
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull(true, doNormalize, false);
}, "~B");
Clazz.overrideMethod(c$, "addSpaceGroupOperation", 
function(xyz, opId){
return this.spaceGroup.addSymmetry(xyz, opId, false);
}, "~S,~N");
Clazz.overrideMethod(c$, "addBioMoleculeOperation", 
function(mat, isReverse){
this.$isBio = this.spaceGroup.isBio = true;
return this.spaceGroup.addSymmetry((isReverse ? "!" : "") + "[[bio" + mat, 0, false);
}, "JU.M4,~B");
Clazz.overrideMethod(c$, "setLattice", 
function(latt){
this.spaceGroup.setLatticeParam(latt);
}, "~N");
Clazz.overrideMethod(c$, "getSpaceGroup", 
function(){
return this.spaceGroup;
});
Clazz.overrideMethod(c$, "getSpaceGroupInfoObj", 
function(name, params, isFull, addNonstandard){
var isNameToXYZList = false;
switch (name) {
case "list":
return this.getSpaceGroupList(params);
case "opsCtr":
return this.spaceGroup.getOpsCtr(params);
case "nameToXYZList":
isNameToXYZList = true;
case "itaIndex":
case "itaTransform":
case "itaNumber":
var sg = null;
if (params != null) {
sg = JS.SpaceGroup.determineSpaceGroupN(params);
if (sg == null && isNameToXYZList) sg = JS.SpaceGroup.createSpaceGroupN(params);
} else if (this.spaceGroup != null) {
sg = this.spaceGroup;
} else if (this.symmetryInfo != null) {
sg = this.symmetryInfo.getDerivedSpaceGroup();
}switch (sg == null ? "" : name) {
case "nameToXYZList":
var genPos =  new JU.Lst();
sg.setFinalOperations();
for (var i = 0, n = sg.getOperationCount(); i < n; i++) {
genPos.addLast((sg.getOperation(i)).xyz);
}
return genPos;
case "itaIndex":
return sg.getItaIndex();
case "itaTransform":
return sg.itaTransform;
case "itaNumber":
return sg.itaNumber;
}
return null;
default:
return JS.SpaceGroup.getInfo(this.spaceGroup, name, params, isFull, addNonstandard);
}
}, "~S,~O,~B,~B");
Clazz.defineMethod(c$, "getSpaceGroupList", 
function(vwr){
var sb =  new JU.SB();
var list = this.getSpaceGroupJSON(vwr, "ITA", "ALL", 0);
for (var i = 0, n = list.size(); i < n; i++) {
var map = list.get(i);
sb.appendO(map.get("sg")).appendC('.').appendO(map.get("set")).appendC('\t').appendO(map.get("hm")).appendC('\t').appendO(map.get("sg")).appendC(':').appendO(map.get("trm")).appendC('\n');
}
return sb.toString();
}, "JV.Viewer");
Clazz.overrideMethod(c$, "getLatticeDesignation", 
function(){
return this.spaceGroup.getLatticeDesignation();
});
Clazz.overrideMethod(c$, "setFinalOperations", 
function(dim, name, atoms, iAtomFirst, noSymmetryCount, doNormalize, filterSymop){
if (name != null && (name.startsWith("bio") || name.indexOf(" *(") >= 0)) this.spaceGroup.setName(name);
if (filterSymop != null) {
var lst =  new JU.Lst();
lst.addLast(this.spaceGroup.operations[0]);
for (var i = 1; i < this.spaceGroup.operationCount; i++) if (filterSymop.contains(" " + (i + 1) + " ")) lst.addLast(this.spaceGroup.operations[i]);

this.spaceGroup = JS.SpaceGroup.createSpaceGroup(-1, name + " *(" + filterSymop.trim() + ")", lst, -1);
}this.spaceGroup.setFinalOperationsForAtoms(dim, atoms, iAtomFirst, noSymmetryCount, doNormalize);
}, "~N,~S,~A,~N,~N,~B,~S");
Clazz.overrideMethod(c$, "getSpaceGroupOperation", 
function(i){
return (this.spaceGroup == null || this.spaceGroup.operations == null || i >= this.spaceGroup.operations.length ? null : this.spaceGroup.finalOperations == null ? this.spaceGroup.operations[i] : this.spaceGroup.finalOperations[i]);
}, "~N");
Clazz.overrideMethod(c$, "getSpaceGroupXyz", 
function(i, doNormalize){
return this.spaceGroup.getXyz(i, doNormalize);
}, "~N,~B");
Clazz.overrideMethod(c$, "newSpaceGroupPoint", 
function(pt, i, o, transX, transY, transZ, retPoint){
if (o == null && this.spaceGroup.finalOperations == null) {
var op = this.spaceGroup.operations[i];
if (!op.isFinalized) op.doFinalize();
o = op;
}JS.SymmetryOperation.rotateAndTranslatePoint((o == null ? this.spaceGroup.finalOperations[i] : o), pt, transX, transY, transZ, retPoint);
}, "JU.P3,~N,JU.M4,~N,~N,~N,JU.P3");
Clazz.overrideMethod(c$, "rotateAxes", 
function(iop, axes, ptTemp, mTemp){
return (iop == 0 ? axes : this.spaceGroup.finalOperations[iop].rotateAxes(axes, this.unitCell, ptTemp, mTemp));
}, "~N,~A,JU.P3,JU.M3");
Clazz.overrideMethod(c$, "getSpinOp", 
function(op){
return this.spaceGroup.operations[op].getMagneticOp();
}, "~N");
Clazz.overrideMethod(c$, "getLatticeOp", 
function(){
return this.spaceGroup.latticeOp;
});
Clazz.overrideMethod(c$, "getLatticeCentering", 
function(){
return JS.SymmetryOperation.getLatticeCentering(this.getSymmetryOperations());
});
Clazz.overrideMethod(c$, "getOperationRsVs", 
function(iop){
return (this.spaceGroup.finalOperations == null ? this.spaceGroup.operations : this.spaceGroup.finalOperations)[iop].rsvs;
}, "~N");
Clazz.overrideMethod(c$, "getSiteMultiplicity", 
function(pt){
return this.spaceGroup.getSiteMultiplicity(pt, this.unitCell);
}, "JU.P3");
Clazz.overrideMethod(c$, "getSpaceGroupName", 
function(){
return (this.spaceGroup != null ? this.spaceGroup.getName() : this.symmetryInfo != null ? this.symmetryInfo.sgName : this.unitCell != null && this.unitCell.name.length > 0 ? "cell=" + this.unitCell.name : "");
});
Clazz.overrideMethod(c$, "getSpaceGroupNameType", 
function(type){
return (this.spaceGroup == null ? null : this.spaceGroup.getNameType(type, this));
}, "~S");
Clazz.overrideMethod(c$, "getLatticeType", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.latticeType : this.spaceGroup == null ? 'P' : this.spaceGroup.latticeType);
});
Clazz.overrideMethod(c$, "getIntTableNumber", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableNo : this.spaceGroup == null ? null : this.spaceGroup.itaNumber);
});
Clazz.overrideMethod(c$, "getIntTableIndex", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableIndex : this.spaceGroup == null ? null : this.spaceGroup.getItaIndex());
});
Clazz.overrideMethod(c$, "getIntTableTransform", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableTransform : this.spaceGroup == null ? null : this.spaceGroup.itaTransform);
});
Clazz.overrideMethod(c$, "getIntTableNumberFull", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableJmolID : this.spaceGroup == null ? null : this.spaceGroup.jmolId != null ? this.spaceGroup.jmolId : this.spaceGroup.itaNumber);
});
Clazz.overrideMethod(c$, "getCoordinatesAreFractional", 
function(){
return this.symmetryInfo == null || this.symmetryInfo.coordinatesAreFractional;
});
Clazz.overrideMethod(c$, "getCellRange", 
function(){
return this.symmetryInfo == null ? null : this.symmetryInfo.cellRange;
});
Clazz.overrideMethod(c$, "getSymmetryInfoStr", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.infoStr;
if (this.spaceGroup == null) return "";
(this.symmetryInfo =  new JS.SymmetryInfo()).setSymmetryInfoFromModelkit(this.spaceGroup);
return this.symmetryInfo.infoStr;
});
Clazz.overrideMethod(c$, "getSpaceGroupOperationCount", 
function(){
return (this.symmetryInfo != null && this.symmetryInfo.symmetryOperations != null ? this.symmetryInfo.symmetryOperations.length : this.spaceGroup != null ? (this.spaceGroup.finalOperations != null ? this.spaceGroup.finalOperations.length : this.spaceGroup.operationCount) : 0);
});
Clazz.overrideMethod(c$, "getSymmetryOperations", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.symmetryOperations;
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull(true, false, true);
this.spaceGroup.setFinalOperations();
return this.spaceGroup.finalOperations;
});
Clazz.overrideMethod(c$, "getAdditionalOperationsCount", 
function(){
return (this.symmetryInfo != null && this.symmetryInfo.symmetryOperations != null && this.symmetryInfo.getAdditionalOperations() != null ? this.symmetryInfo.additionalOperations.length : this.spaceGroup != null && this.spaceGroup.finalOperations != null ? this.spaceGroup.getAdditionalOperationsCount() : 0);
});
Clazz.overrideMethod(c$, "getAdditionalOperations", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.getAdditionalOperations();
this.getSymmetryOperations();
return this.spaceGroup.getAdditionalOperations();
});
Clazz.overrideMethod(c$, "isSimple", 
function(){
return (this.spaceGroup == null && (this.symmetryInfo == null || this.symmetryInfo.symmetryOperations == null));
});
Clazz.overrideMethod(c$, "haveUnitCell", 
function(){
return (this.unitCell != null);
});
Clazz.overrideMethod(c$, "setUnitCellFromParams", 
function(unitCellParams, setRelative, slop){
if (unitCellParams == null) unitCellParams =  Clazz.newFloatArray(-1, [1, 1, 1, 90, 90, 90]);
this.unitCell = JS.UnitCell.fromParams(unitCellParams, setRelative, slop);
return this;
}, "~A,~B,~N");
Clazz.overrideMethod(c$, "unitCellEquals", 
function(uc2){
return ((uc2)).unitCell.isSameAs(this.unitCell.getF2C());
}, "J.api.SymmetryInterface");
Clazz.overrideMethod(c$, "isSymmetryCell", 
function(sym){
var uc = ((sym)).unitCell;
var myf2c = (!uc.isStandard() ? null : (this.symmetryInfo != null ? this.symmetryInfo.spaceGroupF2C : this.unitCell.getF2C()));
var ret = uc.isSameAs(myf2c);
if (this.symmetryInfo != null) {
if (this.symmetryInfo.setIsCurrentCell(ret)) {
this.setUnitCellFromParams(this.symmetryInfo.spaceGroupF2CParams, false, NaN);
}}return ret;
}, "J.api.SymmetryInterface");
Clazz.overrideMethod(c$, "getUnitCellState", 
function(){
if (this.unitCell == null) return "";
return this.unitCell.getState();
});
Clazz.overrideMethod(c$, "getMoreInfo", 
function(){
return this.unitCell.moreInfo;
});
Clazz.overrideMethod(c$, "initializeOrientation", 
function(mat){
this.unitCell.initOrientation(mat);
}, "JU.M3");
Clazz.overrideMethod(c$, "unitize", 
function(ptFrac){
this.unitCell.unitize(ptFrac);
}, "JU.T3");
Clazz.overrideMethod(c$, "toUnitCell", 
function(pt, offset){
this.unitCell.toUnitCell(pt, offset);
}, "JU.T3,JU.T3");
Clazz.overrideMethod(c$, "toSupercell", 
function(fpt){
return this.unitCell.toSupercell(fpt);
}, "JU.P3");
Clazz.overrideMethod(c$, "toFractional", 
function(pt, ignoreOffset){
if (!this.$isBio) this.unitCell.toFractional(pt, ignoreOffset);
}, "JU.T3,~B");
Clazz.overrideMethod(c$, "toCartesian", 
function(pt, ignoreOffset){
if (!this.$isBio) this.unitCell.toCartesian(pt, ignoreOffset);
}, "JU.T3,~B");
Clazz.overrideMethod(c$, "getUnitCellParams", 
function(){
return this.unitCell.getUnitCellParams();
});
Clazz.overrideMethod(c$, "getUnitCellAsArray", 
function(vectorsOnly){
return this.unitCell.getUnitCellAsArray(vectorsOnly);
}, "~B");
Clazz.overrideMethod(c$, "getUnitCellVerticesNoOffset", 
function(){
return this.unitCell.getVertices();
});
Clazz.overrideMethod(c$, "getCartesianOffset", 
function(){
return this.unitCell.getCartesianOffset();
});
Clazz.overrideMethod(c$, "getFractionalOffset", 
function(){
return this.unitCell.getFractionalOffset();
});
Clazz.overrideMethod(c$, "setOffsetPt", 
function(pt){
this.unitCell.setOffset(pt);
}, "JU.T3");
Clazz.overrideMethod(c$, "setOffset", 
function(nnn){
var pt =  new JU.P3();
JU.SimpleUnitCell.ijkToPoint3f(nnn, pt, 0, 0);
this.unitCell.setOffset(pt);
}, "~N");
Clazz.overrideMethod(c$, "getUnitCellMultiplier", 
function(){
return this.unitCell.getUnitCellMultiplier();
});
Clazz.overrideMethod(c$, "getUnitCellMultiplied", 
function(){
var uc = this.unitCell.getUnitCellMultiplied();
if (uc === this.unitCell) return this;
var s =  new JS.Symmetry();
s.unitCell = uc;
return s;
});
Clazz.overrideMethod(c$, "getCanonicalCopy", 
function(scale, withOffset){
return this.unitCell.getCanonicalCopy(scale, withOffset);
}, "~N,~B");
Clazz.overrideMethod(c$, "getUnitCellInfoType", 
function(infoType){
return this.unitCell.getInfo(infoType);
}, "~N");
Clazz.overrideMethod(c$, "getUnitCellInfo", 
function(scaled){
return (this.unitCell == null ? null : this.unitCell.dumpInfo(false, scaled));
}, "~B");
Clazz.overrideMethod(c$, "isSlab", 
function(){
return this.unitCell.isSlab();
});
Clazz.overrideMethod(c$, "isPolymer", 
function(){
return this.unitCell.isPolymer();
});
Clazz.defineMethod(c$, "getUnitCellVectors", 
function(){
return this.unitCell.getUnitCellVectors();
});
Clazz.overrideMethod(c$, "getUnitCell", 
function(oabc, setRelative, name){
if (oabc == null) return null;
this.unitCell = JS.UnitCell.fromOABC(oabc, setRelative);
if (name != null) this.unitCell.name = name;
return this;
}, "~A,~B,~S");
Clazz.overrideMethod(c$, "isSupercell", 
function(){
return this.unitCell.isSupercell();
});
Clazz.overrideMethod(c$, "notInCentroid", 
function(modelSet, bsAtoms, minmax){
try {
var bsDelete =  new JU.BS();
var iAtom0 = bsAtoms.nextSetBit(0);
var molecules = modelSet.getMolecules();
var moleculeCount = molecules.length;
var atoms = modelSet.at;
var isOneMolecule = (molecules[moleculeCount - 1].firstAtomIndex == modelSet.am[atoms[iAtom0].mi].firstAtomIndex);
var center =  new JU.P3();
var centroidPacked = (minmax[6] == 1);
nextMol : for (var i = moleculeCount; --i >= 0 && bsAtoms.get(molecules[i].firstAtomIndex); ) {
var bs = molecules[i].atomList;
center.set(0, 0, 0);
var n = 0;
for (var j = bs.nextSetBit(0); j >= 0; j = bs.nextSetBit(j + 1)) {
if (isOneMolecule || centroidPacked) {
center.setT(atoms[j]);
if (this.isNotCentroid(center, 1, minmax, centroidPacked)) {
if (isOneMolecule) bsDelete.set(j);
} else if (!isOneMolecule) {
continue nextMol;
}} else {
center.add(atoms[j]);
n++;
}}
if (centroidPacked || n > 0 && this.isNotCentroid(center, n, minmax, false)) bsDelete.or(bs);
}
return bsDelete;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "JM.ModelSet,JU.BS,~A");
Clazz.defineMethod(c$, "isNotCentroid", 
function(center, n, minmax, centroidPacked){
center.scale(1 / n);
this.toFractional(center, false);
if (centroidPacked) return (center.x + 0.000005 <= minmax[0] || center.x - 0.000005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y - 0.000005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z - 0.000005 > minmax[5]);
return (center.x + 0.000005 <= minmax[0] || center.x + 0.00005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y + 0.00005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z + 0.00005 > minmax[5]);
}, "JU.P3,~N,~A,~B");
Clazz.defineMethod(c$, "getDesc", 
function(modelSet){
if (modelSet == null) {
return (JS.Symmetry.nullDesc == null ? (JS.Symmetry.nullDesc = (J.api.Interface.getInterface("JS.SymmetryDesc", null, "modelkit"))) : JS.Symmetry.nullDesc);
}return (this.desc == null ? (this.desc = (J.api.Interface.getInterface("JS.SymmetryDesc", modelSet.vwr, "eval"))) : this.desc).set(modelSet);
}, "JM.ModelSet");
Clazz.overrideMethod(c$, "getSymmetryInfoAtom", 
function(modelSet, iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList){
return this.getDesc(modelSet).getSymopInfo(iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList);
}, "JM.ModelSet,~N,~S,~N,JU.P3,JU.P3,JU.P3,~S,~N,~N,~N,~N,~A");
Clazz.overrideMethod(c$, "getSpaceGroupInfo", 
function(modelSet, sgName, modelIndex, isFull, cellParams){
var isForModel = (sgName == null);
if (sgName == null) {
var info = modelSet.getModelAuxiliaryInfo(modelSet.vwr.am.cmi);
if (info != null) sgName = info.get("spaceGroup");
}var cellInfo = null;
if (cellParams != null) {
cellInfo =  new JS.Symmetry().setUnitCellFromParams(cellParams, false, NaN);
}return this.getDesc(modelSet).getSpaceGroupInfo(this, modelIndex, sgName, 0, null, null, null, 0, -1, isFull, isForModel, 0, cellInfo, null);
}, "JM.ModelSet,~S,~N,~B,~A");
Clazz.overrideMethod(c$, "getV0abc", 
function(def, retMatrix){
var t = null;
{
t = (def && def[0] ? def[0] : null);
}return ((t != null ? Clazz.instanceOf(t,"JU.T3") : Clazz.instanceOf(def,Array)) ? def : JS.UnitCell.getMatrixAndUnitCell(this.unitCell, def, retMatrix));
}, "~O,JU.M4");
Clazz.overrideMethod(c$, "getQuaternionRotation", 
function(abc){
return (this.unitCell == null ? null : this.unitCell.getQuaternionRotation(abc));
}, "~S");
Clazz.overrideMethod(c$, "getFractionalOrigin", 
function(){
return this.unitCell.getFractionalOrigin();
});
Clazz.overrideMethod(c$, "getState", 
function(ms, modelIndex, commands){
var isAssigned = (ms.getInfo(modelIndex, "spaceGroupAssigned") != null);
var pt = this.getFractionalOffset();
var loadUC = false;
if (pt != null && (pt.x != 0 || pt.y != 0 || pt.z != 0)) {
commands.append("; set unitcell ").append(JU.Escape.eP(pt));
loadUC = true;
}var ptm = this.getUnitCellMultiplier();
if (ptm != null) {
commands.append("; set unitcell ").append(JU.SimpleUnitCell.escapeMultiplier(ptm));
loadUC = true;
}var sg = ms.getInfo(modelIndex, "spaceGroup");
if (isAssigned && sg != null) {
var cmd = "\n UNITCELL " + JU.Escape.e(ms.getUnitCell(modelIndex).getUnitCellVectors());
commands.append(cmd);
commands.append("\n MODELKIT SPACEGROUP " + JU.PT.esc(sg));
commands.append(cmd);
loadUC = true;
}return loadUC;
}, "JM.ModelSet,~N,JU.SB");
Clazz.overrideMethod(c$, "getIterator", 
function(vwr, atom, bsAtoms, radius){
return (J.api.Interface.getInterface("JS.UnitCellIterator", vwr, "script")).set(this, atom, vwr.ms.at, bsAtoms, radius);
}, "JV.Viewer,JM.Atom,JU.BS,~N");
Clazz.overrideMethod(c$, "toFromPrimitive", 
function(toPrimitive, type, oabc, primitiveToCrystal){
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromOABC(oabc, false);
return this.unitCell.toFromPrimitive(toPrimitive, type, oabc, primitiveToCrystal);
}, "~B,~S,~A,JU.M3");
Clazz.overrideMethod(c$, "generateCrystalClass", 
function(pt00){
if (this.symmetryInfo == null || !this.symmetryInfo.isCurrentCell) return null;
var ops = this.getSymmetryOperations();
var lst =  new JU.Lst();
var isRandom = (pt00 == null);
var rand1 = 0;
var rand2 = 0;
var rand3 = 0;
var pt0;
if (isRandom) {
rand1 = 2.718281828459045;
rand2 = 3.141592653589793;
rand3 = Math.log10(2000);
pt0 = JU.P3.new3(rand1 + 1, rand2 + 2, rand3 + 3);
} else {
pt0 = JU.P3.newP(pt00);
}if (ops == null || this.unitCell == null) {
lst.addLast(pt0);
} else {
this.unitCell.toFractional(pt0, true);
var pt1 = null;
var pt2 = null;
if (isRandom) {
pt1 = JU.P3.new3(rand2 + 4, rand3 + 5, rand1 + 6);
this.unitCell.toFractional(pt1, true);
pt2 = JU.P3.new3(rand3 + 7, rand1 + 8, rand2 + 9);
this.unitCell.toFractional(pt2, true);
}var bspt =  new J.bspt.Bspt(3, 0);
var iter = bspt.allocateCubeIterator();
var pt =  new JU.P3();
out : for (var i = ops.length; --i >= 0; ) {
ops[i].rotate2(pt0, pt);
iter.initialize(pt, 0.001, false);
if (iter.hasMoreElements()) continue out;
var ptNew = JU.P3.newP(pt);
lst.addLast(ptNew);
bspt.addTuple(ptNew);
if (isRandom) {
if (pt2 != null) {
ops[i].rotate2(pt2, pt);
lst.addLast(JU.P3.newP(pt));
}if (pt1 != null) {
ops[i].rotate2(pt1, pt);
lst.addLast(JU.P3.newP(pt));
}}}
for (var j = lst.size(); --j >= 0; ) {
pt = lst.get(j);
if (isRandom) pt.scale(0.5);
this.unitCell.toCartesian(pt, true);
}
}return lst;
}, "JU.P3");
Clazz.overrideMethod(c$, "calculateCIPChiralityForAtoms", 
function(vwr, bsAtoms){
vwr.setCursor(3);
var cip = this.getCIPChirality(vwr);
var dataClass = (vwr.getBoolean(603979960) ? "CIPData" : "CIPDataTracker");
var data = (J.api.Interface.getInterface("JS." + dataClass, vwr, "script")).set(vwr, bsAtoms);
data.setRule6Full(vwr.getBoolean(603979823));
cip.getChiralityForAtoms(data);
vwr.setCursor(0);
}, "JV.Viewer,JU.BS");
Clazz.overrideMethod(c$, "calculateCIPChiralityForSmiles", 
function(vwr, smiles){
vwr.setCursor(3);
var cip = this.getCIPChirality(vwr);
var data = (J.api.Interface.getInterface("JS.CIPDataSmiles", vwr, "script")).setAtomsForSmiles(vwr, smiles);
cip.getChiralityForAtoms(data);
vwr.setCursor(0);
return data.getSmilesChiralityArray();
}, "JV.Viewer,~S");
Clazz.defineMethod(c$, "getCIPChirality", 
function(vwr){
return (this.cip == null ? (this.cip = (J.api.Interface.getInterface("JS.CIPChirality", vwr, "script"))) : this.cip);
}, "JV.Viewer");
Clazz.overrideMethod(c$, "getUnitCellInfoMap", 
function(){
return (this.unitCell == null ? null : this.unitCell.getInfo());
});
Clazz.overrideMethod(c$, "setUnitCell", 
function(uc){
this.unitCell = JS.UnitCell.cloneUnitCell((uc).unitCell);
}, "J.api.SymmetryInterface");
Clazz.overrideMethod(c$, "findSpaceGroup", 
function(vwr, atoms, xyzList, unitCellParams, origin, oabc, flags){
return (J.api.Interface.getInterface("JS.SpaceGroupFinder", vwr, "eval")).findSpaceGroup(vwr, atoms, xyzList, unitCellParams, origin, oabc, this, flags);
}, "JV.Viewer,JU.BS,~S,~A,JU.T3,~A,~N");
Clazz.overrideMethod(c$, "setSpaceGroupName", 
function(name){
this.symmetryInfo = null;
if (this.spaceGroup != null) this.spaceGroup.setName(name);
}, "~S");
Clazz.overrideMethod(c$, "setSpaceGroupTo", 
function(sg){
this.symmetryInfo = null;
if (Clazz.instanceOf(sg,"JS.SpaceGroup")) {
this.spaceGroup = sg;
} else {
this.spaceGroup = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(sg.toString());
}}, "~O");
Clazz.overrideMethod(c$, "removeDuplicates", 
function(ms, bs, highPrec){
var uc = this.unitCell;
var atoms = ms.at;
var occs = ms.occupancies;
var haveOccupancies = (occs != null);
var unitized =  new Array(bs.length());
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var pt = unitized[i] = JU.P3.newP(atoms[i]);
uc.toFractional(pt, false);
if (highPrec) uc.unitizeRnd(pt);
 else uc.unitize(pt);
}
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var a = atoms[i];
var pt = unitized[i];
var type = a.getAtomicAndIsotopeNumber();
var occ = (haveOccupancies ? occs[i] : 0);
for (var j = bs.nextSetBit(i + 1); j >= 0; j = bs.nextSetBit(j + 1)) {
var b = atoms[j];
if (type != b.getAtomicAndIsotopeNumber() || (haveOccupancies && occ != occs[j])) continue;
var pt2 = unitized[j];
if (pt.distanceSquared(pt2) < 1.96E-6) {
bs.clear(j);
}}
}
return bs;
}, "JM.ModelSet,JU.BS,~B");
Clazz.overrideMethod(c$, "getEquivPoints", 
function(pts, pt, flags){
var ops = this.getSymmetryOperations();
return (ops == null || this.unitCell == null ? null : this.unitCell.getEquivPoints(pt, flags, ops, pts == null ?  new JU.Lst() : pts, 0, 0, 0));
}, "JU.Lst,JU.P3,~S");
Clazz.overrideMethod(c$, "getEquivPointList", 
function(pts, nInitial, flags, opsCtr){
var ops = (opsCtr == null ? this.getSymmetryOperations() : opsCtr);
var newPt = (flags.indexOf("newpt") >= 0);
var zapped = (flags.indexOf("zapped") >= 0);
var n = pts.size();
var tofractional = (flags.indexOf("tofractional") >= 0);
if (flags.indexOf("fromfractional") < 0) {
for (var i = 0; i < pts.size(); i++) {
this.toFractional(pts.get(i), false);
}
}flags += ",fromfractional,tofractional";
var check0 = (nInitial > 0 ? 0 : n);
var allPoints = (nInitial == n);
var n0 = (nInitial > 0 ? nInitial : n);
if (allPoints) {
nInitial--;
n0--;
}if (zapped) n0 = 0;
var p0 = (nInitial > 0 ? pts.get(nInitial) : null);
var dup0 = (opsCtr == null ? n0 : check0);
if (ops != null || this.unitCell != null) {
for (var i = nInitial; i < n; i++) {
this.unitCell.getEquivPoints(pts.get(i), flags, ops, pts, check0, n0, dup0);
}
}if (!zapped && (pts.size() == nInitial || pts.get(nInitial) !== p0 || allPoints || newPt)) n--;
for (var i = n - nInitial; --i >= 0; ) pts.removeItemAt(nInitial);

if (!tofractional) {
for (var i = pts.size(); --i >= nInitial; ) this.toCartesian(pts.get(i), false);

}}, "JU.Lst,~N,~S,~A");
Clazz.overrideMethod(c$, "getInvariantSymops", 
function(pt, v0){
var ops = this.getSymmetryOperations();
if (ops == null) return  Clazz.newIntArray (0, 0);
var bs =  new JU.BS();
var p =  new JU.P3();
var p0 =  new JU.P3();
var nops = ops.length;
for (var i = 1; i < nops; i++) {
p.setT(pt);
this.unitCell.toFractional(p, false);
this.unitCell.unitize(p);
p0.setT(p);
ops[i].rotTrans(p);
this.unitCell.unitize(p);
if (p0.distanceSquared(p) < 1.96E-6) {
bs.set(i);
}}
var ret =  Clazz.newIntArray (bs.cardinality(), 0);
if (v0 != null && ret.length != v0.length) return null;
for (var k = 0, i = 1; i < nops; i++) {
var isOK = bs.get(i);
if (isOK) {
if (v0 != null && v0[k] != i + 1) return null;
ret[k++] = i + 1;
}}
return ret;
}, "JU.P3,~A");
Clazz.overrideMethod(c$, "getWyckoffPosition", 
function(vwr, p, letter){
if (this.unitCell == null) return "";
var sg = this.spaceGroup;
if (sg == null && this.symmetryInfo != null) {
sg = JS.SpaceGroup.determineSpaceGroupN(this.symmetryInfo.sgName);
if (sg == null) sg = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(this.symmetryInfo.intlTableJmolID);
}if (sg == null || sg.itaNumber == null) {
return "?";
}if (p == null) {
p = JU.P3.new3(0.53, 0.20, 0.16);
} else {
p = JU.P3.newP(p);
this.unitCell.toFractional(p, false);
this.unitCell.unitize(p);
}if (JS.Symmetry.wyckoffFinder == null) {
JS.Symmetry.wyckoffFinder = J.api.Interface.getInterface("JS.WyckoffFinder", null, "symmetry");
}try {
var w = JS.Symmetry.wyckoffFinder.getWyckoffFinder(vwr, sg);
var withMult = (letter != null && letter.charAt(0) == 'M');
if (withMult) {
letter = (letter.length == 1 ? null : letter.substring(1));
}var mode = (letter == null ? -1 : letter.equalsIgnoreCase("coord") ? -2 : letter.equalsIgnoreCase("coords") ? -3 : letter.endsWith("*") ? (letter.charAt(0)).charCodeAt(0) : 0);
if (mode != 0) {
return (w == null ? "?" : w.getInfo(this.unitCell, p, mode, withMult));
}if (w.findPositionFor(p, letter) == null) return null;
this.unitCell.toCartesian(p, false);
return p;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
return (letter == null ? "?" : null);
} else {
throw e;
}
}
}, "JV.Viewer,JU.P3,~S");
Clazz.overrideMethod(c$, "getTransform", 
function(fracA, fracB, best){
return this.getDesc(null).getTransform(this.unitCell, this.getSymmetryOperations(), fracA, fracB, best);
}, "JU.P3,JU.P3,~B");
Clazz.overrideMethod(c$, "isWithinUnitCell", 
function(pt, x, y, z){
return this.unitCell.isWithinUnitCell(x, y, z, pt);
}, "JU.P3,~N,~N,~N");
Clazz.overrideMethod(c$, "checkPeriodic", 
function(pt){
return this.unitCell.checkPeriodic(pt);
}, "JU.P3");
Clazz.overrideMethod(c$, "staticConvertOperation", 
function(xyz, matrix){
return (matrix == null ? JS.SymmetryOperation.stringToMatrix(xyz) : JS.SymmetryOperation.getXYZFromMatrixFrac(matrix, false, false, false, true));
}, "~S,JU.M4");
Clazz.overrideMethod(c$, "getSubgroupJSON", 
function(vwr, itaFrom, itaTo, index1, index2){
var allSubsMap = (itaTo < 0);
var asIntArray = (itaTo == 0 && index1 == 0);
var asSSIntArray = (itaTo == 0 && index1 < 0);
var isIndexMap = (itaTo == 0 && index1 > 0 && index2 < 0);
var isIndexTStr = (itaTo == 0 && index1 > 0 && index2 > 0);
var isWhereList = (itaTo > 0 && index1 < 0);
var isWhereMap = (itaTo > 0 && index1 > 0 && index2 < 0);
var isWhereTStr = (itaTo > 0 && index1 > 0 && index2 > 0);
try {
var o = this.getSpaceGroupJSON(vwr, "subgroups", "map", itaFrom);
var ithis = 0;
if (o != null) {
if (allSubsMap) return o;
if (asIntArray || asSSIntArray) {
var list = o.get("subgroups");
var n = list.size();
var groups = (asIntArray ?  Clazz.newIntArray (n, 0) : null);
var bs = (asSSIntArray ?  new JU.BS() : null);
for (var i = n; --i >= 0; ) {
o = list.get(i);
var isub = (o.get("subgroup")).intValue();
if (asSSIntArray) {
bs.set(isub);
continue;
}var subIndex = (o.get("subgroupIndex")).intValue();
var trType = "k".equals(o.get("trType")) ? 2 : 1;
var subType = (trType == 1 ? o.get("trSubtype") : "");
var det = (o.get("det")).doubleValue();
var idet = Clazz.doubleToInt(det < 1 ? -1 / det : det);
if (subType.equals("ct")) trType = 3;
 else if (subType.equals("eu")) trType = 4;
var ntrm = (o.get("trm")).size();
groups[i] =  Clazz.newIntArray(-1, [isub, ntrm, subIndex, idet, trType]);
}
if (asSSIntArray) {
var a =  Clazz.newIntArray (bs.cardinality(), 0);
for (var p = 0, i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
a[p++] = i;
}
return a;
}return groups;
}var list = o.get("subgroups");
var i0 = 0;
var n = list.size();
if (isIndexMap || isIndexTStr) {
if (index1 > n) {
throw  new ArrayIndexOutOfBoundsException("no map.subgroups[" + index1 + "]!");
}i0 = index1 - 1;
if (isIndexMap) return list.get(i0);
n = index1;
}var whereList = (isWhereList ?  new JU.Lst() : null);
for (var i = i0; i < n; i++) {
o = list.get(i);
var isub = (o.get("subgroup")).intValue();
if (!isIndexTStr && isub != itaTo) continue;
if (++ithis == index1) {
if (isWhereMap) return o;
} else if (isWhereTStr) {
continue;
}if (isWhereList) {
whereList.addLast(o);
continue;
}var trms = o.get("trm");
n = trms.size();
if (index2 < 1 || index2 > n) return null;
return (trms.get(index2 - 1)).substring(2);
}
if (isWhereList && !whereList.isEmpty()) {
return whereList;
}}if (index1 == 0) return null;
if (isWhereTStr && ithis > 0) {
throw  new ArrayIndexOutOfBoundsException("only " + ithis + " maximal subgroup information for " + itaFrom + ">>" + itaTo + "!");
}throw  new ArrayIndexOutOfBoundsException("no maximal subgroup information for " + itaFrom + ">>" + itaTo + "!");
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return e.getMessage();
} else {
throw e;
}
}
}, "JV.Viewer,~N,~N,~N,~N");
Clazz.overrideMethod(c$, "getSpaceGroupJSON", 
function(vwr, name, data, index){
var isSettings = name.equals("settings");
var isSubgroups = !isSettings && name.equals("subgroups");
var isThis = ((isSettings || isSubgroups) && index == -2147483648);
var s0 = (!isSettings && !isSubgroups ? name : isThis ? this.getSpaceGroupName() : "" + index);
try {
var itno;
var tm = null;
var isTM;
var isInt;
var sgname;
if (isSettings || isSubgroups) {
isTM = false;
isInt = true;
sgname = (isSettings ? data : null);
if (isThis) {
itno = JU.PT.parseInt(this.getIntTableNumber());
if (isSettings) {
if (this.spaceGroup == null) {
var sg = this.symmetryInfo.getDerivedSpaceGroup();
if (sg == null) return  new java.util.Hashtable();
sgname = sg.jmolId;
} else {
sgname = this.getIntTableNumberFull();
}}} else {
itno = index;
}} else {
sgname = data;
var pt = sgname.indexOf("(");
if (pt < 0) pt = sgname.indexOf(":");
isTM = (pt >= 0 && sgname.indexOf(",") > pt);
if (isTM) {
tm = sgname.substring(pt + 1, sgname.length - (sgname.endsWith(")") ? 1 : 0));
sgname = sgname.substring(0, pt);
isThis = true;
}itno = (sgname.equalsIgnoreCase("ALL") ? 0 : JU.PT.parseInt(sgname));
isInt = (itno != -2147483648);
pt = sgname.indexOf('.');
if (!isTM && isInt && index == 0 && pt > 0) {
index = JU.PT.parseInt(sgname.substring(pt + 1));
sgname = sgname.substring(0, pt);
}}if (isInt && (itno > 230 || (isSettings ? itno < 1 : itno < 0))) throw  new ArrayIndexOutOfBoundsException(itno);
if (isSubgroups) {
if (JS.Symmetry.itaSubData == null) JS.Symmetry.itaSubData =  new Array(230);
var resource = JS.Symmetry.itaSubData[itno - 1];
if (resource == null) JS.Symmetry.itaSubData[itno - 1] = resource = this.getResource(vwr, "sg/json/sub_" + itno + ".json");
if (resource != null) {
return resource;
}} else if (isSettings || name.equalsIgnoreCase("ITA")) {
if (itno == 0) {
if (JS.Symmetry.allDataITA == null) JS.Symmetry.allDataITA = this.getResource(vwr, "sg/json/ita_all.json");
return JS.Symmetry.allDataITA;
}if (JS.Symmetry.itaData == null) JS.Symmetry.itaData =  new Array(230);
var resource = JS.Symmetry.itaData[itno - 1];
if (resource == null) JS.Symmetry.itaData[itno - 1] = resource = this.getResource(vwr, "sg/json/ita_" + itno + ".json");
if (resource != null) {
if (index == 0 && tm == null) return resource;
var its = resource.get("its");
if (its != null) {
if (isSettings && !isThis) {
return its;
}var n = its.size();
var i0 = (isInt && !isThis ? index : n);
if (i0 > n) return null;
var map = null;
for (var i = i0; --i >= 0; ) {
map = its.get(i);
if (i == index - 1 || (tm == null ? sgname.equals(map.get("jmolId")) : tm.equals(map.get("trm")))) {
System.out.println(tm);
System.out.println(map);
if (!map.containsKey("more")) {
return map;
}break;
}map = null;
}
if (map != null) {
return JS.SpaceGroup.fillMoreData(map, map.get("clegId"), itno, its.get(0));
}}}} else if (name.equalsIgnoreCase("AFLOW") && tm == null) {
if (JS.Symmetry.aflowStructures == null) JS.Symmetry.aflowStructures = this.getResource(vwr, "sg/json/aflow_structures.json");
if (itno == 0) return JS.Symmetry.aflowStructures;
if (itno == -2147483648) {
var start = null;
if (sgname.endsWith("*")) {
start =  new JU.Lst();
sgname = sgname.substring(0, sgname.length - 1);
}for (var j = 1; j <= 230; j++) {
var list = JS.Symmetry.aflowStructures.get("" + j);
for (var i = 0, n = list.size(); i < n; i++) {
var id = list.get(i);
if (start != null && id.startsWith(sgname)) {
start.addLast("=aflowlib/" + j + "." + (i + 1) + "\t" + id);
} else if (id.equalsIgnoreCase(sgname)) {
return j + "." + (i + 1);
}}
}
return (start != null && start.size() > 0 ? start : null);
}var adata = JS.Symmetry.aflowStructures.get("" + sgname);
if (index <= adata.size()) {
return (index == 0 ? adata : adata.get(index - 1));
}}if (isThis) return  new java.util.Hashtable();
throw  new IllegalArgumentException(s0);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return e.getMessage();
} else {
throw e;
}
}
}, "JV.Viewer,~S,~O,~N");
Clazz.defineMethod(c$, "getResource", 
function(vwr, resource){
try {
var r = JV.FileManager.getBufferedReaderForResource(vwr, this, "JS/", resource);
var data =  new Array(1);
if (JU.Rdr.readAllAsString(r, 2147483647, false, data, 0)) {
return  new JU.JSJSONParser().parse(data[0], true);
}} catch (e) {
System.err.println(e.getMessage());
}
return null;
}, "JV.Viewer,~S");
Clazz.overrideMethod(c$, "getCellWeight", 
function(pt){
return this.unitCell.getCellWeight(pt);
}, "JU.P3");
Clazz.overrideMethod(c$, "getPrecision", 
function(){
return (this.unitCell == null ? NaN : this.unitCell.getPrecision());
});
Clazz.overrideMethod(c$, "fixUnitCell", 
function(params){
return JS.UnitCell.createCompatibleUnitCell(this.spaceGroup, params, null, true);
}, "~A");
Clazz.overrideMethod(c$, "staticGetTransformABC", 
function(transform, normalize){
return JS.SymmetryOperation.getTransformABC(transform, normalize);
}, "~O,~B");
Clazz.defineMethod(c$, "setCartesianOffset", 
function(origin){
this.unitCell.setCartesianOffset(origin);
}, "JU.T3");
Clazz.defineMethod(c$, "setSymmetryInfoFromFile", 
function(ms, modelIndex, unitCellParams){
var modelAuxiliaryInfo = ms.getModelAuxiliaryInfo(modelIndex);
this.symmetryInfo =  new JS.SymmetryInfo();
var params = this.symmetryInfo.setSymmetryInfoFromFile(modelAuxiliaryInfo, unitCellParams);
if (params != null) {
this.setUnitCellFromParams(params, modelAuxiliaryInfo.containsKey("jmolData"), NaN);
this.unitCell.moreInfo = modelAuxiliaryInfo.get("moreUnitCellInfo");
modelAuxiliaryInfo.put("infoUnitCell", this.getUnitCellAsArray(false));
this.setOffsetPt(modelAuxiliaryInfo.get("unitCellOffset"));
var matUnitCellOrientation = modelAuxiliaryInfo.get("matUnitCellOrientation");
if (matUnitCellOrientation != null) this.initializeOrientation(matUnitCellOrientation);
var s = this.symmetryInfo.strSUPERCELL;
if (s != null) {
var oabc = this.unitCell.getUnitCellVectors();
oabc[0] =  new JU.P3();
ms.setModelCagePts(modelIndex, oabc, "conventional");
}if (JU.Logger.debugging) JU.Logger.debug("symmetryInfos[" + modelIndex + "]:\n" + this.unitCell.dumpInfo(true, true));
}}, "JM.ModelSet,~N,~A");
Clazz.defineMethod(c$, "transformUnitCell", 
function(trm){
if (trm == null) {
trm = JS.UnitCell.toTrm(this.spaceGroup.itaTransform, null);
}var trmInv = JU.M4.newM4(trm);
trmInv.invert();
var oabc = this.getUnitCellVectors();
for (var i = 1; i <= 3; i++) {
this.toFractional(oabc[i], true);
trmInv.rotate(oabc[i]);
this.toCartesian(oabc[i], true);
}
var o =  new JU.P3();
trm.getTranslation(o);
this.toCartesian(o, true);
oabc[0].add(o);
this.unitCell = JS.UnitCell.fromOABC(oabc, false);
}, "JU.M4");
Clazz.overrideMethod(c$, "getITASettingValue", 
function(vwr, itaIndex, key){
var o = this.getSpaceGroupJSON(vwr, "ITA", itaIndex, 0);
return (Clazz.instanceOf(o,"java.util.Map") ? (o).get(key) : o);
}, "JV.Viewer,~S,~S");
Clazz.overrideMethod(c$, "staticCleanTransform", 
function(tr){
return JS.SymmetryOperation.getTransformABC(JS.UnitCell.toTrm(tr, null), true);
}, "~S");
Clazz.overrideMethod(c$, "replaceTransformMatrix", 
function(trm){
var trm0 = this.transformMatrix;
this.transformMatrix = trm;
return trm0;
}, "JU.M4");
Clazz.overrideMethod(c$, "getUnitCellDisplayName", 
function(){
var name = (this.symmetryInfo != null ? this.symmetryInfo.getDisplayName(this) : this.spaceGroup != null ? this.spaceGroup.getDisplayName() : null);
return (name.length > 0 ? name : null);
});
Clazz.overrideMethod(c$, "staticToRationalXYZ", 
function(fPt, sep){
var s = JS.SymmetryOperation.fcoord(fPt, sep);
return (",".equals(sep) ? s : "(" + s + ")");
}, "JU.P3,~S");
Clazz.overrideMethod(c$, "getClegId", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.getDerivedSpaceGroup().clegId;
return this.spaceGroup.clegId;
});
Clazz.overrideMethod(c$, "getFinalOperationCount", 
function(){
this.setFinalOperations(3, null, null, -1, -1, false, null);
return this.spaceGroup.getOperationCount();
});
Clazz.overrideMethod(c$, "convertTransform", 
function(transform, trm){
if (transform == null) {
return this.staticGetTransformABC(trm, false);
}if (transform.equals("xyz")) {
return (trm == null ? null : JS.SymmetryOperation.getXYZFromMatrix(trm, false, false, false));
}if (trm == null) trm =  new JU.M4();
JS.UnitCell.getMatrixAndUnitCell(null, transform, trm);
return trm;
}, "~S,JU.M4");
c$.nullDesc = null;
c$.aflowStructures = null;
c$.itaData = null;
c$.itaSubData = null;
c$.allDataITA = null;
c$.wyckoffFinder = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
