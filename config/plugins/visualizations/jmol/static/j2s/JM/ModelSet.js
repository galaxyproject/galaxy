Clazz.declarePackage("JM");
Clazz.load(["JM.BondCollection"], "JM.ModelSet", ["java.util.Hashtable", "JU.A4", "$.AU", "$.BS", "$.Lst", "$.M3", "$.M4", "$.Measure", "$.P3", "$.P4", "$.PT", "$.Quat", "$.SB", "$.V3", "J.api.Interface", "J.atomdata.RadiusData", "J.bspt.Bspf", "J.c.PAL", "$.VDW", "JM.Atom", "$.AtomIteratorWithinModel", "$.AtomIteratorWithinModelSet", "$.HBond", "$.Model", "$.StateScript", "JS.ScriptCompiler", "JU.BSUtil", "$.BoxInfo", "$.Edge", "$.Elements", "$.Escape", "$.JmolMolecule", "$.Logger", "JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.haveBioModels = false;
this.bsSymmetry = null;
this.modelSetName = null;
this.am = null;
this.mc = 0;
this.unitCells = null;
this.haveUnitCells = false;
this.closest = null;
this.modelNumbers = null;
this.modelFileNumbers = null;
this.modelNumbersForAtomLabel = null;
this.modelNames = null;
this.frameTitles = null;
this.elementsPresent = null;
this.isXYZ = false;
this.modelSetProperties = null;
this.msInfo = null;
this.someModelsHaveSymmetry = false;
this.someModelsHaveAromaticBonds = false;
this.someModelsHaveFractionalCoordinates = false;
this.isBbcageDefault = false;
this.bboxModels = null;
this.bboxAtoms = null;
this.boxInfo = null;
this.stateScripts = null;
this.thisStateModel = 0;
this.vibrationSteps = null;
this.selectedMolecules = null;
this.showRebondTimes = true;
this.bsAll = null;
this.sm = null;
this.proteinStructureTainted = false;
this.htPeaks = null;
this.vOrientations = null;
this.ptTemp = null;
this.ptTemp1 = null;
this.ptTemp2 = null;
this.matTemp = null;
this.matInv = null;
this.mat4 = null;
this.mat4t = null;
this.vTemp = null;
this.defaultBBox = null;
this.haveJmolDataFrames = false;
this.echoShapeActive = false;
this.modelSetTypeName = null;
this.translations = null;
this.maxBondWarned = false;
Clazz.instantialize(this, arguments);}, JM, "ModelSet", JM.BondCollection);
Clazz.makeConstructor(c$, 
function(vwr, name){
Clazz.superConstructor (this, JM.ModelSet, []);
this.vwr = vwr;
this.modelSetName = name;
this.selectedMolecules =  new JU.BS();
this.stateScripts =  new JU.Lst();
this.boxInfo =  new JU.BoxInfo();
this.boxInfo.addBoundBoxPoint(JU.P3.new3(-10, -10, -10));
this.boxInfo.addBoundBoxPoint(JU.P3.new3(10, 10, 10));
this.am =  new Array(1);
this.modelNumbers =  Clazz.newIntArray (1, 0);
this.modelFileNumbers =  Clazz.newIntArray (1, 0);
this.modelNumbersForAtomLabel =  new Array(1);
this.modelNames =  new Array(1);
this.frameTitles =  new Array(1);
this.closest =  new Array(1);
this.ptTemp =  new JU.P3();
this.ptTemp1 =  new JU.P3();
this.ptTemp2 =  new JU.P3();
this.matTemp =  new JU.M3();
this.matInv =  new JU.M3();
this.mat4 =  new JU.M4();
this.mat4t =  new JU.M4();
this.vTemp =  new JU.V3();
this.setupBC();
}, "JV.Viewer,~S");
Clazz.defineMethod(c$, "getBoxInfo", 
function(){
return this.boxInfo;
});
Clazz.defineMethod(c$, "releaseModelSet", 
function(){
this.am = null;
this.mc = 0;
this.closest[0] = null;
this.am = null;
this.bsSymmetry = null;
this.bsAll = null;
this.unitCells = null;
this.releaseModelSetBC();
});
Clazz.defineMethod(c$, "getEchoStateActive", 
function(){
return this.echoShapeActive;
});
Clazz.defineMethod(c$, "setEchoStateActive", 
function(TF){
this.echoShapeActive = TF;
}, "~B");
Clazz.defineMethod(c$, "getModelSetTypeName", 
function(){
return this.modelSetTypeName;
});
Clazz.defineMethod(c$, "getModelNumberIndex", 
function(modelNumber, useModelNumber, doSetTrajectory){
if (useModelNumber) {
for (var i = 0; i < this.mc; i++) if (this.modelNumbers[i] == modelNumber || modelNumber < 1000000 && this.modelNumbers[i] == 1000000 + modelNumber) return i;

return -1;
}if (modelNumber < 1000000) return modelNumber;
for (var i = 0; i < this.mc; i++) if (this.modelFileNumbers[i] == modelNumber) {
if (doSetTrajectory && this.isTrajectory(i)) this.setTrajectory(i);
return i;
}
return -1;
}, "~N,~B,~B");
Clazz.defineMethod(c$, "getModelDataBaseName", 
function(bsAtoms){
for (var i = 0; i < this.mc; i++) {
if (bsAtoms.equals(this.am[i].bsAtoms)) return this.getInfo(i, "dbName");
}
return null;
}, "JU.BS");
Clazz.defineMethod(c$, "setTrajectory", 
function(modelIndex){
if (modelIndex >= 0 && this.isTrajectory(modelIndex) && this.at[this.am[modelIndex].firstAtomIndex].mi != modelIndex) this.trajectory.setModel(modelIndex);
}, "~N");
Clazz.defineMethod(c$, "getBitSetTrajectories", 
function(){
return (this.trajectory == null ? null : this.trajectory.getModelsSelected());
});
Clazz.defineMethod(c$, "setTrajectoryBs", 
function(bsModels){
if (this.trajectory != null) for (var i = 0; i < this.mc; i++) if (bsModels.get(i)) this.setTrajectory(i);

}, "JU.BS");
Clazz.defineMethod(c$, "morphTrajectories", 
function(m1, m2, f){
if (m1 >= 0 && m2 >= 0 && this.isTrajectory(m1) && this.isTrajectory(m2)) this.trajectory.morph(m1, m2, f);
}, "~N,~N,~N");
Clazz.defineMethod(c$, "getTranslation", 
function(iModel){
return (this.translations == null || iModel >= this.translations.length ? null : this.translations[iModel]);
}, "~N");
Clazz.defineMethod(c$, "translateModel", 
function(iModel, pt){
if (pt == null) {
var t = this.getTranslation(iModel);
if (t == null) return;
pt = JU.P3.newP(t);
pt.scale(-1);
this.translateModel(iModel, pt);
this.translations[iModel] = null;
return;
}if (this.translations == null || this.translations.length <= iModel) this.translations =  new Array(this.mc);
if (this.translations[iModel] == null) this.translations[iModel] =  new JU.P3();
this.translations[iModel].add(pt);
var bs = this.am[iModel].bsAtoms;
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) this.at[i].add(pt);

}, "~N,JU.T3");
Clazz.defineMethod(c$, "getFrameOffsets", 
function(bsAtoms, isFull){
if (bsAtoms == null) {
if (isFull) for (var i = this.mc; --i >= 0; ) {
var m = this.am[i];
if (!m.isJmolDataFrame && !m.isTrajectory) this.translateModel(m.modelIndex, null);
}
return null;
}var i0 = bsAtoms.nextSetBit(0);
if (i0 < 0) return null;
if (isFull) {
var bs = JU.BSUtil.copy(bsAtoms);
var pt = null;
var pdiff =  new JU.P3();
for (var i = 0; i < this.mc; i++) {
var m = this.am[i];
if (!m.isJmolDataFrame && !m.isTrajectory) {
var j = bs.nextSetBit(0);
if (m.bsAtoms.get(j)) {
if (pt == null) {
pt = JU.P3.newP(this.at[j]);
} else {
pdiff.sub2(pt, this.at[j]);
this.translateModel(i, pdiff);
}}}bs.andNot(m.bsAtoms);
}
return null;
}var offsets =  new Array(this.mc);
for (var i = this.mc; --i >= 0; ) offsets[i] =  new JU.P3();

var lastModel = 0;
var n = 0;
var lastOffset = null;
var asTrajectory = (this.trajectory != null && this.trajectory.steps.size() == this.mc);
var m1 = (asTrajectory ? this.mc : 1);
for (var m = 0; m < m1; m++) {
if (asTrajectory) this.setTrajectory(m);
for (var i = 0; i <= this.ac; i++) {
if (i < this.ac && JM.AtomCollection.isDeleted(this.at[i])) continue;
if (i == this.ac || this.at[i].mi != lastModel) {
if (n > 0) {
lastOffset.scale(-1.0 / n);
if (lastModel != 0) lastOffset.sub(offsets[0]);
n = 0;
}if (i == this.ac) break;
lastModel = this.at[i].mi;
lastOffset = offsets[lastModel];
}if (!bsAtoms.get(i)) continue;
lastOffset.add(this.at[i]);
n++;
}
}
offsets[0].set(0, 0, 0);
return offsets;
}, "JU.BS,~B");
Clazz.defineMethod(c$, "getAtoms", 
function(tokType, specInfo){
switch (tokType) {
default:
return JU.BSUtil.andNot(this.getAtomBitsMaybeDeleted(tokType, specInfo), this.vwr.slm.bsDeleted);
case 1073742358:
var modelNumber = (specInfo).intValue();
var modelIndex = this.getModelNumberIndex(modelNumber, true, true);
return (modelIndex < 0 && modelNumber > 0 ?  new JU.BS() : this.vwr.getModelUndeletedAtomsBitSet(modelIndex));
case 1275203608:
var data =  Clazz.newArray(-1, [null, null, null]);
this.vwr.shm.getShapePropertyData(21, "getCenters", data);
return (data[1] == null ?  new JU.BS() : data[1]);
}
}, "~N,~O");
Clazz.defineMethod(c$, "findNearestAtomIndex", 
function(x, y, bsNot, min){
if (this.ac == 0) return -1;
this.closest[0] = null;
if (this.g3d.isAntialiased()) {
x <<= 1;
y <<= 1;
}this.findNearest2(x, y, this.closest, bsNot, min);
this.sm.findNearestShapeAtomIndex(x, y, this.closest, bsNot);
var closestIndex = (this.closest[0] == null ? -1 : this.closest[0].i);
this.closest[0] = null;
return closestIndex;
}, "~N,~N,JU.BS,~N");
Clazz.defineMethod(c$, "calculatePointGroup", 
function(bsAtoms){
return this.calculatePointGroupForFirstModel(bsAtoms, false, false, null, 0, 0, null, null, null);
}, "JU.BS");
Clazz.defineMethod(c$, "getPointGroupInfo", 
function(bsAtoms){
return this.calculatePointGroupForFirstModel(bsAtoms, false, true, null, 0, 0, null, null, null);
}, "JU.BS");
Clazz.defineMethod(c$, "getPointGroupAsString", 
function(bsAtoms, type, index, scale, pts, center, id){
return this.calculatePointGroupForFirstModel(bsAtoms, true, false, type, index, scale, pts, center, id);
}, "JU.BS,~S,~N,~N,~A,JU.P3,~S");
Clazz.defineMethod(c$, "calculatePointGroupForFirstModel", 
function(bsAtoms, doAll, asInfo, type, index, scale, pts, center, id){
var pointGroup = this.pointGroup;
var symmetry = J.api.Interface.getSymmetry(this.vwr, "ms");
var bs = null;
var haveVibration = false;
var isPolyhedron = false;
var localEnvOnly = false;
var isPoints = (pts != null);
var modelIndex = this.vwr.am.cmi;
if (!isPoints) {
var iAtom = (bsAtoms == null ? -1 : bsAtoms.nextSetBit(0));
if (modelIndex < 0 && iAtom >= 0) modelIndex = this.at[iAtom].mi;
if (modelIndex < 0) {
modelIndex = this.vwr.getVisibleFramesBitSet().nextSetBit(0);
bsAtoms = null;
}bs = this.vwr.getModelUndeletedAtomsBitSet(modelIndex);
localEnvOnly = (bsAtoms != null && bs.cardinality() != bsAtoms.cardinality());
if (bsAtoms != null) bs.and(bsAtoms);
iAtom = bs.nextSetBit(0);
if (iAtom < 0) {
bs = this.vwr.getModelUndeletedAtomsBitSet(modelIndex);
iAtom = bs.nextSetBit(0);
}var obj = this.vwr.shm.getShapePropertyIndex(18, "mad", iAtom);
haveVibration = (obj != null && (obj).intValue() != 0 || this.vwr.tm.vibrationOn);
isPolyhedron = (type != null && type.toUpperCase().indexOf(":POLY") >= 0);
if (isPolyhedron) {
var data =  Clazz.newArray(-1, [Integer.$valueOf(iAtom), null]);
this.vwr.shm.getShapePropertyData(21, "points", data);
pts = data[1];
if (pts == null) return null;
bs = null;
haveVibration = false;
pointGroup = null;
} else {
pts = this.at;
}}var tp;
if (type != null && (tp = type.indexOf(":")) >= 0) type = type.substring(0, tp);
if (type != null && (tp = type.indexOf(".")) >= 0) {
index = JU.PT.parseInt(type.substring(tp + 1));
if (index < 0) index = 0;
type = type.substring(0, tp);
}pointGroup = symmetry.setPointGroup(this.vwr, pointGroup, center, pts, bs, haveVibration, (isPoints ? 0 : this.vwr.getFloat(570425382)), this.vwr.getFloat(570425384), (bs == null ? pts.length : bs.cardinality()), localEnvOnly);
if (!isPolyhedron && !isPoints) this.pointGroup = pointGroup;
if (!doAll && !asInfo) return pointGroup.getPointGroupName();
var ret = pointGroup.getPointGroupInfo(modelIndex, id, asInfo, type, index, scale);
return (asInfo ? ret : (this.mc > 1 ? "frame " + this.getModelNumberDotted(modelIndex) + "; " : "") + ret);
}, "JU.BS,~B,~B,~S,~N,~N,~A,JU.P3,~S");
Clazz.defineMethod(c$, "getDefaultStructure", 
function(bsAtoms, bsModified){
return (this.haveBioModels ? this.bioModelset.getAllDefaultStructures(bsAtoms, bsModified) : "");
}, "JU.BS,JU.BS");
Clazz.defineMethod(c$, "deleteModelBonds", 
function(modelIndex){
var bsAtoms = this.getModelAtomBitSetIncludingDeleted(modelIndex, false);
this.makeConnections(0, 3.4028235E38, 131071, 12291, bsAtoms, bsAtoms, null, false, false, 0);
}, "~N");
Clazz.defineMethod(c$, "makeConnections", 
function(minDistance, maxDistance, order, connectOperation, bsA, bsB, bsBonds, isBonds, addGroup, energy){
this.moleculeCount = 0;
var autoState = (connectOperation == 1073741852 && order != 2048 ?  new JU.SB() : null);
var result = this.makeConnections2(minDistance, maxDistance, order, connectOperation, bsA, bsB, bsBonds, isBonds, addGroup, energy, autoState);
if (autoState != null) {
this.addStateScript(autoState.toString(), null, null, null, null, false, true);
}return result;
}, "~N,~N,~N,~N,JU.BS,JU.BS,JU.BS,~B,~B,~N");
Clazz.defineMethod(c$, "setPdbConectBonding", 
function(baseAtomIndex, baseModelIndex, bsExclude){
var mad = this.vwr.getMadBond();
for (var i = baseModelIndex; i < this.mc; i++) {
var vConnect = this.getInfo(i, "PDB_CONECT_bonds");
if (vConnect == null) continue;
var nConnect = vConnect.size();
this.setInfo(i, "initialBondCount", Integer.$valueOf(nConnect));
var atomInfo = this.getInfo(i, "PDB_CONECT_firstAtom_count_max");
var firstAtom = atomInfo[0] + baseAtomIndex;
var atomMax = firstAtom + atomInfo[1];
if (atomMax > this.atomSerials.length) atomMax = this.atomSerials.length;
var max = atomInfo[2];
var serialMap =  Clazz.newIntArray (max + 1, 0);
var iSerial;
for (var iAtom = firstAtom; iAtom < atomMax; iAtom++) if ((iSerial = this.atomSerials[iAtom]) > 0) serialMap[iSerial] = iAtom + 1;

for (var iConnect = 0; iConnect < nConnect; iConnect++) {
var pair = vConnect.get(iConnect);
var sourceSerial = pair[0];
var targetSerial = pair[1];
var order = pair[2];
if (sourceSerial < 0 || targetSerial < 0 || sourceSerial > max || targetSerial > max) continue;
var sourceIndex = serialMap[sourceSerial] - 1;
var targetIndex = serialMap[targetSerial] - 1;
if (sourceIndex < 0 || targetIndex < 0) continue;
var atomA = this.at[sourceIndex];
var atomB = this.at[targetIndex];
if (bsExclude != null) {
if (atomA.isHetero()) bsExclude.set(sourceIndex);
if (atomB.isHetero()) bsExclude.set(targetIndex);
}if (atomA.altloc == atomB.altloc || atomA.altloc == '\0' || atomB.altloc == '\0') this.getOrAddBond(atomA, atomB, order, (order == 2048 ? 1 : mad), null, 0, false);
}
}
}, "~N,~N,JU.BS");
Clazz.defineMethod(c$, "deleteAllBonds", 
function(){
this.moleculeCount = 0;
for (var i = this.stateScripts.size(); --i >= 0; ) {
if (this.stateScripts.get(i).isConnect()) {
this.stateScripts.removeItemAt(i);
}}
this.deleteAllBonds2();
});
Clazz.defineMethod(c$, "includeAllRelatedFrames", 
function(bsModels){
var baseModel = 0;
for (var i = 0; i < this.mc; i++) {
var isTraj = this.isTrajectory(i);
var isBase = (isTraj && bsModels.get(baseModel = this.am[i].trajectoryBaseIndex));
if (bsModels.get(i)) {
if (isTraj && !isBase) {
bsModels.set(baseModel);
this.includeAllRelatedFrames(bsModels);
return;
}} else if (isTraj || this.isJmolDataFrameForModel(i) && bsModels.get(this.am[i].dataSourceFrame)) {
bsModels.set(i);
}}
}, "JU.BS");
Clazz.defineMethod(c$, "deleteModels", 
function(bsModels){
this.includeAllRelatedFrames(bsModels);
var nModelsDeleted = bsModels.cardinality();
if (nModelsDeleted == 0) return null;
this.moleculeCount = 0;
if (this.msInfo != null) this.msInfo.remove("models");
var bsAtomsToDelete =  new JU.BS();
for (var i = bsModels.nextSetBit(0); i >= 0; i = bsModels.nextSetBit(i + 1)) {
this.clearDataFrameReference(i);
bsAtomsToDelete.or(this.am[i].bsAtoms);
}
var bsDeleted;
if (nModelsDeleted == this.mc) {
bsDeleted = this.getModelAtomBitSetIncludingDeleted(-1, true);
this.vwr.zap(true, false, false);
return bsDeleted;
}this.validateBspf(false);
bsDeleted =  new JU.BS();
var allOrderly = true;
var isOneOfSeveral = false;
var files =  new JU.BS();
var firstAtom = bsAtomsToDelete.nextSetBit(0);
for (var i = 0; i < this.mc; i++) {
var m = this.am[i];
if (i < this.mc - 1) allOrderly = new Boolean (allOrderly & (m.isOrderly || m.bsAtoms.length() <= firstAtom)).valueOf();
if (bsModels.get(i)) {
if (m.fileIndex >= 0) files.set(m.fileIndex);
bsDeleted.or(this.getModelAtomBitSetIncludingDeleted(i, false));
} else {
if (m.fileIndex >= 0 && files.get(m.fileIndex)) isOneOfSeveral = true;
}}
if (!allOrderly || isOneOfSeveral) {
this.vwr.deleteAtoms(bsDeleted, false);
return null;
}var newModels =  new Array(this.mc - nModelsDeleted);
var oldModels = this.am;
for (var i = 0, mpt = 0; i < this.mc; i++) {
if (!bsModels.get(i)) {
var m = this.am[i];
m.modelIndex = mpt;
newModels[mpt++] = m;
}}
this.am = newModels;
var oldModelCount = this.mc;
var bsBonds = this.getBondsForSelectedAtoms(bsDeleted, true);
this.deleteBonds(bsBonds, true);
for (var i = 0, mpt = 0; i < oldModelCount; i++) {
if (!bsModels.get(i)) {
mpt++;
continue;
}var old = oldModels[i];
var nAtoms = old.act;
if (nAtoms == 0) continue;
var bsModelAtoms = old.bsAtoms;
var firstAtomIndex = old.firstAtomIndex;
JU.BSUtil.deleteBits(this.bsSymmetry, bsModelAtoms);
this.deleteModel(mpt, bsModelAtoms, bsBonds);
this.deleteModelAtoms(firstAtomIndex, nAtoms, bsModelAtoms);
this.vwr.deleteModelAtoms(mpt, firstAtomIndex, nAtoms, bsModelAtoms);
for (var j = oldModelCount; --j > i; ) oldModels[j].fixIndices(mpt, nAtoms, bsModelAtoms);

this.vwr.shm.deleteShapeAtoms( Clazz.newArray(-1, [newModels, this.at,  Clazz.newIntArray(-1, [mpt, firstAtomIndex, nAtoms])]), bsModelAtoms);
this.mc--;
}
this.haveBioModels = false;
for (var i = this.mc; --i >= 0; ) if (this.am[i].isBioModel) {
this.haveBioModels = true;
this.bioModelset.set(this.vwr, this);
}
this.validateBspf(false);
this.bsAll = null;
this.resetMolecules();
this.isBbcageDefault = false;
this.calcBoundBoxDimensions(null, 1);
return bsDeleted;
}, "JU.BS");
Clazz.defineMethod(c$, "resetMolecules", 
function(){
this.bsAll = null;
this.molecules = null;
this.moleculeCount = 0;
this.resetChirality();
});
Clazz.defineMethod(c$, "resetChirality", 
function(){
if (this.haveChirality) {
var modelIndex = -1;
for (var i = this.ac; --i >= 0; ) {
var a = this.at[i];
if (a == null) continue;
a.setCIPChirality(0);
if (a.mi != modelIndex && a.mi < this.am.length) this.am[modelIndex = a.mi].hasChirality = false;
}
}});
Clazz.defineMethod(c$, "deleteModel", 
function(modelIndex, bsModelAtoms, bsBonds){
if (modelIndex < 0) {
return;
}this.modelNumbers = JU.AU.deleteElements(this.modelNumbers, modelIndex, 1);
this.modelFileNumbers = JU.AU.deleteElements(this.modelFileNumbers, modelIndex, 1);
this.modelNumbersForAtomLabel = JU.AU.deleteElements(this.modelNumbersForAtomLabel, modelIndex, 1);
this.modelNames = JU.AU.deleteElements(this.modelNames, modelIndex, 1);
this.frameTitles = JU.AU.deleteElements(this.frameTitles, modelIndex, 1);
this.thisStateModel = -1;
var group3Lists = this.getInfoM("group3Lists");
var group3Counts = this.getInfoM("group3Counts");
var ptm = modelIndex + 1;
if (group3Lists != null && group3Lists[ptm] != null) {
for (var i = Clazz.doubleToInt(group3Lists[ptm].length / 6); --i >= 0; ) if (group3Counts[ptm][i] > 0) {
group3Counts[0][i] -= group3Counts[ptm][i];
if (group3Counts[0][i] == 0) group3Lists[0] = group3Lists[0].substring(0, i * 6) + ",[" + group3Lists[0].substring(i * 6 + 2);
}
}if (group3Lists != null) {
this.msInfo.put("group3Lists", JU.AU.deleteElements(group3Lists, modelIndex, 1));
this.msInfo.put("group3Counts", JU.AU.deleteElements(group3Counts, modelIndex, 1));
}if (this.unitCells != null) {
this.unitCells = JU.AU.deleteElements(this.unitCells, modelIndex, 1);
}for (var i = this.stateScripts.size(); --i >= 0; ) {
if (!this.stateScripts.get(i).deleteAtoms(modelIndex, bsBonds, bsModelAtoms)) {
this.stateScripts.removeItemAt(i);
}}
}, "~N,JU.BS,JU.BS");
Clazz.defineMethod(c$, "setAtomProperty", 
function(bs, tok, iValue, fValue, sValue, values, list){
switch (tok) {
case 1114249217:
case 1112152066:
case 1112152071:
case 1112152073:
case 1112152074:
case 1649022989:
case 1112152078:
if (fValue > 4.0) fValue = 4.0;
if (values != null) {
var newValues =  Clazz.newFloatArray (this.ac, 0);
try {
for (var i = bs.nextSetBit(0), ii = 0; i >= 0; i = bs.nextSetBit(i + 1)) newValues[i] = values[ii++];

} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return;
} else {
throw e;
}
}
values = newValues;
}case 1112152070:
case 1112152076:
var rd = null;
var mar = 0;
if (values == null) {
if (fValue > 16) fValue = 16.1;
if (fValue < 0) fValue = 0;
mar = Clazz.doubleToInt(Math.floor(fValue * 2000));
} else {
rd =  new J.atomdata.RadiusData(values, 0, null, null);
}this.sm.setShapeSizeBs(JV.JC.shapeTokenIndex(tok), mar, rd, bs);
return;
}
this.setAPm(bs, tok, iValue, fValue, sValue, values, list);
}, "JU.BS,~N,~N,~N,~S,~A,~A");
Clazz.defineMethod(c$, "getFileData", 
function(modelIndex){
if (modelIndex < 0) return "";
var fileData = this.getInfo(modelIndex, "fileData");
if (fileData != null) return fileData;
if (!this.getInfoB(modelIndex, "isCIF")) return this.getPDBHeader(modelIndex);
fileData = this.vwr.getCifData(modelIndex);
this.setInfo(modelIndex, "fileData", fileData);
return fileData;
}, "~N");
Clazz.defineMethod(c$, "addHydrogens", 
function(vConnections, pts){
var modelIndex = vConnections.get(0).mi;
var bs =  new JU.BS();
if (this.isTrajectory(modelIndex) || this.am[modelIndex].getGroupCount() > 1) {
return bs;
}this.growAtomArrays(this.ac + pts.length);
var rd = this.vwr.rd;
var mad = this.getDefaultMadFromOrder(1);
this.am[modelIndex].resetDSSR(false);
for (var i = 0, n = this.am[modelIndex].act + 1; i < vConnections.size(); i++, n++) {
var atom1 = vConnections.get(i);
var atom2 = this.addAtom(modelIndex, atom1.group, 1, "H" + n, null, n, atom1.getSeqID(), n, pts[i], NaN, null, 0, 0, 100, NaN, null, false, 0, null, NaN);
atom2.setMadAtom(this.vwr, rd);
bs.set(atom2.i);
this.bondAtoms(atom1, atom2, 1, mad, null, 0, false, false);
}
this.sm.loadDefaultShapes(this);
return bs;
}, "JU.Lst,~A");
Clazz.defineMethod(c$, "mergeModelArrays", 
function(mergeModelSet){
this.at = mergeModelSet.at;
this.bo = mergeModelSet.bo;
this.stateScripts = mergeModelSet.stateScripts;
this.proteinStructureTainted = mergeModelSet.proteinStructureTainted;
this.thisStateModel = -1;
this.bsSymmetry = mergeModelSet.bsSymmetry;
this.modelFileNumbers = mergeModelSet.modelFileNumbers;
this.modelNumbersForAtomLabel = mergeModelSet.modelNumbersForAtomLabel;
this.modelNames = mergeModelSet.modelNames;
this.modelNumbers = mergeModelSet.modelNumbers;
this.frameTitles = mergeModelSet.frameTitles;
this.haveChirality = mergeModelSet.haveChirality;
this.boxInfo.setBoundBox(mergeModelSet.boxInfo.bbCorner0, mergeModelSet.boxInfo.bbCorner1, true, 1);
if (this.msInfo != null) this.msInfo.remove("models");
this.mergeAtomArrays(mergeModelSet);
}, "JM.ModelSet");
Clazz.defineMethod(c$, "getUnitCell", 
function(modelIndex){
var returnCage = (modelIndex == -2147483648);
if (returnCage) modelIndex = this.vwr.am.cmi;
if (modelIndex < 0 || modelIndex >= this.mc) return null;
var ucSimple = this.am[modelIndex].simpleCage;
var uc = null;
if (this.unitCells != null && modelIndex < this.unitCells.length && this.unitCells[modelIndex] != null && this.unitCells[modelIndex].haveUnitCell()) uc = this.unitCells[modelIndex];
if (uc != null && returnCage) {
return (ucSimple == null ? this.setModelCagePts(modelIndex, uc.getUnitCellVectors(), "cage") : ucSimple);
}if (uc == null || ucSimple != null && !uc.isSymmetryCell(ucSimple)) {
uc = ucSimple;
}return uc;
}, "~N");
Clazz.defineMethod(c$, "setModelCagePts", 
function(iModel, originABC, name){
if (iModel < 0 && (iModel = this.vwr.am.cmi) < 0) return null;
var sym = this.vwr.getSymTemp();
try {
return this.setModelCage(iModel, originABC == null ? null : sym.getUnitCell(originABC, false, name));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
return null;
} else {
throw e;
}
}
}, "~N,~A,~S");
Clazz.defineMethod(c$, "getModelName", 
function(modelIndex){
return this.mc < 1 ? "" : modelIndex >= 0 ? this.modelNames[modelIndex] : this.modelNumbersForAtomLabel[-1 - modelIndex];
}, "~N");
Clazz.defineMethod(c$, "getModelTitle", 
function(modelIndex){
return this.getInfo(modelIndex, "title");
}, "~N");
Clazz.defineMethod(c$, "getModelFileName", 
function(modelIndex){
return this.getInfo(modelIndex, "fileName");
}, "~N");
Clazz.defineMethod(c$, "getModelFileType", 
function(modelIndex){
return this.getInfo(modelIndex, "fileType");
}, "~N");
Clazz.defineMethod(c$, "setFrameTitle", 
function(bsFrames, title){
if ((typeof(title)=='string')) {
for (var i = bsFrames.nextSetBit(0); i >= 0; i = bsFrames.nextSetBit(i + 1)) this.frameTitles[i] = title;

} else {
var list = title;
for (var i = bsFrames.nextSetBit(0), n = 0; i >= 0; i = bsFrames.nextSetBit(i + 1)) if (n < list.length) this.frameTitles[i] = list[n++];

}}, "JU.BS,~O");
Clazz.defineMethod(c$, "getFrameTitle", 
function(modelIndex){
return (modelIndex >= 0 && modelIndex < this.mc ? this.frameTitles[modelIndex] : "");
}, "~N");
Clazz.defineMethod(c$, "getModelNumberForAtomLabel", 
function(modelIndex){
return this.modelNumbersForAtomLabel[modelIndex];
}, "~N");
Clazz.defineMethod(c$, "getGroups", 
function(){
var n = 0;
for (var i = 0; i < this.mc; i++) n += this.am[i].getGroupCount();

var groups =  new Array(n);
for (var i = 0, iGroup = 0; i < this.mc; i++) for (var j = 0; j < this.am[i].chainCount; j++) for (var k = 0; k < this.am[i].chains[j].groupCount; k++) {
groups[iGroup] = this.am[i].chains[j].groups[k];
groups[iGroup].groupIndex = iGroup;
iGroup++;
}


return groups;
});
Clazz.defineMethod(c$, "setCrystallographicDefaults", 
function(){
return !this.haveBioModels && (this.someModelsHaveSymmetry && this.someModelsHaveFractionalCoordinates || this.getUnitCell(this.vwr.am.cmi) != null);
});
Clazz.defineMethod(c$, "getBoundBoxCenter", 
function(modelIndex){
return (this.isJmolDataFrameForModel(modelIndex) ?  new JU.P3() : (this.getDefaultBoundBox() == null ? this.boxInfo : this.defaultBBox).getBoundBoxCenter());
}, "~N");
Clazz.defineMethod(c$, "getBoundBoxCornerVector", 
function(){
return this.boxInfo.getBoundBoxCornerVector();
});
Clazz.defineMethod(c$, "getBBoxVertices", 
function(){
return this.boxInfo.getBoundBoxVertices();
});
Clazz.defineMethod(c$, "setBoundBox", 
function(pt1, pt2, byCorner, scale){
if (scale == 0 && this.msInfo != null) {
this.msInfo.remove("boundbox");
this.defaultBBox = null;
this.isBbcageDefault = false;
this.calcBoundBoxDimensions(null, scale = 1);
}this.isBbcageDefault = false;
this.bboxModels = null;
this.bboxAtoms = null;
this.boxInfo.setBoundBox(pt1, pt2, byCorner, scale);
}, "JU.T3,JU.T3,~B,~N");
Clazz.defineMethod(c$, "getBoundBoxCommand", 
function(withOptions){
if (!withOptions && this.bboxAtoms != null) return "boundbox " + JU.Escape.eBS(this.bboxAtoms);
this.ptTemp.setT(this.boxInfo.getBoundBoxCenter());
var bbVector = this.boxInfo.getBoundBoxCornerVector();
var s = (withOptions ? "boundbox " + JU.Escape.eP(this.ptTemp) + " " + JU.Escape.eP(bbVector) + "\n#or\n" : "");
this.ptTemp.sub(bbVector);
s += "boundbox corners " + JU.Escape.eP(this.ptTemp) + " ";
this.ptTemp.scaleAdd2(2, bbVector, this.ptTemp);
var v = Math.abs(8 * bbVector.x * bbVector.y * bbVector.z);
s += JU.Escape.eP(this.ptTemp) + " # volume = " + v;
return s;
}, "~B");
Clazz.defineMethod(c$, "findAtomsInRectangle", 
function(rect){
var bsModels = this.vwr.getVisibleFramesBitSet();
var bs =  new JU.BS();
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
if (!bsModels.get(atom.mi)) i = this.am[atom.mi].firstAtomIndex;
 else if (atom.checkVisible() && rect.contains(atom.sX, atom.sY)) bs.set(i);
}
return bs;
}, "JU.Rectangle");
Clazz.defineMethod(c$, "getDefaultVdwType", 
function(modelIndex){
return (!this.am[modelIndex].isBioModel ? J.c.VDW.AUTO_BABEL : this.am[modelIndex].hydrogenCount == 0 ? J.c.VDW.AUTO_JMOL : J.c.VDW.AUTO_BABEL);
}, "~N");
Clazz.defineMethod(c$, "setRotationRadius", 
function(modelIndex, angstroms){
if (this.isJmolDataFrameForModel(modelIndex)) {
this.am[modelIndex].defaultRotationRadius = angstroms;
return false;
}return true;
}, "~N,~N");
Clazz.defineMethod(c$, "calcRotationRadius", 
function(modelIndex, center, useBoundBox){
if (this.isJmolDataFrameForModel(modelIndex)) {
var r = this.am[modelIndex].defaultRotationRadius;
return (r == 0 ? 10 : r);
}if (useBoundBox && this.getDefaultBoundBox() != null) return this.defaultBBox.getMaxDim() / 2 * 1.2;
if (this.ac == 0) return 10;
modelIndex = -2;
var maxRadius = 0;
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
if (this.isJmolDataFrameForAtom(atom)) {
modelIndex = atom.mi;
while (i >= 0 && this.at[i] != null && this.at[i].mi == modelIndex) i--;

i++;
continue;
} else if (atom.mi != modelIndex) {
modelIndex = atom.mi;
var uc = (this.am[modelIndex].isBioModel ? null : this.getUnitCell(modelIndex));
if (uc != null) {
var pts = uc.getUnitCellVerticesNoOffset();
var off = uc.getCartesianOffset();
for (var j = 0; j < 8; j++) {
this.ptTemp.setT(pts[j]);
this.ptTemp.add(off);
maxRadius = Math.max(maxRadius, center.distance(this.ptTemp));
}
}}var d = center.distance(atom) + this.getRadiusVdwJmol(atom);
if (d > maxRadius) maxRadius = d;
}
return (maxRadius == 0 ? 10 : maxRadius);
}, "~N,JU.P3,~B");
Clazz.defineMethod(c$, "calcBoundBoxDimensions", 
function(bs, scale){
if (bs != null && bs.nextSetBit(0) < 0) bs = null;
if (bs == null && this.isBbcageDefault || this.ac == 0) return;
if (this.getDefaultBoundBox() == null) {
this.bboxModels = this.getModelBS(this.bboxAtoms = JU.BSUtil.copy(bs), false);
if (this.calcAtomsMinMax(bs, this.boxInfo) == this.ac) this.isBbcageDefault = true;
if (bs == null) {
if (this.unitCells != null) this.calcUnitCellMinMax();
}} else {
var vertices = this.defaultBBox.getBoundBoxVertices();
this.boxInfo.reset();
for (var j = 0; j < 8; j++) this.boxInfo.addBoundBoxPoint(vertices[j]);

}this.boxInfo.setBbcage(scale);
}, "JU.BS,~N");
Clazz.defineMethod(c$, "getDefaultBoundBox", 
function(){
var bbox = this.getInfoM("boundbox");
if (bbox == null) this.defaultBBox = null;
 else {
if (this.defaultBBox == null) this.defaultBBox =  new JU.BoxInfo();
this.defaultBBox.setBoundBoxFromOABC(bbox);
}return this.defaultBBox;
});
Clazz.defineMethod(c$, "getBoxInfo", 
function(bs, scale){
if (bs == null) return this.boxInfo;
var bi =  new JU.BoxInfo();
this.calcAtomsMinMax(bs, bi);
bi.setBbcage(scale);
return bi;
}, "JU.BS,~N");
Clazz.defineMethod(c$, "calcAtomsMinMax", 
function(bs, boxInfo){
boxInfo.reset();
var nAtoms = 0;
var isAll = (bs == null);
var i0 = (isAll ? this.ac - 1 : bs.nextSetBit(0));
for (var i = i0; i >= 0; i = (isAll ? i - 1 : bs.nextSetBit(i + 1))) {
nAtoms++;
var a = this.at[i];
if (a != null && !this.isJmolDataFrameForAtom(a)) boxInfo.addBoundBoxPoint(a);
}
return nAtoms;
}, "JU.BS,JU.BoxInfo");
Clazz.defineMethod(c$, "calcUnitCellMinMax", 
function(){
var pt =  new JU.P3();
for (var i = 0; i < this.mc; i++) {
var uc = this.unitCells[i];
if (uc == null || !uc.getCoordinatesAreFractional()) continue;
var vertices = uc.getUnitCellVerticesNoOffset();
var offset = uc.getCartesianOffset();
for (var j = 0; j < 8; j++) {
pt.add2(offset, vertices[j]);
this.boxInfo.addBoundBoxPoint(pt);
}
}
});
Clazz.defineMethod(c$, "calcRotationRadiusBs", 
function(bs){
var center = this.getAtomSetCenter(bs);
var maxRadius = 0;
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var atom = this.at[i];
var distAtom = center.distance(atom);
var outerVdw = distAtom + this.getRadiusVdwJmol(atom);
if (outerVdw > maxRadius) maxRadius = outerVdw;
}
return (maxRadius == 0 ? 10 : maxRadius);
}, "JU.BS");
Clazz.defineMethod(c$, "getCenterAndPoints", 
function(vAtomSets, addCenters){
var bsAtoms1;
var bsAtoms2;
var n = (addCenters ? 1 : 0);
for (var ii = vAtomSets.size(); --ii >= 0; ) {
var bss = vAtomSets.get(ii);
bsAtoms1 = bss[0];
if (Clazz.instanceOf(bss[1],"JU.BS")) {
bsAtoms2 = bss[1];
n += Math.min(bsAtoms1.cardinality(), bsAtoms2.cardinality());
} else {
n += Math.min(bsAtoms1.cardinality(), (bss[1]).length);
}}
var points =  Clazz.newArray(2, n, null);
if (addCenters) {
points[0][0] =  new JU.P3();
points[1][0] =  new JU.P3();
}for (var ii = vAtomSets.size(); --ii >= 0; ) {
var bss = vAtomSets.get(ii);
bsAtoms1 = bss[0];
if (Clazz.instanceOf(bss[1],"JU.BS")) {
bsAtoms2 = bss[1];
for (var i = bsAtoms1.nextSetBit(0), j = bsAtoms2.nextSetBit(0); i >= 0 && j >= 0; i = bsAtoms1.nextSetBit(i + 1), j = bsAtoms2.nextSetBit(j + 1)) {
points[0][--n] = this.at[i];
points[1][n] = this.at[j];
if (addCenters) {
points[0][0].add(this.at[i]);
points[1][0].add(this.at[j]);
}}
} else {
var coords = bss[1];
for (var i = bsAtoms1.nextSetBit(0), j = 0; i >= 0 && j < coords.length; i = bsAtoms1.nextSetBit(i + 1), j++) {
points[0][--n] = this.at[i];
points[1][n] = coords[j];
if (addCenters) {
points[0][0].add(this.at[i]);
points[1][0].add(coords[j]);
}}
}}
if (addCenters) {
points[0][0].scale(1 / (points[0].length - 1));
points[1][0].scale(1 / (points[1].length - 1));
}return points;
}, "JU.Lst,~B");
Clazz.defineMethod(c$, "getAtomSetCenter", 
function(bs){
var ptCenter =  new JU.P3();
var nPoints = 0;
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
if (!this.isJmolDataFrameForAtom(this.at[i])) {
nPoints++;
ptCenter.add(this.at[i]);
}}
if (nPoints > 1) ptCenter.scale(1.0 / nPoints);
return ptCenter;
}, "JU.BS");
Clazz.defineMethod(c$, "getAverageAtomPoint", 
function(){
return this.getAtomSetCenter(this.vwr.bsA());
});
Clazz.defineMethod(c$, "setAPm", 
function(bs, tok, iValue, fValue, sValue, values, list){
this.setAPa(bs, tok, iValue, fValue, sValue, values, list);
switch (tok) {
case 1094715418:
case 1631586315:
if (this.vwr.getBoolean(603979944)) this.assignAromaticBondsBs(true, null);
break;
}
}, "JU.BS,~N,~N,~N,~S,~A,~A");
Clazz.defineMethod(c$, "addStateScript", 
function(script1, bsBonds, bsAtoms1, bsAtoms2, script2, addFrameNumber, postDefinitions){
var iModel = this.vwr.am.cmi;
if (addFrameNumber) {
if (this.thisStateModel != iModel) script1 = "frame " + (iModel < 0 ? "all #" + iModel : this.getModelNumberDotted(iModel)) + ";\n  " + script1;
this.thisStateModel = iModel;
} else {
this.thisStateModel = -1;
}var stateScript =  new JM.StateScript(this.thisStateModel, script1, bsBonds, bsAtoms1, bsAtoms2, script2, postDefinitions);
if (stateScript.isValid()) {
this.stateScripts.addLast(stateScript);
}return stateScript;
}, "~S,JU.BS,JU.BS,JU.BS,~S,~B,~B");
Clazz.defineMethod(c$, "freezeModels", 
function(){
this.haveBioModels = false;
for (var iModel = this.mc; --iModel >= 0; ) this.haveBioModels = new Boolean (this.haveBioModels | this.am[iModel].freeze()).valueOf();

});
Clazz.defineMethod(c$, "getStructureList", 
function(){
return this.vwr.getStructureList();
});
Clazz.defineMethod(c$, "getInfoM", 
function(keyName){
return (this.msInfo == null ? null : this.msInfo.get(keyName));
}, "~S");
Clazz.defineMethod(c$, "getMSInfoB", 
function(keyName){
var val = this.getInfoM(keyName);
return (Clazz.instanceOf(val, Boolean) && (val).booleanValue());
}, "~S");
Clazz.defineMethod(c$, "isTrajectory", 
function(modelIndex){
return this.am[modelIndex].isTrajectory;
}, "~N");
Clazz.defineMethod(c$, "isTrajectorySubFrame", 
function(i){
return (this.am[i].trajectoryBaseIndex != i);
}, "~N");
Clazz.defineMethod(c$, "isTrajectoryMeasurement", 
function(countPlusIndices){
return (this.trajectory != null && this.trajectory.hasMeasure(countPlusIndices));
}, "~A");
Clazz.defineMethod(c$, "getModelBS", 
function(atomList, allTrajectories){
var bs =  new JU.BS();
var modelIndex = 0;
var isAll = (atomList == null);
allTrajectories = new Boolean (allTrajectories & (this.trajectory != null)).valueOf();
var i0 = (isAll ? 0 : atomList.nextSetBit(0));
for (var i = i0; i >= 0 && i < this.ac; i = (isAll ? i + 1 : atomList.nextSetBit(i + 1))) {
if (JM.AtomCollection.isDeleted(this.at[i])) continue;
bs.set(modelIndex = this.at[i].mi);
if (allTrajectories) this.trajectory.getModelBS(modelIndex, bs);
var m = this.am[modelIndex];
if (m.isOrderly) i = m.firstAtomIndex + m.act - 1;
}
return bs;
}, "JU.BS,~B");
Clazz.defineMethod(c$, "getIterativeModels", 
function(allowJmolData){
var bs =  new JU.BS();
for (var i = 0; i < this.mc; i++) {
if (!allowJmolData && this.isJmolDataFrameForModel(i)) continue;
if (!this.isTrajectorySubFrame(i)) bs.set(i);
}
return bs;
}, "~B");
Clazz.defineMethod(c$, "fillAtomData", 
function(atomData, mode){
if ((mode & 4) != 0) {
this.getMolecules();
atomData.bsMolecules =  new Array(this.molecules.length);
atomData.atomMolecule =  Clazz.newIntArray (this.ac, 0);
var bs;
for (var i = 0; i < this.molecules.length; i++) {
bs = atomData.bsMolecules[i] = this.molecules[i].atomList;
for (var iAtom = bs.nextSetBit(0); iAtom >= 0; iAtom = bs.nextSetBit(iAtom + 1)) atomData.atomMolecule[iAtom] = i;

}
}if ((mode & 8) != 0) {
var nH =  Clazz.newIntArray (1, 0);
atomData.hAtomRadius = this.vwr.getVanderwaalsMar(1) / 1000;
atomData.hAtoms = this.calculateHydrogens(atomData.bsSelected, nH, null, 512);
atomData.hydrogenAtomCount = nH[0];
return;
}if (atomData.modelIndex < 0) atomData.firstAtomIndex = (atomData.bsSelected == null ? 0 : Math.max(0, atomData.bsSelected.nextSetBit(0)));
 else atomData.firstAtomIndex = this.am[atomData.modelIndex].firstAtomIndex;
atomData.lastModelIndex = atomData.firstModelIndex = (this.ac == 0 ? 0 : this.at[atomData.firstAtomIndex].mi);
atomData.modelName = this.getModelNumberDotted(atomData.firstModelIndex);
this.fillADa(atomData, mode);
}, "J.atomdata.AtomData,~N");
Clazz.defineMethod(c$, "getModelNumberDotted", 
function(modelIndex){
return (this.mc < 1 || modelIndex >= this.mc || modelIndex < 0 ? "" : JU.Escape.escapeModelFileNumber(this.modelFileNumbers[modelIndex]));
}, "~N");
Clazz.defineMethod(c$, "getModelNumber", 
function(modelIndex){
return this.modelNumbers[modelIndex == 2147483647 ? this.mc - 1 : modelIndex];
}, "~N");
Clazz.defineMethod(c$, "getModelProperty", 
function(modelIndex, property){
var props = this.am[modelIndex].properties;
return props == null ? null : props.getProperty(property);
}, "~N,~S");
Clazz.defineMethod(c$, "getModelAuxiliaryInfo", 
function(modelIndex){
return (modelIndex < 0 ? null : this.am[modelIndex].auxiliaryInfo);
}, "~N");
Clazz.defineMethod(c$, "setInfo", 
function(modelIndex, key, value){
if (modelIndex >= 0 && modelIndex < this.mc) {
if (value == null) this.am[modelIndex].auxiliaryInfo.remove(key);
 else this.am[modelIndex].auxiliaryInfo.put(key, value);
}}, "~N,~O,~O");
Clazz.defineMethod(c$, "getInfo", 
function(modelIndex, key){
return (modelIndex < 0 ? null : this.am[modelIndex].auxiliaryInfo.get(key));
}, "~N,~S");
Clazz.defineMethod(c$, "getInfoB", 
function(modelIndex, keyName){
var info = this.am[modelIndex].auxiliaryInfo;
return (info != null && info.containsKey(keyName) && (info.get(keyName)).booleanValue());
}, "~N,~S");
Clazz.defineMethod(c$, "getInfoI", 
function(modelIndex, keyName){
var info = this.am[modelIndex].auxiliaryInfo;
if (info != null && info.containsKey(keyName)) {
return (info.get(keyName)).intValue();
}return -2147483648;
}, "~N,~S");
Clazz.defineMethod(c$, "getInsertionCountInModel", 
function(modelIndex){
return this.am[modelIndex].insertionCount;
}, "~N");
c$.modelFileNumberFromFloat = Clazz.defineMethod(c$, "modelFileNumberFromFloat", 
function(fDotM){
var file = Clazz.doubleToInt(Math.floor(fDotM));
var model = Clazz.doubleToInt(Math.floor((fDotM - file + 0.00001) * 10000));
while (model != 0 && model % 10 == 0) model /= 10;

return file * 1000000 + model;
}, "~N");
Clazz.defineMethod(c$, "getChainCountInModelWater", 
function(modelIndex, countWater){
if (modelIndex < 0) {
var chainCount = 0;
for (var i = this.mc; --i >= 0; ) chainCount += this.am[i].getChainCount(countWater);

return chainCount;
}return this.am[modelIndex].getChainCount(countWater);
}, "~N,~B");
Clazz.defineMethod(c$, "getGroupCountInModel", 
function(modelIndex){
if (modelIndex < 0) {
var groupCount = 0;
for (var i = this.mc; --i >= 0; ) groupCount += this.am[i].getGroupCount();

return groupCount;
}return this.am[modelIndex].getGroupCount();
}, "~N");
Clazz.defineMethod(c$, "calcSelectedGroupsCount", 
function(){
var bsSelected = this.vwr.bsA();
for (var i = this.mc; --i >= 0; ) this.am[i].calcSelectedGroupsCount(bsSelected);

});
Clazz.defineMethod(c$, "isJmolDataFrameForModel", 
function(modelIndex){
return this.haveJmolDataFrames && (this.am != null && modelIndex >= 0 && modelIndex < this.mc && this.am[modelIndex].isJmolDataFrame);
}, "~N");
Clazz.defineMethod(c$, "isJmolDataFrameForAtom", 
function(atom){
return this.haveJmolDataFrames && this.am[atom.mi].isJmolDataFrame;
}, "JM.Atom");
Clazz.defineMethod(c$, "setJmolDataFrame", 
function(type, modelIndex, modelDataIndex){
this.haveJmolDataFrames = true;
var model = this.am[type == null ? this.am[modelDataIndex].dataSourceFrame : modelIndex];
if (type == null) {
type = this.am[modelDataIndex].jmolFrameType;
}if (modelIndex >= 0) {
if (model.dataFrames == null) {
model.dataFrames =  new java.util.Hashtable();
}this.am[modelDataIndex].dataSourceFrame = modelIndex;
this.am[modelDataIndex].jmolFrameType = type;
model.dataFrames.put(type, Integer.$valueOf(modelDataIndex));
}if (type.startsWith("quaternion") && type.indexOf("deriv") < 0) {
type = type.substring(0, type.indexOf(" "));
model.dataFrames.put(type, Integer.$valueOf(modelDataIndex));
}}, "~S,~N,~N");
Clazz.defineMethod(c$, "getJmolDataFrameIndex", 
function(modelIndex, type){
if (this.am[modelIndex].dataFrames == null) {
return -1;
}var index = this.am[modelIndex].dataFrames.get(type);
return (index == null ? -1 : index.intValue());
}, "~N,~S");
Clazz.defineMethod(c$, "clearDataFrameReference", 
function(modelIndex){
for (var i = 0; i < this.mc; i++) {
var df = this.am[i].dataFrames;
if (df == null) {
continue;
}var e = df.values().iterator();
while (e.hasNext()) {
if ((e.next()).intValue() == modelIndex) {
e.remove();
}}
}
}, "~N");
Clazz.defineMethod(c$, "getJmolFrameType", 
function(modelIndex){
return (modelIndex >= 0 && modelIndex < this.mc ? this.am[modelIndex].jmolFrameType : "modelSet");
}, "~N");
Clazz.defineMethod(c$, "getJmolDataSourceFrame", 
function(modelIndex){
return (modelIndex >= 0 && modelIndex < this.mc ? this.am[modelIndex].dataSourceFrame : -1);
}, "~N");
Clazz.defineMethod(c$, "saveModelOrientation", 
function(modelIndex, orientation){
this.am[modelIndex].orientation = orientation;
}, "~N,JM.Orientation");
Clazz.defineMethod(c$, "getModelOrientation", 
function(modelIndex){
return this.am[modelIndex].orientation;
}, "~N");
Clazz.defineMethod(c$, "getPDBHeader", 
function(modelIndex){
return (this.am[modelIndex].isBioModel ? (this.am[modelIndex]).getFullPDBHeader() : this.getFileHeader(modelIndex));
}, "~N");
Clazz.defineMethod(c$, "getFileHeader", 
function(modelIndex){
if (modelIndex < 0) return "";
if (this.am[modelIndex].isBioModel) return this.getPDBHeader(modelIndex);
var info = this.getInfo(modelIndex, "fileHeader");
if (info == null) info = this.modelSetName;
if (info != null) return info;
return "no header information found";
}, "~N");
Clazz.defineMethod(c$, "getAltLocCountInModel", 
function(modelIndex){
return this.am[modelIndex].altLocCount;
}, "~N");
Clazz.defineMethod(c$, "getAltLocIndexInModel", 
function(modelIndex, alternateLocationID){
if (alternateLocationID == '\0') {
return 0;
}var altLocList = this.getAltLocListInModel(modelIndex);
if (altLocList.length == 0) {
return 0;
}return altLocList.indexOf(alternateLocationID) + 1;
}, "~N,~S");
Clazz.defineMethod(c$, "getInsertionCodeIndexInModel", 
function(modelIndex, insertionCode){
if (insertionCode == '\0') return 0;
var codeList = this.getInsertionListInModel(modelIndex);
if (codeList.length == 0) return 0;
return codeList.indexOf(insertionCode) + 1;
}, "~N,~S");
Clazz.defineMethod(c$, "getAltLocListInModel", 
function(modelIndex){
var str = this.getInfo(modelIndex, "altLocs");
return (str == null ? "" : str);
}, "~N");
Clazz.defineMethod(c$, "getInsertionListInModel", 
function(modelIndex){
var str = this.getInfo(modelIndex, "insertionCodes");
return (str == null ? "" : str);
}, "~N");
Clazz.defineMethod(c$, "getModelSymmetryCount", 
function(modelIndex){
return (this.am[modelIndex].biosymmetryCount > 0 ? this.am[modelIndex].biosymmetryCount : this.unitCells == null || this.unitCells[modelIndex] == null ? 0 : this.unitCells[modelIndex].getSpaceGroupOperationCount());
}, "~N");
Clazz.defineMethod(c$, "getModelCellRange", 
function(modelIndex){
return (this.unitCells == null ? null : this.unitCells[modelIndex].getCellRange());
}, "~N");
Clazz.defineMethod(c$, "getLastVibrationVector", 
function(modelIndex, tok){
if (this.vibrations != null && modelIndex < this.vwr.ms.mc) {
var v;
var a1 = (modelIndex < 0 || this.isTrajectory(modelIndex) || modelIndex >= this.mc - 1 ? this.ac : this.am[modelIndex + 1].firstAtomIndex);
var a0 = (modelIndex <= 0 ? 0 : this.am[modelIndex].firstAtomIndex);
for (var i = a1; --i >= a0; ) {
if ((modelIndex < 0 || !JM.AtomCollection.isDeleted(this.at[i]) && this.at[i].mi == modelIndex) && ((tok == 1275072532 || tok == 0) && (v = this.getModulation(i)) != null || (tok == 4166 || tok == 0) && (v = this.getVibration(i, false)) != null) && v.isNonzero()) return i;
}
}return -1;
}, "~N,~N");
Clazz.defineMethod(c$, "getModulationList", 
function(bs, type, t456){
var list =  new JU.Lst();
if (this.vibrations != null) for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) if (Clazz.instanceOf(this.vibrations[i],"J.api.JmolModulationSet")) list.addLast((this.vibrations[i]).getModulation(type, t456, false));
 else list.addLast(Float.$valueOf(type == 'O' ? NaN : -1));

return list;
}, "JU.BS,~S,JU.P3");
Clazz.defineMethod(c$, "getElementsPresentBitSet", 
function(modelIndex){
if (modelIndex >= 0) return this.elementsPresent[modelIndex];
var bs =  new JU.BS();
for (var i = 0; i < this.mc; i++) bs.or(this.elementsPresent[i]);

return bs;
}, "~N");
Clazz.defineMethod(c$, "getMoleculeIndex", 
function(atomIndex, inModel){
if (this.moleculeCount == 0) this.getMolecules();
for (var i = 0; i < this.moleculeCount; i++) {
if (this.molecules[i].atomList.get(atomIndex)) return (inModel ? this.molecules[i].indexInModel : i);
}
return 0;
}, "~N,~B");
Clazz.defineMethod(c$, "getMoleculeBitSet", 
function(bs){
if (this.moleculeCount == 0) this.getMolecules();
var bsResult = JU.BSUtil.copy(bs);
var bsInitial = JU.BSUtil.copy(bs);
var i = 0;
var bsTemp =  new JU.BS();
while ((i = bsInitial.length() - 1) >= 0) {
bsTemp = this.getMoleculeBitSetForAtom(i);
if (bsTemp == null) {
bsInitial.clear(i);
bsResult.clear(i);
continue;
}bsInitial.andNot(bsTemp);
bsResult.or(bsTemp);
}
return bsResult;
}, "JU.BS");
Clazz.defineMethod(c$, "getMoleculeBitSetForAtom", 
function(atomIndex){
if (this.moleculeCount == 0) this.getMolecules();
for (var i = 0; i < this.moleculeCount; i++) if (this.molecules[i].atomList.get(atomIndex)) return this.molecules[i].atomList;

return null;
}, "~N");
Clazz.defineMethod(c$, "getModelDipole", 
function(modelIndex){
if (modelIndex < 0) return null;
var dipole = this.getInfo(modelIndex, "dipole");
if (dipole == null) dipole = this.getInfo(modelIndex, "DIPOLE_VEC");
return dipole;
}, "~N");
Clazz.defineMethod(c$, "calculateMolecularDipole", 
function(modelIndex, bsAtoms){
if (bsAtoms != null) {
var ia = bsAtoms.nextSetBit(0);
if (ia < 0) return null;
modelIndex = this.at[ia].mi;
}if (modelIndex < 0) return null;
var nPos = 0;
var nNeg = 0;
var cPos = 0;
var cNeg = 0;
var pos =  new JU.V3();
var neg =  new JU.V3();
if (bsAtoms == null) bsAtoms = this.getModelAtomBitSetIncludingDeleted(-1, false);
this.vwr.getOrCalcPartialCharges(this.am[modelIndex].bsAtoms, null);
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
if (JM.AtomCollection.isDeleted(this.at[i]) || this.at[i].mi != modelIndex) {
continue;
}var c = this.partialCharges[i];
if (c < 0) {
nNeg++;
cNeg += c;
neg.scaleAdd2(c, this.at[i], neg);
} else if (c > 0) {
nPos++;
cPos += c;
pos.scaleAdd2(c, this.at[i], pos);
}}
if (Math.abs(cPos + cNeg) > 0.015) {
JU.Logger.info("Dipole calculation requires balanced charges: " + cPos + " " + cNeg);
return null;
}if (nNeg == 0 || nPos == 0) return null;
pos.add(neg);
pos.scale(4.8);
return pos;
}, "~N,JU.BS");
Clazz.defineMethod(c$, "getMoleculeCountInModel", 
function(modelIndex){
var n = 0;
if (this.moleculeCount == 0) this.getMolecules();
if (modelIndex < 0) return this.moleculeCount;
for (var i = 0; i < this.mc; i++) {
if (modelIndex == i) n += this.am[i].moleculeCount;
}
return n;
}, "~N");
Clazz.defineMethod(c$, "calcSelectedMoleculesCount", 
function(){
var bsSelected = this.vwr.bsA();
if (this.moleculeCount == 0) this.getMolecules();
this.selectedMolecules.xor(this.selectedMolecules);
var bsTemp =  new JU.BS();
for (var i = 0; i < this.moleculeCount; i++) {
JU.BSUtil.copy2(bsSelected, bsTemp);
bsTemp.and(this.molecules[i].atomList);
if (bsTemp.length() > 0) {
this.selectedMolecules.set(i);
}}
});
Clazz.defineMethod(c$, "setCentroid", 
function(bs, minmax){
var bsDelete = this.getNotInCentroid(bs, minmax);
if (bsDelete != null && bsDelete.nextSetBit(0) >= 0) this.vwr.deleteAtoms(bsDelete, false);
}, "JU.BS,~A");
Clazz.defineMethod(c$, "getNotInCentroid", 
function(bs, minmax){
var iAtom0 = bs.nextSetBit(0);
if (iAtom0 < 0) return null;
var uc = this.getUnitCell(this.at[iAtom0].mi);
return (uc == null ? null : uc.notInCentroid(this, bs, minmax));
}, "JU.BS,~A");
Clazz.defineMethod(c$, "getMolecules", 
function(){
if (this.moleculeCount > 0) return this.molecules;
if (this.molecules == null) this.molecules =  new Array(4);
this.moleculeCount = 0;
var m = null;
var bsModelAtoms =  new Array(this.mc);
var biobranches = null;
for (var i = 0; i < this.mc; i++) {
bsModelAtoms[i] = this.vwr.getModelUndeletedAtomsBitSet(i);
m = this.am[i];
m.moleculeCount = 0;
biobranches = (m.isBioModel ? (m).getBioBranches(biobranches) : null);
}
this.molecules = JU.JmolMolecule.getMolecules(this.at, bsModelAtoms, biobranches, null);
this.moleculeCount = this.molecules.length;
for (var i = this.moleculeCount; --i >= 0; ) {
m = this.am[this.molecules[i].modelIndex];
m.firstMoleculeIndex = i;
m.moleculeCount++;
}
return this.molecules;
});
Clazz.defineMethod(c$, "initializeBspf", 
function(){
if (this.bspf != null && this.bspf.isValid) return;
if (this.showRebondTimes) JU.Logger.startTimer("build bspf");
var bspf =  new J.bspt.Bspf(3);
if (JU.Logger.debugging) JU.Logger.debug("sequential bspt order");
var bsNew = JU.BS.newN(this.mc);
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (!JM.AtomCollection.isDeleted(atom) && !this.isTrajectorySubFrame(atom.mi)) {
bspf.addTuple(this.am[atom.mi].trajectoryBaseIndex, atom);
bsNew.set(atom.mi);
}}
if (this.showRebondTimes) {
JU.Logger.checkTimer("build bspf", false);
bspf.stats();
}for (var i = bsNew.nextSetBit(0); i >= 0; i = bsNew.nextSetBit(i + 1)) bspf.validateModel(i, true);

bspf.isValid = true;
this.bspf = bspf;
});
Clazz.defineMethod(c$, "initializeBspt", 
function(modelIndex){
this.initializeBspf();
if (this.bspf.isInitializedIndex(modelIndex)) return;
this.bspf.initialize(modelIndex, this.at, this.vwr.getModelUndeletedAtomsBitSet(modelIndex));
}, "~N");
Clazz.defineMethod(c$, "setIteratorForPoint", 
function(iterator, modelIndex, pt, distance){
if (modelIndex < 0) {
iterator.setCenter(pt, distance);
return;
}this.initializeBspt(modelIndex);
iterator.setModel(this, modelIndex, this.am[modelIndex].firstAtomIndex, 2147483647, pt, distance, null);
}, "J.api.AtomIndexIterator,~N,JU.T3,~N");
Clazz.defineMethod(c$, "setIteratorForAtom", 
function(iterator, modelIndex, atomIndex, distance, rd){
if (modelIndex < 0) modelIndex = this.at[atomIndex].mi;
modelIndex = this.am[modelIndex].trajectoryBaseIndex;
this.initializeBspt(modelIndex);
iterator.setModel(this, modelIndex, this.am[modelIndex].firstAtomIndex, atomIndex, this.at[atomIndex], distance, rd);
}, "J.api.AtomIndexIterator,~N,~N,~N,J.atomdata.RadiusData");
Clazz.defineMethod(c$, "getSelectedAtomIterator", 
function(bsSelected, isGreaterOnly, modelZeroBased, hemisphereOnly, isMultiModel){
this.initializeBspf();
var iter;
if (isMultiModel) {
var bsModels = this.getModelBS(bsSelected, false);
for (var i = bsModels.nextSetBit(0); i >= 0; i = bsModels.nextSetBit(i + 1)) this.initializeBspt(i);

iter =  new JM.AtomIteratorWithinModelSet(bsModels);
} else {
iter =  new JM.AtomIteratorWithinModel();
}iter.initialize(this.bspf, bsSelected, isGreaterOnly, modelZeroBased, hemisphereOnly, this.vwr.isParallel());
return iter;
}, "JU.BS,~B,~B,~B,~B");
Clazz.overrideMethod(c$, "getBondCountInModel", 
function(modelIndex){
return (modelIndex < 0 ? this.bondCount : this.am[modelIndex].getBondCount());
}, "~N");
Clazz.defineMethod(c$, "getAtomCountInModel", 
function(modelIndex){
return (modelIndex < 0 ? this.ac : this.am[modelIndex].act);
}, "~N");
Clazz.defineMethod(c$, "getModelAtomBitSetIncludingDeletedBs", 
function(bsModels){
var bs =  new JU.BS();
if (bsModels == null && this.bsAll == null) this.bsAll = JU.BSUtil.setAll(this.ac);
if (bsModels == null) bs.or(this.bsAll);
 else for (var i = bsModels.nextSetBit(0); i >= 0; i = bsModels.nextSetBit(i + 1)) bs.or(this.getModelAtomBitSetIncludingDeleted(i, false));

return bs;
}, "JU.BS");
Clazz.defineMethod(c$, "getModelAtomBitSetIncludingDeleted", 
function(modelIndex, asCopy){
var bs = (modelIndex < 0 ? this.bsAll : this.am[modelIndex].bsAtoms);
if (bs == null) bs = this.bsAll = JU.BSUtil.setAll(this.ac);
return (asCopy ? JU.BSUtil.copy(bs) : bs);
}, "~N,~B");
Clazz.defineMethod(c$, "getAtomBitsMaybeDeleted", 
function(tokType, specInfo){
var bs;
switch (tokType) {
default:
return this.getAtomBitsMDa(tokType, specInfo, bs =  new JU.BS());
case 1073741925:
case 1073742189:
case 1111490587:
case 1073742128:
case 1073741863:
case 1086324744:
bs =  new JU.BS();
return (this.haveBioModels ? this.bioModelset.getAtomBitsStr(tokType, specInfo, bs) : bs);
case 1677721602:
case 1073742331:
return this.getAtomBitsMDb(tokType, specInfo);
case 1812599299:
var boxInfo = this.getBoxInfo(specInfo, 1);
bs = this.getAtomsWithin(boxInfo.getBoundBoxCornerVector().length() + 0.0001, boxInfo.getBoundBoxCenter(), null, -1);
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) if (!boxInfo.isWithin(this.at[i])) bs.clear(i);

return bs;
case 1094713350:
bs = JU.BSUtil.newBitSet2(0, this.ac);
var pt1 = specInfo;
var minmax =  Clazz.newIntArray(-1, [Clazz.floatToInt(pt1.x) - 1, Clazz.floatToInt(pt1.y) - 1, Clazz.floatToInt(pt1.z) - 1, Clazz.floatToInt(pt1.x), Clazz.floatToInt(pt1.y), Clazz.floatToInt(pt1.z), 0]);
for (var i = this.mc; --i >= 0; ) {
var uc1 = this.getUnitCell(i);
if (uc1 == null) {
JU.BSUtil.andNot(bs, this.am[i].bsAtoms);
continue;
}bs.andNot(uc1.notInCentroid(this, this.am[i].bsAtoms, minmax));
}
return bs;
case 1094713360:
return this.getMoleculeBitSet(specInfo);
case 1073742363:
return this.getSelectCodeRange(specInfo);
case 2097196:
bs = JU.BS.newN(this.ac);
var modelIndex = -1;
var nOps = 0;
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
var bsSym = atom.atomSymmetry;
if (bsSym != null) {
if (atom.mi != modelIndex) {
modelIndex = atom.mi;
if (this.getModelCellRange(modelIndex) == null) continue;
nOps = this.getModelSymmetryCount(modelIndex);
}var n = 0;
for (var j = nOps; --j >= 0; ) if (bsSym.get(j)) if (++n > 1) {
bs.set(i);
break;
}
}}
return bs;
case 1088421903:
return JU.BSUtil.copy(this.bsSymmetry == null ? this.bsSymmetry = JU.BS.newN(this.ac) : this.bsSymmetry);
case 1814695966:
var isSelectUC = ("unitcell".equals(specInfo));
if (isSelectUC) {
specInfo = JU.P3.new3(1, 1, 1);
} else {
bs =  new JU.BS();
var uc1 = (Clazz.instanceOf(specInfo,"J.api.SymmetryInterface") ? specInfo : this.vwr.getCurrentUnitCell());
if (uc1 == null) return bs;
uc1 = uc1.getUnitCellMultiplied();
for (var i = this.ac; --i >= 0; ) {
if (this.at[i] != null) {
this.ptTemp1.setT(this.at[i]);
uc1.toFractional(this.ptTemp1, false);
if (uc1.checkPeriodic(this.ptTemp1)) bs.set(i);
}}
return bs;
}case 1094713349:
bs =  new JU.BS();
var pt = specInfo;
var uc = this.vwr.getSymTemp();
System.out.println("MS test within");
for (var mi = -1, i = this.ac; --i >= 0; ) {
if (JM.AtomCollection.isDeleted(this.at[i])) continue;
var mia = this.at[i].getModelIndex();
if (mi != mia) {
mi = mia;
uc = this.getUnitCell(mi);
}if (uc == null) continue;
this.ptTemp.setT(this.at[i]);
uc.toFractional(this.ptTemp, false);
if (uc.isWithinUnitCell(this.ptTemp, pt.x, pt.y, pt.z)) bs.set(i);
}
System.out.println("MS test within" + bs);
return bs;
}
}, "~N,~O");
Clazz.defineMethod(c$, "getSelectCodeRange", 
function(info){
var bs =  new JU.BS();
var seqcodeA = info[0];
var seqcodeB = info[1];
var chainID = info[2];
var caseSensitive = this.vwr.getBoolean(603979822);
if (chainID >= 0 && chainID < 300 && !caseSensitive) chainID = this.chainToUpper(chainID);
for (var iModel = this.mc; --iModel >= 0; ) if (this.am[iModel].isBioModel) {
var m = this.am[iModel];
var id;
for (var i = m.chainCount; --i >= 0; ) {
var chain = m.chains[i];
if (chainID == -1 || chainID == (id = chain.chainID) || !caseSensitive && id > 0 && id < 300 && chainID == this.chainToUpper(id)) {
var groups = chain.groups;
var n = chain.groupCount;
for (var index = 0; index >= 0; ) {
index = JM.ModelSet.selectSeqcodeRange(groups, n, index, seqcodeA, seqcodeB, bs);
}
}}
}
return bs;
}, "~A");
c$.selectSeqcodeRange = Clazz.defineMethod(c$, "selectSeqcodeRange", 
function(groups, n, index, seqcodeA, seqcodeB, bs){
var seqcode;
var indexA;
var indexB;
var minDiff;
var isInexact = false;
for (indexA = index; indexA < n && groups[indexA].seqcode != seqcodeA; indexA++) {
}
if (indexA == n) {
if (index > 0) return -1;
isInexact = true;
minDiff = 2147483647;
for (var i = n; --i >= 0; ) if ((seqcode = groups[i].seqcode) > seqcodeA && (seqcode - seqcodeA) < minDiff) {
indexA = i;
minDiff = seqcode - seqcodeA;
}
if (minDiff == 2147483647) return -1;
}if (seqcodeB == 2147483647) {
indexB = n - 1;
isInexact = true;
} else {
for (indexB = indexA; indexB < n && groups[indexB].seqcode != seqcodeB; indexB++) {
}
if (indexB == n) {
if (index > 0) return -1;
isInexact = true;
minDiff = 2147483647;
for (var i = indexA; i < n; i++) if ((seqcode = groups[i].seqcode) < seqcodeB && (seqcodeB - seqcode) < minDiff) {
indexB = i;
minDiff = seqcodeB - seqcode;
}
if (minDiff == 2147483647) return -1;
}}for (var i = indexA; i <= indexB; ++i) groups[i].setAtomBits(bs);

return (isInexact ? -1 : indexB + 1);
}, "~A,~N,~N,~N,~N,JU.BS");
Clazz.defineMethod(c$, "getAtomsWithinRadius", 
function(distance, bs, withinAllModels, rd, bsSubset){
var bsResult =  new JU.BS();
bs = JU.BSUtil.andNot(bs, this.vwr.slm.bsDeleted);
var iter = this.getSelectedAtomIterator(bsSubset, false, false, false, false);
if (withinAllModels) {
var fixJavaFloat = !this.vwr.g.legacyJavaFloat;
var ptTemp =  new JU.P3();
var bsModels = (bsSubset == null ? JU.BSUtil.newBitSet2(0, this.mc) : this.getModelBS(bsSubset, false));
bsModels.and(this.getIterativeModels(false));
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) for (var iModel = bsModels.nextSetBit(0); iModel >= 0; iModel = bsModels.nextSetBit(iModel + 1)) {
if (distance < 0) {
this.getAtomsWithin(distance, this.at[i].getFractionalUnitCoordPt(fixJavaFloat, true, ptTemp), bsResult, iModel);
} else {
this.setIteratorForAtom(iter, iModel, i, distance, rd);
iter.addAtoms(bsResult);
}}

} else {
if (bsSubset == null) bsResult.or(bs);
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
if (distance < 0) {
this.getAtomsWithin(distance, this.at[i], bsResult, this.at[i].mi);
} else {
this.setIteratorForAtom(iter, -1, i, distance, rd);
iter.addAtoms(bsResult);
}}
}iter.release();
return bsResult;
}, "~N,JU.BS,~B,J.atomdata.RadiusData,JU.BS");
Clazz.defineMethod(c$, "getAtomsWithin", 
function(distance, coord, bsResult, modelIndex){
if (bsResult == null) bsResult =  new JU.BS();
if (distance < 0) {
distance = -distance;
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom) || modelIndex >= 0 && atom.mi != modelIndex) continue;
if (!bsResult.get(i) && atom.getFractionalUnitDistance(coord, this.ptTemp1, this.ptTemp2) <= distance) bsResult.set(atom.i);
}
return bsResult;
}var iter = this.getSelectedAtomIterator(null, false, false, false, false);
var bsCheck = (modelIndex >= 0 ? JU.BSUtil.newAndSetBit(modelIndex) : this.getIterativeModels(true));
for (var m = bsCheck.nextSetBit(0); m >= 0; m = bsCheck.nextSetBit(m + 1)) {
var i = this.am[m].bsAtoms.nextSetBit(0);
if (i < 0) continue;
this.setIteratorForAtom(iter, modelIndex, i, -1, null);
iter.setCenter(coord, distance);
iter.addAtoms(bsResult);
}
iter.release();
return bsResult;
}, "~N,JU.T3,JU.BS,~N");
Clazz.defineMethod(c$, "deleteBonds", 
function(bsBonds, isFullModel){
if (!isFullModel) {
var bsA =  new JU.BS();
var bsB =  new JU.BS();
for (var i = bsBonds.nextSetBit(0); i >= 0; i = bsBonds.nextSetBit(i + 1)) {
var atom1 = this.bo[i].atom1;
if (this.am[atom1.mi].isModelKit) continue;
bsA.clearAll();
bsB.clearAll();
bsA.set(atom1.i);
bsB.set(this.bo[i].getAtomIndex2());
this.addStateScript("connect ", null, bsA, bsB, "delete", false, true);
}
}this.dBb(bsBonds, isFullModel);
}, "JU.BS,~B");
Clazz.defineMethod(c$, "makeConnections2", 
function(minD, maxD, order, connectOperation, bsA, bsB, bsBonds, isBonds, addGroup, energy, state){
if (bsBonds == null) bsBonds =  new JU.BS();
var matchAny = (order == 65535);
var matchNull = (order == 131071);
var isAtrop = (order == 65537);
if (matchNull) order = 1;
var matchHbond = JU.Edge.isOrderH(order);
var identifyOnly = false;
var idOrModifyOnly = false;
var createOnly = false;
var autoAromatize = false;
switch (connectOperation) {
case 12291:
return this.deleteConnections(minD, maxD, order, bsA, bsB, isBonds, matchNull);
case 603979872:
case 1073741852:
if (order != 515) {
if (isBonds) {
var bs = bsA;
bsA =  new JU.BS();
bsB =  new JU.BS();
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
bsA.set(this.bo[i].atom1.i);
bsB.set(this.bo[i].atom2.i);
}
}return  Clazz.newIntArray(-1, [matchHbond ? this.autoHbond(bsA, bsB, false) : this.autoBondBs4(bsA, bsB, null, bsBonds, this.vwr.getMadBond(), connectOperation == 603979872, state), 0]);
}idOrModifyOnly = autoAromatize = true;
break;
case 1086324745:
identifyOnly = idOrModifyOnly = true;
break;
case 1073742025:
idOrModifyOnly = true;
break;
case 1073741904:
createOnly = true;
break;
}
var anyOrNoId = matchAny;
var notAnyAndNoId = (!identifyOnly && !matchAny);
this.defaultCovalentMad = this.vwr.getMadBond();
var minDIsFrac = (minD < 0);
var maxDIsFrac = (maxD < 0);
var isFractional = (minDIsFrac || maxDIsFrac);
var checkDistance = (!isBonds || minD != 0.1 || maxD != 1.0E8);
if (checkDistance) {
minD = this.fixD(minD, minDIsFrac);
maxD = this.fixD(maxD, maxDIsFrac);
}var mad = this.getDefaultMadFromOrder(order);
var nNew = 0;
var nModified = 0;
var bondAB = null;
var atomA = null;
var atomB = null;
var altloc = '\u0000';
var newOrder = (order | 131072);
var isAromaticOnly = (order != 65535 && (order & 512) != 0);
try {
for (var i = bsA.nextSetBit(0); i >= 0; i = bsA.nextSetBit(i + 1)) {
if (isBonds) {
bondAB = this.bo[i];
atomA = bondAB.atom1;
atomB = bondAB.atom2;
} else {
atomA = this.at[i];
if (atomA.isDeleted()) continue;
altloc = (this.isModulated(i) ? '\0' : atomA.altloc);
}for (var j = (isBonds ? 0 : bsB.nextSetBit(0)); j >= 0; j = bsB.nextSetBit(j + 1)) {
if (isBonds) {
j = 2147483646;
} else {
if (j == i) continue;
atomB = this.at[j];
if (atomB == null || atomA.mi != atomB.mi || atomB.isDeleted()) continue;
if (altloc != '\0' && altloc != atomB.altloc && atomB.altloc != '\0') continue;
bondAB = atomA.getBond(atomB);
}if ((bondAB == null ? idOrModifyOnly : createOnly) || checkDistance && !this.isInRange(atomA, atomB, minD, maxD, minDIsFrac, maxDIsFrac, isFractional) || isAromaticOnly && (bondAB != null && !this.allowAromaticBond(bondAB))) continue;
if (bondAB == null) {
bsBonds.set(this.bondAtoms(atomA, atomB, order, mad, bsBonds, energy, addGroup, true).index);
nNew++;
} else {
if (notAnyAndNoId) {
bondAB.setOrder(order);
if (isAtrop) {
this.haveAtropicBonds = true;
bondAB.setAtropisomerOptions();
}this.bsAromatic.clear(bondAB.index);
}if (anyOrNoId || order == bondAB.order || newOrder == bondAB.order || matchHbond && bondAB.isHydrogen()) {
bsBonds.set(bondAB.index);
nModified++;
}}}
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
if (autoAromatize) this.assignAromaticBondsBs(true, bsBonds);
if (!identifyOnly) this.sm.setShapeSizeBs(1, -2147483648, null, bsBonds);
return  Clazz.newIntArray(-1, [nNew, nModified]);
}, "~N,~N,~N,~N,JU.BS,JU.BS,JU.BS,~B,~B,~N,JU.SB");
Clazz.defineMethod(c$, "autoBondBs4", 
function(bsA, bsB, bsExclude, bsBonds, mad, preJmol11_9_24, state){
if (preJmol11_9_24) return this.autoBond_Pre_11_9_24(bsA, bsB, bsExclude, bsBonds, mad);
if (this.ac == 0) return 0;
if (mad == 0) mad = 1;
if (this.maxBondingRadius == 1.4E-45) this.findMaxRadii();
var bondTolerance = this.vwr.getFloat(570425348);
var minBondDistance = this.vwr.getFloat(570425364);
var minBondDistance2 = minBondDistance * minBondDistance;
var nNew = 0;
if (this.showRebondTimes) JU.Logger.startTimer("autobond");
var lastModelIndex = -1;
var isAll = (bsA == null);
var bsCheck;
var i0;
if (isAll) {
i0 = 0;
bsCheck = null;
} else {
if (bsA.equals(bsB)) {
bsCheck = bsA;
} else {
bsCheck = JU.BSUtil.copy(bsA);
bsCheck.or(bsB);
}i0 = bsCheck.nextSetBit(0);
}var iter = this.getSelectedAtomIterator(null, false, false, true, false);
var useOccupation = false;
for (var i = i0; i >= 0 && i < this.ac; i = (isAll ? i + 1 : bsCheck.nextSetBit(i + 1))) {
var isAtomInSetA = (isAll || bsA.get(i));
var isAtomInSetB = (isAll || bsB.get(i));
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
var modelIndex = atom.mi;
if (modelIndex != lastModelIndex) {
lastModelIndex = modelIndex;
if (this.isJmolDataFrameForModel(modelIndex)) {
i = this.am[modelIndex].firstAtomIndex + this.am[modelIndex].act - 1;
continue;
}useOccupation = this.getInfoB(modelIndex, "autoBondUsingOccupation");
}var myBondingRadius = atom.getBondingRadius();
if (myBondingRadius == 0) continue;
var myFormalCharge = atom.getFormalCharge();
var useCharge = (myFormalCharge != 0);
if (useCharge) myFormalCharge = Math.signum(myFormalCharge);
var isFirstExcluded = (bsExclude != null && bsExclude.get(i));
var searchRadius = myBondingRadius + this.maxBondingRadius + bondTolerance;
this.setIteratorForAtom(iter, -1, i, searchRadius, null);
while (iter.hasNext()) {
var atomNear = this.at[iter.next()];
if (atomNear.isDeleted()) continue;
var j = atomNear.i;
var isNearInSetA = (isAll || bsA.get(j));
var isNearInSetB = (isAll || bsB.get(j));
if (!isNearInSetA && !isNearInSetB || !(isAtomInSetA && isNearInSetB || isAtomInSetB && isNearInSetA) || isFirstExcluded && bsExclude.get(j) || useOccupation && this.occupancies != null && (this.occupancies[i] < 50) != (this.occupancies[j] < 50) || useCharge && (Math.signum(atomNear.getFormalCharge()) == myFormalCharge)) continue;
var order = (this.isBondable(myBondingRadius, atomNear.getBondingRadius(), iter.foundDistance2(), minBondDistance2, bondTolerance) ? 1 : 0);
if (order > 0 && this.autoBondCheck(atom, atomNear, order, mad, bsBonds)) {
nNew++;
if (state != null) state.append("connect ({" + i + "}) ({" + j + "});");
}}
iter.release();
}
if (this.showRebondTimes) JU.Logger.checkTimer("autoBond", false);
return nNew;
}, "JU.BS,JU.BS,JU.BS,JU.BS,~N,~B,JU.SB");
Clazz.defineMethod(c$, "isBondable", 
function(bondingRadiusA, bondingRadiusB, distance2, minBondDistance2, bondTolerance){
if (bondingRadiusA == 0 || bondingRadiusB == 0 || distance2 < minBondDistance2) return false;
var maxAcceptable = bondingRadiusA + bondingRadiusB + bondTolerance;
var maxAcceptable2 = maxAcceptable * maxAcceptable;
return (distance2 <= maxAcceptable2);
}, "~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "autoBondCheck", 
function(atomA, atomB, order, mad, bsBonds){
if (atomA.getCurrentBondCount() > 20 || atomB.getCurrentBondCount() > 20) {
if (!this.maxBondWarned) JU.Logger.warn("maximum auto bond count reached");
this.maxBondWarned = true;
return false;
}var formalChargeA = atomA.getFormalCharge();
if (formalChargeA != 0) {
var formalChargeB = atomB.getFormalCharge();
if ((formalChargeA < 0 && formalChargeB < 0) || (formalChargeA > 0 && formalChargeB > 0)) return false;
}if (atomA.altloc != atomB.altloc && atomA.altloc != '\0' && atomB.altloc != '\0' && this.getModulation(atomA.i) == null) return false;
this.getOrAddBond(atomA, atomB, order, mad, bsBonds, 0, false);
return true;
}, "JM.Atom,JM.Atom,~N,~N,JU.BS");
Clazz.defineMethod(c$, "autoBond_Pre_11_9_24", 
function(bsA, bsB, bsExclude, bsBonds, mad){
if (this.ac == 0) return 0;
if (mad == 0) mad = 1;
if (this.maxBondingRadius == 1.4E-45) this.findMaxRadii();
var bondTolerance = this.vwr.getFloat(570425348);
var minBondDistance = this.vwr.getFloat(570425364);
var minBondDistance2 = minBondDistance * minBondDistance;
var nNew = 0;
this.initializeBspf();
var lastModelIndex = -1;
for (var i = this.ac; --i >= 0; ) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
var isAtomInSetA = (bsA == null || bsA.get(i));
var isAtomInSetB = (bsB == null || bsB.get(i));
if (!isAtomInSetA && !isAtomInSetB) continue;
if (atom.isDeleted()) continue;
var modelIndex = atom.mi;
if (modelIndex != lastModelIndex) {
lastModelIndex = modelIndex;
if (this.isJmolDataFrameForModel(modelIndex)) {
for (; --i >= 0; ) if (JM.AtomCollection.isDeleted(this.at[i]) || this.at[i].mi != modelIndex) break;

i++;
continue;
}}var myBondingRadius = atom.getBondingRadius();
if (myBondingRadius == 0) continue;
var searchRadius = myBondingRadius + this.maxBondingRadius + bondTolerance;
this.initializeBspt(modelIndex);
var iter = this.bspf.getCubeIterator(modelIndex);
iter.initialize(atom, searchRadius, true);
while (iter.hasMoreElements()) {
var atomNear = iter.nextElement();
if (atomNear === atom || atomNear.isDeleted()) continue;
var atomIndexNear = atomNear.i;
var isNearInSetA = (bsA == null || bsA.get(atomIndexNear));
var isNearInSetB = (bsB == null || bsB.get(atomIndexNear));
if (!isNearInSetA && !isNearInSetB || bsExclude != null && bsExclude.get(atomIndexNear) && bsExclude.get(i)) continue;
if (!(isAtomInSetA && isNearInSetB || isAtomInSetB && isNearInSetA)) continue;
var order = (this.isBondable(myBondingRadius, atomNear.getBondingRadius(), iter.foundDistance2(), minBondDistance2, bondTolerance) ? 1 : 0);
if (order > 0) {
if (this.autoBondCheck(atom, atomNear, order, mad, bsBonds)) nNew++;
}}
iter.release();
}
return nNew;
}, "JU.BS,JU.BS,JU.BS,JU.BS,~N");
Clazz.defineMethod(c$, "autoHbond", 
function(bsA, bsB, onlyIfHaveCalculated){
if (onlyIfHaveCalculated) {
var bsModels = this.getModelBS(bsA, false);
for (var i = bsModels.nextSetBit(0); i >= 0 && onlyIfHaveCalculated; i = bsModels.nextSetBit(i + 1)) onlyIfHaveCalculated = !this.am[i].hasRasmolHBonds;

if (onlyIfHaveCalculated) return 0;
}var haveHAtoms = false;
for (var i = bsA.nextSetBit(0); i >= 0; i = bsA.nextSetBit(i + 1)) if (this.at[i].getElementNumber() == 1) {
haveHAtoms = true;
break;
}
var bsHBonds =  new JU.BS();
var useRasMol = this.vwr.getBoolean(603979853);
if (bsB == null || useRasMol && !haveHAtoms) {
JU.Logger.info((bsB == null ? "DSSP/DSSR " : "RasMol") + " pseudo-hbond calculation");
this.calcRasmolHydrogenBonds(bsA, bsB, null, false, 2147483647, false, bsHBonds);
return -bsHBonds.cardinality();
}JU.Logger.info(haveHAtoms ? "Standard Hbond calculation" : "Jmol pseudo-hbond calculation");
var bsCO = null;
if (!haveHAtoms) {
bsCO =  new JU.BS();
for (var i = bsA.nextSetBit(0); i >= 0; i = bsA.nextSetBit(i + 1)) {
var atomID = this.at[i].atomID;
switch (atomID) {
case 64:
case 4:
case 14:
case 15:
case 16:
case 17:
bsCO.set(i);
break;
}
}
}var dmax;
var min2;
if (haveHAtoms) {
dmax = this.vwr.getFloat(570425361);
min2 = 1;
} else {
dmax = this.vwr.getFloat(570425360);
min2 = JM.ModelSet.hbondMinRasmol * JM.ModelSet.hbondMinRasmol;
}var max2 = dmax * dmax;
var minAttachedAngle = (this.vwr.getFloat(570425359) * 3.141592653589793 / 180);
var nNew = 0;
var d2 = 0;
if (this.showRebondTimes && JU.Logger.debugging) JU.Logger.startTimer("hbond");
var C = null;
var D = null;
var iter = this.getSelectedAtomIterator(bsB, false, false, false, false);
for (var i = bsA.nextSetBit(0); i >= 0; i = bsA.nextSetBit(i + 1)) {
var atom = this.at[i];
var elementNumber = atom.getElementNumber();
var isH = (elementNumber == 1);
if (isH ? !haveHAtoms : haveHAtoms || elementNumber != 7 && elementNumber != 8) continue;
var firstIsCO;
if (isH) {
firstIsCO = false;
var b = atom.bonds;
if (b == null) continue;
var isOK = false;
for (var j = 0; !isOK && j < b.length; j++) {
var a2 = b[j].getOtherAtom(atom);
var element = a2.getElementNumber();
isOK = (element == 7 || element == 8);
}
if (!isOK) continue;
} else {
firstIsCO = bsCO.get(i);
}this.setIteratorForAtom(iter, -1, atom.i, dmax, null);
while (iter.hasNext()) {
var atomNear = this.at[iter.next()];
var elementNumberNear = atomNear.getElementNumber();
if (atomNear === atom || (isH ? elementNumberNear == 1 : elementNumberNear != 7 && elementNumberNear != 8) || (d2 = iter.foundDistance2()) < min2 || d2 > max2 || firstIsCO && bsCO.get(atomNear.i) || atom.isBonded(atomNear)) {
continue;
}this.v1.sub2(atom, atomNear);
if ((D = JM.ModelSet.checkMinAttachedAngle(atom, minAttachedAngle, this.v1, this.v2, haveHAtoms)) == null) continue;
this.v1.scale(-1);
if ((C = JM.ModelSet.checkMinAttachedAngle(atomNear, minAttachedAngle, this.v1, this.v2, haveHAtoms)) == null) continue;
var energy = 0;
var bo;
if (isH && !Float.isNaN(C.x) && !Float.isNaN(D.x)) {
bo = 4096;
energy = JM.HBond.calcEnergy(Math.sqrt(d2), C.distance(atom), C.distance(D), atomNear.distance(D)) / 1000;
} else {
bo = 2048;
}bsHBonds.set(this.addHBond(atom, atomNear, bo, energy));
nNew++;
}
}
iter.release();
this.sm.setShapeSizeBs(1, -2147483648, null, bsHBonds);
if (this.showRebondTimes) JU.Logger.checkTimer("hbond", false);
return (haveHAtoms ? nNew : -nNew);
}, "JU.BS,JU.BS,~B");
c$.checkMinAttachedAngle = Clazz.defineMethod(c$, "checkMinAttachedAngle", 
function(atom1, minAngle, v1, v2, haveHAtoms){
var bonds = atom1.bonds;
var ignore = true;
var X = null;
if (bonds != null && bonds.length > 0) {
var dMin = 3.4028235E38;
for (var i = bonds.length; --i >= 0; ) if (bonds[i].isCovalent()) {
ignore = false;
var atomA = bonds[i].getOtherAtom(atom1);
if (!haveHAtoms && atomA.getElementNumber() == 1) continue;
v2.sub2(atom1, atomA);
var d = v2.angle(v1);
if (d < minAngle) return null;
if (d < dMin) {
X = atomA;
dMin = d;
}}
}return (ignore ? JU.P3.new3(NaN, 0, 0) : X);
}, "JM.Atom,~N,JU.V3,JU.V3,~B");
Clazz.defineMethod(c$, "setStructureIndexes", 
function(){
var id;
var idnew = 0;
var lastid = -1;
var imodel = -1;
var lastmodel = -1;
for (var i = 0; i < this.ac; i++) {
if (JM.AtomCollection.isDeleted(this.at[i])) continue;
if ((imodel = this.at[i].mi) != lastmodel) {
idnew = 0;
lastmodel = imodel;
lastid = -1;
}if ((id = this.at[i].group.getStrucNo()) != lastid && id != 0) {
this.at[i].group.setStrucNo(++idnew);
lastid = idnew;
}}
});
Clazz.defineMethod(c$, "getModelInfoAsString", 
function(){
var sb =  new JU.SB().append("<models count=\"");
sb.appendI(this.mc).append("\" modelSetHasVibrationVectors=\"").append(this.modelSetHasVibrationVectors() + "\">\n<properties>");
if (this.modelSetProperties != null) {
var e = this.modelSetProperties.propertyNames();
while (e.hasMoreElements()) {
var propertyName = e.nextElement();
sb.append("\n <property name=\"").append(propertyName).append("\" value=").append(JU.PT.esc(this.modelSetProperties.getProperty(propertyName))).append(" />");
}
sb.append("\n</properties>");
}for (var i = 0; i < this.mc; ++i) {
sb.append("\n<model index=\"").appendI(i).append("\" n=\"").append(this.getModelNumberDotted(i)).append("\" id=").append(JU.PT.esc("" + this.getInfo(i, "modelID")));
var ib = this.vwr.getJDXBaseModelIndex(i);
if (ib != i) sb.append(" baseModelId=").append(JU.PT.esc(this.getInfo(ib, "jdxModelID")));
sb.append(" name=").append(JU.PT.esc(this.getModelName(i))).append(" title=").append(JU.PT.esc(this.getModelTitle(i))).append(" hasVibrationVectors=\"").appendB(this.vwr.modelHasVibrationVectors(i)).append("\" />");
}
sb.append("\n</models>");
return sb.toString();
});
Clazz.defineMethod(c$, "getSymmetryInfoAsString", 
function(){
var sb =  new JU.SB().append("Symmetry Information:");
for (var i = 0; i < this.mc; ++i) {
sb.append("\nmodel #").append(this.getModelNumberDotted(i)).append("; name=").append(this.getModelName(i)).append("\n");
var unitCell = this.getUnitCell(i);
sb.append(unitCell == null ? "no symmetry information" : unitCell.getSymmetryInfoStr());
}
return sb.toString();
});
Clazz.defineMethod(c$, "createModels", 
function(n){
var newModelCount = this.mc + n;
var newModels = JU.AU.arrayCopyObject(this.am, newModelCount);
this.validateBspf(false);
this.modelNumbers = JU.AU.arrayCopyI(this.modelNumbers, newModelCount);
this.modelFileNumbers = JU.AU.arrayCopyI(this.modelFileNumbers, newModelCount);
this.modelNumbersForAtomLabel = JU.AU.arrayCopyS(this.modelNumbersForAtomLabel, newModelCount);
this.modelNames = JU.AU.arrayCopyS(this.modelNames, newModelCount);
this.frameTitles = JU.AU.arrayCopyS(this.frameTitles, newModelCount);
var f = Clazz.doubleToInt(this.modelFileNumbers[this.mc - 1] / 1000000) + 1;
for (var i = this.mc, pt = 0; i < newModelCount; i++) {
this.modelNumbers[i] = i + this.mc;
this.modelFileNumbers[i] = f * 1000000 + (++pt);
this.modelNumbersForAtomLabel[i] = this.modelNames[i] = f + "." + pt;
}
this.thisStateModel = -1;
var group3Lists = this.getInfoM("group3Lists");
if (group3Lists != null) {
var group3Counts = this.getInfoM("group3Counts");
group3Lists = JU.AU.arrayCopyS(group3Lists, newModelCount);
group3Counts = JU.AU.arrayCopyII(group3Counts, newModelCount);
this.msInfo.put("group3Lists", group3Lists);
this.msInfo.put("group3Counts", group3Counts);
}this.unitCells = (this.unitCells == null ?  new Array(newModelCount) : JU.AU.arrayCopyObject(this.unitCells, newModelCount));
for (var i = this.mc; i < newModelCount; i++) {
newModels[i] =  new JM.Model().set(this, i, -1, null, null, null);
newModels[i].loadState = " model create #" + i + ";";
}
this.am = newModels;
this.mc = newModelCount;
this.vwr.setAnimationRange(-1, -1);
}, "~N");
Clazz.defineMethod(c$, "deleteAtoms", 
function(bs){
if (bs == null) return;
var bsModels = this.getModelBS(bs, false);
var bsBonds =  new JU.BS();
var doNull = false;
for (var i = bs.nextSetBit(0); i >= 0 && i < this.ac; i = bs.nextSetBit(i + 1)) {
if (JM.AtomCollection.isDeleted(this.at[i])) continue;
this.at[i].$delete(bsBonds);
if (doNull) this.at[i] = null;
}
var bsAtoms = JU.BSUtil.copy(bs);
for (var i = 0; i < this.mc; i++) {
var m = this.am[i];
m.resetDSSR(false);
m.bsAtomsDeleted.or(bs);
m.bsAtomsDeleted.and(m.bsAtoms);
if (m.bsAsymmetricUnit != null) m.bsAsymmetricUnit.andNot(bs);
if (bsModels.get(m.modelIndex)) {
this.updateBasisFromSite(m.modelIndex);
}bs = JU.BSUtil.andNot(m.bsAtoms, m.bsAtomsDeleted);
m.firstAtomIndex = bs.nextSetBit(0);
m.act = bs.cardinality();
m.isOrderly = (m.act == m.bsAtoms.length() - m.firstAtomIndex);
}
this.deleteBonds(bsBonds, false);
this.vwr.shm.notifyAtoms("atomsDeleted",  Clazz.newArray(-1, [bsAtoms, bsModels]));
this.validateBspf(false);
}, "JU.BS");
Clazz.defineMethod(c$, "clearDB", 
function(atomIndex){
this.getModelAuxiliaryInfo(this.at[atomIndex].mi).remove("dbName");
}, "~N");
Clazz.defineMethod(c$, "adjustAtomArrays", 
function(map, i0, ac){
this.ac = ac;
for (var i = i0; i < ac; i++) {
this.at[i] = this.at[map[i]];
this.at[i].i = i;
var m = this.am[this.at[i].mi];
if (m.firstAtomIndex == map[i]) m.firstAtomIndex = i;
m.bsAtoms.set(i);
}
if (this.vibrations != null) for (var i = i0; i < ac; i++) this.vibrations[i] = this.vibrations[map[i]];

if (this.atomTensorList != null) {
for (var i = i0; i < ac; i++) {
var list = this.atomTensorList[i] = this.atomTensorList[map[i]];
if (list != null) for (var j = list.length; --j >= 0; ) {
var t = list[j];
if (t != null) {
t.atomIndex1 = i;
}}
}
}if (this.atomNames != null) for (var i = i0; i < ac; i++) this.atomNames[i] = this.atomNames[map[i]];

if (this.atomTypes != null) for (var i = i0; i < ac; i++) this.atomTypes[i] = this.atomTypes[map[i]];

if (this.atomResnos != null) for (var i = i0; i < ac; i++) this.atomResnos[i] = this.atomResnos[map[i]];

if (this.atomSerials != null) for (var i = i0; i < ac; i++) this.atomSerials[i] = this.atomSerials[map[i]];

if (this.atomSeqIDs != null) for (var i = i0; i < ac; i++) this.atomSeqIDs[i] = this.atomSeqIDs[map[i]];

if (this.bfactor100s != null) for (var i = i0; i < ac; i++) this.bfactor100s[i] = this.bfactor100s[map[i]];

if (this.occupancies != null) for (var i = i0; i < ac; i++) this.occupancies[i] = this.occupancies[map[i]];

if (this.partialCharges != null) for (var i = i0; i < ac; i++) this.partialCharges[i] = this.partialCharges[map[i]];

}, "~A,~N,~N");
Clazz.defineMethod(c$, "growAtomArrays", 
function(newLength){
this.at = JU.AU.arrayCopyObject(this.at, newLength);
if (this.vibrations != null) this.vibrations = JU.AU.arrayCopyObject(this.vibrations, newLength);
if (this.occupancies != null) this.occupancies = JU.AU.arrayCopyF(this.occupancies, newLength);
if (this.bfactor100s != null) this.bfactor100s = JU.AU.arrayCopyShort(this.bfactor100s, newLength);
if (this.partialCharges != null) this.partialCharges = JU.AU.arrayCopyF(this.partialCharges, newLength);
if (this.atomTensorList != null) this.atomTensorList = JU.AU.arrayCopyObject(this.atomTensorList, newLength);
if (this.atomNames != null) this.atomNames = JU.AU.arrayCopyS(this.atomNames, newLength);
if (this.atomTypes != null) this.atomTypes = JU.AU.arrayCopyS(this.atomTypes, newLength);
if (this.atomResnos != null) this.atomResnos = JU.AU.arrayCopyI(this.atomResnos, newLength);
if (this.atomSerials != null) this.atomSerials = JU.AU.arrayCopyI(this.atomSerials, newLength);
if (this.atomSeqIDs != null) this.atomSeqIDs = JU.AU.arrayCopyI(this.atomSeqIDs, newLength);
}, "~N");
Clazz.defineMethod(c$, "addAtom", 
function(modelIndex, group, atomicAndIsotopeNumber, atomName, atomType, atomSerial, atomSeqID, atomSite, xyz, radius, vib, formalCharge, partialCharge, occupancy, bfactor, tensors, isHetero, specialAtomID, atomSymmetry, bondRadius){
var atom =  new JM.Atom().setAtom(modelIndex, this.ac, xyz, radius, atomSymmetry, atomSite, atomicAndIsotopeNumber, formalCharge, isHetero);
this.am[modelIndex].act++;
this.am[modelIndex].bsAtoms.set(this.ac);
if (JU.Elements.isElement(atomicAndIsotopeNumber, 1)) this.am[modelIndex].hydrogenCount++;
if (this.ac >= this.at.length) this.growAtomArrays(this.ac + 100);
this.at[this.ac] = atom;
this.setBFactor(this.ac, bfactor, false);
this.setOccupancy(this.ac, occupancy, false);
this.setPartialCharge(this.ac, partialCharge, false);
if (tensors != null) this.setAtomTensors(this.ac, tensors);
atom.group = group;
atom.colixAtom = this.vwr.cm.getColixAtomPalette(atom, J.c.PAL.CPK.id);
if (atomName != null) {
if (atomType != null) {
if (this.atomTypes == null) this.atomTypes =  new Array(this.at.length);
this.atomTypes[this.ac] = atomType;
}atom.atomID = specialAtomID;
if (specialAtomID == 0) {
if (this.atomNames == null) this.atomNames =  new Array(this.at.length);
this.atomNames[this.ac] = atomName.intern();
}}if (atomSerial != -2147483648) {
if (this.atomSerials == null) this.atomSerials =  Clazz.newIntArray (this.at.length, 0);
this.atomSerials[this.ac] = atomSerial;
}if (atomSeqID != 0) {
if (this.atomSeqIDs == null) this.atomSeqIDs =  Clazz.newIntArray (this.at.length, 0);
this.atomSeqIDs[this.ac] = atomSeqID;
}if (vib != null) this.setVibrationVector(this.ac, vib);
if (!Float.isNaN(bondRadius)) this.setBondingRadius(this.ac, bondRadius);
this.ac++;
return atom;
}, "~N,JM.Group,~N,~S,~S,~N,~N,~N,JU.P3,~N,JU.V3,~N,~N,~N,~N,JU.Lst,~B,~N,JU.BS,~N");
Clazz.defineMethod(c$, "getInlineData", 
function(modelIndex){
var data = null;
if (modelIndex >= 0) data = this.am[modelIndex].loadScript;
 else for (modelIndex = this.mc; --modelIndex >= 0; ) if ((data = this.am[modelIndex].loadScript).length() > 0) break;

var pt = data.lastIndexOf("data \"");
if (pt < 0) {
var s = JU.PT.getQuotedStringAt(data.toString(), 0);
return JS.ScriptCompiler.unescapeString(s, 0, s.length);
}pt = data.indexOf2("\"", pt + 7);
var pt2 = data.lastIndexOf("end \"");
if (pt2 < pt || pt < 0) return null;
return data.substring2(pt + 2, pt2);
}, "~N");
Clazz.defineMethod(c$, "isAtomPDB", 
function(i){
return i >= 0 && this.am[this.at[i].mi].isBioModel;
}, "~N");
Clazz.defineMethod(c$, "setAtomNamesAndNumbers", 
function(iFirst, baseAtomIndex, mergeSet, isModelKit){
var mi0 = -1;
if (isModelKit) {
while (iFirst < this.ac && JM.AtomCollection.isDeleted(this.at[iFirst])) iFirst++;

if (iFirst >= this.ac) return;
mi0 = this.at[iFirst].mi;
iFirst = this.am[mi0].firstAtomIndex;
}if (this.atomSerials == null) this.atomSerials =  Clazz.newIntArray (this.ac, 0);
if (this.atomNames == null) this.atomNames =  new Array(this.ac);
var isZeroBased = this.isXYZ && this.vwr.getBoolean(603979978);
var thisModelIndex = 2147483647;
var atomNo = 1;
for (var i = iFirst; i < this.ac; ++i) {
var atom = this.at[i];
if (JM.AtomCollection.isDeleted(atom)) continue;
if (atom.mi != thisModelIndex) {
if (isModelKit && thisModelIndex != 2147483647 && atom.mi != mi0) continue;
thisModelIndex = atom.mi;
atomNo = (isZeroBased ? 0 : 1);
}var ano = this.atomSerials[i];
if (i >= -baseAtomIndex) {
if (ano == 0 || isModelKit) this.atomSerials[i] = (i < baseAtomIndex ? mergeSet.atomSerials[i] : atomNo);
if (this.atomNames[i] == null || isModelKit) this.atomNames[i] = (atom.getElementSymbol() + this.atomSerials[i]).intern();
} else {
if (ano > atomNo) {
atomNo = ano;
}if (isModelKit) {
this.atomNames[i] = (atom.getElementSymbol() + ano).intern();
}}if (!this.am[thisModelIndex].isModelKit || atom.getElementNumber() > 0) atomNo++;
}
}, "~N,~N,JM.AtomCollection,~B");
Clazz.defineMethod(c$, "connect", 
function(connections){
this.resetMolecules();
var bsDelete =  new JU.BS();
for (var i = 0; i < connections.length; i++) {
var f = connections[i];
if (f == null || f.length < 2) continue;
var index1 = Clazz.floatToInt(f[0]);
var addGroup = (index1 < 0);
if (addGroup) index1 = -1 - index1;
var index2 = Clazz.floatToInt(f[1]);
if (index2 < 0 || index1 >= this.ac || index2 >= this.ac) continue;
var order = (f.length > 2 ? Clazz.floatToInt(f[2]) : 1);
if (order < 0) order &= 0xFFFF;
var mad = (f.length > 3 ? Clazz.floatToShort(1000 * connections[i][3]) : this.getDefaultMadFromOrder(order));
if (order == 0 || mad == 0 && order != 32768 && !JU.Edge.isOrderH(order)) {
var b = this.at[index1].getBond(this.at[index2]);
if (b != null) bsDelete.set(b.index);
continue;
}var energy = (f.length > 4 ? f[4] : 0);
this.bondAtoms(this.at[index1], this.at[index2], order, mad, null, energy, addGroup, true);
}
if (bsDelete.nextSetBit(0) >= 0) this.deleteBonds(bsDelete, false);
}, "~A");
Clazz.defineMethod(c$, "setFrameDelayMs", 
function(millis, bsModels){
for (var i = bsModels.nextSetBit(0); i >= 0; i = bsModels.nextSetBit(i + 1)) this.am[this.am[i].trajectoryBaseIndex].frameDelay = millis;

}, "~N,JU.BS");
Clazz.defineMethod(c$, "getFrameDelayMs", 
function(i){
return (i < this.am.length && i >= 0 ? this.am[this.am[i].trajectoryBaseIndex].frameDelay : 0);
}, "~N");
Clazz.defineMethod(c$, "getModelIndexFromId", 
function(id){
var haveFile = (id.indexOf("#") >= 0);
var isBaseModel = id.toLowerCase().endsWith(".basemodel");
if (isBaseModel) id = id.substring(0, id.length - 10);
var errCode = -1;
var fname = null;
for (var i = 0; i < this.mc; i++) {
var mid = this.getInfo(i, "modelID");
var mnum = (id.startsWith("~") ? "~" + this.getModelNumberDotted(i) : null);
if (mnum == null && mid == null && (mid = this.getModelTitle(i)) == null) continue;
if (haveFile) {
fname = this.getModelFileName(i);
if (fname.endsWith("#molfile")) {
mid = fname;
} else {
fname += "#";
mid = fname + mid;
}}if (id.equalsIgnoreCase(mid) || id.equalsIgnoreCase(mnum)) return (isBaseModel ? this.vwr.getJDXBaseModelIndex(i) : i);
if (fname != null && id.startsWith(fname)) errCode = -2;
}
return (fname == null && !haveFile ? -2 : errCode);
}, "~S");
Clazz.defineMethod(c$, "getModelSetAuxiliaryInfo", 
function(bsModels){
var info = this.msInfo;
if (info == null) info =  new java.util.Hashtable();
if (bsModels != null || !info.containsKey("models")) {
var minfo =  new JU.Lst();
for (var i = 0; i < this.mc; ++i) if (bsModels == null || bsModels.get(i)) {
var m = this.getModelAuxiliaryInfo(i);
m.put("modelIndex", Integer.$valueOf(i));
minfo.addLast(m);
}
info.put("models", minfo);
}return info;
}, "JU.BS");
Clazz.defineMethod(c$, "getDihedralMap", 
function(alist){
var list =  new JU.Lst();
var n = alist.length;
var ai = null;
var aj = null;
var ak = null;
var al = null;
for (var i = n - 1; --i >= 0; ) for (var j = n; --j > i; ) {
ai = this.at[alist[i]];
aj = this.at[alist[j]];
if (ai.isBonded(aj)) {
for (var k = n; --k >= 0; ) if (k != i && k != j && (ak = this.at[alist[k]]).isBonded(ai)) for (var l = n; --l >= 0; ) if (l != i && l != j && l != k && (al = this.at[alist[l]]).isBonded(aj)) {
var a =  Clazz.newIntArray (4, 0);
a[0] = ak.i;
a[1] = ai.i;
a[2] = aj.i;
a[3] = al.i;
list.addLast(a);
}

}}

n = list.size();
var ilist = JU.AU.newInt2(n);
for (var i = n; --i >= 0; ) ilist[n - i - 1] = list.get(i);

return ilist;
}, "~A");
Clazz.defineMethod(c$, "setModulation", 
function(bs, isOn, qtOffset, isQ){
if (this.bsModulated == null) {
if (isOn) this.bsModulated =  new JU.BS();
 else if (bs == null) return;
}if (bs == null) bs = this.getModelAtomBitSetIncludingDeleted(-1, false);
var scale = this.vwr.getFloat(1275072532);
var haveMods = false;
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var ms = this.getModulation(i);
if (ms == null) continue;
ms.setModTQ(this.at[i], isOn, qtOffset, isQ, scale);
if (this.bsModulated != null) this.bsModulated.setBitTo(i, isOn);
haveMods = true;
}
if (!haveMods) this.bsModulated = null;
}, "JU.BS,~B,JU.P3,~B");
Clazz.defineMethod(c$, "getBoundBoxOrientation", 
function(type, bsAtoms, points){
var dx = 0;
var dy = 0;
var dz = 0;
var q = null;
var qBest = null;
var j0 = bsAtoms.nextSetBit(0);
var vMin = 0;
if (j0 >= 0) {
if (this.vOrientations == null) {
var n = 0;
var p4 =  new JU.P4();
var av =  new Array(3375);
for (var i = -7; i <= 7; i++) for (var j = -7; j <= 7; j++) for (var k = 0; k <= 14; k++, n++) if ((av[n] = JU.V3.new3(i / 7, j / 7, k / 14)).length() > 1) --n;



this.vOrientations =  new Array(n);
for (var i = n; --i >= 0; ) {
p4.set4(av[i].x, av[i].y, av[i].z, 0);
this.vOrientations[i] = JU.Quat.newP4(p4);
}
for (var i = n; --i >= 0; ) {
var cos = Math.sqrt(1 - av[i].lengthSquared());
if (Float.isNaN(cos)) cos = 0;
p4.set4(av[i].x, av[i].y, av[i].z, cos);
this.vOrientations[i] = JU.Quat.newP4(p4);
}
}var pt =  new JU.P3();
vMin = 3.4028235E38;
var bBest = null;
var v;
var b =  new JU.BoxInfo();
b.setMargin(type == 1312817669 ? 0 : 0.1);
for (var i = this.vOrientations.length; --i >= 0; ) {
q = this.vOrientations[i];
b.reset();
if (points == null) {
for (var j = j0; j >= 0; j = bsAtoms.nextSetBit(j + 1)) {
var p = q.transform2(this.at[j], pt);
b.addBoundBoxPoint(p);
}
} else {
for (var j = points.length; --j >= 0; ) b.addBoundBoxPoint(q.transform2(points[j], pt));

}switch (type) {
default:
case 1312817669:
case 1073741864:
case 1814695966:
v = (b.bbCorner1.x - b.bbCorner0.x) * (b.bbCorner1.y - b.bbCorner0.y) * (b.bbCorner1.z - b.bbCorner0.z);
break;
case 1111492629:
v = b.bbCorner1.x - b.bbCorner0.x;
break;
case 1111492630:
v = b.bbCorner1.y - b.bbCorner0.y;
break;
case 1111492631:
v = b.bbCorner1.z - b.bbCorner0.z;
break;
}
if (v < vMin) {
qBest = q;
bBest = b;
b =  new JU.BoxInfo();
b.setMargin(0.1);
vMin = v;
}}
switch (type) {
default:
return qBest;
case 1814695966:
var pts = bBest.getBoundBoxVertices();
pts =  Clazz.newArray(-1, [pts[0], pts[4], pts[2], pts[1]]);
qBest = qBest.inv();
for (var i = 0; i < 4; i++) {
qBest.transform2(pts[i], pts[i]);
if (i > 0) pts[i].sub(pts[0]);
}
return pts;
case 1312817669:
case 1073741864:
q = JU.Quat.newQ(qBest);
dx = bBest.bbCorner1.x - bBest.bbCorner0.x;
dy = bBest.bbCorner1.y - bBest.bbCorner0.y;
dz = bBest.bbCorner1.z - bBest.bbCorner0.z;
if (dx < dy) {
pt.set(0, 0, 1);
q = JU.Quat.newVA(pt, 90).mulQ(q);
var f = dx;
dx = dy;
dy = f;
}if (dy < dz) {
if (dz > dx) {
pt.set(0, 1, 0);
q = JU.Quat.newVA(pt, 90).mulQ(q);
var f = dx;
dx = dz;
dz = f;
}pt.set(1, 0, 0);
q = JU.Quat.newVA(pt, 90).mulQ(q);
var f = dy;
dy = dz;
dz = f;
}break;
}
}return (type == 1312817669 ? vMin + "\t{" + dx + " " + dy + " " + dz + "}\t" + bsAtoms : type == 1814695966 ? null : q == null || q.getTheta() == 0 ?  new JU.Quat() : q);
}, "~N,JU.BS,~A");
Clazz.defineMethod(c$, "getUnitCellForAtom", 
function(index){
if (index < 0 || index > this.ac || this.at[index] == null) return null;
if (this.bsModulated != null) {
var ms = this.getModulation(index);
var uc = (ms == null ? null : ms.getSubSystemUnitCell());
if (uc != null) return uc;
}return this.getUnitCell(this.at[index].mi);
}, "~N");
Clazz.defineMethod(c$, "clearCache", 
function(){
for (var i = this.mc; --i >= 0; ) this.am[i].resetDSSR(false);

});
Clazz.defineMethod(c$, "getSymMatrices", 
function(modelIndex){
var n = this.getModelSymmetryCount(modelIndex);
if (n == 0) return null;
var ops =  new Array(n);
var unitcell = this.am[modelIndex].biosymmetry;
if (unitcell == null) unitcell = this.getUnitCell(modelIndex);
for (var i = n; --i >= 0; ) ops[i] = unitcell.getSpaceGroupOperation(i);

return ops;
}, "~N");
Clazz.defineMethod(c$, "getSymmetryInvariant", 
function(iatom){
var a = this.getBasisAtom(iatom, true);
if (a == null) return  Clazz.newIntArray (0, 0);
return this.getUnitCellForAtom(a.i).getInvariantSymops(a, null);
}, "~N");
Clazz.defineMethod(c$, "getBsBranches", 
function(dihedralList){
var n = Clazz.doubleToInt(dihedralList.length / 6);
var bsBranches =  new Array(n);
var map =  new java.util.Hashtable();
for (var i = 0, pt = 0; i < n; i++, pt += 6) {
var dv = dihedralList[pt + 5] - dihedralList[pt + 4];
if (Math.abs(dv) < 1) continue;
var i0 = Clazz.floatToInt(dihedralList[pt + 1]);
var i1 = Clazz.floatToInt(dihedralList[pt + 2]);
var s = "" + i0 + "_" + i1;
if (map.containsKey(s)) continue;
map.put(s, Boolean.TRUE);
var bs = this.vwr.getBranchBitSet(i1, i0, true);
var bonds = this.at[i0].bonds;
var a0 = this.at[i0];
for (var j = 0; j < bonds.length; j++) {
var b = bonds[j];
if (!b.isCovalent()) continue;
var i2 = b.getOtherAtom(a0).i;
if (i2 == i1) continue;
if (bs.get(i2)) {
bs = null;
break;
}}
bsBranches[i] = bs;
}
return bsBranches;
}, "~A");
Clazz.defineMethod(c$, "recalculatePositionDependentQuantities", 
function(bsAtoms, mat){
if ((this.vwr.shm.getShape(21) != null)) this.vwr.shm.getShapePropertyData(21, "move",  Clazz.newArray(-1, [bsAtoms, mat]));
if (this.haveStraightness) this.calculateStraightnessAll();
this.recalculateLeadMidpointsAndWingVectors(-1);
var bsModels = this.getModelBS(bsAtoms, false);
for (var i = bsModels.nextSetBit(0); i >= 0; i = bsModels.nextSetBit(i + 1)) {
this.sm.notifyAtomPositionsChanged(i, bsAtoms, mat);
if (mat != null) {
var m = this.am[i];
if (m.isContainedIn(bsAtoms)) {
if (m.mat4 == null) m.mat4 = JU.M4.newM4(null);
m.mat4.mul2(mat, m.mat4);
}}}
}, "JU.BS,JU.M4");
Clazz.defineMethod(c$, "moveAtoms", 
function(m4, mNew, rotation, translation, bs, center, isInternal, translationOnly){
if (m4 != null) {
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
m4.rotTrans(this.at[i]);
this.taintAtom(i, 2);
}
this.mat4.setM4(m4);
translation = null;
} else if (translationOnly) {
if (!isInternal) {
this.matInv.setM3(rotation);
this.matInv.invert();
this.matInv.rotate(translation);
}} else {
if (mNew == null) {
this.matTemp.setM3(rotation);
} else {
this.ptTemp.set(0, 0, 0);
this.matInv.setM3(rotation);
this.matInv.invert();
this.matTemp.mul2(mNew, rotation);
this.matTemp.mul2(this.matInv, this.matTemp);
}if (isInternal) {
this.vTemp.setT(center);
this.mat4.setIdentity();
this.mat4.setTranslation(this.vTemp);
this.mat4t.setToM3(this.matTemp);
this.mat4.mul(this.mat4t);
this.mat4t.setIdentity();
this.vTemp.scale(-1);
this.mat4t.setTranslation(this.vTemp);
this.mat4.mul(this.mat4t);
} else {
this.mat4.setToM3(this.matTemp);
}for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
if (isInternal) {
this.mat4.rotTrans(this.at[i]);
} else {
this.ptTemp.add(this.at[i]);
this.mat4.rotTrans(this.at[i]);
this.ptTemp.sub(this.at[i]);
}this.taintAtom(i, 2);
}
if (!isInternal) {
this.ptTemp.scale(1 / bs.cardinality());
if (translation == null) translation =  new JU.V3();
translation.add(this.ptTemp);
}}if (translation != null) {
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
this.at[i].add(translation);
this.taintAtom(i, 2);
}
if (!translationOnly) {
this.mat4t.setIdentity();
this.mat4t.setTranslation(translation);
this.mat4.mul2(this.mat4t, this.mat4);
}}this.recalculatePositionDependentQuantities(bs, this.mat4);
}, "JU.M4,JU.M3,JU.M3,JU.V3,JU.BS,JU.P3,~B,~B");
Clazz.defineMethod(c$, "setDihedrals", 
function(dihedralList, bsBranches, f){
var n = Clazz.doubleToInt(dihedralList.length / 6);
if (f > 1) f = 1;
for (var j = 0, pt = 0; j < n; j++, pt += 6) {
var bs = bsBranches[j];
if (bs == null || bs.isEmpty()) continue;
var a1 = this.at[Clazz.floatToInt(dihedralList[pt + 1])];
var v = JU.V3.newVsub(this.at[Clazz.floatToInt(dihedralList[pt + 2])], a1);
var angle = (dihedralList[pt + 5] - dihedralList[pt + 4]) * f;
var aa = JU.A4.newVA(v, (-angle / 57.29577951308232));
this.matTemp.setAA(aa);
this.ptTemp.setT(a1);
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
this.at[i].sub(this.ptTemp);
this.matTemp.rotate(this.at[i]);
this.at[i].add(this.ptTemp);
this.taintAtom(i, 2);
}
}
}, "~A,~A,~N");
Clazz.defineMethod(c$, "setAtomCoordsRelative", 
function(offset, bs){
this.setAtomsCoordRelative(bs, offset.x, offset.y, offset.z);
this.mat4.setIdentity();
this.vTemp.setT(offset);
this.mat4.setTranslation(this.vTemp);
this.recalculatePositionDependentQuantities(bs, this.mat4);
}, "JU.T3,JU.BS");
Clazz.defineMethod(c$, "setAtomCoords", 
function(bs, tokType, xyzValues){
this.setAtomCoord2(bs, tokType, xyzValues);
switch (tokType) {
case 1111492626:
case 1111492627:
case 1111492628:
case 1145047055:
break;
default:
this.recalculatePositionDependentQuantities(bs, null);
}
}, "JU.BS,~N,~O");
Clazz.defineMethod(c$, "invertSelected", 
function(pt, plane, iAtom, bsAtoms){
this.resetChirality();
if (pt != null) {
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
var x = (pt.x - this.at[i].x) * 2;
var y = (pt.y - this.at[i].y) * 2;
var z = (pt.z - this.at[i].z) * 2;
this.setAtomCoordRelative(i, x, y, z);
}
return;
}if (plane != null) {
var norm = JU.V3.new3(plane.x, plane.y, plane.z);
norm.normalize();
var d = Math.sqrt(plane.x * plane.x + plane.y * plane.y + plane.z * plane.z);
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
var twoD = -JU.Measure.distanceToPlaneD(plane, d, this.at[i]) * 2;
var x = norm.x * twoD;
var y = norm.y * twoD;
var z = norm.z * twoD;
this.setAtomCoordRelative(i, x, y, z);
}
return;
}if (iAtom >= 0) {
var thisAtom = this.at[iAtom];
var bonds = thisAtom.bonds;
if (bonds == null) return;
var bsToMove =  new JU.BS();
var vNot =  new JU.Lst();
var bsModel = this.vwr.getModelUndeletedAtomsBitSet(thisAtom.mi);
for (var i = 0; i < bonds.length; i++) {
var a = bonds[i].getOtherAtom(thisAtom);
if (bsAtoms.get(a.i)) {
bsToMove.or(JU.JmolMolecule.getBranchBitSet(this.at, a.i, bsModel, null, iAtom, true, true));
} else {
vNot.addLast(a);
}}
if (vNot.size() == 0) return;
pt = JU.Measure.getCenterAndPoints(vNot)[0];
var v = JU.V3.newVsub(thisAtom, pt);
var q = JU.Quat.newVA(v, 180);
this.moveAtoms(null, null, q.getMatrix(), null, bsToMove, thisAtom, true, false);
}}, "JU.P3,JU.P4,~N,JU.BS");
Clazz.defineMethod(c$, "getCellWeights", 
function(bsAtoms){
var wts = null;
var i = bsAtoms.nextSetBit(0);
var iModel = -1;
var sym;
var a;
if (i >= 0 && (sym = this.getUnitCell(iModel = (a = this.at[i]).mi)) != null) {
sym = sym.getUnitCellMultiplied();
var bs = this.getModelAtomBitSetIncludingDeleted(iModel, true);
bs.and(bsAtoms);
wts =  Clazz.newFloatArray (bsAtoms.cardinality(), 0);
var pt =  new JU.P3();
for (var p = 0; i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
a = this.at[i];
pt.setT(a);
sym.toFractional(pt, false);
sym.unitize(pt);
wts[p++] = sym.getCellWeight(pt);
}
}return wts;
}, "JU.BS");
Clazz.defineMethod(c$, "getAtomGroupQuaternions", 
function(bsAtoms, nMax, qtype){
var n = 0;
var v =  new JU.Lst();
bsAtoms = JU.BSUtil.copy(bsAtoms);
var bsDone =  new JU.BS();
for (var i = bsAtoms.nextSetBit(0); i >= 0 && n < nMax; i = bsAtoms.nextSetBit(i + 1)) {
var g = this.at[i].group;
g.setAtomBits(bsDone);
bsAtoms.andNot(bsDone);
var q = g.getQuaternion(qtype);
if (q == null) {
if (!this.am[this.at[i].mi].isBioModel) q = g.getQuaternionFrame(this.at);
if (q == null) continue;
}n++;
v.addLast(q);
}
return v.toArray( new Array(v.size()));
}, "JU.BS,~N,~S");
Clazz.defineMethod(c$, "getConformation", 
function(modelIndex, conformationIndex, doSet, bsSelected){
var bs =  new JU.BS();
for (var i = this.mc; --i >= 0; ) {
if (modelIndex >= 0 && i != modelIndex) continue;
var m = this.am[i];
var bsAtoms = this.vwr.getModelUndeletedAtomsBitSet(modelIndex);
if (bsSelected != null) bsAtoms.and(bsSelected);
if (bsAtoms.nextSetBit(0) < 0) continue;
if (conformationIndex > m.altLocCount) {
if (conformationIndex == 1) bs.or(bsAtoms);
continue;
}var c0;
if (this.am[i].isBioModel) {
if (conformationIndex < -1000) {
c0 = 1000 + conformationIndex;
var altLocs = this.getAltLocListInModel(i);
if (c0 != -32 && altLocs.indexOf(String.fromCharCode(-c0)) < 0) c0 = -2147483648;
} else if (conformationIndex < 0) {
var altLocs = this.getAltLocListInModel(i);
c0 = -1 - conformationIndex;
c0 = (c0 >= altLocs.length ? -2147483648 : -(altLocs.charAt(c0)).charCodeAt(0));
} else {
c0 = conformationIndex;
}if (c0 == -2147483648) continue;
(this.am[i]).getConformation(c0, doSet, bsAtoms, bs);
} else {
var nAltLocs = this.getAltLocCountInModel(i);
var altLocs = this.getAltLocListInModel(i);
var bsTemp =  new JU.BS();
if (conformationIndex < -1000) {
var c = String.fromCharCode(-1000 - conformationIndex);
c0 = altLocs.indexOf(c);
} else {
c0 = Math.abs(conformationIndex) - 1;
}if (c0 < 0 || c0 >= nAltLocs) {
continue;
}for (var c = nAltLocs; --c >= 0; ) if (c != c0) bsAtoms.andNot(this.getAtomBitsMDa(1073742355, altLocs.substring(c, c + 1), bsTemp));

}bs.or(bsAtoms);
}
return bs;
}, "~N,~N,~B,JU.BS");
Clazz.defineMethod(c$, "getSequenceBits", 
function(specInfo, bsAtoms, bsResult){
return (this.haveBioModels ? this.bioModelset.getAllSequenceBits(specInfo, bsAtoms, bsResult) : bsResult);
}, "~S,JU.BS,JU.BS");
Clazz.defineMethod(c$, "getBioPolymerCountInModel", 
function(modelIndex){
return (this.haveBioModels ? this.bioModelset.getBioPolymerCountInModel(modelIndex) : 0);
}, "~N");
Clazz.defineMethod(c$, "getPolymerPointsAndVectors", 
function(bs, vList, isTraceAlpha, sheetSmoothing){
if (this.haveBioModels) this.bioModelset.getAllPolymerPointsAndVectors(bs, vList, isTraceAlpha, sheetSmoothing);
}, "JU.BS,JU.Lst,~B,~N");
Clazz.defineMethod(c$, "recalculateLeadMidpointsAndWingVectors", 
function(modelIndex){
if (this.haveBioModels) this.bioModelset.recalculatePoints(modelIndex);
}, "~N");
Clazz.defineMethod(c$, "calcRasmolHydrogenBonds", 
function(bsA, bsB, vHBonds, nucleicOnly, nMax, dsspIgnoreHydrogens, bsHBonds){
if (this.haveBioModels) this.bioModelset.calcAllRasmolHydrogenBonds(bsA, bsB, vHBonds, nucleicOnly, nMax, dsspIgnoreHydrogens, bsHBonds, 2);
}, "JU.BS,JU.BS,JU.Lst,~B,~N,~B,JU.BS");
Clazz.defineMethod(c$, "calculateStraightnessAll", 
function(){
if (this.haveBioModels && !this.haveStraightness) this.bioModelset.calculateStraightnessAll();
});
Clazz.defineMethod(c$, "calculateStruts", 
function(bs1, bs2){
return (this.haveBioModels ? this.bioModelset.calculateStruts(bs1, bs2) : 0);
}, "JU.BS,JU.BS");
Clazz.defineMethod(c$, "getGroupsWithin", 
function(nResidues, bs){
return (this.haveBioModels ? this.bioModelset.getGroupsWithinAll(nResidues, bs) :  new JU.BS());
}, "~N,JU.BS");
Clazz.defineMethod(c$, "getProteinStructureState", 
function(bsAtoms, mode){
return (this.haveBioModels ? this.bioModelset.getFullProteinStructureState(bsAtoms, mode) : "");
}, "JU.BS,~N");
Clazz.defineMethod(c$, "calculateStructures", 
function(bsAtoms, asDSSP, doReport, dsspIgnoreHydrogen, setStructure, version){
return (this.haveBioModels ? this.bioModelset.calculateAllStuctures(bsAtoms, asDSSP, doReport, dsspIgnoreHydrogen, setStructure, version) : "");
}, "JU.BS,~B,~B,~B,~B,~N");
Clazz.defineMethod(c$, "calculateStructuresAllExcept", 
function(alreadyDefined, asDSSP, doReport, dsspIgnoreHydrogen, setStructure, includeAlpha, version){
this.freezeModels();
return (this.haveBioModels ? this.bioModelset.calculateAllStructuresExcept(alreadyDefined, asDSSP, doReport, dsspIgnoreHydrogen, setStructure, includeAlpha, version) : "");
}, "JU.BS,~B,~B,~B,~B,~B,~N");
Clazz.defineMethod(c$, "recalculatePolymers", 
function(bsModelsExcluded){
this.bioModelset.recalculateAllPolymers(bsModelsExcluded, this.getGroups());
}, "JU.BS");
Clazz.defineMethod(c$, "calculatePolymers", 
function(groups, groupCount, baseGroupIndex, modelsExcluded){
if (this.bioModelset != null) this.bioModelset.calculateAllPolymers(groups, groupCount, baseGroupIndex, modelsExcluded);
}, "~A,~N,~N,JU.BS");
Clazz.defineMethod(c$, "calcSelectedMonomersCount", 
function(){
if (this.haveBioModels) this.bioModelset.calcSelectedMonomersCount();
});
Clazz.defineMethod(c$, "setProteinType", 
function(bs, type){
if (this.haveBioModels) this.bioModelset.setAllProteinType(bs, type);
}, "JU.BS,J.c.STR");
Clazz.defineMethod(c$, "setStructureList", 
function(structureList){
if (this.haveBioModels) this.bioModelset.setAllStructureList(structureList);
}, "java.util.Map");
Clazz.defineMethod(c$, "setConformation", 
function(bsAtoms){
if (this.haveBioModels) this.bioModelset.setAllConformation(bsAtoms);
return JU.BSUtil.copy(bsAtoms);
}, "JU.BS");
Clazz.defineMethod(c$, "getHeteroList", 
function(modelIndex){
var o = (this.haveBioModels ? this.bioModelset.getAllHeteroList(modelIndex) : null);
return (o == null ? this.getInfoM("hetNames") : o);
}, "~N");
Clazz.defineMethod(c$, "getUnitCellPointsWithin", 
function(distance, bs, pt, asMap){
var lst =  new JU.Lst();
var map = null;
var lstI = null;
if (asMap) {
map =  new java.util.Hashtable();
lstI =  new JU.Lst();
map.put("atoms", lstI);
map.put("points", lst);
}var iAtom = (bs == null ? -1 : bs.nextSetBit(0));
bs = this.vwr.getModelUndeletedAtomsBitSet(iAtom < 0 ? this.vwr.am.cmi : this.at[iAtom].mi);
if (iAtom < 0) iAtom = bs.nextSetBit(0);
if (iAtom >= 0) {
var unitCell = this.getUnitCellForAtom(iAtom);
if (unitCell != null) {
var iter = unitCell.getIterator(this.vwr, this.at[iAtom], bs, distance);
if (pt != null) iter.setCenter(pt, distance);
while (iter.hasNext()) {
iAtom = iter.next();
pt = iter.getPosition();
lst.addLast(pt);
if (asMap) {
lstI.addLast(Integer.$valueOf(iAtom));
}}
}}return (asMap ? map : lst);
}, "~N,JU.BS,JU.P3,~B");
Clazz.defineMethod(c$, "calculateDssrProperty", 
function(dataType){
if (dataType == null) return;
if (this.dssrData == null || this.dssrData.length < this.ac) this.dssrData =  Clazz.newFloatArray (this.ac, 0);
for (var i = 0; i < this.ac; i++) this.dssrData[i] = NaN;

for (var i = this.mc; --i >= 0; ) if (this.am[i].isBioModel) (this.am[i]).getAtomicDSSRData(this.dssrData, dataType);

}, "~S");
Clazz.defineMethod(c$, "getAtomicDSSRData", 
function(i){
return (this.dssrData == null || this.dssrData.length <= i ? NaN : this.dssrData[i]);
}, "~N");
Clazz.defineMethod(c$, "getAtomCIPChiralityCode", 
function(atom){
this.haveChirality = true;
var m = this.am[atom.mi];
if (!m.hasChirality) {
this.calculateChiralityForAtoms(m.bsAtoms, false);
m.hasChirality = true;
}return atom.getCIPChiralityCode();
}, "JM.Atom");
Clazz.defineMethod(c$, "calculateChiralityForAtoms", 
function(bsAtoms, withReturn){
this.haveChirality = true;
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) this.at[i].setCIPChirality(0);

J.api.Interface.getSymmetry(this.vwr, "ms").calculateCIPChiralityForAtoms(this.vwr, bsAtoms);
if (!withReturn) return null;
var s = "";
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) s += this.at[i].getCIPChirality(false);

return s;
}, "JU.BS,~B");
Clazz.defineMethod(c$, "getPointTransf", 
function(i, a, q, pTemp){
if (this.isTrajectory(i >= 0 ? i : a.mi)) this.trajectory.getFractional(a, pTemp);
 else pTemp.setT(a);
if (q != null) q.transform2(pTemp, pTemp);
}, "~N,JM.Atom,JU.Quat,JU.P3");
Clazz.defineMethod(c$, "getSymmetryEquivAtoms", 
function(bsAtoms, sym, bsModelAtoms){
bsAtoms = JU.BS.copy(bsAtoms);
var bsEquiv = JU.BS.copy(bsAtoms);
var iAtom = bsAtoms.nextSetBit(0);
if (sym == null) sym = this.getUnitCellForAtom(iAtom);
if (sym != null) {
if (bsModelAtoms == null) bsModelAtoms = this.vwr.getModelUndeletedAtomsBitSet(this.at[iAtom].mi);
var bsRemaining = JU.BSUtil.copy(bsModelAtoms);
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
this.getSymmetryEquivAtomsForAtom(i, bsAtoms, bsRemaining, bsEquiv);
}
}return bsEquiv;
}, "JU.BS,J.api.SymmetryInterface,JU.BS");
Clazz.defineMethod(c$, "getSymmetryEquivAtomsForAtom", 
function(i, bsAtoms, bsCheck, bsEquiv){
var a = this.at[i];
var site = a.getAtomSite();
if (site > 0) {
for (var j = bsCheck.nextSetBit(0); j >= 0; j = bsCheck.nextSetBit(j + 1)) {
if (this.at[j].getAtomSite() == site) {
bsEquiv.set(j);
if (bsAtoms != null) {
bsAtoms.clear(j);
bsCheck.clear(j);
}}}
} else {
}}, "~N,JU.BS,JU.BS,JU.BS");
Clazz.defineMethod(c$, "setSpaceGroup", 
function(mi, sg, basis){
if (this.unitCells == null) this.unitCells =  new Array(this.mc);
this.unitCells[mi] = sg;
this.haveUnitCells = true;
var isP1 = (sg.getSpaceGroupOperationCount() == 1);
var nops = sg.getFinalOperationCount();
if (basis != null) {
var needBasis = basis.isEmpty();
var bs = this.vwr.getModelUndeletedAtomsBitSet(mi);
if (needBasis) {
basis = JU.BSUtil.copy(bs);
} else {
this.setAsymmetricUnit(mi, bs, basis, !isP1);
}if (nops > 1) this.setModelCage(mi, null);
var nid = (this.atomSeqIDs == null ? 0 : this.atomSeqIDs.length);
if (nid > 0) {
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
this.atomSeqIDs[i] = 0;
}
}if (isP1) {
this.fixP1AtomSites(sg, bs);
} else {
var haveOccupancies = (this.occupancies != null);
var ops = sg.getSymmetryOperations();
var a =  new JU.P3();
var b =  new JU.P3();
var t =  new JU.P3();
var site = 0;
for (var j = basis.nextSetBit(0); j >= 0; j = basis.nextSetBit(j + 1)) {
var bb = this.at[j];
b.setT(bb);
sg.toFractional(b, false);
sg.unitize(b);
if (needBasis) this.setSite(bb, ++site, true);
site = bb.atomSite;
bs.clear(j);
var occj = (haveOccupancies ? this.occupancies[j] : 0);
out : for (var i = bs.nextSetBit(needBasis ? j + 1 : 0); i >= 0; i = bs.nextSetBit(i + 1)) {
var ba = this.at[i];
var type = ba.atomNumberFlags;
if (ba.atomNumberFlags != type || haveOccupancies && occj != this.occupancies[i]) continue;
a.setT(ba);
sg.toFractional(a, false);
sg.unitize(a);
for (var k = 0; k < nops; k++) {
t.setT(b);
ops[k].rotTrans(t);
sg.unitize(t);
if (t.distanceSquared(a) < 1.96E-6) {
this.setSite(ba, site, true);
bs.clear(i);
basis.clear(i);
continue out;
}}
}
}
if (!bs.isEmpty()) {
System.err.println("Model basis atoms not found for " + bs);
}if (needBasis) {
this.setAsymmetricUnit(mi, null, basis, !isP1);
}}}this.setInfo(mi, "unitCellParams", sg.getUnitCellParams());
this.setInfo(mi, "spaceGroupAssigned", Boolean.TRUE);
this.setInfo(mi, "spaceGroup", sg.getClegId());
this.setInfo(mi, "spaceGroupInfo", null);
if (this.am[mi].simpleCage != null) {
sg.getUnitCell(this.am[mi].simpleCage.getUnitCellVectors(), false, null);
this.setInfo(mi, "unitCellParams", sg.getUnitCellParams());
}this.setModelCage(mi, null);
}, "~N,J.api.SymmetryInterface,JU.BS");
Clazz.defineMethod(c$, "setAsymmetricUnit", 
function(mi, bsModelAtoms, basis, haveSymmetry){
if (bsModelAtoms == null) bsModelAtoms = this.vwr.getModelUndeletedAtomsBitSet(mi);
this.am[mi].bsAsymmetricUnit = basis;
if (this.bsSymmetry == null) this.bsSymmetry = JU.BS.newN(this.ac);
this.bsSymmetry.or(bsModelAtoms);
this.bsSymmetry.andNot(basis);
if (haveSymmetry) {
for (var p = 0, i = bsModelAtoms.nextSetBit(0); i >= 0; i = bsModelAtoms.nextSetBit(i + 1)) {
var isBasis = basis.get(i);
this.at[i].setSymop(isBasis ? 1 : 0, false);
if (isBasis) this.setSite(this.at[i], ++p, false);
}
bsModelAtoms.andNot(basis);
}}, "~N,JU.BS,JU.BS,~B");
Clazz.defineMethod(c$, "setModelCage", 
function(modelIndex, simpleCage){
if (modelIndex >= 0 && modelIndex < this.mc) {
this.am[modelIndex].setSimpleCage(simpleCage);
this.haveUnitCells = true;
}return simpleCage;
}, "~N,J.api.SymmetryInterface");
Clazz.defineMethod(c$, "fixP1AtomSites", 
function(sym, bsAtoms){
if (sym == null || sym.getSpaceGroupOperationCount() != 1) return;
var n = bsAtoms.cardinality();
var baseAtoms =  new Array(n);
var nbase = 0;
var slop2 = sym.getPrecision();
slop2 *= slop2;
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
var a = this.at[i];
var p =  new JU.A4();
p.setT(a);
sym.toFractional(p, false);
sym.unitize(p);
var found = false;
for (var ib = 0; ib < nbase; ib++) {
var b = baseAtoms[ib];
if (a.atomNumberFlags == b.angle && b.distanceSquared(p) < slop2) {
found = true;
this.setSite(a, ib + 1, true);
break;
}}
if (!found) {
p.angle = a.atomNumberFlags;
baseAtoms[nbase] = p;
this.setSite(a, ++nbase, true);
}}
}, "J.api.SymmetryInterface,JU.BS");
Clazz.defineMethod(c$, "getBasisAtom", 
function(iatom, doCheck){
var a = this.at[iatom];
if (!doCheck || this.getUnitCellForAtom(iatom) != null) {
var site = a.atomSite;
if (site > 0) {
var au = this.am[a.mi].bsAsymmetricUnit;
if (au != null) {
for (var i = au.nextSetBit(0); i >= 0; i = au.nextSetBit(i + 1)) {
if (this.at[i].atomSite == site) return this.at[i];
}
}}}return a;
}, "~N,~B");
Clazz.defineMethod(c$, "updateBasisFromSite", 
function(imodel){
if (this.getUnitCell(imodel) == null) return;
var bsAU = this.am[imodel].bsAsymmetricUnit;
if (bsAU == null) return;
bsAU.clearAll();
var bsSites =  new JU.BS();
var bs = this.am[imodel].bsAtoms;
var sites =  Clazz.newIntArray (this.ac, 0);
for (var p = 0, i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
if (JM.AtomCollection.isDeleted(this.at[i])) continue;
var site = this.at[i].atomSite;
if (!bsSites.get(site)) {
bsSites.set(site);
if (site >= sites.length) continue;
sites[site] = ++p;
bsAU.set(i);
}this.setSite(this.at[i], -1, false);
this.setSite(this.at[i], sites[site], true);
}
if (this.bsSymmetry == null) this.bsSymmetry = JU.BS.newN(this.ac);
this.bsSymmetry.or(bs);
this.bsSymmetry.andNot(bsAU);
}, "~N");
Clazz.defineMethod(c$, "getConnectingAtoms", 
function(bsAtoms, bsFixed){
var bs =  new JU.BS();
var bsAttached =  new JU.BS();
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
var a = this.at[i];
var bonds = a.bonds;
for (var k = 0, j = a.getBondCount(); --j >= 0; ) {
if (bonds[j].isCovalent() && !bsAtoms.get(k = bonds[j].getOtherAtom(a).i)) {
bs.set(i);
bsAttached.set(k);
}}
}
bsAtoms.or(bsAttached);
bsFixed.or(bsAttached);
return bs;
}, "JU.BS,JU.BS");
Clazz.defineMethod(c$, "saveAtomPositions", 
function(){
var pos =  new Array(this.at.length);
for (var i = pos.length; --i >= 0; ) {
var a = this.at[i];
if (!JM.AtomCollection.isDeleted(a)) pos[i] = JU.P3.newP(a);
}
return pos;
});
Clazz.defineMethod(c$, "restoreAtomPositions", 
function(apos0){
for (var i = apos0.length; --i >= 0; ) {
var a = this.at[i];
if (!JM.AtomCollection.isDeleted(a)) a.setT(apos0[i]);
}
}, "~A");
Clazz.defineMethod(c$, "clearUnitCell", 
function(modelIndex){
if (this.unitCells == null) return;
if (modelIndex < 0) {
for (var i = 0; i < this.mc; i++) this.clearUnitCell(i);

} else {
this.am[modelIndex].simpleCage = null;
if (modelIndex < this.unitCells.length) {
this.unitCells[modelIndex] = null;
var info = this.getModelAuxiliaryInfo(modelIndex);
var it = info.entrySet().iterator();
while (it.hasNext()) {
if (JV.JC.isSpaceGroupInfoKey(it.next().getKey())) it.remove();
}
if (this.mc > 1) return;
}}this.unitCells = null;
this.haveUnitCells = false;
}, "~N");
c$.hbondMinRasmol = 2.5;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
