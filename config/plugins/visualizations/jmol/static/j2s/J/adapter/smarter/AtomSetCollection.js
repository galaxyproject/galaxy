Clazz.declarePackage("J.adapter.smarter");
Clazz.load(["java.util.Hashtable"], "J.adapter.smarter.AtomSetCollection", ["java.util.Collections", "$.Properties", "JU.AU", "$.BS", "$.Lst", "$.P3", "$.V3", "J.adapter.smarter.Atom", "$.Bond", "$.SmarterJmolAdapter", "J.api.Interface", "JU.BSUtil", "$.Logger", "JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.reader = null;
this.bsAtoms = null;
this.fileTypeName = null;
this.collectionName = null;
this.atomSetInfo = null;
this.atoms = null;
this.ac = 0;
this.bonds = null;
this.bondCount = 0;
this.structures = null;
this.structureCount = 0;
this.atomSetCount = 0;
this.iSet = -1;
this.atomSetNumbers = null;
this.atomSetAtomIndexes = null;
this.atomSetAtomCounts = null;
this.atomSetBondCounts = null;
this.atomSetAuxiliaryInfo = null;
this.errorMessage = null;
this.coordinatesAreFractional = false;
this.isTrajectory = false;
this.trajectoryStepCount = 0;
this.trajectorySteps = null;
this.vibrationSteps = null;
this.trajectoryNames = null;
this.doFixPeriodic = false;
this.allowMultiple = false;
this.readerList = null;
this.atomMapAnyCase = false;
this.fixedSite = 0;
this.bsStructuredModels = null;
this.haveAnisou = false;
this.baseSymmetryAtomCount = 0;
this.crystalReaderLatticeOpsOnly = false;
this.xtalSymmetry = null;
this.bondIndex0 = 0;
this.atomSymbolicMap = null;
this.haveUnitCell = false;
this.vibScale = 0;
this.firstAtomToBond = -1;
Clazz.instantialize(this, arguments);}, J.adapter.smarter, "AtomSetCollection", null);
Clazz.prepareFields (c$, function(){
this.atomSetInfo =  new java.util.Hashtable();
this.atoms =  new Array(256);
this.bonds =  new Array(256);
this.structures =  new Array(16);
this.atomSetNumbers =  Clazz.newIntArray (16, 0);
this.atomSetAtomIndexes =  Clazz.newIntArray (16, 0);
this.atomSetAtomCounts =  Clazz.newIntArray (16, 0);
this.atomSetBondCounts =  Clazz.newIntArray (16, 0);
this.atomSetAuxiliaryInfo =  new Array(16);
this.atomSymbolicMap =  new java.util.Hashtable();
});
Clazz.makeConstructor(c$, 
function(fileTypeName, reader, array, list){
this.fileTypeName = fileTypeName;
this.reader = reader;
this.allowMultiple = (reader == null || reader.desiredVibrationNumber < 0);
var p =  new java.util.Properties();
p.put("PATH_KEY", ".PATH");
p.put("PATH_SEPARATOR", J.adapter.smarter.SmarterJmolAdapter.PATH_SEPARATOR);
this.setInfo("properties", p);
if (reader != null) {
var ii = reader.htParams.get("appendToModelIndex");
if (ii != null) this.setInfo("appendToModelIndex", ii);
ii = reader.htParams.get("fixedSite");
if (ii != null) this.fixedSite = ii.intValue();
}if (array != null) {
var n = 0;
this.readerList =  new JU.Lst();
for (var i = 0; i < array.length; i++) if (array[i] != null && (array[i].ac > 0 || array[i].reader != null && array[i].reader.mustFinalizeModelSet)) this.appendAtomSetCollection(n++, array[i]);

if (n > 1) this.setInfo("isMultiFile", Boolean.TRUE);
} else if (list != null) {
this.setInfo("isMultiFile", Boolean.TRUE);
this.appendAtomSetCollectionList(list);
}}, "~S,J.adapter.smarter.AtomSetCollectionReader,~A,JU.Lst");
Clazz.defineMethod(c$, "setCollectionName", 
function(collectionName){
if (collectionName != null && (collectionName = collectionName.trim()).length > 0) this.collectionName = collectionName;
}, "~S");
Clazz.defineMethod(c$, "clearGlobalBoolean", 
function(globalIndex){
this.atomSetInfo.remove(JV.JC.getBoolName(globalIndex));
}, "~N");
Clazz.defineMethod(c$, "setGlobalBoolean", 
function(globalIndex){
this.setInfo(JV.JC.getBoolName(globalIndex), Boolean.TRUE);
}, "~N");
Clazz.defineMethod(c$, "getGlobalBoolean", 
function(globalIndex){
return (this.atomSetInfo.get(JV.JC.getBoolName(globalIndex)) === Boolean.TRUE);
}, "~N");
Clazz.defineMethod(c$, "appendAtomSetCollectionList", 
function(list){
var n = list.size();
if (n == 0) {
this.errorMessage = "No file found!";
return;
}for (var i = 0; i < n; i++) {
var o = list.get(i);
if (Clazz.instanceOf(o,"JU.Lst")) this.appendAtomSetCollectionList(o);
 else this.appendAtomSetCollection(i, o);
}
}, "JU.Lst");
Clazz.defineMethod(c$, "setTrajectory", 
function(){
if (!this.isTrajectory) this.trajectorySteps =  new JU.Lst();
this.isTrajectory = true;
var n = (this.bsAtoms == null ? this.ac : this.bsAtoms.cardinality());
if (n <= 1) return;
var trajectoryStep =  new Array(n);
var haveVibrations = (n > 0 && this.atoms[0].vib != null && !Float.isNaN(this.atoms[0].vib.z));
var vibrationStep = (haveVibrations ?  new Array(n) : null);
var prevSteps = (this.trajectoryStepCount == 0 ? null : this.trajectorySteps.get(this.trajectoryStepCount - 1));
for (var i = 0, ii = 0; i < this.ac; i++) {
if (this.bsAtoms != null && !this.bsAtoms.get(i)) continue;
var pt = JU.P3.newP(this.atoms[i]);
if (this.doFixPeriodic && prevSteps != null) pt = J.adapter.smarter.AtomSetCollection.fixPeriodic(pt, prevSteps[i]);
trajectoryStep[ii] = pt;
if (haveVibrations) vibrationStep[ii] = this.atoms[i].vib;
ii++;
}
if (haveVibrations) {
if (this.vibrationSteps == null) {
this.vibrationSteps =  new JU.Lst();
for (var i = 0; i < this.trajectoryStepCount; i++) this.vibrationSteps.addLast(null);

}this.vibrationSteps.addLast(vibrationStep);
}this.trajectorySteps.addLast(trajectoryStep);
this.trajectoryStepCount++;
});
Clazz.defineMethod(c$, "appendAtomSetCollection", 
function(collectionIndex, collection){
if (collection.reader != null && collection.reader.mustFinalizeModelSet) this.readerList.addLast(collection.reader);
var existingAtomsCount = this.ac;
this.setInfo("loadState", collection.atomSetInfo.get("loadState"));
if (collection.bsAtoms != null) {
this.getBSAtoms(0);
for (var i = collection.bsAtoms.nextSetBit(0); i >= 0; i = collection.bsAtoms.nextSetBit(i + 1)) this.bsAtoms.set(existingAtomsCount + i);

}var clonedAtoms = 0;
var atomSetCount0 = this.atomSetCount;
for (var atomSetNum = 0; atomSetNum < collection.atomSetCount; atomSetNum++) {
this.newAtomSet();
var info = this.atomSetAuxiliaryInfo[this.iSet] = collection.atomSetAuxiliaryInfo[atomSetNum];
var atomInfo = info.get("PDB_CONECT_firstAtom_count_max");
if (atomInfo != null) atomInfo[0] += existingAtomsCount;
this.setCurrentModelInfo("title", collection.collectionName);
this.setAtomSetName(collection.getAtomSetName(atomSetNum));
for (var atomNum = 0; atomNum < collection.atomSetAtomCounts[atomSetNum]; atomNum++) {
if (this.bsAtoms != null) this.bsAtoms.set(this.ac);
this.newCloneAtom(collection.atoms[clonedAtoms]);
clonedAtoms++;
}
this.atomSetNumbers[this.iSet] = (collectionIndex < 0 ? this.iSet + 1 : ((collectionIndex + 1) * 1000000) + collection.atomSetNumbers[atomSetNum]);
}
for (var bondNum = 0; bondNum < collection.bondCount; bondNum++) {
var bond = collection.bonds[bondNum];
this.addNewBondWithOrder(bond.atomIndex1 + existingAtomsCount, bond.atomIndex2 + existingAtomsCount, bond.order);
}
for (var i = JV.JC.globalBooleans.length; --i >= 0; ) if (collection.getGlobalBoolean(i)) this.setGlobalBoolean(i);

for (var i = 0; i < collection.structureCount; i++) {
var s = collection.structures[i];
this.addStructure(s);
s.modelStartEnd[0] += atomSetCount0;
s.modelStartEnd[1] += atomSetCount0;
}
}, "~N,J.adapter.smarter.AtomSetCollection");
Clazz.defineMethod(c$, "setNoAutoBond", 
function(){
this.setInfo("noAutoBond", Boolean.TRUE);
});
Clazz.defineMethod(c$, "freeze", 
function(reverseModels){
if (this.atomSetCount == 1 && this.collectionName == null) this.collectionName = this.getAtomSetAuxiliaryInfoValue(0, "name");
if (reverseModels) this.reverseAtomSets();
if (this.trajectoryStepCount > 1) this.finalizeTrajectory();
this.getList(true);
this.getList(false);
for (var i = 0; i < this.atomSetCount; i++) {
this.setModelInfoForSet("initialAtomCount", Integer.$valueOf(this.atomSetAtomCounts[i]), i);
this.setModelInfoForSet("initialBondCount", Integer.$valueOf(this.atomSetBondCounts[i]), i);
}
}, "~B");
Clazz.defineMethod(c$, "reverseAtomSets", 
function(){
this.reverseArray(this.atomSetAtomIndexes);
this.reverseArray(this.atomSetNumbers);
this.reverseArray(this.atomSetAtomCounts);
this.reverseArray(this.atomSetBondCounts);
J.adapter.smarter.AtomSetCollection.reverseList(this.trajectorySteps);
J.adapter.smarter.AtomSetCollection.reverseList(this.trajectoryNames);
J.adapter.smarter.AtomSetCollection.reverseList(this.vibrationSteps);
this.reverseObject(this.atomSetAuxiliaryInfo);
for (var i = 0; i < this.ac; i++) this.atoms[i].atomSetIndex = this.atomSetCount - 1 - this.atoms[i].atomSetIndex;

for (var i = 0; i < this.structureCount; i++) {
var m = this.structures[i].modelStartEnd[0];
if (m >= 0) {
this.structures[i].modelStartEnd[0] = this.atomSetCount - 1 - this.structures[i].modelStartEnd[1];
this.structures[i].modelStartEnd[1] = this.atomSetCount - 1 - m;
}}
for (var i = 0; i < this.bondCount; i++) this.bonds[i].atomSetIndex = this.atomSetCount - 1 - this.atoms[this.bonds[i].atomIndex1].atomSetIndex;

this.reverseSets(this.bonds, this.bondCount);
var lists = JU.AU.createArrayOfArrayList(this.atomSetCount);
for (var i = 0; i < this.atomSetCount; i++) lists[i] =  new JU.Lst();

for (var i = 0; i < this.ac; i++) lists[this.atoms[i].atomSetIndex].addLast(this.atoms[i]);

var newIndex =  Clazz.newIntArray (this.ac, 0);
var n = this.ac;
for (var i = this.atomSetCount; --i >= 0; ) for (var j = lists[i].size(); --j >= 0; ) {
var a = this.atoms[--n] = lists[i].get(j);
newIndex[a.index] = n;
a.index = n;
}

for (var i = 0; i < this.bondCount; i++) {
this.bonds[i].atomIndex1 = newIndex[this.bonds[i].atomIndex1];
this.bonds[i].atomIndex2 = newIndex[this.bonds[i].atomIndex2];
}
for (var i = 0; i < this.atomSetCount; i++) {
var conect = this.getAtomSetAuxiliaryInfoValue(i, "PDB_CONECT_firstAtom_count_max");
if (conect == null) continue;
conect[0] = newIndex[conect[0]];
conect[1] = this.atomSetAtomCounts[i];
}
});
Clazz.defineMethod(c$, "reverseSets", 
function(o, n){
var lists = JU.AU.createArrayOfArrayList(this.atomSetCount);
for (var i = 0; i < this.atomSetCount; i++) lists[i] =  new JU.Lst();

for (var i = 0; i < n; i++) {
var index = o[i].atomSetIndex;
if (index < 0) return;
lists[o[i].atomSetIndex].addLast(o[i]);
}
for (var i = this.atomSetCount; --i >= 0; ) for (var j = lists[i].size(); --j >= 0; ) o[--n] = lists[i].get(j);


}, "~A,~N");
Clazz.defineMethod(c$, "reverseObject", 
function(o){
var n = this.atomSetCount;
for (var i = Clazz.doubleToInt(n / 2); --i >= 0; ) JU.AU.swap(o, i, n - 1 - i);

}, "~A");
c$.reverseList = Clazz.defineMethod(c$, "reverseList", 
function(list){
if (list == null) return;
java.util.Collections.reverse(list);
}, "JU.Lst");
Clazz.defineMethod(c$, "reverseArray", 
function(a){
var n = this.atomSetCount;
for (var i = Clazz.doubleToInt(n / 2); --i >= 0; ) JU.AU.swapInt(a, i, n - 1 - i);

}, "~A");
Clazz.defineMethod(c$, "getList", 
function(isAltLoc){
var i;
for (i = this.ac; --i >= 0; ) if (this.atoms[i] != null && (isAltLoc ? this.atoms[i].altLoc : this.atoms[i].insertionCode) != '\0') break;

if (i < 0) return;
var lists =  new Array(this.atomSetCount);
for (i = 0; i < this.atomSetCount; i++) lists[i] = "";

var pt;
for (i = 0; i < this.ac; i++) {
if (this.atoms[i] == null) continue;
var id = (isAltLoc ? this.atoms[i].altLoc : this.atoms[i].insertionCode);
if (id != '\0' && lists[pt = this.atoms[i].atomSetIndex].indexOf(id) < 0) lists[pt] += id;
}
var type = (isAltLoc ? "altLocs" : "insertionCodes");
for (i = 0; i < this.atomSetCount; i++) if (lists[i].length > 0) this.setModelInfoForSet(type, lists[i], i);

}, "~B");
Clazz.defineMethod(c$, "finish", 
function(){
if (this.reader != null) this.reader.finalizeModelSet();
 else if (this.readerList != null) for (var i = 0; i < this.readerList.size(); i++) this.readerList.get(i).finalizeModelSet();

this.atoms = null;
this.atomSetAtomCounts =  Clazz.newIntArray (16, 0);
this.atomSetAuxiliaryInfo =  new Array(16);
this.atomSetInfo =  new java.util.Hashtable();
this.atomSetCount = 0;
this.atomSetNumbers =  Clazz.newIntArray (16, 0);
this.atomSymbolicMap =  new java.util.Hashtable();
this.bonds = null;
this.iSet = -1;
this.readerList = null;
this.xtalSymmetry = null;
this.structures =  new Array(16);
this.structureCount = 0;
this.trajectorySteps = null;
this.vibrationSteps = null;
});
Clazz.defineMethod(c$, "discardPreviousAtoms", 
function(){
for (var i = this.ac; --i >= 0; ) this.atoms[i] = null;

this.ac = 0;
this.clearMap();
this.atomSetCount = 0;
this.iSet = -1;
for (var i = this.atomSetAuxiliaryInfo.length; --i >= 0; ) {
this.atomSetAtomCounts[i] = 0;
this.atomSetBondCounts[i] = 0;
this.atomSetAuxiliaryInfo[i] = null;
}
});
Clazz.defineMethod(c$, "removeCurrentAtomSet", 
function(){
if (this.iSet < 0) return;
var ai = this.atomSetAtomIndexes[this.iSet];
if (this.bsAtoms != null) this.bsAtoms.clearBits(ai, this.ac);
this.ac = ai;
this.atomSetAtomCounts[this.iSet] = 0;
this.iSet--;
this.atomSetCount--;
this.reader.doCheckUnitCell = false;
});
Clazz.defineMethod(c$, "getHydrogenAtomCount", 
function(){
var n = 0;
for (var i = 0; i < this.ac; i++) if (this.atoms[i].elementNumber == 1 || this.atoms[i].elementSymbol.equals("H")) n++;

return n;
});
Clazz.defineMethod(c$, "newCloneAtom", 
function(atom){
var clone = atom.getClone();
this.addAtom(clone);
return clone;
}, "J.adapter.smarter.Atom");
Clazz.defineMethod(c$, "cloneFirstAtomSet", 
function(atomCount){
if (!this.allowMultiple) return 0;
this.newAtomSet();
if (atomCount == 0) atomCount = this.atomSetAtomCounts[0];
for (var i = 0; i < atomCount; ++i) this.newCloneAtom(this.atoms[i]);

return this.ac;
}, "~N");
Clazz.defineMethod(c$, "cloneAtomSetWithBonds", 
function(isLast){
var nBonds = this.atomSetBondCounts[isLast ? this.iSet : 0];
var atomIncrement = (isLast ? this.cloneLastAtomSet() : this.cloneFirstAtomSet(0));
if (atomIncrement > 0) for (var i = 0; i < nBonds; i++) {
var bond = this.bonds[this.bondCount - nBonds];
this.addNewBondWithOrder(bond.atomIndex1 + atomIncrement, bond.atomIndex2 + atomIncrement, bond.order);
}
}, "~B");
Clazz.defineMethod(c$, "cloneLastAtomSet", 
function(){
return this.cloneLastAtomSetFromPoints(0, null);
});
Clazz.defineMethod(c$, "cloneLastAtomSetFromPoints", 
function(ac, pts){
if (!this.allowMultiple) return 0;
var count = (ac > 0 ? ac : this.getLastAtomSetAtomCount());
var atomIndex = this.getLastAtomSetAtomIndex();
this.newAtomSet();
for (var i = 0; i < count; ++i) {
var atom = this.newCloneAtom(this.atoms[atomIndex++]);
if (pts != null) atom.setT(pts[i]);
}
return count;
}, "~N,~A");
Clazz.defineMethod(c$, "getLastAtomSetAtomCount", 
function(){
return this.atomSetAtomCounts[this.iSet];
});
Clazz.defineMethod(c$, "getLastAtomSetAtomIndex", 
function(){
return this.ac - this.atomSetAtomCounts[this.iSet];
});
Clazz.defineMethod(c$, "addNewAtom", 
function(){
return this.addAtom( new J.adapter.smarter.Atom());
});
Clazz.defineMethod(c$, "addAtom", 
function(atom){
if (this.ac == this.atoms.length) {
if (this.ac > 200000) this.atoms = JU.AU.ensureLength(this.atoms, this.ac + 50000);
 else this.atoms = JU.AU.doubleLength(this.atoms);
}if (this.atomSetCount == 0) this.newAtomSet();
atom.index = this.ac;
this.atoms[this.ac++] = atom;
atom.atomSetIndex = this.iSet;
atom.atomSite = (this.fixedSite > 0 ? this.fixedSite - 1 : this.atomSetAtomCounts[this.iSet]++);
return atom;
}, "J.adapter.smarter.Atom");
Clazz.defineMethod(c$, "addAtomWithMappedName", 
function(atom){
var atomName = this.addAtom(atom).atomName;
if (atomName != null) this.atomSymbolicMap.put(atomName, atom);
}, "J.adapter.smarter.Atom");
Clazz.defineMethod(c$, "addAtomWithMappedSerialNumber", 
function(atom){
var atomSerial = this.addAtom(atom).atomSerial;
if (atomSerial != -2147483648) this.atomSymbolicMap.put("" + atomSerial, atom);
}, "J.adapter.smarter.Atom");
Clazz.defineMethod(c$, "getAtomFromName", 
function(atomName){
return this.atomSymbolicMap.get(atomName);
}, "~S");
Clazz.defineMethod(c$, "setAtomMapAnyCase", 
function(){
this.atomMapAnyCase = true;
var newMap =  new java.util.Hashtable();
newMap.putAll(this.atomSymbolicMap);
for (var e, $e = this.atomSymbolicMap.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var name = e.getKey();
var uc = name.toUpperCase();
if (!uc.equals(name)) newMap.put(uc, e.getValue());
}
this.atomSymbolicMap = newMap;
});
Clazz.defineMethod(c$, "getAtomIndex", 
function(name){
var a = this.atomSymbolicMap.get(name);
if (a == null && this.atomMapAnyCase) a = this.atomSymbolicMap.get(name.toUpperCase());
return (a == null ? -1 : a.index);
}, "~S");
Clazz.defineMethod(c$, "addNewBondWithOrder", 
function(atomIndex1, atomIndex2, order){
var b = null;
if (atomIndex1 >= 0 && atomIndex1 < this.ac && atomIndex2 >= 0 && atomIndex2 < this.ac && atomIndex1 != atomIndex2) {
b =  new J.adapter.smarter.Bond(atomIndex1, atomIndex2, order);
this.addBond(b);
}return b;
}, "~N,~N,~N");
Clazz.defineMethod(c$, "addNewBondFromNames", 
function(atomName1, atomName2, order){
return this.addNewBondWithOrderA(this.getAtomFromName(atomName1), this.getAtomFromName(atomName2), order);
}, "~S,~S,~N");
Clazz.defineMethod(c$, "addNewBondWithOrderA", 
function(atom1, atom2, order){
return (atom1 != null && atom2 != null ? this.addNewBondWithOrder(atom1.index, atom2.index, order) : null);
}, "J.adapter.smarter.Atom,J.adapter.smarter.Atom,~N");
Clazz.defineMethod(c$, "addBond", 
function(bond){
if (this.trajectoryStepCount > 0) return;
if (bond.atomIndex1 < 0 || bond.atomIndex2 < 0 || bond.order < 0 || bond.atomIndex1 == bond.atomIndex2 || this.atoms[bond.atomIndex1].atomSetIndex != this.atoms[bond.atomIndex2].atomSetIndex) {
if (JU.Logger.debugging) {
JU.Logger.debug(">>>>>>BAD BOND:" + bond.atomIndex1 + "-" + bond.atomIndex2 + " order=" + bond.order);
}return;
}this.addBondNoCheck(bond);
}, "J.adapter.smarter.Bond");
Clazz.defineMethod(c$, "addBondNoCheck", 
function(bond){
if (this.bondCount == this.bonds.length) this.bonds = JU.AU.arrayCopyObject(this.bonds, this.bondCount + 1024);
this.bonds[this.bondCount++] = bond;
this.atomSetBondCounts[this.iSet]++;
}, "J.adapter.smarter.Bond");
Clazz.defineMethod(c$, "finalizeStructures", 
function(){
if (this.structureCount == 0) return;
this.bsStructuredModels =  new JU.BS();
var map =  new java.util.Hashtable();
for (var i = 0; i < this.structureCount; i++) {
var s = this.structures[i];
if (s.modelStartEnd[0] == -1) {
s.modelStartEnd[0] = 0;
s.modelStartEnd[1] = this.atomSetCount - 1;
}this.bsStructuredModels.setBits(s.modelStartEnd[0], s.modelStartEnd[1] + 1);
if (s.strandCount == 0) continue;
var key = s.structureID + " " + s.modelStartEnd[0];
var v = map.get(key);
var count = (v == null ? 0 : v.intValue()) + 1;
map.put(key, Integer.$valueOf(count));
}
for (var i = 0; i < this.structureCount; i++) {
var s = this.structures[i];
if (s.strandCount == 1) s.strandCount = map.get(s.structureID + " " + s.modelStartEnd[0]).intValue();
}
});
Clazz.defineMethod(c$, "addStructure", 
function(structure){
if (this.structureCount == this.structures.length) this.structures = JU.AU.arrayCopyObject(this.structures, this.structureCount + 32);
this.structures[this.structureCount++] = structure;
}, "J.adapter.smarter.Structure");
Clazz.defineMethod(c$, "addVibrationVectorWithSymmetry", 
function(iatom, vx, vy, vz, withSymmetry){
if (!withSymmetry) {
this.addVibrationVector(iatom, vx, vy, vz);
return;
}var atomSite = this.atoms[iatom].atomSite;
var atomSetIndex = this.atoms[iatom].atomSetIndex;
for (var i = iatom; i < this.ac && this.atoms[i].atomSetIndex == atomSetIndex; i++) {
if (this.atoms[i].atomSite == atomSite) this.addVibrationVector(i, vx, vy, vz);
}
}, "~N,~N,~N,~N,~B");
Clazz.defineMethod(c$, "addVibrationVector", 
function(iatom, x, y, z){
if (!this.allowMultiple) iatom = iatom % this.ac;
return (this.atoms[iatom].vib = JU.V3.new3(x, y, z));
}, "~N,~N,~N,~N");
Clazz.defineMethod(c$, "setCoordinatesAreFractional", 
function(tf){
this.coordinatesAreFractional = tf;
this.setCurrentModelInfo("coordinatesAreFractional", Boolean.$valueOf(tf));
if (tf) this.setGlobalBoolean(0);
}, "~B");
Clazz.defineMethod(c$, "setAnisoBorU", 
function(atom, data, type){
this.haveAnisou = true;
atom.anisoBorU = data;
data[6] = type;
}, "J.adapter.smarter.Atom,~A,~N");
Clazz.defineMethod(c$, "setU", 
function(atom, i, val){
var data = atom.anisoBorU;
if (data == null) this.setAnisoBorU(atom, data =  Clazz.newFloatArray (8, 0), 8);
data[i] = val;
}, "J.adapter.smarter.Atom,~N,~N");
Clazz.defineMethod(c$, "getXSymmetry", 
function(){
if (this.xtalSymmetry == null) this.xtalSymmetry = (J.api.Interface.getOption("adapter.smarter.XtalSymmetry", this.reader.vwr, "file")).set(this.reader);
return this.xtalSymmetry;
});
Clazz.defineMethod(c$, "getSymmetry", 
function(){
return this.getXSymmetry().getSymmetry();
});
Clazz.defineMethod(c$, "setSymmetry", 
function(symmetry){
return (symmetry == null ? null : this.getXSymmetry().setSymmetry(symmetry));
}, "J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz.defineMethod(c$, "newFileSymmetry", 
function(){
return this.getXSymmetry().newFileSymmetry();
});
Clazz.defineMethod(c$, "setTensors", 
function(){
if (this.haveAnisou) this.getXSymmetry().setTensors();
});
Clazz.defineMethod(c$, "setInfo", 
function(key, value){
if (value == null) this.atomSetInfo.remove(key);
 else this.atomSetInfo.put(key, value);
}, "~S,~O");
Clazz.defineMethod(c$, "setAtomSetCollectionPartialCharges", 
function(auxKey){
if (!this.atomSetInfo.containsKey(auxKey)) return false;
var atomData = this.atomSetInfo.get(auxKey);
var n = atomData.size();
for (var i = this.ac; --i >= 0; ) this.atoms[i].partialCharge = atomData.get(i % n).floatValue();

JU.Logger.info("Setting partial charges type " + auxKey);
return true;
}, "~S");
Clazz.defineMethod(c$, "mapPartialCharge", 
function(atomName, charge){
this.getAtomFromName(atomName).partialCharge = charge;
}, "~S,~N");
c$.fixPeriodic = Clazz.defineMethod(c$, "fixPeriodic", 
function(pt, pt0){
pt.x = J.adapter.smarter.AtomSetCollection.fixPoint(pt.x, pt0.x);
pt.y = J.adapter.smarter.AtomSetCollection.fixPoint(pt.y, pt0.y);
pt.z = J.adapter.smarter.AtomSetCollection.fixPoint(pt.z, pt0.z);
return pt;
}, "JU.P3,JU.P3");
c$.fixPoint = Clazz.defineMethod(c$, "fixPoint", 
function(x, x0){
while (x - x0 > 0.9) {
x -= 1;
}
while (x - x0 < -0.9) {
x += 1;
}
return x;
}, "~N,~N");
Clazz.defineMethod(c$, "finalizeTrajectoryAs", 
function(trajectorySteps, vibrationSteps){
this.trajectorySteps = trajectorySteps;
this.vibrationSteps = vibrationSteps;
this.trajectoryStepCount = trajectorySteps.size();
this.finalizeTrajectory();
}, "JU.Lst,JU.Lst");
Clazz.defineMethod(c$, "finalizeTrajectory", 
function(){
if (this.trajectoryStepCount == 0) return;
var trajectory = this.trajectorySteps.get(0);
var vibrations = (this.vibrationSteps == null ? null : this.vibrationSteps.get(0));
var n = (this.bsAtoms == null ? this.ac : this.bsAtoms.cardinality());
if (this.vibrationSteps != null && vibrations != null && vibrations.length < n || trajectory.length < n) {
this.errorMessage = "File cannot be loaded as a trajectory";
return;
}var v =  new JU.V3();
for (var i = 0, ii = 0; i < this.ac; i++) {
if (this.bsAtoms != null && !this.bsAtoms.get(i)) continue;
if (this.vibrationSteps != null) this.atoms[i].vib = (vibrations == null ? v : vibrations[ii]);
if (trajectory[ii] != null) this.atoms[i].setT(trajectory[ii]);
ii++;
}
this.setInfo("trajectorySteps", this.trajectorySteps);
if (this.vibrationSteps != null) this.setInfo("vibrationSteps", this.vibrationSteps);
if (this.ac == 0) this.ac = trajectory.length;
});
Clazz.defineMethod(c$, "newAtomSet", 
function(){
this.newAtomSetClear(true);
});
Clazz.defineMethod(c$, "newAtomSetClear", 
function(doClearMap){
if (!this.allowMultiple && this.iSet >= 0) this.reader.discardPreviousAtoms();
this.bondIndex0 = this.bondCount;
if (this.isTrajectory) this.reader.discardPreviousAtoms();
this.iSet = this.atomSetCount++;
if (this.atomSetCount > this.atomSetNumbers.length) {
this.atomSetAtomIndexes = JU.AU.doubleLengthI(this.atomSetAtomIndexes);
this.atomSetAtomCounts = JU.AU.doubleLengthI(this.atomSetAtomCounts);
this.atomSetBondCounts = JU.AU.doubleLengthI(this.atomSetBondCounts);
this.atomSetAuxiliaryInfo = JU.AU.doubleLength(this.atomSetAuxiliaryInfo);
}this.atomSetAtomIndexes[this.iSet] = this.ac;
if (this.atomSetCount + this.trajectoryStepCount > this.atomSetNumbers.length) {
this.atomSetNumbers = JU.AU.doubleLengthI(this.atomSetNumbers);
}if (this.isTrajectory) {
this.atomSetNumbers[this.iSet + this.trajectoryStepCount] = this.atomSetCount + this.trajectoryStepCount;
} else {
this.atomSetNumbers[this.iSet] = this.atomSetCount;
}if (doClearMap) {
this.clearMap();
}this.setCurrentModelInfo("title", this.collectionName);
}, "~B");
Clazz.defineMethod(c$, "clearMap", 
function(){
this.atomSymbolicMap.clear();
this.atomMapAnyCase = false;
});
Clazz.defineMethod(c$, "getAtomSetAtomIndex", 
function(i){
return this.atomSetAtomIndexes[i];
}, "~N");
Clazz.defineMethod(c$, "getAtomSetAtomCount", 
function(i){
return this.atomSetAtomCounts[i];
}, "~N");
Clazz.defineMethod(c$, "getAtomSetBondCount", 
function(i){
return this.atomSetBondCounts[i];
}, "~N");
Clazz.defineMethod(c$, "setAtomSetName", 
function(atomSetName){
if (atomSetName == null) return;
if (this.isTrajectory) {
this.setTrajectoryName(atomSetName);
return;
}var name0 = (this.iSet < 0 ? null : this.getAtomSetName(this.iSet));
this.setModelInfoForSet("name", atomSetName, this.iSet);
if (this.reader != null && atomSetName.length > 0 && !atomSetName.equals(name0)) this.reader.appendLoadNote(atomSetName);
if (!this.allowMultiple) this.setCollectionName(atomSetName);
}, "~S");
Clazz.defineMethod(c$, "setTrajectoryName", 
function(name){
if (this.trajectoryStepCount == 0) return;
if (this.trajectoryNames == null) {
this.trajectoryNames =  new JU.Lst();
}for (var i = this.trajectoryNames.size(); i < this.trajectoryStepCount; i++) this.trajectoryNames.addLast(null);

this.trajectoryNames.set(this.trajectoryStepCount - 1, name);
}, "~S");
Clazz.defineMethod(c$, "setCurrentAtomSetNumber", 
function(atomSetNumber){
this.setAtomSetNumber(this.iSet + (this.isTrajectory ? this.trajectoryStepCount : 0), atomSetNumber);
}, "~N");
Clazz.defineMethod(c$, "setAtomSetNumber", 
function(index, atomSetNumber){
this.atomSetNumbers[index] = atomSetNumber;
}, "~N,~N");
Clazz.defineMethod(c$, "setAtomSetModelProperty", 
function(key, value){
this.setAtomSetModelPropertyForSet(key, value, this.iSet);
}, "~S,~S");
Clazz.defineMethod(c$, "setAtomSetModelPropertyForSet", 
function(key, value, atomSetIndex){
var p = this.getAtomSetAuxiliaryInfoValue(atomSetIndex, "modelProperties");
if (p == null) this.setModelInfoForSet("modelProperties", p =  new java.util.Properties(), atomSetIndex);
p.put(key, value);
if (key.startsWith(".")) p.put(key.substring(1), value);
}, "~S,~S,~N");
Clazz.defineMethod(c$, "setAtomProperties", 
function(key, data, atomSetIndex, isGroup){
if ((typeof(data)=='string') && !(data).endsWith("\n")) data = data + "\n";
if (atomSetIndex < 0) atomSetIndex = this.iSet;
var p = this.getAtomSetAuxiliaryInfoValue(atomSetIndex, "atomProperties");
if (p == null) this.setModelInfoForSet("atomProperties", p =  new java.util.Hashtable(), atomSetIndex);
p.put(key, data);
}, "~S,~O,~N,~B");
Clazz.defineMethod(c$, "setAtomSetPartialCharges", 
function(auxKey){
if (!this.atomSetAuxiliaryInfo[this.iSet].containsKey(auxKey)) {
return false;
}var atomData = this.getAtomSetAuxiliaryInfoValue(this.iSet, auxKey);
for (var i = atomData.size(); --i >= 0; ) {
this.atoms[i].partialCharge = atomData.get(i).floatValue();
}
return true;
}, "~S");
Clazz.defineMethod(c$, "getAtomSetAuxiliaryInfoValue", 
function(index, key){
return this.atomSetAuxiliaryInfo[index >= 0 ? index : this.iSet].get(key);
}, "~N,~S");
Clazz.defineMethod(c$, "setCurrentModelInfo", 
function(key, value){
this.setModelInfoForSet(key, value, this.iSet);
}, "~S,~O");
Clazz.defineMethod(c$, "setModelInfoForSet", 
function(key, value, atomSetIndex){
if (atomSetIndex < 0) return;
if (this.atomSetAuxiliaryInfo[atomSetIndex] == null) this.atomSetAuxiliaryInfo[atomSetIndex] =  new java.util.Hashtable();
if (value == null) this.atomSetAuxiliaryInfo[atomSetIndex].remove(key);
 else this.atomSetAuxiliaryInfo[atomSetIndex].put(key, value);
}, "~S,~O,~N");
Clazz.defineMethod(c$, "getAtomSetNumber", 
function(atomSetIndex){
return this.atomSetNumbers[atomSetIndex >= this.atomSetCount ? 0 : atomSetIndex];
}, "~N");
Clazz.defineMethod(c$, "getAtomSetName", 
function(atomSetIndex){
if (this.trajectoryNames != null && atomSetIndex < this.trajectoryNames.size()) return this.trajectoryNames.get(atomSetIndex);
if (atomSetIndex >= this.atomSetCount) atomSetIndex = this.atomSetCount - 1;
return this.getAtomSetAuxiliaryInfoValue(atomSetIndex, "name");
}, "~N");
Clazz.defineMethod(c$, "getAtomSetAuxiliaryInfo", 
function(atomSetIndex){
var i = (atomSetIndex >= this.atomSetCount ? this.atomSetCount - 1 : atomSetIndex);
return (i < 0 ? null : this.atomSetAuxiliaryInfo[i]);
}, "~N");
Clazz.defineMethod(c$, "setAtomSetEnergy", 
function(energyString, value){
if (this.iSet < 0) return;
JU.Logger.info("Energy for model " + (this.iSet + 1) + " = " + energyString);
this.setCurrentModelInfo("EnergyString", energyString);
this.setCurrentModelInfo("Energy", Float.$valueOf(value));
this.setAtomSetModelProperty("Energy", "" + value);
}, "~S,~N");
Clazz.defineMethod(c$, "setAtomSetFrequency", 
function(mode, pathKey, label, freq, units){
this.setAtomSetModelProperty("FreqValue", freq);
freq += " " + (units == null ? "cm^-1" : units);
var name = (label == null ? "" : label + " ") + freq;
this.setAtomSetName(name);
this.setAtomSetModelProperty("Frequency", freq);
this.setAtomSetModelProperty("Mode", "" + mode);
this.setModelInfoForSet("vibrationalMode", Integer.$valueOf(mode), this.iSet);
if (label != null) this.setAtomSetModelProperty("FrequencyLabel", label);
this.setAtomSetModelProperty(".PATH", (pathKey == null ? "" : pathKey + J.adapter.smarter.SmarterJmolAdapter.PATH_SEPARATOR + "Frequencies") + "Frequencies");
return name;
}, "~N,~S,~S,~S,~S");
Clazz.defineMethod(c$, "getBondList", 
function(){
var info =  new Array(this.bondCount);
for (var i = 0; i < this.bondCount; i++) {
info[i] =  Clazz.newArray(-1, [this.atoms[this.bonds[i].atomIndex1].atomName, this.atoms[this.bonds[i].atomIndex2].atomName, "" + this.bonds[i].order]);
}
return info;
});
Clazz.defineMethod(c$, "centralize", 
function(){
var pt =  new JU.P3();
for (var i = 0; i < this.atomSetCount; i++) {
var n = this.atomSetAtomCounts[i];
var atom0 = this.atomSetAtomIndexes[i];
pt.set(0, 0, 0);
for (var j = atom0 + n; --j >= atom0; ) pt.add(this.atoms[j]);

pt.scale(1 / n);
for (var j = atom0 + n; --j >= atom0; ) this.atoms[j].sub(pt);

}
});
Clazz.defineMethod(c$, "mergeTrajectories", 
function(a){
if (!this.isTrajectory || !a.isTrajectory || this.vibrationSteps != null) return;
for (var i = 0; i < a.trajectoryStepCount; i++) this.trajectorySteps.add(this.trajectoryStepCount++, a.trajectorySteps.get(i));

this.setInfo("trajectorySteps", this.trajectorySteps);
this.setInfo("ignoreUnitCell", a.atomSetInfo.get("ignoreUnitCell"));
}, "J.adapter.smarter.AtomSetCollection");
Clazz.defineMethod(c$, "removeAtomSet", 
function(imodel){
if (this.bsAtoms == null) this.bsAtoms = JU.BSUtil.newBitSet2(0, this.ac);
var i0 = this.atomSetAtomIndexes[imodel];
var nAtoms = this.atomSetAtomCounts[imodel];
var i1 = i0 + nAtoms;
this.bsAtoms.clearBits(i0, i1);
for (var i = i1; i < this.ac; i++) this.atoms[i].atomSetIndex--;

for (var i = imodel + 1; i < this.atomSetCount; i++) {
this.atomSetAuxiliaryInfo[i - 1] = this.atomSetAuxiliaryInfo[i];
this.atomSetAtomIndexes[i - 1] = this.atomSetAtomIndexes[i];
this.atomSetBondCounts[i - 1] = this.atomSetBondCounts[i];
this.atomSetAtomCounts[i - 1] = this.atomSetAtomCounts[i];
this.atomSetNumbers[i - 1] = this.atomSetNumbers[i];
}
for (var i = 0; i < this.bondCount; i++) this.bonds[i].atomSetIndex = this.atoms[this.bonds[i].atomIndex1].atomSetIndex;

this.atomSetAuxiliaryInfo[--this.atomSetCount] = null;
var n = 0;
for (var i = 0; i < this.structureCount; i++) {
var s = this.structures[i];
if (s.modelStartEnd[0] == imodel && s.modelStartEnd[1] == imodel) {
this.structures[i] = null;
n++;
}}
if (n > 0) {
var ss =  new Array(this.structureCount - n);
for (var i = 0, pt = 0; i < this.structureCount; i++) if (this.structures[i] != null) ss[pt++] = this.structures[i];

this.structures = ss;
}}, "~N");
Clazz.defineMethod(c$, "removeLastUnselectedAtoms", 
function(){
var n = this.ac;
var nremoved = 0;
var i0 = this.getLastAtomSetAtomIndex();
var nnow = 0;
for (var i = i0; i < n; i++) {
if (!this.bsAtoms.get(i)) {
nremoved++;
this.ac--;
this.atoms[i] = null;
continue;
}if (nremoved > 0) {
this.atoms[this.atoms[i].index = i - nremoved] = this.atoms[i];
this.atoms[i] = null;
}nnow++;
}
this.atomSetAtomCounts[this.iSet] = nnow;
if (nnow == 0) {
this.iSet--;
this.atomSetCount--;
} else {
this.bsAtoms.setBits(i0, i0 + nnow);
}});
Clazz.defineMethod(c$, "checkNoEmptyModel", 
function(){
while (this.atomSetCount > 0 && this.atomSetAtomCounts[this.atomSetCount - 1] == 0) this.atomSetCount--;

});
Clazz.defineMethod(c$, "getBSAtoms", 
function(n){
if (this.bsAtoms == null) {
this.bsAtoms =  new JU.BS();
if (n != 0) this.bsAtoms.setBits(0, (n < 0 ? this.ac : n));
}return this.bsAtoms;
}, "~N");
Clazz.defineMethod(c$, "setBSAtomsForSet", 
function(iSet){
if (this.bsAtoms != null) {
if (iSet < 0) iSet = this.iSet;
var pt = this.atomSetAtomIndexes[iSet];
if (this.bsAtoms.nextSetBit(pt) < 0) {
var n = this.atomSetAtomCounts[iSet];
this.bsAtoms.setBits(pt, pt + n);
}}}, "~N");
Clazz.defineMethod(c$, "fix2Stereo", 
function(){
this.getBSAtoms(-1);
for (var i = this.bondCount; --i >= 0; ) {
var b = this.bonds[i];
if (this.atoms[b.atomIndex2].elementSymbol.equals("H") && b.order != 1025 && b.order != 1041 && this.atoms[b.atomIndex1].elementSymbol.equals("C")) {
this.bsAtoms.clear(b.atomIndex2);
} else if (this.atoms[b.atomIndex1].elementSymbol.equals("H") && this.atoms[b.atomIndex2].elementSymbol.equals("C")) {
this.bsAtoms.clear(b.atomIndex1);
}}
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
