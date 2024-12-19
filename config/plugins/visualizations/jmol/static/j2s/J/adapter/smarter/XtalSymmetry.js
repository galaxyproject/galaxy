Clazz.declarePackage("J.adapter.smarter");
Clazz.load(["JS.Symmetry", "JU.P3", "$.SB"], "J.adapter.smarter.XtalSymmetry", ["java.util.Hashtable", "JU.BS", "$.Lst", "$.M3", "$.M4", "$.P3i", "$.PT", "$.V3", "J.adapter.smarter.Atom", "JS.SpaceGroup", "$.SymmetryOperation", "$.UnitCell", "JU.BSUtil", "$.Logger", "$.SimpleUnitCell"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.acr = null;
this.applySymmetryToBonds = false;
this.asc = null;
this.baseSymmetry = null;
this.bondCount0 = 0;
this.bondsFound = null;
this.centroidPacked = false;
this.checkAll = false;
this.checkNearAtoms = false;
this.crystalReaderLatticeOpsOnly = false;
this.disorderMap = null;
this.disorderMapMax = 0;
this.doCentroidUnitCell = false;
this.doNormalize = true;
this.doPackUnitCell = false;
this.filterSymop = null;
this.firstAtom = 0;
this.latticeCells = null;
this.latticeOp = 0;
this.mident = null;
this.minXYZ = null;
this.maxXYZ = null;
this.minXYZ0 = null;
this.maxXYZ0 = null;
this.mTemp = null;
this.ndims = 3;
this.noSymmetryCount = 0;
this.nVib = 0;
this.packingRange = 0;
this.ptOffset = null;
this.ptTemp = null;
this.rminx = 0;
this.rminy = 0;
this.rminz = 0;
this.rmaxx = 0;
this.rmaxy = 0;
this.rmaxz = 0;
this.symmetry = null;
this.symmetryRange = 0;
this.trajectoryUnitCells = null;
this.unitCellParams = null;
this.unitCellTranslations = null;
Clazz.instantialize(this, arguments);}, J.adapter.smarter, "XtalSymmetry", null);
Clazz.prepareFields (c$, function(){
this.bondsFound =  new JU.SB();
this.ptOffset =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "addRotatedTensor", 
function(a, t, iSym, reset, symmetry){
if (this.ptTemp == null) {
this.ptTemp =  new JU.P3();
this.mTemp =  new JU.M3();
}return a.addTensor((this.acr.getInterface("JU.Tensor")).setFromEigenVectors(symmetry.rotateAxes(iSym, t.eigenVectors, this.ptTemp, this.mTemp), t.eigenValues, t.isIsotropic ? "iso" : t.type, t.id, t), null, reset);
}, "J.adapter.smarter.Atom,JU.Tensor,~N,~B,J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz.defineMethod(c$, "applySymmetryBio", 
function(thisBiomolecule, applySymmetryToBonds, filter){
var biomts = thisBiomolecule.get("biomts");
var len = biomts.size();
if (this.mident == null) {
this.mident =  new JU.M4();
this.mident.setIdentity();
}this.acr.lstNCS = null;
this.setLatticeCells();
var lc = (this.latticeCells != null && this.latticeCells[0] != 0 ?  Clazz.newIntArray (3, 0) : null);
if (lc != null) for (var i = 0; i < 3; i++) lc[i] = this.latticeCells[i];

this.latticeCells = null;
var bmChains = this.acr.getFilterWithCase("BMCHAINS");
var fixBMChains = (bmChains == null ? -1 : bmChains.length < 2 ? 0 : JU.PT.parseInt(bmChains.substring(1)));
if (fixBMChains == -2147483648) {
fixBMChains = -(bmChains.charAt(1)).charCodeAt(0);
}var particleMode = (filter.indexOf("BYCHAIN") >= 0 ? 1 : filter.indexOf("BYSYMOP") >= 0 ? 2 : 0);
this.doNormalize = false;
var biomtchains = thisBiomolecule.get("chains");
(this.symmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry()).setSpaceGroup(this.doNormalize);
this.addSpaceGroupOperation("x,y,z", false);
var name = thisBiomolecule.get("name");
this.setAtomSetSpaceGroupName(this.acr.sgName = name);
this.applySymmetryToBonds = applySymmetryToBonds;
this.bondCount0 = this.asc.bondCount;
this.firstAtom = this.asc.getLastAtomSetAtomIndex();
var atomMax = this.asc.ac;
var ht =  new java.util.Hashtable();
var nChain = 0;
var atoms = this.asc.atoms;
var addBonds = (this.bondCount0 > this.asc.bondIndex0 && applySymmetryToBonds);
switch (particleMode) {
case 1:
for (var i = atomMax; --i >= this.firstAtom; ) {
var id = Integer.$valueOf(atoms[i].chainID);
var bs = ht.get(id);
if (bs == null) {
nChain++;
ht.put(id, bs =  new JU.BS());
}bs.set(i);
}
this.asc.bsAtoms =  new JU.BS();
for (var i = 0; i < nChain; i++) {
this.asc.bsAtoms.set(atomMax + i);
var a =  new J.adapter.smarter.Atom();
a.set(0, 0, 0);
a.radius = 16;
this.asc.addAtom(a);
}
var ichain = 0;
for (var e, $e = ht.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var a = atoms[atomMax + ichain++];
var bs = e.getValue();
for (var i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) a.add(atoms[i]);

a.scale(1 / bs.cardinality());
a.atomName = "Pt" + ichain;
a.chainID = e.getKey().intValue();
}
this.firstAtom = atomMax;
atomMax += nChain;
addBonds = false;
break;
case 2:
this.asc.bsAtoms =  new JU.BS();
this.asc.bsAtoms.set(atomMax);
var a = atoms[atomMax] =  new J.adapter.smarter.Atom();
a.set(0, 0, 0);
for (var i = atomMax; --i >= this.firstAtom; ) a.add(atoms[i]);

a.scale(1 / (atomMax - this.firstAtom));
a.atomName = "Pt";
a.radius = 16;
this.asc.addAtom(a);
this.firstAtom = atomMax++;
addBonds = false;
break;
}
var assemblyIdAtoms = thisBiomolecule.get("asemblyIdAtoms");
if (filter.indexOf("#<") >= 0) {
len = Math.min(len, JU.PT.parseInt(filter.substring(filter.indexOf("#<") + 2)) - 1);
filter = JU.PT.rep(filter, "#<", "_<");
}var maxChain = 0;
for (var iAtom = this.firstAtom; iAtom < atomMax; iAtom++) {
atoms[iAtom].bsSymmetry =  new JU.BS();
var chainID = atoms[iAtom].chainID;
if (chainID > maxChain) maxChain = chainID;
}
var bsAtoms = this.asc.bsAtoms;
var atomMap = (addBonds ?  Clazz.newIntArray (this.asc.ac, 0) : null);
for (var imt = (biomtchains == null ? 1 : 0); imt < len; imt++) {
if (filter.indexOf("!#") >= 0) {
if (filter.indexOf("!#" + (imt + 1) + ";") >= 0) continue;
} else if (filter.indexOf("#") >= 0 && filter.indexOf("#" + (imt + 1) + ";") < 0) {
continue;
}var mat = biomts.get(imt);
var notIdentity = !mat.equals(this.mident);
var chains = (biomtchains == null ? null : biomtchains.get(imt));
if (chains != null && assemblyIdAtoms != null) {
bsAtoms =  new JU.BS();
for (var e, $e = assemblyIdAtoms.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) if (chains.indexOf(":" + e.getKey() + ";") >= 0) bsAtoms.or(e.getValue());

if (this.asc.bsAtoms != null) bsAtoms.and(this.asc.bsAtoms);
chains = null;
}var lastID = -1;
var id;
var skipping = false;
for (var iAtom = this.firstAtom; iAtom < atomMax; iAtom++) {
if (bsAtoms != null) {
skipping = !bsAtoms.get(iAtom);
} else if (chains != null && (id = atoms[iAtom].chainID) != lastID) {
skipping = (chains.indexOf(":" + this.acr.vwr.getChainIDStr(lastID = id) + ";") < 0);
}if (skipping) continue;
try {
var atomSite = atoms[iAtom].atomSite;
var atom1;
if (addBonds) atomMap[atomSite] = this.asc.ac;
atom1 = this.asc.newCloneAtom(atoms[iAtom]);
atom1.bondingRadius = imt;
this.asc.atomSymbolicMap.put("" + atom1.atomSerial, atom1);
if (this.asc.bsAtoms != null) this.asc.bsAtoms.set(atom1.index);
atom1.atomSite = atomSite;
if (notIdentity) mat.rotTrans(atom1);
atom1.bsSymmetry = JU.BSUtil.newAndSetBit(imt);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
this.asc.errorMessage = "appendAtomCollection error: " + e;
} else {
throw e;
}
}
}
if (notIdentity) this.symmetry.addBioMoleculeOperation(mat, false);
if (addBonds) {
for (var bondNum = this.asc.bondIndex0; bondNum < this.bondCount0; bondNum++) {
var bond = this.asc.bonds[bondNum];
var iAtom1 = atomMap[atoms[bond.atomIndex1].atomSite];
var iAtom2 = atomMap[atoms[bond.atomIndex2].atomSite];
this.asc.addNewBondWithOrder(iAtom1, iAtom2, bond.order);
}
}}
if (biomtchains != null) {
if (this.asc.bsAtoms == null) this.asc.bsAtoms = JU.BSUtil.newBitSet2(0, this.asc.ac);
this.asc.bsAtoms.clearBits(this.firstAtom, atomMax);
if (particleMode == 0) {
if (fixBMChains != -1) {
var assignABC = (fixBMChains != 0);
var bsChains = (assignABC ?  new JU.BS() : null);
atoms = this.asc.atoms;
var firstNew = 0;
if (assignABC) {
firstNew = (fixBMChains < 0 ? Math.max(-fixBMChains, maxChain + 1) : Math.max(maxChain + fixBMChains, 65));
bsChains.setBits(0, firstNew - 1);
bsChains.setBits(91, 97);
bsChains.setBits(123, 200);
}var bsAll = (this.asc.structureCount == 1 ? this.asc.structures[0].bsAll : null);
var chainMap =  new java.util.Hashtable();
var knownMap =  new java.util.Hashtable();
var knownAtomMap = (bsAll == null ? null :  new java.util.Hashtable());
var lastKnownAtom = null;
for (var i = atomMax, n = this.asc.ac; i < n; i++) {
var ic = atoms[i].chainID;
var isym = atoms[i].bsSymmetry.nextSetBit(0);
var ch0 = this.acr.vwr.getChainIDStr(ic);
var ch = (isym == 0 ? ch0 : ch0 + isym);
var known = chainMap.get(ch);
if (known == null) {
if (assignABC && isym != 0) {
var pt = (firstNew < 200 ? bsChains.nextClearBit(firstNew) : 200);
if (pt < 200) {
bsChains.set(pt);
known = Integer.$valueOf(this.acr.vwr.getChainID("" + String.fromCharCode(pt), true));
firstNew = pt;
} else {
}}if (known == null) known = Integer.$valueOf(this.acr.vwr.getChainID(ch, true));
if (ch !== ch0) {
knownMap.put(known, Integer.$valueOf(ic));
if (bsAll != null) {
if (lastKnownAtom != null) lastKnownAtom[1] = i;
knownAtomMap.put(known, lastKnownAtom =  Clazz.newIntArray(-1, [i, n]));
}}chainMap.put(ch, known);
}atoms[i].chainID = known.intValue();
}
if (this.asc.structureCount > 0) {
var strucs = this.asc.structures;
var nStruc = this.asc.structureCount;
for (var e, $e = knownMap.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var known = e.getKey();
var ch1 = known.intValue();
var ch0 = e.getValue().intValue();
for (var i = 0; i < nStruc; i++) {
var s = strucs[i];
if (s.bsAll != null) {
} else if (s.startChainID == s.endChainID) {
if (s.startChainID == ch0) {
var s1 = s.clone();
s1.startChainID = s1.endChainID = ch1;
this.asc.addStructure(s1);
}} else {
System.err.println("XtalSymmetry not processing biomt chain structure " + this.acr.vwr.getChainIDStr(ch0) + " to " + this.acr.vwr.getChainIDStr(ch1));
}}
}
}}var vConnect = this.asc.getAtomSetAuxiliaryInfoValue(-1, "PDB_CONECT_bonds");
if (!addBonds && vConnect != null) {
for (var i = vConnect.size(); --i >= 0; ) {
var bond = vConnect.get(i);
var a = this.asc.getAtomFromName("" + bond[0]);
var b = this.asc.getAtomFromName("" + bond[1]);
if (a != null && b != null && a.bondingRadius != b.bondingRadius && (bsAtoms == null || bsAtoms.get(a.index) && bsAtoms.get(b.index)) && a.distanceSquared(b) > 25.0) {
vConnect.removeItemAt(i);
System.out.println("long interchain bond removed for @" + a.atomSerial + "-@" + b.atomSerial);
}}
}}for (var i = atomMax, n = this.asc.ac; i < n; i++) {
this.asc.atoms[i].bondingRadius = NaN;
}
}this.noSymmetryCount = atomMax - this.firstAtom;
this.finalizeSymmetry(this.symmetry);
this.setCurrentModelInfo(len, null, null);
this.reset();
}, "java.util.Map,~B,~S");
Clazz.defineMethod(c$, "getBaseSymmetry", 
function(){
return (this.baseSymmetry == null ? this.symmetry : this.baseSymmetry);
});
Clazz.defineMethod(c$, "getOverallSpan", 
function(){
return (this.maxXYZ0 == null ? JU.V3.new3(this.maxXYZ.x - this.minXYZ.x, this.maxXYZ.y - this.minXYZ.y, this.maxXYZ.z - this.minXYZ.z) : JU.V3.newVsub(this.maxXYZ0, this.minXYZ0));
});
Clazz.defineMethod(c$, "getSymmetry", 
function(){
return (this.symmetry == null ? (this.symmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry()) : this.symmetry);
});
Clazz.defineMethod(c$, "isWithinCell", 
function(ndims, pt, minX, maxX, minY, maxY, minZ, maxZ, slop){
return (pt.x > minX - slop && pt.x < maxX + slop && (ndims < 2 || pt.y > minY - slop && pt.y < maxY + slop) && (ndims < 3 || pt.z > minZ - slop && pt.z < maxZ + slop));
}, "~N,JU.P3,~N,~N,~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "scaleFractionalVibs", 
function(){
var params = this.acr.unitCellParams;
var ptScale = JU.P3.new3(1 / params[0], 1 / params[1], 1 / params[2]);
var i0 = this.asc.getAtomSetAtomIndex(this.asc.iSet);
for (var i = this.asc.ac; --i >= i0; ) {
var v = this.asc.atoms[i].vib;
if (v != null) {
v.scaleT(ptScale);
}}
});
Clazz.defineMethod(c$, "set", 
function(reader){
this.acr = reader;
this.asc = reader.asc;
this.getSymmetry();
return this;
}, "J.adapter.smarter.AtomSetCollectionReader");
Clazz.defineMethod(c$, "setLatticeParameter", 
function(latt){
this.symmetry.setSpaceGroup(this.doNormalize);
this.symmetry.setLattice(latt);
}, "~N");
Clazz.defineMethod(c$, "setSpinVectors", 
function(){
if (this.nVib > 0 || this.asc.iSet < 0 || !this.acr.vibsFractional) return this.nVib;
var i0 = this.asc.getAtomSetAtomIndex(this.asc.iSet);
var sym = this.getBaseSymmetry();
for (var i = this.asc.ac; --i >= i0; ) {
var v = this.asc.atoms[i].vib;
if (v != null) {
if (v.modDim > 0) {
(v).setMoment();
} else {
v = v.clone();
sym.toCartesian(v, true);
this.asc.atoms[i].vib = v;
}this.nVib++;
}}
return this.nVib;
});
Clazz.defineMethod(c$, "addSpaceGroupOperation", 
function(xyz, andSetLattice){
this.symmetry.setSpaceGroup(this.doNormalize);
if (andSetLattice && this.symmetry.getSpaceGroupOperationCount() == 1) this.setLatticeCells();
return this.symmetry.addSpaceGroupOperation(xyz, 0);
}, "~S,~B");
Clazz.defineMethod(c$, "applySymmetryFromReader", 
function(readerSymmetry){
this.asc.setCoordinatesAreFractional(this.acr.iHaveFractionalCoordinates);
this.setAtomSetSpaceGroupName(this.acr.sgName);
this.symmetryRange = this.acr.symmetryRange;
this.asc.setInfo("symmetryRange", Float.$valueOf(this.symmetryRange));
if (this.acr.doConvertToFractional || this.acr.fileCoordinatesAreFractional) {
this.setLatticeCells();
var doApplySymmetry = true;
if (this.acr.ignoreFileSpaceGroupName || !this.acr.iHaveSymmetryOperators) {
if (this.acr.unitCellParams[0] == 0 && this.acr.unitCellParams[2] == 0) {
JU.SimpleUnitCell.fillParams(null, null, null, this.acr.unitCellParams);
}if (!this.acr.merging || readerSymmetry == null) readerSymmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry();
doApplySymmetry = readerSymmetry.createSpaceGroup(this.acr.desiredSpaceGroupIndex, (this.acr.sgName.indexOf("!") >= 0 ? "P1" : this.acr.sgName), this.acr.unitCellParams, this.acr.modDim);
} else {
this.acr.doPreSymmetry();
readerSymmetry = null;
}this.packingRange = this.acr.getPackingRangeValue(0);
if (doApplySymmetry) {
if (readerSymmetry != null) this.getSymmetry().setSpaceGroupTo(readerSymmetry.getSpaceGroup());
this.applySymmetryLattice();
if (readerSymmetry != null && this.filterSymop == null) this.setAtomSetSpaceGroupName(readerSymmetry.getSpaceGroupName());
} else {
this.setUnitCellSafely();
}}if (this.acr.iHaveFractionalCoordinates && this.acr.merging && readerSymmetry != null) {
var atoms = this.asc.atoms;
for (var i = this.asc.getLastAtomSetAtomIndex(), n = this.asc.ac; i < n; i++) readerSymmetry.toCartesian(atoms[i], true);

this.asc.setCoordinatesAreFractional(false);
this.acr.addVibrations = false;
}return this.symmetry;
}, "J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz.defineMethod(c$, "setSymmetry", 
function(symmetry){
return (this.symmetry = symmetry);
}, "J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz.defineMethod(c$, "setTensors", 
function(){
var n = this.asc.ac;
for (var i = this.asc.getLastAtomSetAtomIndex(); i < n; i++) {
var a = this.asc.atoms[i];
if (a.anisoBorU == null) continue;
a.addTensor(this.symmetry.getTensor(this.acr.vwr, a.anisoBorU), null, false);
if (Float.isNaN(a.bfactor)) a.bfactor = a.anisoBorU[7] * 100;
a.anisoBorU = null;
}
});
Clazz.defineMethod(c$, "adjustRangeMinMax", 
function(oabc){
var pa =  new JU.P3();
var pb =  new JU.P3();
var pc =  new JU.P3();
if (this.acr.forcePacked) {
pa.setT(oabc[1]);
pb.setT(oabc[2]);
pc.setT(oabc[3]);
pa.scale(this.packingRange);
pb.scale(this.packingRange);
pc.scale(this.packingRange);
}oabc[0].scaleAdd2(this.minXYZ.x, oabc[1], oabc[0]);
oabc[0].scaleAdd2(this.minXYZ.y, oabc[2], oabc[0]);
oabc[0].scaleAdd2(this.minXYZ.z, oabc[3], oabc[0]);
oabc[0].sub(pa);
oabc[0].sub(pb);
oabc[0].sub(pc);
var pt = JU.P3.newP(oabc[0]);
this.symmetry.toFractional(pt, true);
this.setSymmetryMinMax(pt);
oabc[1].scale(this.maxXYZ.x - this.minXYZ.x);
oabc[2].scale(this.maxXYZ.y - this.minXYZ.y);
oabc[3].scale(this.maxXYZ.z - this.minXYZ.z);
oabc[1].scaleAdd2(2, pa, oabc[1]);
oabc[2].scaleAdd2(2, pb, oabc[2]);
oabc[3].scaleAdd2(2, pc, oabc[3]);
for (var i = 0; i < 3; i++) {
for (var j = i + 1; j < 4; j++) {
pt.add2(oabc[i], oabc[j]);
if (i != 0) pt.add(oabc[0]);
this.symmetry.toFractional(pt, false);
this.setSymmetryMinMax(pt);
}
}
this.symmetry.toCartesian(pt, false);
pt.add(oabc[1]);
this.symmetry.toFractional(pt, false);
this.setSymmetryMinMax(pt);
this.minXYZ = JU.P3i.new3(Clazz.doubleToInt(Math.min(0, Math.floor(this.rminx + 0.001))), Clazz.doubleToInt(Math.min(0, Math.floor(this.rminy + 0.001))), Clazz.doubleToInt(Math.min(0, Math.floor(this.rminz + 0.001))));
this.maxXYZ = JU.P3i.new3(Clazz.doubleToInt(Math.max(1, Math.ceil(this.rmaxx - 0.001))), Clazz.doubleToInt(Math.max(1, Math.ceil(this.rmaxy - 0.001))), Clazz.doubleToInt(Math.max(1, Math.ceil(this.rmaxz - 0.001))));
}, "~A");
Clazz.defineMethod(c$, "applyAllSymmetry", 
function(ms, bsAtoms){
if (this.asc.ac == 0 || bsAtoms != null && bsAtoms.isEmpty()) return;
var n = this.noSymmetryCount = this.asc.baseSymmetryAtomCount > 0 ? this.asc.baseSymmetryAtomCount : bsAtoms == null ? this.asc.getLastAtomSetAtomCount() : this.asc.ac - bsAtoms.nextSetBit(this.asc.getLastAtomSetAtomIndex());
this.asc.setTensors();
this.applySymmetryToBonds = this.acr.applySymmetryToBonds;
this.doPackUnitCell = this.acr.doPackUnitCell && !this.applySymmetryToBonds;
this.bondCount0 = this.asc.bondCount;
this.ndims = JU.SimpleUnitCell.getDimensionFromParams(this.acr.unitCellParams);
this.finalizeSymmetry(this.symmetry);
var operationCount = this.symmetry.getSpaceGroupOperationCount();
var excludedOps = (this.acr.thisBiomolecule == null ? null :  new JU.BS());
this.checkNearAtoms = this.acr.checkNearAtoms || excludedOps != null;
JU.SimpleUnitCell.setMinMaxLatticeParameters(this.ndims, this.minXYZ, this.maxXYZ, 0);
this.latticeOp = this.symmetry.getLatticeOp();
this.crystalReaderLatticeOpsOnly = (this.asc.crystalReaderLatticeOpsOnly && this.latticeOp >= 0);
if (this.doCentroidUnitCell) this.asc.setInfo("centroidMinMax",  Clazz.newIntArray(-1, [this.minXYZ.x, this.minXYZ.y, this.minXYZ.z, this.maxXYZ.x, this.maxXYZ.y, this.maxXYZ.z, (this.centroidPacked ? 1 : 0)]));
if (this.doCentroidUnitCell || this.acr.doPackUnitCell || this.symmetryRange != 0 && this.maxXYZ.x - this.minXYZ.x == 1 && this.maxXYZ.y - this.minXYZ.y == 1 && this.maxXYZ.z - this.minXYZ.z == 1) {
this.minXYZ0 = JU.P3.new3(this.minXYZ.x, this.minXYZ.y, this.minXYZ.z);
this.maxXYZ0 = JU.P3.new3(this.maxXYZ.x, this.maxXYZ.y, this.maxXYZ.z);
if (ms != null) {
ms.setMinMax0(this.minXYZ0, this.maxXYZ0);
this.minXYZ.set(Clazz.floatToInt(this.minXYZ0.x), Clazz.floatToInt(this.minXYZ0.y), Clazz.floatToInt(this.minXYZ0.z));
this.maxXYZ.set(Clazz.floatToInt(this.maxXYZ0.x), Clazz.floatToInt(this.maxXYZ0.y), Clazz.floatToInt(this.maxXYZ0.z));
}switch (this.ndims) {
case 3:
this.minXYZ.z--;
this.maxXYZ.z++;
case 2:
this.minXYZ.y--;
this.maxXYZ.y++;
case 1:
this.minXYZ.x--;
this.maxXYZ.x++;
}
}var nCells = (this.maxXYZ.x - this.minXYZ.x) * (this.maxXYZ.y - this.minXYZ.y) * (this.maxXYZ.z - this.minXYZ.z);
var nsym = n * (this.crystalReaderLatticeOpsOnly ? 4 : operationCount);
var cartesianCount = (this.checkNearAtoms || this.acr.thisBiomolecule != null ? nsym * nCells : this.symmetryRange > 0 ? nsym : 1);
var cartesians =  new Array(cartesianCount);
var atoms = this.asc.atoms;
for (var i = 0; i < n; i++) atoms[this.firstAtom + i].bsSymmetry = JU.BS.newN(operationCount * (nCells + 1));

var pt = 0;
this.unitCellTranslations =  new Array(nCells);
var iCell = 0;
var cell555Count = 0;
var absRange = Math.abs(this.symmetryRange);
var checkCartesianRange = (this.symmetryRange != 0);
var checkRangeNoSymmetry = (this.symmetryRange < 0);
var checkRange111 = (this.symmetryRange > 0);
if (checkCartesianRange) {
this.rminx = this.rminy = this.rminz = 3.4028235E38;
this.rmaxx = this.rmaxy = this.rmaxz = -3.4028235E38;
}var sym = this.symmetry;
var lastSymmetry = sym;
this.checkAll = (this.crystalReaderLatticeOpsOnly || this.asc.atomSetCount == 1 && this.checkNearAtoms && this.latticeOp >= 0);
var lstNCS = this.acr.lstNCS;
if (lstNCS != null && lstNCS.get(0).m33 == 0) {
var nOp = sym.getSpaceGroupOperationCount();
var nn = lstNCS.size();
for (var i = nn; --i >= 0; ) {
var m = lstNCS.get(i);
m.m33 = 1;
sym.toFractionalM(m);
}
for (var i = 1; i < nOp; i++) {
var m1 = sym.getSpaceGroupOperation(i);
for (var j = 0; j < nn; j++) {
var m = JU.M4.newM4(lstNCS.get(j));
m.mul2(m1, m);
if (this.doNormalize && this.noSymmetryCount > 0) JS.SymmetryOperation.normalizeOperationToCentroid(3, m, atoms, this.firstAtom, this.noSymmetryCount);
lstNCS.addLast(m);
}
}
}var pttemp = null;
var op = sym.getSpaceGroupOperation(0);
if (this.doPackUnitCell) {
pttemp =  new JU.P3();
this.ptOffset.set(0, 0, 0);
}var atomMap = (this.bondCount0 > this.asc.bondIndex0 && this.applySymmetryToBonds ?  Clazz.newIntArray (n, 0) : null);
var unitCells =  Clazz.newIntArray (nCells, 0);
for (var tx = this.minXYZ.x; tx < this.maxXYZ.x; tx++) {
for (var ty = this.minXYZ.y; ty < this.maxXYZ.y; ty++) {
for (var tz = this.minXYZ.z; tz < this.maxXYZ.z; tz++) {
this.unitCellTranslations[iCell] = JU.V3.new3(tx, ty, tz);
unitCells[iCell++] = 555 + tx * 100 + ty * 10 + tz;
if (tx != 0 || ty != 0 || tz != 0 || cartesians.length == 0) continue;
for (pt = 0; pt < n; pt++) {
var atom = atoms[this.firstAtom + pt];
if (ms != null) {
sym = ms.getAtomSymmetry(atom, this.symmetry);
if (sym !== lastSymmetry) {
if (sym.getSpaceGroupOperationCount() == 0) this.finalizeSymmetry(lastSymmetry = sym);
op = sym.getSpaceGroupOperation(0);
}}var c = JU.P3.newP(atom);
op.rotTrans(c);
sym.toCartesian(c, false);
if (this.doPackUnitCell) {
sym.toUnitCellRnd(c, this.ptOffset);
pttemp.setT(c);
sym.toFractional(pttemp, false);
this.acr.fixFloatPt(pttemp, 100000.0);
if (bsAtoms == null) atom.setT(pttemp);
 else if (atom.distance(pttemp) < 1.0E-4) bsAtoms.set(atom.index);
 else {
bsAtoms.clear(atom.index);
continue;
}}if (bsAtoms != null) atom.bsSymmetry.clearAll();
atom.bsSymmetry.set(iCell * operationCount);
atom.bsSymmetry.set(0);
if (checkCartesianRange) this.setSymmetryMinMax(c);
if (pt < cartesianCount) cartesians[pt] = c;
}
if (checkRangeNoSymmetry) {
this.rminx -= absRange;
this.rminy -= absRange;
this.rminz -= absRange;
this.rmaxx += absRange;
this.rmaxy += absRange;
this.rmaxz += absRange;
}cell555Count = pt = this.symmetryAddAtoms(0, 0, 0, 0, pt, iCell * operationCount, cartesians, ms, excludedOps, atomMap);
}
}
}
if (checkRange111) {
this.rminx -= absRange;
this.rminy -= absRange;
this.rminz -= absRange;
this.rmaxx += absRange;
this.rmaxy += absRange;
this.rmaxz += absRange;
}iCell = 0;
for (var tx = this.minXYZ.x; tx < this.maxXYZ.x; tx++) {
for (var ty = this.minXYZ.y; ty < this.maxXYZ.y; ty++) {
for (var tz = this.minXYZ.z; tz < this.maxXYZ.z; tz++) {
iCell++;
if (tx != 0 || ty != 0 || tz != 0) pt = this.symmetryAddAtoms(tx, ty, tz, cell555Count, pt, iCell * operationCount, cartesians, ms, excludedOps, atomMap);
}
}
}
if (iCell * n == this.asc.ac - this.firstAtom) this.duplicateAtomProperties(iCell);
this.setCurrentModelInfo(n, sym, unitCells);
this.unitCellParams = null;
this.reset();
}, "J.adapter.smarter.MSInterface,JU.BS");
Clazz.defineMethod(c$, "applyRangeSymmetry", 
function(bsAtoms){
var range = this.acr.fillRange;
bsAtoms = this.updateBSAtoms();
this.acr.forcePacked = true;
this.doPackUnitCell = false;
var minXYZ2 = JU.P3i.new3(this.minXYZ.x, this.minXYZ.y, this.minXYZ.z);
var maxXYZ2 = JU.P3i.new3(this.maxXYZ.x, this.maxXYZ.y, this.maxXYZ.z);
var oabc =  new Array(4);
for (var i = 0; i < 4; i++) oabc[i] = JU.P3.newP(range[i]);

this.setUnitCellSafely();
this.adjustRangeMinMax(oabc);
var superSymmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry();
superSymmetry.getUnitCell(this.acr.fillRange, false, null);
this.applyAllSymmetry(this.acr.ms, bsAtoms);
var pt0 =  new JU.P3();
var atoms = this.asc.atoms;
for (var i = this.asc.ac; --i >= this.firstAtom; ) {
pt0.setT(atoms[i]);
this.symmetry.toCartesian(pt0, false);
superSymmetry.toFractional(pt0, false);
if (this.acr.noPack ? !this.removePacking(this.ndims, pt0, minXYZ2.x, maxXYZ2.x, minXYZ2.y, maxXYZ2.y, minXYZ2.z, maxXYZ2.z, this.packingRange) : !this.isWithinCell(this.ndims, pt0, minXYZ2.x, maxXYZ2.x, minXYZ2.y, maxXYZ2.y, minXYZ2.z, maxXYZ2.z, this.packingRange)) bsAtoms.clear(i);
}
}, "JU.BS");
Clazz.defineMethod(c$, "applySuperSymmetry", 
function(supercell, bsAtoms, iAtomFirst, oabc, pt0, vabc, slop){
this.asc.setGlobalBoolean(7);
var doPack0 = this.doPackUnitCell;
this.doPackUnitCell = doPack0;
this.applyAllSymmetry(this.acr.ms, null);
this.doPackUnitCell = doPack0;
var atoms = this.asc.atoms;
var atomCount = this.asc.ac;
for (var i = iAtomFirst; i < atomCount; i++) {
this.symmetry.toCartesian(atoms[i], true);
bsAtoms.set(i);
}
this.asc.setCurrentModelInfo("unitcell_conventional", this.symmetry.getV0abc("a,b,c", null));
var va = vabc[0];
var vb = vabc[1];
var vc = vabc[2];
this.symmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry();
this.setUnitCell( Clazz.newFloatArray(-1, [0, 0, 0, 0, 0, 0, va.x, va.y, va.z, vb.x, vb.y, vb.z, vc.x, vc.y, vc.z, 0, 0, 0, 0, 0, 0, NaN, NaN, NaN, NaN, NaN, slop]), null, null);
var name = oabc == null || supercell == null ? "P1" : "cell=" + supercell;
this.setAtomSetSpaceGroupName(name);
this.symmetry.setSpaceGroupName(name);
this.symmetry.setSpaceGroup(this.doNormalize);
this.symmetry.addSpaceGroupOperation("x,y,z", 0);
if (pt0 != null && pt0.length() == 0) pt0 = null;
if (pt0 != null) this.symmetry.toFractional(pt0, true);
for (var i = iAtomFirst; i < atomCount; i++) {
this.symmetry.toFractional(atoms[i], true);
if (pt0 != null) atoms[i].sub(pt0);
}
this.asc.haveAnisou = false;
this.asc.setCurrentModelInfo("matUnitCellOrientation", null);
}, "~S,JU.BS,~N,~A,JU.P3,~A,~N");
Clazz.defineMethod(c$, "applySymmetryLattice", 
function(){
if (!this.asc.coordinatesAreFractional || this.symmetry.getSpaceGroup() == null) return;
var maxX = this.latticeCells[0];
var maxY = this.latticeCells[1];
var maxZ = Math.abs(this.latticeCells[2]);
var kcode = this.latticeCells[3];
this.firstAtom = this.asc.getLastAtomSetAtomIndex();
var bsAtoms = this.asc.bsAtoms;
if (bsAtoms != null) {
this.updateBSAtoms();
this.firstAtom = bsAtoms.nextSetBit(this.firstAtom);
}this.rminx = this.rminy = this.rminz = 3.4028235E38;
this.rmaxx = this.rmaxy = this.rmaxz = -3.4028235E38;
if (this.acr.latticeType == null) this.acr.latticeType = "" + this.symmetry.getLatticeType();
if (this.acr.isPrimitive) {
this.asc.setCurrentModelInfo("isprimitive", Boolean.TRUE);
if (!"P".equals(this.acr.latticeType) || this.acr.primitiveToCrystal != null) {
this.asc.setCurrentModelInfo("unitcell_conventional", this.symmetry.getConventionalUnitCell(this.acr.latticeType, this.acr.primitiveToCrystal));
}}this.setUnitCellSafely();
this.asc.setCurrentModelInfo("f2c", this.symmetry.getUnitCellF2C());
var s = this.symmetry.getSpaceGroupTitle();
if (s.indexOf("--") < 0) this.asc.setCurrentModelInfo("f2cTitle", s);
this.asc.setCurrentModelInfo("f2cParams", this.symmetry.getUnitCellParams());
if (this.acr.latticeType != null) {
this.asc.setCurrentModelInfo("latticeType", this.acr.latticeType);
if ((typeof(this.acr.fillRange)=='string')) {
var range = this.setLatticeRange(this.acr.latticeType, this.acr.fillRange);
if (range == null) {
this.acr.appendLoadNote(this.acr.fillRange + " symmetry could not be implemented");
this.acr.fillRange = null;
} else {
this.acr.fillRange = range;
}}}this.baseSymmetry = this.symmetry;
if (this.acr.fillRange != null) {
this.setMinMax(this.ndims, kcode, maxX, maxY, maxZ);
this.applyRangeSymmetry(bsAtoms);
return;
}var oabc = null;
var slop = 1e-6;
this.nVib = 0;
var supercell = this.acr.strSupercell;
var isSuper = (supercell != null && supercell.indexOf(",") >= 0);
var matSuper = null;
var pt0 = null;
var vabc =  new Array(3);
if (isSuper) {
matSuper =  new JU.M4();
if (this.mident == null) this.mident =  new JU.M4();
this.setUnitCellSafely();
oabc = this.symmetry.getV0abc(supercell, matSuper);
matSuper.transpose33();
if (oabc != null && !matSuper.equals(this.mident)) {
this.setMinMax(this.ndims, kcode, maxX, maxY, maxZ);
pt0 = JU.P3.newP(oabc[0]);
vabc[0] = JU.V3.newV(oabc[1]);
vabc[1] = JU.V3.newV(oabc[2]);
vabc[2] = JU.V3.newV(oabc[3]);
this.adjustRangeMinMax(oabc);
}}var iAtomFirst = this.asc.getLastAtomSetAtomIndex();
if (bsAtoms != null) iAtomFirst = bsAtoms.nextSetBit(iAtomFirst);
if (this.rminx == 3.4028235E38) {
supercell = null;
oabc = null;
} else {
bsAtoms = this.updateBSAtoms();
slop = this.symmetry.getPrecision();
this.applySuperSymmetry(supercell, bsAtoms, iAtomFirst, oabc, pt0, vabc, slop);
}this.setMinMax(this.ndims, kcode, maxX, maxY, maxZ);
if (oabc == null) {
this.applyAllSymmetry(this.acr.ms, bsAtoms);
if (!this.acr.noPack && (!this.applySymmetryToBonds || !this.acr.doPackUnitCell)) {
return;
}this.setMinMax(this.ndims, kcode, maxX, maxY, maxZ);
}if (this.acr.forcePacked || this.acr.doPackUnitCell || this.acr.noPack) {
this.trimToUnitCell(iAtomFirst);
}this.updateSupercellAtomSites(matSuper, bsAtoms, slop);
});
Clazz.defineMethod(c$, "duplicateAtomProperties", 
function(nTimes){
var p = this.asc.getAtomSetAuxiliaryInfoValue(-1, "atomProperties");
if (p != null) for (var entry, $entry = p.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
var key = entry.getKey();
var val = entry.getValue();
if ((typeof(val)=='string')) {
var data = val;
var s =  new JU.SB();
for (var i = nTimes; --i >= 0; ) s.append(data);

p.put(key, s.toString());
} else {
var f = val;
var fnew =  Clazz.newFloatArray (f.length * nTimes, 0);
for (var i = nTimes; --i >= 0; ) System.arraycopy(f, 0, fnew, i * f.length, f.length);

}}
}, "~N");
Clazz.defineMethod(c$, "finalizeSymmetry", 
function(symmetry){
var name = this.asc.getAtomSetAuxiliaryInfoValue(-1, "spaceGroup");
symmetry.setFinalOperations(this.ndims, name, this.asc.atoms, this.firstAtom, this.noSymmetryCount, this.doNormalize, this.filterSymop);
if (this.filterSymop != null || name == null || name.equals("unspecified!")) {
this.setAtomSetSpaceGroupName(symmetry.getSpaceGroupName());
}if (this.unitCellParams != null || Float.isNaN(this.acr.unitCellParams[0])) return;
if (symmetry.fixUnitCell(this.acr.unitCellParams)) {
this.acr.appendLoadNote("Unit cell parameters were adjusted to match space group!");
}this.setUnitCellSafely();
}, "J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz.defineMethod(c$, "removePacking", 
function(ndims, pt, minX, maxX, minY, maxY, minZ, maxZ, slop){
return (pt.x > minX - slop && pt.x < maxX - slop && (ndims < 2 || pt.y > minY - slop && pt.y < maxY - slop) && (ndims < 3 || pt.z > minZ - slop && pt.z < maxZ - slop));
}, "~N,JU.P3,~N,~N,~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "reset", 
function(){
this.asc.coordinatesAreFractional = false;
this.asc.setCurrentModelInfo("hasSymmetry", Boolean.TRUE);
this.asc.setGlobalBoolean(1);
});
Clazz.defineMethod(c$, "setAtomSetSpaceGroupName", 
function(spaceGroupName){
this.symmetry.setSpaceGroupName(spaceGroupName);
this.asc.setCurrentModelInfo("spaceGroup", spaceGroupName + "");
}, "~S");
Clazz.defineMethod(c$, "setCurrentModelInfo", 
function(n, sym, unitCells){
if (sym == null) {
this.asc.setCurrentModelInfo("presymmetryAtomCount", Integer.$valueOf(this.noSymmetryCount));
this.asc.setCurrentModelInfo("biosymmetryCount", Integer.$valueOf(n));
this.asc.setCurrentModelInfo("biosymmetry", this.symmetry);
} else {
this.asc.setCurrentModelInfo("presymmetryAtomCount", Integer.$valueOf(n));
this.asc.setCurrentModelInfo("latticeDesignation", sym.getLatticeDesignation());
this.asc.setCurrentModelInfo("ML_unitCellRange", unitCells);
if (this.acr.isSUPERCELL) this.asc.setCurrentModelInfo("supercell", this.acr.strSupercell);
}this.asc.setCurrentModelInfo("presymmetryAtomIndex", Integer.$valueOf(this.firstAtom));
var operationCount = this.symmetry.getSpaceGroupOperationCount();
if (operationCount > 0) {
var symmetryList =  new Array(operationCount);
for (var i = 0; i < operationCount; i++) symmetryList[i] = "" + this.symmetry.getSpaceGroupXyz(i, this.doNormalize);

this.asc.setCurrentModelInfo("symmetryOperations", symmetryList);
this.asc.setCurrentModelInfo("symmetryOps", this.symmetry.getSymmetryOperations());
}this.asc.setCurrentModelInfo("symmetryCount", Integer.$valueOf(operationCount));
this.asc.setCurrentModelInfo("latticeType", this.acr.latticeType == null ? "P" : this.acr.latticeType);
this.asc.setCurrentModelInfo("intlTableNo", this.symmetry.getIntTableNumber());
this.asc.setCurrentModelInfo("intlTableIndex", this.symmetry.getSpaceGroupInfoObj("itaIndex", null, false, false));
this.asc.setCurrentModelInfo("intlTableTransform", this.symmetry.getSpaceGroupInfoObj("itaTransform", null, false, false));
this.asc.setCurrentModelInfo("intlTableJmolID", this.symmetry.getIntTableNumberFull());
this.asc.setCurrentModelInfo("spaceGroupIndex", Integer.$valueOf(this.symmetry.getSpaceGroupIndex()));
this.asc.setCurrentModelInfo("spaceGroupTitle", this.symmetry.getSpaceGroupTitle());
if (this.acr.sgName == null || this.acr.sgName.indexOf("?") >= 0 || this.acr.sgName.indexOf("!") >= 0) this.setAtomSetSpaceGroupName(this.acr.sgName = this.symmetry.getSpaceGroupName());
}, "~N,J.adapter.smarter.XtalSymmetry.FileSymmetry,~A");
Clazz.defineMethod(c$, "setCurrentModelUCInfo", 
function(unitCellParams, unitCellOffset, matUnitCellOrientation){
if (unitCellParams != null) this.asc.setCurrentModelInfo("unitCellParams", unitCellParams);
if (unitCellOffset != null) this.asc.setCurrentModelInfo("unitCellOffset", unitCellOffset);
if (matUnitCellOrientation != null) this.asc.setCurrentModelInfo("matUnitCellOrientation", matUnitCellOrientation);
}, "~A,JU.P3,JU.M3");
Clazz.defineMethod(c$, "setLatticeCells", 
function(){
this.latticeCells = this.acr.latticeCells;
var isLatticeRange = (this.latticeCells[0] <= 555 && this.latticeCells[1] >= 555 && (this.latticeCells[2] == 0 || this.latticeCells[2] == 1 || this.latticeCells[2] == -1));
this.doNormalize = this.latticeCells[0] != 0 && (!isLatticeRange || this.latticeCells[2] == 1);
this.applySymmetryToBonds = this.acr.applySymmetryToBonds;
this.doPackUnitCell = this.acr.doPackUnitCell && !this.applySymmetryToBonds;
this.doCentroidUnitCell = this.acr.doCentroidUnitCell;
this.centroidPacked = this.acr.centroidPacked;
this.filterSymop = this.acr.filterSymop;
});
Clazz.defineMethod(c$, "setLatticeRange", 
function(latticetype, rangeType){
var range = null;
var isRhombohedral = "R".equals(latticetype);
if (rangeType.equals("conventional")) {
range = this.symmetry.getConventionalUnitCell(latticetype, this.acr.primitiveToCrystal);
} else if (rangeType.equals("primitive")) {
range = this.symmetry.getUnitCellVectors();
this.symmetry.toFromPrimitive(true, latticetype.charAt(0), range, this.acr.primitiveToCrystal);
} else if (isRhombohedral && rangeType.equals("rhombohedral")) {
if (this.symmetry.getUnitCellInfoType(7) == 1) {
rangeType = "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c";
} else {
rangeType = null;
}} else if (isRhombohedral && rangeType.equals("trigonal")) {
if (this.symmetry.getUnitCellInfoType(8) == 1) {
rangeType = "a-b,b-c,a+b+c";
} else {
rangeType = null;
}} else if (rangeType.indexOf(",") < 0 || rangeType.indexOf("a") < 0 || rangeType.indexOf("b") < 0 || rangeType.indexOf("c") < 0) {
rangeType = null;
} else {
rangeType = null;
}if (rangeType != null && range == null && (range = this.symmetry.getV0abc(rangeType, null)) == null) {
rangeType = null;
}if (rangeType == null) return null;
this.acr.addJmolScript("unitcell " + JU.PT.esc(rangeType));
return range;
}, "~S,~S");
Clazz.defineMethod(c$, "setMinMax", 
function(dim, kcode, maxX, maxY, maxZ){
this.minXYZ =  new JU.P3i();
this.maxXYZ = JU.P3i.new3(maxX, maxY, maxZ);
JU.SimpleUnitCell.setMinMaxLatticeParameters(dim, this.minXYZ, this.maxXYZ, kcode);
}, "~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "setSymmetryMinMax", 
function(c){
if (this.rminx > c.x) this.rminx = c.x;
if (this.rminy > c.y) this.rminy = c.y;
if (this.rminz > c.z) this.rminz = c.z;
if (this.rmaxx < c.x) this.rmaxx = c.x;
if (this.rmaxy < c.y) this.rmaxy = c.y;
if (this.rmaxz < c.z) this.rmaxz = c.z;
}, "JU.P3");
Clazz.defineMethod(c$, "setUnitCell", 
function(info, matUnitCellOrientation, unitCellOffset){
this.unitCellParams =  Clazz.newFloatArray (info.length, 0);
for (var i = 0; i < info.length; i++) this.unitCellParams[i] = info[i];

this.asc.haveUnitCell = true;
if (this.asc.isTrajectory) {
if (this.trajectoryUnitCells == null) {
this.trajectoryUnitCells =  new JU.Lst();
this.asc.setInfo("unitCells", this.trajectoryUnitCells);
}this.trajectoryUnitCells.addLast(this.unitCellParams);
}this.asc.setGlobalBoolean(2);
this.getSymmetry().setUnitCellFromParams(this.unitCellParams, false, this.unitCellParams[26]);
if (unitCellOffset != null) this.symmetry.setOffsetPt(unitCellOffset);
if (matUnitCellOrientation != null) this.symmetry.initializeOrientation(matUnitCellOrientation);
this.setCurrentModelUCInfo(this.unitCellParams, unitCellOffset, matUnitCellOrientation);
}, "~A,JU.M3,JU.P3");
Clazz.defineMethod(c$, "setUnitCellSafely", 
function(){
if (this.unitCellParams == null) this.setUnitCell(this.acr.unitCellParams, this.acr.matUnitCellOrientation, this.acr.unitCellOffset);
});
Clazz.defineMethod(c$, "symmetryAddAtoms", 
function(transX, transY, transZ, baseCount, pt, iCellOpPt, cartesians, ms, excludedOps, atomMap){
var isBaseCell = (baseCount == 0);
var addBonds = (atomMap != null);
if (this.doPackUnitCell) this.ptOffset.set(transX, transY, transZ);
var range2 = this.symmetryRange * this.symmetryRange;
var checkRangeNoSymmetry = (this.symmetryRange < 0);
var checkRange111 = (this.symmetryRange > 0);
var checkSymmetryMinMax = (isBaseCell && checkRange111);
checkRange111 = new Boolean (checkRange111 & !isBaseCell).valueOf();
var nOp = this.symmetry.getSpaceGroupOperationCount();
var lstNCS = this.acr.lstNCS;
var nNCS = (lstNCS == null ? 0 : lstNCS.size());
var nOperations = nOp + nNCS;
nNCS = Clazz.doubleToInt(nNCS / nOp);
var checkNearAtoms = (this.checkNearAtoms && (nOperations > 1 || this.doPackUnitCell));
var checkSymmetryRange = (checkRangeNoSymmetry || checkRange111);
var checkDistances = (checkNearAtoms || checkSymmetryRange);
var checkOps = (excludedOps != null);
var addCartesian = (checkNearAtoms || checkSymmetryMinMax);
var bsAtoms = (this.acr.isMolecular ? null : this.asc.bsAtoms);
var sym = this.symmetry;
if (checkRangeNoSymmetry) baseCount = this.noSymmetryCount;
var atomMax = this.firstAtom + this.noSymmetryCount;
var bondAtomMin = (this.asc.firstAtomToBond < 0 ? atomMax : this.asc.firstAtomToBond);
var pttemp =  new JU.P3();
var code = null;
var minCartDist2 = (checkOps ? 0.01 : 1.0E-4);
var subSystemId = '\u0000';
var j00 = (bsAtoms == null ? this.firstAtom : bsAtoms.nextSetBit(this.firstAtom));
out : for (var iSym = 0; iSym < nOperations; iSym++) {
if (isBaseCell && iSym == 0 || this.crystalReaderLatticeOpsOnly && iSym > 0 && (iSym % this.latticeOp) != 0 || excludedOps != null && excludedOps.get(iSym)) continue;
var pt0 = this.firstAtom + (checkNearAtoms ? pt : checkRange111 ? baseCount : 0);
var spinOp = (iSym >= nOp ? 0 : this.asc.vibScale == 0 ? sym.getSpinOp(iSym) : this.asc.vibScale);
var i0 = Math.max(this.firstAtom, (bsAtoms == null ? 0 : bsAtoms.nextSetBit(0)));
var checkDistance = checkDistances;
var spt = (iSym >= nOp ? Clazz.doubleToInt((iSym - nOp) / nNCS) : iSym);
var cpt = spt + iCellOpPt;
for (var i = i0; i < atomMax; i++) {
var a = this.asc.atoms[i];
if (bsAtoms != null && !bsAtoms.get(i)) continue;
if (ms == null) {
sym.newSpaceGroupPoint(a, iSym, (iSym >= nOp ? lstNCS.get(iSym - nOp) : null), transX, transY, transZ, pttemp);
} else {
sym = ms.getAtomSymmetry(a, this.symmetry);
sym.newSpaceGroupPoint(a, iSym, null, transX, transY, transZ, pttemp);
code = sym.getSpaceGroupOperationCode(iSym);
if (code != null) {
subSystemId = code.charAt(0);
sym = ms.getSymmetryFromCode(code);
if (sym.getSpaceGroupOperationCount() == 0) this.finalizeSymmetry(sym);
}}this.acr.fixFloatPt(pttemp, 100000.0);
var c = JU.P3.newP(pttemp);
sym.toCartesian(c, false);
if (this.doPackUnitCell) {
sym.toUnitCellRnd(c, this.ptOffset);
pttemp.setT(c);
sym.toFractional(pttemp, false);
this.acr.fixFloatPt(pttemp, 100000.0);
if (!this.isWithinCell(this.ndims, pttemp, this.minXYZ0.x, this.maxXYZ0.x, this.minXYZ0.y, this.maxXYZ0.y, this.minXYZ0.z, this.maxXYZ0.z, this.packingRange)) {
continue;
}}if (checkSymmetryMinMax) this.setSymmetryMinMax(c);
var special = null;
if (checkDistance) {
if (checkSymmetryRange && (c.x < this.rminx || c.y < this.rminy || c.z < this.rminz || c.x > this.rmaxx || c.y > this.rmaxy || c.z > this.rmaxz)) continue;
var minDist2 = 3.4028235E38;
var j0 = (this.checkAll ? this.asc.ac : pt0);
var name = a.atomName;
var id = (code == null ? a.altLoc : subSystemId);
for (var j = j00; j < j0; j++) {
if (bsAtoms != null && !bsAtoms.get(j)) continue;
var pc = cartesians[j - this.firstAtom];
if (pc == null) continue;
var d2 = c.distanceSquared(pc);
if (checkNearAtoms && d2 < minCartDist2) {
if (checkOps) {
excludedOps.set(iSym);
continue out;
}special = this.asc.atoms[j];
if ((special.atomName == null || special.atomName.equals(name)) && special.altLoc == id) break;
special = null;
}if (checkRange111 && j < baseCount && d2 < minDist2) minDist2 = d2;
}
if (checkRange111 && minDist2 > range2) continue;
}if (checkOps) {
checkDistance = false;
}var atomSite = a.atomSite;
if (special != null) {
if (addBonds) atomMap[atomSite] = special.index;
special.bsSymmetry.set(cpt);
special.bsSymmetry.set(spt);
} else {
if (addBonds) atomMap[atomSite] = this.asc.ac;
var atom1 = a.copyTo(pttemp, this.asc);
if (this.asc.bsAtoms != null) this.asc.bsAtoms.set(atom1.index);
if (spinOp != 0 && atom1.vib != null) {
sym.getSpaceGroupOperation(iSym).rotate(atom1.vib);
atom1.vib.scale(spinOp);
}if (atom1.isNegDisorder) {
if (this.disorderMap == null) this.disorderMap =  new java.util.Hashtable();
var key = Integer.$valueOf(iSym * 1000 + atom1.altLoc.charCodeAt(0));
var ch = this.disorderMap.get(key);
if (ch == null) {
if (this.disorderMapMax == 0 || this.disorderMapMax == 90) this.disorderMapMax = ('@').charCodeAt(0);
this.disorderMap.put(key, ch =  new Character(String.fromCharCode(++this.disorderMapMax)));
}atom1.altLoc = ch.charValue();
}atom1.atomSite = atomSite;
if (code != null) atom1.altLoc = subSystemId;
atom1.bsSymmetry = JU.BSUtil.newAndSetBit(cpt);
atom1.bsSymmetry.set(spt);
if (addCartesian) cartesians[pt++] = c;
var tensors = a.tensors;
if (tensors != null) {
atom1.tensors = null;
for (var j = tensors.size(); --j >= 0; ) {
var t = tensors.get(j);
if (t == null) continue;
if (nOp == 1) atom1.addTensor(t.copyTensor(), null, false);
 else this.addRotatedTensor(atom1, t, iSym, false, sym);
}
}}}
if (addBonds) {
var bonds = this.asc.bonds;
var atoms = this.asc.atoms;
var key;
for (var bondNum = this.asc.bondIndex0; bondNum < this.bondCount0; bondNum++) {
var bond = bonds[bondNum];
var atom1 = atoms[bond.atomIndex1];
var atom2 = atoms[bond.atomIndex2];
if (atom1 == null || atom2 == null || atom2.atomSetIndex < atom1.atomSetIndex) continue;
var ia1 = atomMap[atom1.atomSite];
var ia2 = atomMap[atom2.atomSite];
if (ia1 > ia2) {
var i = ia1;
ia1 = ia2;
ia2 = i;
}if (ia1 != ia2 && (ia1 >= bondAtomMin || ia2 >= bondAtomMin) && this.bondsFound.indexOf(key = "-" + ia1 + "," + ia2) < 0) {
this.bondsFound.append(key);
this.asc.addNewBondWithOrder(ia1, ia2, bond.order);
}}
}}
return pt;
}, "~N,~N,~N,~N,~N,~N,~A,J.adapter.smarter.MSInterface,JU.BS,~A");
Clazz.defineMethod(c$, "trimToUnitCell", 
function(iAtomFirst){
var atoms = this.asc.atoms;
var bs = this.updateBSAtoms();
if (this.acr.noPack) {
for (var i = bs.nextSetBit(iAtomFirst); i >= 0; i = bs.nextSetBit(i + 1)) {
if (!this.removePacking(this.ndims, atoms[i], this.minXYZ.x, this.maxXYZ.x, this.minXYZ.y, this.maxXYZ.y, this.minXYZ.z, this.maxXYZ.z, this.packingRange)) bs.clear(i);
}
} else {
for (var i = bs.nextSetBit(iAtomFirst); i >= 0; i = bs.nextSetBit(i + 1)) {
if (!this.isWithinCell(this.ndims, atoms[i], this.minXYZ.x, this.maxXYZ.x, this.minXYZ.y, this.maxXYZ.y, this.minXYZ.z, this.maxXYZ.z, this.packingRange)) bs.clear(i);
}
}}, "~N");
Clazz.defineMethod(c$, "updateBSAtoms", 
function(){
var bs = this.asc.bsAtoms;
if (bs == null) bs = this.asc.bsAtoms = JU.BSUtil.newBitSet2(0, this.asc.ac);
if (bs.nextSetBit(this.firstAtom) < 0) bs.setBits(this.firstAtom, this.asc.ac);
return bs;
});
Clazz.defineMethod(c$, "updateSupercellAtomSites", 
function(matSuper, bsAtoms, slop){
var n = bsAtoms.cardinality();
var baseAtoms =  new Array(n);
var nbase = 0;
var slop2 = slop * slop;
for (var i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
var a = this.asc.atoms[i];
var p =  new J.adapter.smarter.Atom();
p.setT(a);
if (matSuper != null) {
matSuper.rotTrans(p);
JU.SimpleUnitCell.unitizeDimRnd(3, p, slop);
}p.atomSerial = a.atomSite;
p.atomSite = a.atomSite;
this.symmetry.unitize(p);
var found = false;
for (var ib = 0; ib < nbase; ib++) {
var b = baseAtoms[ib];
if (p.atomSerial == b.atomSerial && p.distanceSquared(b) < slop2) {
found = true;
a.atomSite = b.atomSite;
break;
}}
if (!found) {
a.atomSite = p.atomSite = nbase;
baseAtoms[nbase++] = p;
}}
}, "JU.M4,JU.BS,~N");
Clazz.defineMethod(c$, "newFileSymmetry", 
function(){
return  new J.adapter.smarter.XtalSymmetry.FileSymmetry();
});
/*if3*/;(function(){
var c$ = Clazz.declareType(J.adapter.smarter.XtalSymmetry, "FileSymmetry", JS.Symmetry);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.smarter.XtalSymmetry.FileSymmetry, []);
});
Clazz.defineMethod(c$, "addLatticeVectors", 
function(lattvecs){
return this.spaceGroup.addLatticeVectors(lattvecs);
}, "JU.Lst");
Clazz.defineMethod(c$, "addSubSystemOp", 
function(code, rs, vs, sigma){
this.spaceGroup.isSSG = true;
var s = JS.SymmetryOperation.getXYZFromRsVs(rs, vs, false);
var i = this.spaceGroup.addSymmetry(s, -1, true);
this.spaceGroup.operations[i].setSigma(code, sigma);
return s;
}, "~S,JU.Matrix,JU.Matrix,JU.Matrix");
Clazz.defineMethod(c$, "checkDistance", 
function(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset){
return this.unitCell.checkDistance(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset);
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz.defineMethod(c$, "createSpaceGroup", 
function(desiredSpaceGroupIndex, name, data, modDim){
this.spaceGroup = JS.SpaceGroup.createSpaceGroup(desiredSpaceGroupIndex, name, data, modDim);
if (this.spaceGroup != null && JU.Logger.debugging) JU.Logger.debug("using generated space group " + this.spaceGroup.dumpInfo());
return this.spaceGroup != null;
}, "~N,~S,~O,~N");
Clazz.defineMethod(c$, "fcoord", 
function(p){
return JS.SymmetryOperation.fcoord(p, " ");
}, "JU.T3");
Clazz.defineMethod(c$, "getMatrixFromString", 
function(xyz, rotTransMatrix){
JS.SymmetryOperation.getMatrixFromString(null, xyz, rotTransMatrix, false, true, false);
}, "~S,~A");
Clazz.defineMethod(c$, "getSpaceGroupOperationCode", 
function(iOp){
return this.spaceGroup.operations[iOp].subsystemCode;
}, "~N");
Clazz.defineMethod(c$, "getTensor", 
function(vwr, parBorU){
if (parBorU == null) return null;
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromParams( Clazz.newFloatArray(-1, [1, 1, 1, 90, 90, 90]), true, 1.0E-4);
return this.unitCell.getTensor(vwr, parBorU);
}, "JV.Viewer,~A");
Clazz.defineMethod(c$, "getSpaceGroupTitle", 
function(){
var s = this.getSpaceGroupName();
return (s.startsWith("cell=") ? s : this.spaceGroup != null ? this.spaceGroup.asString() : this.unitCell != null && this.unitCell.name.length > 0 ? "cell=" + this.unitCell.name : "");
});
Clazz.defineMethod(c$, "setPrecision", 
function(prec){
this.unitCell.setPrecision(prec);
}, "~N");
Clazz.defineMethod(c$, "toFractionalM", 
function(m){
if (!this.$isBio) this.unitCell.toFractionalM(m);
}, "JU.M4");
Clazz.defineMethod(c$, "toUnitCellRnd", 
function(pt, offset){
this.unitCell.toUnitCellRnd(pt, offset);
}, "JU.T3,JU.T3");
Clazz.defineMethod(c$, "twelfthify", 
function(pt){
this.unitCell.twelfthify(pt);
}, "JU.P3");
Clazz.defineMethod(c$, "getConventionalUnitCell", 
function(latticeType, primitiveToCrystal){
return (this.unitCell == null || latticeType == null ? null : this.unitCell.getConventionalUnitCell(latticeType, primitiveToCrystal));
}, "~S,JU.M3");
Clazz.defineMethod(c$, "getSpaceGroupIndex", 
function(){
return this.spaceGroup.getIndex();
});
Clazz.defineMethod(c$, "getUnitCellF2C", 
function(){
return this.unitCell.getF2C();
});
Clazz.defineMethod(c$, "addInversion", 
function(){
var ops = this.spaceGroup.operations;
var inv =  new JU.M4();
inv.m00 = inv.m11 = inv.m22 = -1;
inv.m33 = 1;
var n = this.getSpaceGroupOperationCount();
var m =  new JU.M4();
for (var i = 0; i < n; i++) {
m.mul2(inv, ops[i]);
var s = JS.SymmetryOperation.getXYZFromMatrix(m, true, true, false);
this.addSpaceGroupOperation(s, 0);
}
});
/*eoif3*/})();
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
