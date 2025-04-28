(function(Clazz
,Clazz_getClassName
,Clazz_newLongArray
,Clazz_doubleToByte
,Clazz_doubleToInt
,Clazz_doubleToLong
,Clazz_declarePackage
,Clazz_instanceOf
,Clazz_load
,Clazz_instantialize
,Clazz_decorateAsClass
,Clazz_floatToInt
,Clazz_floatToLong
,Clazz_makeConstructor
,Clazz_defineEnumConstant
,Clazz_exceptionOf
,Clazz_newIntArray
,Clazz_newFloatArray
,Clazz_declareType
,Clazz_prepareFields
,Clazz_superConstructor
,Clazz_newByteArray
,Clazz_declareInterface
,Clazz_newShortArray
,Clazz_innerTypeInstance
,Clazz_isClassDefined
,Clazz_prepareCallback
,Clazz_newArray
,Clazz_castNullAs
,Clazz_floatToShort
,Clazz_superCall
,Clazz_decorateAsType
,Clazz_newBooleanArray
,Clazz_newCharArray
,Clazz_implementOf
,Clazz_newDoubleArray
,Clazz_overrideConstructor
,Clazz_clone
,Clazz_doubleToShort
,Clazz_getInheritedLevel
,Clazz_getParamsType
,Clazz_isAF
,Clazz_isAB
,Clazz_isAI
,Clazz_isAS
,Clazz_isASS
,Clazz_isAP
,Clazz_isAFloat
,Clazz_isAII
,Clazz_isAFF
,Clazz_isAFFF
,Clazz_tryToSearchAndExecute
,Clazz_getStackTrace
,Clazz_inheritArgs
,Clazz_alert
,Clazz_defineMethod
,Clazz_overrideMethod
,Clazz_declareAnonymous
//,Clazz_checkPrivateMethod
,Clazz_cloneFinals
){
var $t$;
//var c$;
Clazz_declarePackage("J.adapter.smarter");
Clazz_load(["JS.Symmetry", "JU.P3", "$.SB"], "J.adapter.smarter.XtalSymmetry", ["java.util.Hashtable", "JU.BS", "$.Lst", "$.M3", "$.M4", "$.P3i", "$.PT", "$.V3", "J.adapter.smarter.Atom", "JS.SpaceGroup", "$.SymmetryOperation", "$.UnitCell", "JU.BSUtil", "$.Logger", "$.SimpleUnitCell"], function(){
var c$ = Clazz_decorateAsClass(function(){
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
Clazz_instantialize(this, arguments);}, J.adapter.smarter, "XtalSymmetry", null);
Clazz_prepareFields (c$, function(){
this.bondsFound =  new JU.SB();
this.ptOffset =  new JU.P3();
});
Clazz_makeConstructor(c$, 
function(){
});
Clazz_defineMethod(c$, "addRotatedTensor", 
function(a, t, iSym, reset, symmetry){
if (this.ptTemp == null) {
this.ptTemp =  new JU.P3();
this.mTemp =  new JU.M3();
}return a.addTensor((this.acr.getInterface("JU.Tensor")).setFromEigenVectors(symmetry.rotateAxes(iSym, t.eigenVectors, this.ptTemp, this.mTemp), t.eigenValues, t.isIsotropic ? "iso" : t.type, t.id, t), null, reset);
}, "J.adapter.smarter.Atom,JU.Tensor,~N,~B,J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz_defineMethod(c$, "applySymmetryBio", 
function(thisBiomolecule, applySymmetryToBonds, filter){
var biomts = thisBiomolecule.get("biomts");
var len = biomts.size();
if (this.mident == null) {
this.mident =  new JU.M4();
this.mident.setIdentity();
}this.acr.lstNCS = null;
this.setLatticeCells();
var lc = (this.latticeCells != null && this.latticeCells[0] != 0 ?  Clazz_newIntArray (3, 0) : null);
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
var atomMap = (addBonds ?  Clazz_newIntArray (this.asc.ac, 0) : null);
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
if (Clazz_exceptionOf(e, Exception)){
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
knownAtomMap.put(known, lastKnownAtom =  Clazz_newIntArray(-1, [i, n]));
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
Clazz_defineMethod(c$, "getBaseSymmetry", 
function(){
return (this.baseSymmetry == null ? this.symmetry : this.baseSymmetry);
});
Clazz_defineMethod(c$, "getOverallSpan", 
function(){
return (this.maxXYZ0 == null ? JU.V3.new3(this.maxXYZ.x - this.minXYZ.x, this.maxXYZ.y - this.minXYZ.y, this.maxXYZ.z - this.minXYZ.z) : JU.V3.newVsub(this.maxXYZ0, this.minXYZ0));
});
Clazz_defineMethod(c$, "getSymmetry", 
function(){
return (this.symmetry == null ? (this.symmetry =  new J.adapter.smarter.XtalSymmetry.FileSymmetry()) : this.symmetry);
});
Clazz_defineMethod(c$, "isWithinCell", 
function(ndims, pt, minX, maxX, minY, maxY, minZ, maxZ, slop){
return (pt.x > minX - slop && pt.x < maxX + slop && (ndims < 2 || pt.y > minY - slop && pt.y < maxY + slop) && (ndims < 3 || pt.z > minZ - slop && pt.z < maxZ + slop));
}, "~N,JU.P3,~N,~N,~N,~N,~N,~N,~N");
Clazz_defineMethod(c$, "scaleFractionalVibs", 
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
Clazz_defineMethod(c$, "set", 
function(reader){
this.acr = reader;
this.asc = reader.asc;
this.getSymmetry();
return this;
}, "J.adapter.smarter.AtomSetCollectionReader");
Clazz_defineMethod(c$, "setLatticeParameter", 
function(latt){
this.symmetry.setSpaceGroup(this.doNormalize);
this.symmetry.setLattice(latt);
}, "~N");
Clazz_defineMethod(c$, "setSpinVectors", 
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
Clazz_defineMethod(c$, "addSpaceGroupOperation", 
function(xyz, andSetLattice){
this.symmetry.setSpaceGroup(this.doNormalize);
if (andSetLattice && this.symmetry.getSpaceGroupOperationCount() == 1) this.setLatticeCells();
return this.symmetry.addSpaceGroupOperation(xyz, 0);
}, "~S,~B");
Clazz_defineMethod(c$, "applySymmetryFromReader", 
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
Clazz_defineMethod(c$, "setSymmetry", 
function(symmetry){
return (this.symmetry = symmetry);
}, "J.adapter.smarter.XtalSymmetry.FileSymmetry");
Clazz_defineMethod(c$, "setTensors", 
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
Clazz_defineMethod(c$, "adjustRangeMinMax", 
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
this.minXYZ = JU.P3i.new3(Clazz_doubleToInt(Math.min(0, Math.floor(this.rminx + 0.001))), Clazz_doubleToInt(Math.min(0, Math.floor(this.rminy + 0.001))), Clazz_doubleToInt(Math.min(0, Math.floor(this.rminz + 0.001))));
this.maxXYZ = JU.P3i.new3(Clazz_doubleToInt(Math.max(1, Math.ceil(this.rmaxx - 0.001))), Clazz_doubleToInt(Math.max(1, Math.ceil(this.rmaxy - 0.001))), Clazz_doubleToInt(Math.max(1, Math.ceil(this.rmaxz - 0.001))));
}, "~A");
Clazz_defineMethod(c$, "applyAllSymmetry", 
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
if (this.doCentroidUnitCell) this.asc.setInfo("centroidMinMax",  Clazz_newIntArray(-1, [this.minXYZ.x, this.minXYZ.y, this.minXYZ.z, this.maxXYZ.x, this.maxXYZ.y, this.maxXYZ.z, (this.centroidPacked ? 1 : 0)]));
if (this.doCentroidUnitCell || this.acr.doPackUnitCell || this.symmetryRange != 0 && this.maxXYZ.x - this.minXYZ.x == 1 && this.maxXYZ.y - this.minXYZ.y == 1 && this.maxXYZ.z - this.minXYZ.z == 1) {
this.minXYZ0 = JU.P3.new3(this.minXYZ.x, this.minXYZ.y, this.minXYZ.z);
this.maxXYZ0 = JU.P3.new3(this.maxXYZ.x, this.maxXYZ.y, this.maxXYZ.z);
if (ms != null) {
ms.setMinMax0(this.minXYZ0, this.maxXYZ0);
this.minXYZ.set(Clazz_floatToInt(this.minXYZ0.x), Clazz_floatToInt(this.minXYZ0.y), Clazz_floatToInt(this.minXYZ0.z));
this.maxXYZ.set(Clazz_floatToInt(this.maxXYZ0.x), Clazz_floatToInt(this.maxXYZ0.y), Clazz_floatToInt(this.maxXYZ0.z));
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
}var atomMap = (this.bondCount0 > this.asc.bondIndex0 && this.applySymmetryToBonds ?  Clazz_newIntArray (n, 0) : null);
var unitCells =  Clazz_newIntArray (nCells, 0);
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
Clazz_defineMethod(c$, "applyRangeSymmetry", 
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
Clazz_defineMethod(c$, "applySuperSymmetry", 
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
this.setUnitCell( Clazz_newFloatArray(-1, [0, 0, 0, 0, 0, 0, va.x, va.y, va.z, vb.x, vb.y, vb.z, vc.x, vc.y, vc.z, 0, 0, 0, 0, 0, 0, NaN, NaN, NaN, NaN, NaN, slop]), null, null);
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
Clazz_defineMethod(c$, "applySymmetryLattice", 
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
Clazz_defineMethod(c$, "duplicateAtomProperties", 
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
var fnew =  Clazz_newFloatArray (f.length * nTimes, 0);
for (var i = nTimes; --i >= 0; ) System.arraycopy(f, 0, fnew, i * f.length, f.length);

}}
}, "~N");
Clazz_defineMethod(c$, "finalizeSymmetry", 
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
Clazz_defineMethod(c$, "removePacking", 
function(ndims, pt, minX, maxX, minY, maxY, minZ, maxZ, slop){
return (pt.x > minX - slop && pt.x < maxX - slop && (ndims < 2 || pt.y > minY - slop && pt.y < maxY - slop) && (ndims < 3 || pt.z > minZ - slop && pt.z < maxZ - slop));
}, "~N,JU.P3,~N,~N,~N,~N,~N,~N,~N");
Clazz_defineMethod(c$, "reset", 
function(){
this.asc.coordinatesAreFractional = false;
this.asc.setCurrentModelInfo("hasSymmetry", Boolean.TRUE);
this.asc.setGlobalBoolean(1);
});
Clazz_defineMethod(c$, "setAtomSetSpaceGroupName", 
function(spaceGroupName){
this.symmetry.setSpaceGroupName(spaceGroupName);
this.asc.setCurrentModelInfo("spaceGroup", spaceGroupName + "");
}, "~S");
Clazz_defineMethod(c$, "setCurrentModelInfo", 
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
Clazz_defineMethod(c$, "setCurrentModelUCInfo", 
function(unitCellParams, unitCellOffset, matUnitCellOrientation){
if (unitCellParams != null) this.asc.setCurrentModelInfo("unitCellParams", unitCellParams);
if (unitCellOffset != null) this.asc.setCurrentModelInfo("unitCellOffset", unitCellOffset);
if (matUnitCellOrientation != null) this.asc.setCurrentModelInfo("matUnitCellOrientation", matUnitCellOrientation);
}, "~A,JU.P3,JU.M3");
Clazz_defineMethod(c$, "setLatticeCells", 
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
Clazz_defineMethod(c$, "setLatticeRange", 
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
Clazz_defineMethod(c$, "setMinMax", 
function(dim, kcode, maxX, maxY, maxZ){
this.minXYZ =  new JU.P3i();
this.maxXYZ = JU.P3i.new3(maxX, maxY, maxZ);
JU.SimpleUnitCell.setMinMaxLatticeParameters(dim, this.minXYZ, this.maxXYZ, kcode);
}, "~N,~N,~N,~N,~N");
Clazz_defineMethod(c$, "setSymmetryMinMax", 
function(c){
if (this.rminx > c.x) this.rminx = c.x;
if (this.rminy > c.y) this.rminy = c.y;
if (this.rminz > c.z) this.rminz = c.z;
if (this.rmaxx < c.x) this.rmaxx = c.x;
if (this.rmaxy < c.y) this.rmaxy = c.y;
if (this.rmaxz < c.z) this.rmaxz = c.z;
}, "JU.P3");
Clazz_defineMethod(c$, "setUnitCell", 
function(info, matUnitCellOrientation, unitCellOffset){
this.unitCellParams =  Clazz_newFloatArray (info.length, 0);
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
Clazz_defineMethod(c$, "setUnitCellSafely", 
function(){
if (this.unitCellParams == null) this.setUnitCell(this.acr.unitCellParams, this.acr.matUnitCellOrientation, this.acr.unitCellOffset);
});
Clazz_defineMethod(c$, "symmetryAddAtoms", 
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
nNCS = Clazz_doubleToInt(nNCS / nOp);
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
var spt = (iSym >= nOp ? Clazz_doubleToInt((iSym - nOp) / nNCS) : iSym);
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
Clazz_defineMethod(c$, "trimToUnitCell", 
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
Clazz_defineMethod(c$, "updateBSAtoms", 
function(){
var bs = this.asc.bsAtoms;
if (bs == null) bs = this.asc.bsAtoms = JU.BSUtil.newBitSet2(0, this.asc.ac);
if (bs.nextSetBit(this.firstAtom) < 0) bs.setBits(this.firstAtom, this.asc.ac);
return bs;
});
Clazz_defineMethod(c$, "updateSupercellAtomSites", 
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
Clazz_defineMethod(c$, "newFileSymmetry", 
function(){
return  new J.adapter.smarter.XtalSymmetry.FileSymmetry();
});
/*if3*/;(function(){
var c$ = Clazz_declareType(J.adapter.smarter.XtalSymmetry, "FileSymmetry", JS.Symmetry);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor (this, J.adapter.smarter.XtalSymmetry.FileSymmetry, []);
});
Clazz_defineMethod(c$, "addLatticeVectors", 
function(lattvecs){
return this.spaceGroup.addLatticeVectors(lattvecs);
}, "JU.Lst");
Clazz_defineMethod(c$, "addSubSystemOp", 
function(code, rs, vs, sigma){
this.spaceGroup.isSSG = true;
var s = JS.SymmetryOperation.getXYZFromRsVs(rs, vs, false);
var i = this.spaceGroup.addSymmetry(s, -1, true);
this.spaceGroup.operations[i].setSigma(code, sigma);
return s;
}, "~S,JU.Matrix,JU.Matrix,JU.Matrix");
Clazz_defineMethod(c$, "checkDistance", 
function(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset){
return this.unitCell.checkDistance(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset);
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz_defineMethod(c$, "createSpaceGroup", 
function(desiredSpaceGroupIndex, name, data, modDim){
this.spaceGroup = JS.SpaceGroup.createSpaceGroup(desiredSpaceGroupIndex, name, data, modDim);
if (this.spaceGroup != null && JU.Logger.debugging) JU.Logger.debug("using generated space group " + this.spaceGroup.dumpInfo());
return this.spaceGroup != null;
}, "~N,~S,~O,~N");
Clazz_defineMethod(c$, "fcoord", 
function(p){
return JS.SymmetryOperation.fcoord(p, " ");
}, "JU.T3");
Clazz_defineMethod(c$, "getMatrixFromString", 
function(xyz, rotTransMatrix){
JS.SymmetryOperation.getMatrixFromString(null, xyz, rotTransMatrix, false, true, false);
}, "~S,~A");
Clazz_defineMethod(c$, "getSpaceGroupOperationCode", 
function(iOp){
return this.spaceGroup.operations[iOp].subsystemCode;
}, "~N");
Clazz_defineMethod(c$, "getTensor", 
function(vwr, parBorU){
if (parBorU == null) return null;
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromParams( Clazz_newFloatArray(-1, [1, 1, 1, 90, 90, 90]), true, 1.0E-4);
return this.unitCell.getTensor(vwr, parBorU);
}, "JV.Viewer,~A");
Clazz_defineMethod(c$, "getSpaceGroupTitle", 
function(){
var s = this.getSpaceGroupName();
return (s.startsWith("cell=") ? s : this.spaceGroup != null ? this.spaceGroup.asString() : this.unitCell != null && this.unitCell.name.length > 0 ? "cell=" + this.unitCell.name : "");
});
Clazz_defineMethod(c$, "setPrecision", 
function(prec){
this.unitCell.setPrecision(prec);
}, "~N");
Clazz_defineMethod(c$, "toFractionalM", 
function(m){
if (!this.$isBio) this.unitCell.toFractionalM(m);
}, "JU.M4");
Clazz_defineMethod(c$, "toUnitCellRnd", 
function(pt, offset){
this.unitCell.toUnitCellRnd(pt, offset);
}, "JU.T3,JU.T3");
Clazz_defineMethod(c$, "twelfthify", 
function(pt){
this.unitCell.twelfthify(pt);
}, "JU.P3");
Clazz_defineMethod(c$, "getConventionalUnitCell", 
function(latticeType, primitiveToCrystal){
return (this.unitCell == null || latticeType == null ? null : this.unitCell.getConventionalUnitCell(latticeType, primitiveToCrystal));
}, "~S,JU.M3");
Clazz_defineMethod(c$, "getSpaceGroupIndex", 
function(){
return this.spaceGroup.getIndex();
});
Clazz_defineMethod(c$, "getUnitCellF2C", 
function(){
return this.unitCell.getF2C();
});
Clazz_defineMethod(c$, "addInversion", 
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
Clazz_declarePackage("JS");
Clazz_load(["J.api.SymmetryInterface"], "JS.Symmetry", ["java.util.Hashtable", "JU.BS", "$.JSJSONParser", "$.Lst", "$.M4", "$.P3", "$.PT", "$.Rdr", "$.SB", "J.api.Interface", "J.bspt.Bspt", "JS.PointGroup", "$.SpaceGroup", "$.SymmetryInfo", "$.SymmetryOperation", "$.UnitCell", "JU.Escape", "$.Logger", "$.SimpleUnitCell", "JV.FileManager"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.spaceGroup = null;
this.unitCell = null;
this.$isBio = false;
this.pointGroup = null;
this.cip = null;
this.symmetryInfo = null;
this.desc = null;
this.transformMatrix = null;
Clazz_instantialize(this, arguments);}, JS, "Symmetry", null, J.api.SymmetryInterface);
/*LV!1824 unnec constructor*/Clazz_overrideMethod(c$, "isBio", 
function(){
return this.$isBio;
});
Clazz_overrideMethod(c$, "setPointGroup", 
function(vwr, siLast, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly){
this.pointGroup = JS.PointGroup.getPointGroup(siLast == null ? null : (siLast).pointGroup, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly, vwr.getBoolean(603979956), vwr.getScalePixelsPerAngstrom(false));
return this;
}, "JV.Viewer,J.api.SymmetryInterface,JU.T3,~A,JU.BS,~B,~N,~N,~N,~B");
Clazz_overrideMethod(c$, "getPointGroupName", 
function(){
return this.pointGroup.getName();
});
Clazz_overrideMethod(c$, "getPointGroupInfo", 
function(modelIndex, drawID, asInfo, type, index, scale){
if (drawID == null && !asInfo && this.pointGroup.textInfo != null) return this.pointGroup.textInfo;
 else if (drawID == null && this.pointGroup.isDrawType(type, index, scale)) return this.pointGroup.drawInfo;
 else if (asInfo && this.pointGroup.info != null) return this.pointGroup.info;
return this.pointGroup.getInfo(modelIndex, drawID, asInfo, type, index, scale);
}, "~N,~S,~B,~S,~N,~N");
Clazz_overrideMethod(c$, "setSpaceGroup", 
function(doNormalize){
this.symmetryInfo = null;
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull(true, doNormalize, false);
}, "~B");
Clazz_overrideMethod(c$, "addSpaceGroupOperation", 
function(xyz, opId){
return this.spaceGroup.addSymmetry(xyz, opId, false);
}, "~S,~N");
Clazz_overrideMethod(c$, "addBioMoleculeOperation", 
function(mat, isReverse){
this.$isBio = this.spaceGroup.isBio = true;
return this.spaceGroup.addSymmetry((isReverse ? "!" : "") + "[[bio" + mat, 0, false);
}, "JU.M4,~B");
Clazz_overrideMethod(c$, "setLattice", 
function(latt){
this.spaceGroup.setLatticeParam(latt);
}, "~N");
Clazz_overrideMethod(c$, "getSpaceGroup", 
function(){
return this.spaceGroup;
});
Clazz_overrideMethod(c$, "getSpaceGroupInfoObj", 
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
Clazz_defineMethod(c$, "getSpaceGroupList", 
function(vwr){
var sb =  new JU.SB();
var list = this.getSpaceGroupJSON(vwr, "ITA", "ALL", 0);
for (var i = 0, n = list.size(); i < n; i++) {
var map = list.get(i);
sb.appendO(map.get("sg")).appendC('.').appendO(map.get("set")).appendC('\t').appendO(map.get("hm")).appendC('\t').appendO(map.get("sg")).appendC(':').appendO(map.get("trm")).appendC('\n');
}
return sb.toString();
}, "JV.Viewer");
Clazz_overrideMethod(c$, "getLatticeDesignation", 
function(){
return this.spaceGroup.getLatticeDesignation();
});
Clazz_overrideMethod(c$, "setFinalOperations", 
function(dim, name, atoms, iAtomFirst, noSymmetryCount, doNormalize, filterSymop){
if (name != null && (name.startsWith("bio") || name.indexOf(" *(") >= 0)) this.spaceGroup.setName(name);
if (filterSymop != null) {
var lst =  new JU.Lst();
lst.addLast(this.spaceGroup.operations[0]);
for (var i = 1; i < this.spaceGroup.operationCount; i++) if (filterSymop.contains(" " + (i + 1) + " ")) lst.addLast(this.spaceGroup.operations[i]);

this.spaceGroup = JS.SpaceGroup.createSpaceGroup(-1, name + " *(" + filterSymop.trim() + ")", lst, -1);
}this.spaceGroup.setFinalOperationsForAtoms(dim, atoms, iAtomFirst, noSymmetryCount, doNormalize);
}, "~N,~S,~A,~N,~N,~B,~S");
Clazz_overrideMethod(c$, "getSpaceGroupOperation", 
function(i){
return (this.spaceGroup == null || this.spaceGroup.operations == null || i >= this.spaceGroup.operations.length ? null : this.spaceGroup.finalOperations == null ? this.spaceGroup.operations[i] : this.spaceGroup.finalOperations[i]);
}, "~N");
Clazz_overrideMethod(c$, "getSpaceGroupXyz", 
function(i, doNormalize){
return this.spaceGroup.getXyz(i, doNormalize);
}, "~N,~B");
Clazz_overrideMethod(c$, "newSpaceGroupPoint", 
function(pt, i, o, transX, transY, transZ, retPoint){
if (o == null && this.spaceGroup.finalOperations == null) {
var op = this.spaceGroup.operations[i];
if (!op.isFinalized) op.doFinalize();
o = op;
}JS.SymmetryOperation.rotateAndTranslatePoint((o == null ? this.spaceGroup.finalOperations[i] : o), pt, transX, transY, transZ, retPoint);
}, "JU.P3,~N,JU.M4,~N,~N,~N,JU.P3");
Clazz_overrideMethod(c$, "rotateAxes", 
function(iop, axes, ptTemp, mTemp){
return (iop == 0 ? axes : this.spaceGroup.finalOperations[iop].rotateAxes(axes, this.unitCell, ptTemp, mTemp));
}, "~N,~A,JU.P3,JU.M3");
Clazz_overrideMethod(c$, "getSpinOp", 
function(op){
return this.spaceGroup.operations[op].getMagneticOp();
}, "~N");
Clazz_overrideMethod(c$, "getLatticeOp", 
function(){
return this.spaceGroup.latticeOp;
});
Clazz_overrideMethod(c$, "getLatticeCentering", 
function(){
return JS.SymmetryOperation.getLatticeCentering(this.getSymmetryOperations());
});
Clazz_overrideMethod(c$, "getOperationRsVs", 
function(iop){
return (this.spaceGroup.finalOperations == null ? this.spaceGroup.operations : this.spaceGroup.finalOperations)[iop].rsvs;
}, "~N");
Clazz_overrideMethod(c$, "getSiteMultiplicity", 
function(pt){
return this.spaceGroup.getSiteMultiplicity(pt, this.unitCell);
}, "JU.P3");
Clazz_overrideMethod(c$, "getSpaceGroupName", 
function(){
return (this.spaceGroup != null ? this.spaceGroup.getName() : this.symmetryInfo != null ? this.symmetryInfo.sgName : this.unitCell != null && this.unitCell.name.length > 0 ? "cell=" + this.unitCell.name : "");
});
Clazz_overrideMethod(c$, "getSpaceGroupNameType", 
function(type){
return (this.spaceGroup == null ? null : this.spaceGroup.getNameType(type, this));
}, "~S");
Clazz_overrideMethod(c$, "getLatticeType", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.latticeType : this.spaceGroup == null ? 'P' : this.spaceGroup.latticeType);
});
Clazz_overrideMethod(c$, "getIntTableNumber", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableNo : this.spaceGroup == null ? null : this.spaceGroup.itaNumber);
});
Clazz_overrideMethod(c$, "getIntTableIndex", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableIndex : this.spaceGroup == null ? null : this.spaceGroup.getItaIndex());
});
Clazz_overrideMethod(c$, "getIntTableTransform", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableTransform : this.spaceGroup == null ? null : this.spaceGroup.itaTransform);
});
Clazz_overrideMethod(c$, "getIntTableNumberFull", 
function(){
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableJmolID : this.spaceGroup == null ? null : this.spaceGroup.jmolId != null ? this.spaceGroup.jmolId : this.spaceGroup.itaNumber);
});
Clazz_overrideMethod(c$, "getCoordinatesAreFractional", 
function(){
return this.symmetryInfo == null || this.symmetryInfo.coordinatesAreFractional;
});
Clazz_overrideMethod(c$, "getCellRange", 
function(){
return this.symmetryInfo == null ? null : this.symmetryInfo.cellRange;
});
Clazz_overrideMethod(c$, "getSymmetryInfoStr", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.infoStr;
if (this.spaceGroup == null) return "";
(this.symmetryInfo =  new JS.SymmetryInfo()).setSymmetryInfoFromModelkit(this.spaceGroup);
return this.symmetryInfo.infoStr;
});
Clazz_overrideMethod(c$, "getSpaceGroupOperationCount", 
function(){
return (this.symmetryInfo != null && this.symmetryInfo.symmetryOperations != null ? this.symmetryInfo.symmetryOperations.length : this.spaceGroup != null ? (this.spaceGroup.finalOperations != null ? this.spaceGroup.finalOperations.length : this.spaceGroup.operationCount) : 0);
});
Clazz_overrideMethod(c$, "getSymmetryOperations", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.symmetryOperations;
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull(true, false, true);
this.spaceGroup.setFinalOperations();
return this.spaceGroup.finalOperations;
});
Clazz_overrideMethod(c$, "getAdditionalOperationsCount", 
function(){
return (this.symmetryInfo != null && this.symmetryInfo.symmetryOperations != null && this.symmetryInfo.getAdditionalOperations() != null ? this.symmetryInfo.additionalOperations.length : this.spaceGroup != null && this.spaceGroup.finalOperations != null ? this.spaceGroup.getAdditionalOperationsCount() : 0);
});
Clazz_overrideMethod(c$, "getAdditionalOperations", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.getAdditionalOperations();
this.getSymmetryOperations();
return this.spaceGroup.getAdditionalOperations();
});
Clazz_overrideMethod(c$, "isSimple", 
function(){
return (this.spaceGroup == null && (this.symmetryInfo == null || this.symmetryInfo.symmetryOperations == null));
});
Clazz_overrideMethod(c$, "haveUnitCell", 
function(){
return (this.unitCell != null);
});
Clazz_overrideMethod(c$, "setUnitCellFromParams", 
function(unitCellParams, setRelative, slop){
if (unitCellParams == null) unitCellParams =  Clazz_newFloatArray(-1, [1, 1, 1, 90, 90, 90]);
this.unitCell = JS.UnitCell.fromParams(unitCellParams, setRelative, slop);
return this;
}, "~A,~B,~N");
Clazz_overrideMethod(c$, "unitCellEquals", 
function(uc2){
return ((uc2)).unitCell.isSameAs(this.unitCell.getF2C());
}, "J.api.SymmetryInterface");
Clazz_overrideMethod(c$, "isSymmetryCell", 
function(sym){
var uc = ((sym)).unitCell;
var myf2c = (!uc.isStandard() ? null : (this.symmetryInfo != null ? this.symmetryInfo.spaceGroupF2C : this.unitCell.getF2C()));
var ret = uc.isSameAs(myf2c);
if (this.symmetryInfo != null) {
if (this.symmetryInfo.setIsCurrentCell(ret)) {
this.setUnitCellFromParams(this.symmetryInfo.spaceGroupF2CParams, false, NaN);
}}return ret;
}, "J.api.SymmetryInterface");
Clazz_overrideMethod(c$, "getUnitCellState", 
function(){
if (this.unitCell == null) return "";
return this.unitCell.getState();
});
Clazz_overrideMethod(c$, "getMoreInfo", 
function(){
return this.unitCell.moreInfo;
});
Clazz_overrideMethod(c$, "initializeOrientation", 
function(mat){
this.unitCell.initOrientation(mat);
}, "JU.M3");
Clazz_overrideMethod(c$, "unitize", 
function(ptFrac){
this.unitCell.unitize(ptFrac);
}, "JU.T3");
Clazz_overrideMethod(c$, "toUnitCell", 
function(pt, offset){
this.unitCell.toUnitCell(pt, offset);
}, "JU.T3,JU.T3");
Clazz_overrideMethod(c$, "toSupercell", 
function(fpt){
return this.unitCell.toSupercell(fpt);
}, "JU.P3");
Clazz_overrideMethod(c$, "toFractional", 
function(pt, ignoreOffset){
if (!this.$isBio) this.unitCell.toFractional(pt, ignoreOffset);
}, "JU.T3,~B");
Clazz_overrideMethod(c$, "toCartesian", 
function(pt, ignoreOffset){
if (!this.$isBio) this.unitCell.toCartesian(pt, ignoreOffset);
}, "JU.T3,~B");
Clazz_overrideMethod(c$, "getUnitCellParams", 
function(){
return this.unitCell.getUnitCellParams();
});
Clazz_overrideMethod(c$, "getUnitCellAsArray", 
function(vectorsOnly){
return this.unitCell.getUnitCellAsArray(vectorsOnly);
}, "~B");
Clazz_overrideMethod(c$, "getUnitCellVerticesNoOffset", 
function(){
return this.unitCell.getVertices();
});
Clazz_overrideMethod(c$, "getCartesianOffset", 
function(){
return this.unitCell.getCartesianOffset();
});
Clazz_overrideMethod(c$, "getFractionalOffset", 
function(){
return this.unitCell.getFractionalOffset();
});
Clazz_overrideMethod(c$, "setOffsetPt", 
function(pt){
this.unitCell.setOffset(pt);
}, "JU.T3");
Clazz_overrideMethod(c$, "setOffset", 
function(nnn){
var pt =  new JU.P3();
JU.SimpleUnitCell.ijkToPoint3f(nnn, pt, 0, 0);
this.unitCell.setOffset(pt);
}, "~N");
Clazz_overrideMethod(c$, "getUnitCellMultiplier", 
function(){
return this.unitCell.getUnitCellMultiplier();
});
Clazz_overrideMethod(c$, "getUnitCellMultiplied", 
function(){
var uc = this.unitCell.getUnitCellMultiplied();
if (uc === this.unitCell) return this;
var s =  new JS.Symmetry();
s.unitCell = uc;
return s;
});
Clazz_overrideMethod(c$, "getCanonicalCopy", 
function(scale, withOffset){
return this.unitCell.getCanonicalCopy(scale, withOffset);
}, "~N,~B");
Clazz_overrideMethod(c$, "getUnitCellInfoType", 
function(infoType){
return this.unitCell.getInfo(infoType);
}, "~N");
Clazz_overrideMethod(c$, "getUnitCellInfo", 
function(scaled){
return (this.unitCell == null ? null : this.unitCell.dumpInfo(false, scaled));
}, "~B");
Clazz_overrideMethod(c$, "isSlab", 
function(){
return this.unitCell.isSlab();
});
Clazz_overrideMethod(c$, "isPolymer", 
function(){
return this.unitCell.isPolymer();
});
Clazz_defineMethod(c$, "getUnitCellVectors", 
function(){
return this.unitCell.getUnitCellVectors();
});
Clazz_overrideMethod(c$, "getUnitCell", 
function(oabc, setRelative, name){
if (oabc == null) return null;
this.unitCell = JS.UnitCell.fromOABC(oabc, setRelative);
if (name != null) this.unitCell.name = name;
return this;
}, "~A,~B,~S");
Clazz_overrideMethod(c$, "isSupercell", 
function(){
return this.unitCell.isSupercell();
});
Clazz_overrideMethod(c$, "notInCentroid", 
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
if (Clazz_exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "JM.ModelSet,JU.BS,~A");
Clazz_defineMethod(c$, "isNotCentroid", 
function(center, n, minmax, centroidPacked){
center.scale(1 / n);
this.toFractional(center, false);
if (centroidPacked) return (center.x + 0.000005 <= minmax[0] || center.x - 0.000005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y - 0.000005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z - 0.000005 > minmax[5]);
return (center.x + 0.000005 <= minmax[0] || center.x + 0.00005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y + 0.00005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z + 0.00005 > minmax[5]);
}, "JU.P3,~N,~A,~B");
Clazz_defineMethod(c$, "getDesc", 
function(modelSet){
if (modelSet == null) {
return (JS.Symmetry.nullDesc == null ? (JS.Symmetry.nullDesc = (J.api.Interface.getInterface("JS.SymmetryDesc", null, "modelkit"))) : JS.Symmetry.nullDesc);
}return (this.desc == null ? (this.desc = (J.api.Interface.getInterface("JS.SymmetryDesc", modelSet.vwr, "eval"))) : this.desc).set(modelSet);
}, "JM.ModelSet");
Clazz_overrideMethod(c$, "getSymmetryInfoAtom", 
function(modelSet, iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList){
return this.getDesc(modelSet).getSymopInfo(iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList);
}, "JM.ModelSet,~N,~S,~N,JU.P3,JU.P3,JU.P3,~S,~N,~N,~N,~N,~A");
Clazz_overrideMethod(c$, "getSpaceGroupInfo", 
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
Clazz_overrideMethod(c$, "getV0abc", 
function(def, retMatrix){
var t = null;
{
t = (def && def[0] ? def[0] : null);
}return ((t != null ? Clazz_instanceOf(t,"JU.T3") : Clazz_instanceOf(def,Array)) ? def : JS.UnitCell.getMatrixAndUnitCell(this.unitCell, def, retMatrix));
}, "~O,JU.M4");
Clazz_overrideMethod(c$, "getQuaternionRotation", 
function(abc){
return (this.unitCell == null ? null : this.unitCell.getQuaternionRotation(abc));
}, "~S");
Clazz_overrideMethod(c$, "getFractionalOrigin", 
function(){
return this.unitCell.getFractionalOrigin();
});
Clazz_overrideMethod(c$, "getState", 
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
Clazz_overrideMethod(c$, "getIterator", 
function(vwr, atom, bsAtoms, radius){
return (J.api.Interface.getInterface("JS.UnitCellIterator", vwr, "script")).set(this, atom, vwr.ms.at, bsAtoms, radius);
}, "JV.Viewer,JM.Atom,JU.BS,~N");
Clazz_overrideMethod(c$, "toFromPrimitive", 
function(toPrimitive, type, oabc, primitiveToCrystal){
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromOABC(oabc, false);
return this.unitCell.toFromPrimitive(toPrimitive, type, oabc, primitiveToCrystal);
}, "~B,~S,~A,JU.M3");
Clazz_overrideMethod(c$, "generateCrystalClass", 
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
Clazz_overrideMethod(c$, "calculateCIPChiralityForAtoms", 
function(vwr, bsAtoms){
vwr.setCursor(3);
var cip = this.getCIPChirality(vwr);
var dataClass = (vwr.getBoolean(603979960) ? "CIPData" : "CIPDataTracker");
var data = (J.api.Interface.getInterface("JS." + dataClass, vwr, "script")).set(vwr, bsAtoms);
data.setRule6Full(vwr.getBoolean(603979823));
cip.getChiralityForAtoms(data);
vwr.setCursor(0);
}, "JV.Viewer,JU.BS");
Clazz_overrideMethod(c$, "calculateCIPChiralityForSmiles", 
function(vwr, smiles){
vwr.setCursor(3);
var cip = this.getCIPChirality(vwr);
var data = (J.api.Interface.getInterface("JS.CIPDataSmiles", vwr, "script")).setAtomsForSmiles(vwr, smiles);
cip.getChiralityForAtoms(data);
vwr.setCursor(0);
return data.getSmilesChiralityArray();
}, "JV.Viewer,~S");
Clazz_defineMethod(c$, "getCIPChirality", 
function(vwr){
return (this.cip == null ? (this.cip = (J.api.Interface.getInterface("JS.CIPChirality", vwr, "script"))) : this.cip);
}, "JV.Viewer");
Clazz_overrideMethod(c$, "getUnitCellInfoMap", 
function(){
return (this.unitCell == null ? null : this.unitCell.getInfo());
});
Clazz_overrideMethod(c$, "setUnitCell", 
function(uc){
this.unitCell = JS.UnitCell.cloneUnitCell((uc).unitCell);
}, "J.api.SymmetryInterface");
Clazz_overrideMethod(c$, "findSpaceGroup", 
function(vwr, atoms, xyzList, unitCellParams, origin, oabc, flags){
return (J.api.Interface.getInterface("JS.SpaceGroupFinder", vwr, "eval")).findSpaceGroup(vwr, atoms, xyzList, unitCellParams, origin, oabc, this, flags);
}, "JV.Viewer,JU.BS,~S,~A,JU.T3,~A,~N");
Clazz_overrideMethod(c$, "setSpaceGroupName", 
function(name){
this.symmetryInfo = null;
if (this.spaceGroup != null) this.spaceGroup.setName(name);
}, "~S");
Clazz_overrideMethod(c$, "setSpaceGroupTo", 
function(sg){
this.symmetryInfo = null;
if (Clazz_instanceOf(sg,"JS.SpaceGroup")) {
this.spaceGroup = sg;
} else {
this.spaceGroup = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(sg.toString());
}}, "~O");
Clazz_overrideMethod(c$, "removeDuplicates", 
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
Clazz_overrideMethod(c$, "getEquivPoints", 
function(pts, pt, flags){
var ops = this.getSymmetryOperations();
return (ops == null || this.unitCell == null ? null : this.unitCell.getEquivPoints(pt, flags, ops, pts == null ?  new JU.Lst() : pts, 0, 0, 0));
}, "JU.Lst,JU.P3,~S");
Clazz_overrideMethod(c$, "getEquivPointList", 
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
Clazz_overrideMethod(c$, "getInvariantSymops", 
function(pt, v0){
var ops = this.getSymmetryOperations();
if (ops == null) return  Clazz_newIntArray (0, 0);
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
var ret =  Clazz_newIntArray (bs.cardinality(), 0);
if (v0 != null && ret.length != v0.length) return null;
for (var k = 0, i = 1; i < nops; i++) {
var isOK = bs.get(i);
if (isOK) {
if (v0 != null && v0[k] != i + 1) return null;
ret[k++] = i + 1;
}}
return ret;
}, "JU.P3,~A");
Clazz_overrideMethod(c$, "getWyckoffPosition", 
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
if (Clazz_exceptionOf(e, Exception)){
e.printStackTrace();
return (letter == null ? "?" : null);
} else {
throw e;
}
}
}, "JV.Viewer,JU.P3,~S");
Clazz_overrideMethod(c$, "getTransform", 
function(fracA, fracB, best){
return this.getDesc(null).getTransform(this.unitCell, this.getSymmetryOperations(), fracA, fracB, best);
}, "JU.P3,JU.P3,~B");
Clazz_overrideMethod(c$, "isWithinUnitCell", 
function(pt, x, y, z){
return this.unitCell.isWithinUnitCell(x, y, z, pt);
}, "JU.P3,~N,~N,~N");
Clazz_overrideMethod(c$, "checkPeriodic", 
function(pt){
return this.unitCell.checkPeriodic(pt);
}, "JU.P3");
Clazz_overrideMethod(c$, "staticConvertOperation", 
function(xyz, matrix){
return (matrix == null ? JS.SymmetryOperation.stringToMatrix(xyz) : JS.SymmetryOperation.getXYZFromMatrixFrac(matrix, false, false, false, true));
}, "~S,JU.M4");
Clazz_overrideMethod(c$, "getSubgroupJSON", 
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
var groups = (asIntArray ?  Clazz_newIntArray (n, 0) : null);
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
var idet = Clazz_doubleToInt(det < 1 ? -1 / det : det);
if (subType.equals("ct")) trType = 3;
 else if (subType.equals("eu")) trType = 4;
var ntrm = (o.get("trm")).size();
groups[i] =  Clazz_newIntArray(-1, [isub, ntrm, subIndex, idet, trType]);
}
if (asSSIntArray) {
var a =  Clazz_newIntArray (bs.cardinality(), 0);
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
if (Clazz_exceptionOf(e, Exception)){
return e.getMessage();
} else {
throw e;
}
}
}, "JV.Viewer,~N,~N,~N,~N");
Clazz_overrideMethod(c$, "getSpaceGroupJSON", 
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
if (Clazz_exceptionOf(e, Exception)){
return e.getMessage();
} else {
throw e;
}
}
}, "JV.Viewer,~S,~O,~N");
Clazz_defineMethod(c$, "getResource", 
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
Clazz_overrideMethod(c$, "getCellWeight", 
function(pt){
return this.unitCell.getCellWeight(pt);
}, "JU.P3");
Clazz_overrideMethod(c$, "getPrecision", 
function(){
return (this.unitCell == null ? NaN : this.unitCell.getPrecision());
});
Clazz_overrideMethod(c$, "fixUnitCell", 
function(params){
return JS.UnitCell.createCompatibleUnitCell(this.spaceGroup, params, null, true);
}, "~A");
Clazz_overrideMethod(c$, "staticGetTransformABC", 
function(transform, normalize){
return JS.SymmetryOperation.getTransformABC(transform, normalize);
}, "~O,~B");
Clazz_defineMethod(c$, "setCartesianOffset", 
function(origin){
this.unitCell.setCartesianOffset(origin);
}, "JU.T3");
Clazz_defineMethod(c$, "setSymmetryInfoFromFile", 
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
Clazz_defineMethod(c$, "transformUnitCell", 
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
Clazz_overrideMethod(c$, "getITASettingValue", 
function(vwr, itaIndex, key){
var o = this.getSpaceGroupJSON(vwr, "ITA", itaIndex, 0);
return (Clazz_instanceOf(o,"java.util.Map") ? (o).get(key) : o);
}, "JV.Viewer,~S,~S");
Clazz_overrideMethod(c$, "staticCleanTransform", 
function(tr){
return JS.SymmetryOperation.getTransformABC(JS.UnitCell.toTrm(tr, null), true);
}, "~S");
Clazz_overrideMethod(c$, "replaceTransformMatrix", 
function(trm){
var trm0 = this.transformMatrix;
this.transformMatrix = trm;
return trm0;
}, "JU.M4");
Clazz_overrideMethod(c$, "getUnitCellDisplayName", 
function(){
var name = (this.symmetryInfo != null ? this.symmetryInfo.getDisplayName(this) : this.spaceGroup != null ? this.spaceGroup.getDisplayName() : null);
return (name.length > 0 ? name : null);
});
Clazz_overrideMethod(c$, "staticToRationalXYZ", 
function(fPt, sep){
var s = JS.SymmetryOperation.fcoord(fPt, sep);
return (",".equals(sep) ? s : "(" + s + ")");
}, "JU.P3,~S");
Clazz_overrideMethod(c$, "getClegId", 
function(){
if (this.symmetryInfo != null) return this.symmetryInfo.getDerivedSpaceGroup().clegId;
return this.spaceGroup.clegId;
});
Clazz_overrideMethod(c$, "getFinalOperationCount", 
function(){
this.setFinalOperations(3, null, null, -1, -1, false, null);
return this.spaceGroup.getOperationCount();
});
Clazz_overrideMethod(c$, "convertTransform", 
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
Clazz_declarePackage("JS");
Clazz_load(["JU.M3", "$.V3"], "JS.PointGroup", ["java.util.Hashtable", "JU.Lst", "$.P3", "$.PT", "$.Quat", "$.SB", "J.bspt.Bspt", "JU.BSUtil", "$.Escape", "$.Logger", "$.Point3fi"], function(){
var c$ = Clazz_decorateAsClass(function(){
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
if (!Clazz_isClassDefined("JS.PointGroup.Operation")) {
JS.PointGroup.$PointGroup$Operation$ ();
}
Clazz_instantialize(this, arguments);}, JS, "PointGroup", null);
Clazz_prepareFields (c$, function(){
this.nAxes =  Clazz_newIntArray (JS.PointGroup.maxAxis, 0);
this.axes =  new Array(JS.PointGroup.maxAxis);
this.vTemp =  new JU.V3();
});
Clazz_makeConstructor(c$, 
function(isHM){
this.convention = (isHM ? 1 : 0);
}, "~B");
Clazz_defineMethod(c$, "getName", 
function(){
return this.getConventionalName(this.name);
});
Clazz_defineMethod(c$, "getHermannMauguinName", 
function(){
return JS.PointGroup.getHMfromSFName(this.name);
});
Clazz_defineMethod(c$, "getConventionalName", 
function(name){
return (this.convention == 1 ? JS.PointGroup.getHMfromSFName(name) : name);
}, "~S");
c$.getPointGroup = Clazz_defineMethod(c$, "getPointGroup", 
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
Clazz_defineMethod(c$, "isEqual", 
function(pg){
if (pg == null) return false;
if (this.convention != pg.convention || this.linearTolerance != pg.linearTolerance || this.distanceTolerance != pg.distanceTolerance || this.nAtoms != pg.nAtoms || this.localEnvOnly != pg.localEnvOnly || this.haveVibration != pg.haveVibration || this.bsAtoms == null ? pg.bsAtoms != null : !this.bsAtoms.equals(pg.bsAtoms)) return false;
for (var i = 0; i < this.nAtoms; i++) {
if (this.elements[i] != pg.elements[i] || !this.points[i].equals(pg.points[i])) return false;
}
return true;
}, "JS.PointGroup");
Clazz_defineMethod(c$, "set", 
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
this.principalPlane = this.axes[0][this.nAxes[0]++] = Clazz_innerTypeInstance(JS.PointGroup.Operation, this, null, this.vTemp);
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
if (n < 14) n = Clazz_doubleToInt(n / 2);
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
if (Clazz_exceptionOf(e, Exception)){
this.name = "??";
} else {
throw e;
}
} finally {
JU.Logger.info("Point group found: " + this.name);
}
return true;
}, "JS.PointGroup,~A");
Clazz_defineMethod(c$, "setPrincipalAxis", 
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
Clazz_defineMethod(c$, "setPrincipalPlane", 
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
Clazz_defineMethod(c$, "getPointsAndElements", 
function(atomset){
var ac = this.bsAtoms.cardinality();
if (this.isAtoms && ac > this.maxAtoms) return false;
this.points =  new Array(ac);
this.elements =  Clazz_newIntArray (ac, 0);
if (ac == 0) return true;
var atomIndexMax = 0;
for (var i = this.bsAtoms.nextSetBit(0); i >= 0; i = this.bsAtoms.nextSetBit(i + 1)) {
var p = atomset[i];
if (Clazz_instanceOf(p,"JU.Node")) atomIndexMax = Math.max(atomIndexMax, (p).i);
}
this.atomMap =  Clazz_newIntArray (atomIndexMax + 1, 0);
this.nAtoms = 0;
var needCenter = (this.center == null);
if (needCenter) this.center =  new JU.P3();
var bspt =  new J.bspt.Bspt(3, 0);
for (var i = this.bsAtoms.nextSetBit(0); i >= 0; i = this.bsAtoms.nextSetBit(i + 1), this.nAtoms++) {
var p = atomset[i];
if (Clazz_instanceOf(p,"JU.Node")) {
var bondIndex = (this.localEnvOnly ? 1 : 1 + Math.max(3, (p).getCovalentBondCount()));
this.elements[this.nAtoms] = (p).getElementNumber() * bondIndex;
this.atomMap[(p).i] = this.nAtoms + 1;
} else {
var newPt =  new JU.Point3fi();
newPt.setT(p);
newPt.i = -1 - this.nAtoms;
if (Clazz_instanceOf(p,"JU.Point3fi")) this.elements[this.nAtoms] = Math.max(0, (p).sD);
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
Clazz_defineMethod(c$, "findInversionCenter", 
function(){
this.haveInversionCenter = this.checkOperation(null, this.center, -1);
if (this.haveInversionCenter) {
this.axes[1] =  new Array(1);
this.axes[1][0] = Clazz_innerTypeInstance(JS.PointGroup.Operation, this, null);
}});
Clazz_defineMethod(c$, "checkOperation", 
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
Clazz_defineMethod(c$, "getPointIndex", 
function(j){
return (j < 0 ? -j : this.atomMap[j]) - 1;
}, "~N");
Clazz_defineMethod(c$, "isLinear", 
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
Clazz_defineMethod(c$, "isParallel", 
function(v1, v2){
return (Math.abs(v1.dot(v2)) >= this.cosTolerance);
}, "JU.V3,JU.V3");
Clazz_defineMethod(c$, "isPerpendicular", 
function(v1, v2){
return (Math.abs(v1.dot(v2)) <= 1 - this.cosTolerance);
}, "JU.V3,JU.V3");
Clazz_defineMethod(c$, "getElementCounts", 
function(){
for (var i = this.points.length; --i >= 0; ) {
var e1 = this.elements[i];
if (e1 > this.maxElement) this.maxElement = e1;
}
this.eCounts =  Clazz_newIntArray (++this.maxElement, 0);
for (var i = this.points.length; --i >= 0; ) this.eCounts[this.elements[i]]++;

});
Clazz_defineMethod(c$, "findCAxes", 
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
var iOrder = Clazz_doubleToInt(Math.floor(order + 0.01));
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
Clazz_defineMethod(c$, "getAllAxes", 
function(v3){
for (var o = 16; o < JS.PointGroup.maxAxis; o++) if (this.nAxes[o] < JS.PointGroup.axesMaxN[o]) this.checkAxisOrder(o, v3, this.center);

}, "JU.V3");
Clazz_defineMethod(c$, "getHighestOrder", 
function(){
var n = 0;
for (n = 14; --n > 1 && this.nAxes[n] == 0; ) {
}
if (n > 1) return (n + 14 < JS.PointGroup.maxAxis && this.nAxes[n + 14] > 0 ? n + 14 : n);
for (n = JS.PointGroup.maxAxis; --n > 1 && this.nAxes[n] == 0; ) {
}
return n;
});
Clazz_defineMethod(c$, "checkAxisOrder", 
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
Clazz_defineMethod(c$, "addAxis", 
function(iOrder, v){
if (this.haveAxis(iOrder, v)) return;
if (this.axes[iOrder] == null) this.axes[iOrder] =  new Array(JS.PointGroup.axesMaxN[iOrder]);
this.axes[iOrder][this.nAxes[iOrder]++] = Clazz_innerTypeInstance(JS.PointGroup.Operation, this, null, v, iOrder);
}, "~N,JU.V3");
Clazz_defineMethod(c$, "haveAxis", 
function(iOrder, v){
if (this.nAxes[iOrder] == JS.PointGroup.axesMaxN[iOrder]) {
return true;
}if (this.nAxes[iOrder] > 0) for (var i = this.nAxes[iOrder]; --i >= 0; ) {
if (this.isParallel(v, this.axes[iOrder][i].normalOrAxis)) return true;
}
return false;
}, "~N,JU.V3");
Clazz_defineMethod(c$, "findPlanes", 
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
Clazz_defineMethod(c$, "getPlane", 
function(v3){
if (!this.haveAxis(0, v3) && this.checkOperation(JU.Quat.newVA(v3, 180), this.center, -1)) this.axes[0][this.nAxes[0]++] = Clazz_innerTypeInstance(JS.PointGroup.Operation, this, null, v3);
return this.nAxes[0];
}, "JU.V3");
Clazz_defineMethod(c$, "findAdditionalAxes", 
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
c$.getQuaternion = Clazz_defineMethod(c$, "getQuaternion", 
function(v, iOrder){
return JU.Quat.newVA(v, (iOrder < 14 ? 180 : 0) + (iOrder == 0 ? 0 : Clazz_doubleToInt(360 / (iOrder % 14))));
}, "JU.V3,~N");
Clazz_defineMethod(c$, "getInfo", 
function(modelIndex, drawID, asInfo, type, index, scaleFactor){
var asDraw = (drawID != null);
this.info = (asInfo ?  new java.util.Hashtable() : null);
var v =  new JU.V3();
var op;
if (scaleFactor == 0) scaleFactor = 1;
this.scale = scaleFactor;
var nType =  Clazz_newIntArray (4, 2, 0);
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
Clazz_defineMethod(c$, "isDrawType", 
function(type, index, scale){
return (this.drawInfo != null && this.drawType.equals(type == null ? "" : type) && this.drawIndex == index && this.scale == scale);
}, "~S,~N,~N");
c$.getHMfromSFName = Clazz_defineMethod(c$, "getHMfromSFName", 
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
c$.addNames = Clazz_defineMethod(c$, "addNames", 
function(sch, hm){
JS.PointGroup.htSFToHM.put(sch, hm);
JS.PointGroup.htSFToHM.put(hm, sch);
}, "~S,~S");
c$.$PointGroup$Operation$ = function(){
/*if4*/;(function(){
var c$ = Clazz_decorateAsClass(function(){
Clazz_prepareCallback(this, arguments);
this.type = 0;
this.order = 0;
this.index = 0;
this.normalOrAxis = null;
this.typeOrder = 0;
this.mat = null;
Clazz_instantialize(this, arguments);}, JS.PointGroup, "Operation", null);
Clazz_makeConstructor(c$, 
function(){
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = 3;
this.order = 1;
this.typeOrder = 1;
if (JU.Logger.debugging) JU.Logger.debug("new operation -- " + JS.PointGroup.typeNames[this.type]);
});
Clazz_makeConstructor(c$, 
function(v, i){
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = (i < 14 ? 2 : 1);
this.typeOrder = i;
this.order = i % 14;
this.normalOrAxis = JU.Quat.newVA(v, 180).getNormal();
if (JU.Logger.debugging) JU.Logger.debug("new operation -- " + (this.order == i ? "S" : "C") + this.order + " " + this.normalOrAxis);
}, "JU.V3,~N");
Clazz_makeConstructor(c$, 
function(v){
if (v == null) return;
this.index = ++this.b$["JS.PointGroup"].nOps;
this.type = 0;
this.normalOrAxis = JU.Quat.newVA(v, 180).getNormal();
if (JU.Logger.debugging) JU.Logger.debug("new operation -- plane " + this.normalOrAxis);
}, "JU.V3");
Clazz_defineMethod(c$, "getLabel", 
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
Clazz_defineMethod(c$, "getM3", 
function(){
if (this.mat != null) return this.mat;
var m = JU.M3.newM3(JS.PointGroup.getQuaternion(this.normalOrAxis, this.typeOrder).getMatrix());
if (this.type == 0 || this.type == 2) m.mul(JS.PointGroup.mInv);
this.cleanMatrix(m);
return this.mat = m;
});
Clazz_defineMethod(c$, "cleanMatrix", 
function(m){
for (var i = 0; i < 3; i++) for (var j = 0; j < 3; j++) m.setElement(i, j, this.approx0(m.getElement(i, j)));


}, "JU.M3");
Clazz_defineMethod(c$, "approx0", 
function(v){
return (v > 1e-15 || v < -1.0E-15 ? v : 0);
}, "~N");
Clazz_overrideMethod(c$, "toString", 
function(){
return this.getLabel(false) + " " + this.normalOrAxis;
});
/*eoif4*/})();
};
c$.axesMaxN =  Clazz_newIntArray(-1, [15, 0, 0, 1, 3, 1, 10, 0, 1, 0, 6, 0, 1, 0, 0, 0, 15, 10, 6, 6, 10, 0, 1]);
c$.nUnique =  Clazz_newIntArray(-1, [1, 0, 0, 2, 2, 4, 2, 0, 4, 0, 4, 0, 4, 0, 0, 0, 1, 2, 2, 4, 2, 0, 4]);
c$.maxAxis = JS.PointGroup.axesMaxN.length;
c$.typeNames =  Clazz_newArray(-1, ["plane", "proper axis", "improper axis", "center of inversion"]);
c$.mInv = JU.M3.newA9( Clazz_newFloatArray(-1, [-1, 0, 0, 0, -1, 0, 0, 0, -1]));
c$.SF2HM = ("Cn,1,2,3,4,5,6,7,8,9,10,11,12|Cnv,m,2m,3m,4mm,5m,6mm,7m,8mm,9m,10mm,11m,12mm,\u221em|Sn,,-1,-6,-4,(-10),-3,(-14),-8,(-18),-5,(-22),(-12)|Cnh,m,2/m,-6,4/m,-10,6/m,-14,8/m,-18,10/m,-22,12/m|Dn,,222,32,422,52,622,72,822,92,(10)22,(11)2,(12)22|Dnd,,-42m,-3m,-82m,-5m,(-12)2m,-7m,(-16)2m,-9m,(-20)2m,(-11)m,(-24)2m|Dnh,,mmm,-6m2,4/mmm,(-10)m2,6/mmm,(-14)m2,8/mmm,(-18)m2,10/mmm,(-22)m2,12/mmm,\u221e/mm|Ci,-1|Cs,m|T,23|Th,m-3|Td,-43m|O,432|Oh,m-3m").$plit("\\|");
c$.htSFToHM = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["java.util.Hashtable"], "JS.SpaceGroup", ["java.util.Arrays", "JU.AU", "$.Lst", "$.M4", "$.P3", "$.PT", "$.SB", "JS.HallInfo", "$.HallTranslation", "$.SymmetryOperation", "$.UnitCell", "JU.Logger"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.operations = null;
this.finalOperations = null;
this.allOperations = null;
this.xyzList = null;
this.uniqueAxis = '\0';
this.axisChoice = '\0';
this.itaNumber = null;
this.jmolId = null;
this.clegId = null;
this.operationCount = 0;
this.latticeOp = -1;
this.isBio = false;
this.latticeType = 'P';
this.itaTransform = null;
this.itaIndex = null;
this.index = 0;
this.derivedIndex = -1;
this.isSSG = false;
this.name = "unknown!";
this.hallSymbol = null;
this.hallSymbolAlt = null;
this.crystalClass = null;
this.hmSymbol = null;
this.jmolIdExt = null;
this.hallInfo = null;
this.latticeParameter = 0;
this.modDim = 0;
this.doNormalize = true;
this.info = null;
this.nHallOperators = null;
this.hmSymbolFull = null;
this.hmSymbolExt = null;
this.hmSymbolAbbr = null;
this.hmSymbolAlternative = null;
this.hmSymbolAbbrShort = null;
this.ambiguityType = '\0';
this.strName = null;
this.displayName = null;
Clazz_instantialize(this, arguments);}, JS, "SpaceGroup", null, Cloneable);
Clazz_makeConstructor(c$, 
function(index, strData, doInit){
++JS.SpaceGroup.sgIndex;
if (index < 0) index = JS.SpaceGroup.sgIndex;
this.index = index;
this.init(doInit && strData == null);
if (doInit && strData != null) this.buildSelf(strData);
}, "~N,~S,~B");
Clazz_defineMethod(c$, "setFrom", 
function(sg, isITA){
if (isITA) {
this.setName(sg.itaNumber.equals("0") ? this.clegId : "HM:" + sg.hmSymbolFull + " #" + this.clegId);
this.derivedIndex = -2;
} else {
this.setName(sg.getName());
this.derivedIndex = sg.index;
}this.clegId = sg.clegId;
this.itaIndex = sg.itaIndex;
this.crystalClass = sg.crystalClass;
this.hallSymbol = sg.hallSymbol;
this.hmSymbol = sg.hmSymbol;
this.hmSymbolAbbr = sg.hmSymbolAbbr;
this.hmSymbolAbbrShort = sg.hmSymbolAbbrShort;
this.hmSymbolAlternative = sg.hmSymbolAlternative;
this.hmSymbolExt = sg.hmSymbolExt;
this.hmSymbolFull = sg.hmSymbolFull;
this.itaNumber = sg.itaNumber;
this.itaTransform = sg.itaTransform;
this.jmolId = null;
this.jmolIdExt = null;
this.latticeType = sg.latticeType;
this.strName = this.displayName = null;
return this;
}, "JS.SpaceGroup,~B");
c$.getNull = Clazz_defineMethod(c$, "getNull", 
function(doInit, doNormalize, doFinalize){
var sg =  new JS.SpaceGroup(-1, null, doInit);
sg.doNormalize = doNormalize;
if (doFinalize) sg.setFinalOperations();
return sg;
}, "~B,~B,~B");
Clazz_defineMethod(c$, "init", 
function(addXYZ){
this.xyzList =  new java.util.Hashtable();
this.operationCount = 0;
if (addXYZ) this.addSymmetry("x,y,z", 0, false);
}, "~B");
c$.createSpaceGroup = Clazz_defineMethod(c$, "createSpaceGroup", 
function(desiredSpaceGroupIndex, name, data, modDim){
var sg = null;
if (desiredSpaceGroupIndex >= 0) {
sg = JS.SpaceGroup.SG[desiredSpaceGroupIndex];
} else {
if (Clazz_instanceOf(data,"JU.Lst")) sg = JS.SpaceGroup.createSGFromList(name, data);
 else sg = JS.SpaceGroup.determineSpaceGroupNA(name, data);
if (sg == null) sg = JS.SpaceGroup.createSpaceGroupN(modDim <= 0 ? name : "x1,x2,x3,x4,x5,x6,x7,x8,x9".substring(0, modDim * 3 + 8));
}if (sg != null) sg.generateAllOperators(null);
return sg;
}, "~N,~S,~O,~N");
Clazz_defineMethod(c$, "cloneInfoTo", 
function(sg0){
try {
var sg = this.clone();
sg.operations = sg0.operations;
sg.finalOperations = sg0.finalOperations;
sg.xyzList = sg0.xyzList;
return sg;
} catch (e) {
if (Clazz_exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
}, "JS.SpaceGroup");
Clazz_defineMethod(c$, "getItaIndex", 
function(){
return (this.itaIndex != null && !"--".equals(this.itaIndex) ? this.itaIndex : !"0".equals(this.itaNumber) ? this.itaNumber : !"--".equals(this.hallSymbol) ? "[" + this.hallSymbol + "]" : "?");
});
Clazz_defineMethod(c$, "getIndex", 
function(){
return (this.derivedIndex >= 0 ? this.derivedIndex : this.index);
});
c$.createSGFromList = Clazz_defineMethod(c$, "createSGFromList", 
function(name, data){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
sg.setName(name);
var n = data.size();
for (var i = 0; i < n; i++) {
var operation = data.get(i);
if (Clazz_instanceOf(operation,"JS.SymmetryOperation")) {
var op = operation;
var iop = sg.addOp(op, op.xyz, false);
sg.operations[iop].setTimeReversal(op.timeReversal);
} else {
sg.addSymmetrySM("xyz matrix:" + operation, operation);
}}
var sgn = sg.getDerivedSpaceGroup();
if (sgn != null) sg = sgn;
return sg;
}, "~S,JU.Lst");
Clazz_defineMethod(c$, "addSymmetry", 
function(xyz, opId, allowScaling){
xyz = xyz.toLowerCase();
return (xyz.indexOf("[[") < 0 && xyz.indexOf("x4") < 0 && xyz.indexOf(";") < 0 && (xyz.indexOf("x") < 0 || xyz.indexOf("y") < 0 || xyz.indexOf("z") < 0) ? -1 : this.addOperation(xyz, opId, allowScaling));
}, "~S,~N,~B");
Clazz_defineMethod(c$, "setFinalOperations", 
function(){
this.setFinalOperationsForAtoms(3, null, 0, 0, false);
});
Clazz_defineMethod(c$, "setFinalOperationsForAtoms", 
function(dim, atoms, atomIndex, count, doNormalize){
if (this.hallInfo == null && this.latticeParameter != 0) {
var h =  new JS.HallInfo(JS.HallTranslation.getHallLatticeEquivalent(this.latticeParameter));
this.generateAllOperators(h);
}this.finalOperations = null;
this.isBio = (this.name.indexOf("bio") >= 0);
if (!this.isBio && this.index >= JS.SpaceGroup.SG.length && this.name.indexOf("SSG:") < 0 && this.name.indexOf("[subsystem") < 0) {
var sg = this.getDerivedSpaceGroup();
if (sg != null && sg !== this) {
this.setFrom(sg, false);
}}if (this.operationCount == 0) this.addOperation("x,y,z", 1, false);
this.finalOperations =  new Array(this.operationCount);
var op = null;
var doOffset = (doNormalize && count > 0 && atoms != null);
if (doOffset) {
op = this.finalOperations[0] =  new JS.SymmetryOperation(this.operations[0], 0, true);
if (op.sigma == null) JS.SymmetryOperation.normalizeOperationToCentroid(dim, op, atoms, atomIndex, count);
var atom = atoms[atomIndex];
var c = JU.P3.newP(atom);
op.rotTrans(c);
if (c.distance(atom) > 0.0001) {
for (var i = 0; i < count; i++) {
atom = atoms[atomIndex + i];
c.setT(atom);
op.rotTrans(c);
atom.setT(c);
}
}if (!doNormalize) op = null;
}for (var i = 0; i < this.operationCount; i++) {
if (i > 0 || op == null) {
op = this.finalOperations[i] =  new JS.SymmetryOperation(this.operations[i], 0, doNormalize);
}if (doOffset && op.sigma == null) {
JS.SymmetryOperation.normalizeOperationToCentroid(dim, op, atoms, atomIndex, count);
}op.getCentering();
}
}, "~N,~A,~N,~N,~B");
Clazz_defineMethod(c$, "getOperationCount", 
function(){
if (this.finalOperations == null) this.setFinalOperations();
return this.finalOperations.length;
});
Clazz_defineMethod(c$, "getOperation", 
function(i){
return this.finalOperations[i];
}, "~N");
Clazz_defineMethod(c$, "getAdditionalOperationsCount", 
function(){
if (this.finalOperations == null) this.setFinalOperations();
if (this.allOperations == null) {
this.allOperations = JS.SymmetryOperation.getAdditionalOperations(this.finalOperations);
}return this.allOperations.length - this.getOperationCount();
});
Clazz_defineMethod(c$, "getAdditionalOperations", 
function(){
this.getAdditionalOperationsCount();
return this.allOperations;
});
Clazz_defineMethod(c$, "getAllOperation", 
function(i){
return this.allOperations[i];
}, "~N");
Clazz_defineMethod(c$, "getXyz", 
function(i, doNormalize){
return (this.finalOperations == null ? this.operations[i].getXyz(doNormalize) : this.finalOperations[i].getXyz(doNormalize));
}, "~N,~B");
c$.findSpaceGroupFromXYZ = Clazz_defineMethod(c$, "findSpaceGroupFromXYZ", 
function(xyzList){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
var xyzlist = xyzList.$plit(";");
for (var i = 0, n = xyzlist.length; i < n; i++) {
var op =  new JS.SymmetryOperation(null, i, false);
op.setMatrixFromXYZ(xyzlist[i], 0, false);
sg.addOp(op, xyzlist[i], false);
}
return JS.SpaceGroup.findSpaceGroup(sg.operationCount, sg.getCanonicalSeitzList());
}, "~S");
c$.getInfo = Clazz_defineMethod(c$, "getInfo", 
function(sg, spaceGroup, params, asMap, andNonstandard){
try {
if (sg != null && sg.index >= JS.SpaceGroup.SG.length) {
var sgDerived = JS.SpaceGroup.findSpaceGroup(sg.operationCount, sg.getCanonicalSeitzList());
if (sgDerived != null) sg = sgDerived;
}if (params != null) {
if (sg == null) {
if (spaceGroup.indexOf("[") >= 0) spaceGroup = spaceGroup.substring(0, spaceGroup.indexOf("[")).trim();
if (spaceGroup.equals("unspecified!")) return "no space group identified in file";
sg = JS.SpaceGroup.determineSpaceGroupNA(spaceGroup, params);
}} else if (spaceGroup.equalsIgnoreCase("ALL")) {
return JS.SpaceGroup.dumpAll(asMap);
} else if (spaceGroup.equalsIgnoreCase("MAP")) {
return JS.SpaceGroup.dumpAll(true);
} else if (spaceGroup.equalsIgnoreCase("ALLSEITZ")) {
return JS.SpaceGroup.dumpAllSeitz();
} else {
sg = JS.SpaceGroup.determineSpaceGroupN(spaceGroup);
}if (sg == null) {
var sgFound = JS.SpaceGroup.createSpaceGroupN(spaceGroup);
if (sgFound != null) sgFound = JS.SpaceGroup.findSpaceGroup(sgFound.operationCount, sgFound.getCanonicalSeitzList());
if (sgFound != null) sg = sgFound;
}if (sg != null) {
if (asMap) {
return sg.dumpInfoObj();
}var sb =  new JU.SB();
while (sg != null) {
sb.append(sg.dumpInfo());
if (sg.index >= JS.SpaceGroup.SG.length || !andNonstandard) break;
sg = JS.SpaceGroup.determineSpaceGroupNS(spaceGroup, sg);
}
return sb.toString();
}return asMap ? null : "?";
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
return "?";
} else {
throw e;
}
}
}, "JS.SpaceGroup,~S,~A,~B,~B");
Clazz_defineMethod(c$, "dumpInfo", 
function(){
var info = this.dumpCanonicalSeitzList();
if (Clazz_instanceOf(info,"JS.SpaceGroup")) return (info).dumpInfo();
var sb =  new JU.SB().append("\nHermann-Mauguin symbol: ");
if (this.hmSymbol == null || this.hmSymbolExt == null) sb.append("?");
 else sb.append(this.hmSymbol).append(this.hmSymbolExt.length > 0 ? ":" + this.hmSymbolExt : "");
if (this.itaNumber != null) {
sb.append("\ninternational table number: ").append(this.itaNumber).append(this.itaTransform != null ? ":" + this.itaTransform : "").append("\ncrystal class: " + this.crystalClass);
}if (this.jmolId != null) {
sb.append("\nJmol_ID: ").append(this.jmolId).append(" (" + this.itaIndex + ")");
}sb.append("\n\n").append(this.hallInfo == null ? "Hall symbol unknown" : JU.Logger.debugging ? this.hallInfo.dumpInfo() : "");
sb.append("\n\n").appendI(this.operationCount).append(" operators").append(this.hallInfo != null && !this.hallInfo.hallSymbol.equals("--") ? " from Hall symbol " + this.hallInfo.hallSymbol + "  #" + this.jmolId : "").append(": ");
for (var i = 0; i < this.operationCount; i++) {
sb.append("\n").append(this.operations[i].xyz);
}
return sb.toString();
});
Clazz_defineMethod(c$, "dumpInfoObj", 
function(){
var info = this.dumpCanonicalSeitzList();
if (Clazz_instanceOf(info,"JS.SpaceGroup")) return (info).dumpInfoObj();
var map =  new java.util.Hashtable();
if (this.itaNumber != null && !this.itaNumber.equals("0")) {
var s = (this.hmSymbol == null || this.hmSymbolExt == null ? "?" : this.hmSymbol + (this.hmSymbolExt.length > 0 ? ":" + this.hmSymbolExt : ""));
map.put("HermannMauguinSymbol", s);
map.put("ita", Integer.$valueOf(JU.PT.parseInt(this.itaNumber)));
map.put("itaIndex", this.itaIndex == null ? "n/a" : this.itaIndex);
map.put("clegId", this.itaIndex == null ? "n/a" : this.clegId);
if (this.jmolId != null) map.put("jmolId", this.jmolId);
map.put("crystalClass", this.crystalClass);
map.put("operationCount", Integer.$valueOf(this.operationCount));
}var lst =  new JU.Lst();
for (var i = 0; i < this.operationCount; i++) {
lst.addLast(this.operations[i].xyz);
}
map.put("operationsXYZ", lst);
if (this.hallInfo != null && this.hallInfo.hallSymbol != null) map.put("HallSymbol", this.hallInfo.hallSymbol);
if (this.hallSymbolAlt != null) map.put("HallSymbolAlt", this.hallSymbolAlt);
return map;
});
Clazz_defineMethod(c$, "getName", 
function(){
return this.name;
});
Clazz_defineMethod(c$, "getLatticeDesignation", 
function(){
return JS.HallTranslation.getLatticeDesignation(this.latticeParameter);
});
Clazz_defineMethod(c$, "setLatticeParam", 
function(latticeParameter){
this.latticeParameter = latticeParameter;
if (latticeParameter > 10) this.latticeParameter = -JS.HallTranslation.getLatticeIndex(JS.HallTranslation.getLatticeCode(latticeParameter));
}, "~N");
Clazz_defineMethod(c$, "dumpCanonicalSeitzList", 
function(){
if (this.nHallOperators != null) {
this.hallInfo =  new JS.HallInfo(this.hallSymbol);
this.generateAllOperators(null);
}var s = this.getCanonicalSeitzList();
if (this.index >= JS.SpaceGroup.SG.length) {
var sgDerived = JS.SpaceGroup.findSpaceGroup(this.operationCount, s);
if (sgDerived != null) return sgDerived.getCanonicalSeitzList();
}return (this.index >= 0 && this.index < JS.SpaceGroup.SG.length ? this.hallSymbol + " = " : "") + s;
});
Clazz_defineMethod(c$, "getDerivedSpaceGroup", 
function(){
if (this.derivedIndex == -2 || this.index >= 0 && this.index < JS.SpaceGroup.SG.length || this.modDim > 0 || this.operations == null || this.operations.length == 0 || this.operations[0].timeReversal != 0) return this;
if (this.finalOperations != null) this.setFinalOperations();
var s = this.getCanonicalSeitzList();
return (s == null ? null : JS.SpaceGroup.findSpaceGroup(this.operationCount, s));
});
Clazz_defineMethod(c$, "getCanonicalSeitzList", 
function(){
return JS.SpaceGroup.getCanonicalSeitzForOperations(this.operations, this.operationCount);
});
c$.getCanonicalSeitzForOperations = Clazz_defineMethod(c$, "getCanonicalSeitzForOperations", 
function(operations, n){
var list =  new Array(n);
for (var i = 0; i < n; i++) list[i] = JS.SymmetryOperation.dumpSeitz(operations[i], true);

java.util.Arrays.sort(list, 0, n);
var sb =  new JU.SB().append("\n[");
for (var i = 0; i < n; i++) sb.append(list[i].$replace('\t', ' ').$replace('\n', ' ')).append("; ");

sb.append("]");
return sb.toString();
}, "~A,~N");
c$.findSpaceGroup = Clazz_defineMethod(c$, "findSpaceGroup", 
function(opCount, s){
var lst = JS.SpaceGroup.htByOpCount.get(Integer.$valueOf(opCount));
if (lst != null) for (var i = 0, n = lst.size(); i < n; i++) {
var sg = lst.get(i);
if (JS.SpaceGroup.getCanonicalSeitz(sg.index).indexOf(s) >= 0) return JS.SpaceGroup.SG[sg.index];
}
return null;
}, "~N,~S");
c$.dumpAll = Clazz_defineMethod(c$, "dumpAll", 
function(asMap){
if (asMap) {
var info =  new JU.Lst();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) info.addLast(JS.SpaceGroup.SG[i].dumpInfoObj());

return info;
}var sb =  new JU.SB();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) sb.append("\n----------------------\n" + JS.SpaceGroup.SG[i].dumpInfo());

return sb.toString();
}, "~B");
c$.dumpAllSeitz = Clazz_defineMethod(c$, "dumpAllSeitz", 
function(){
var sb =  new JU.SB();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) sb.append("\n").appendO(JS.SpaceGroup.getCanonicalSeitz(i));

return sb.toString();
});
c$.getCanonicalSeitz = Clazz_defineMethod(c$, "getCanonicalSeitz", 
function(i){
if (JS.SpaceGroup.canonicalSeitzList == null) JS.SpaceGroup.canonicalSeitzList =  new Array(JS.SpaceGroup.SG.length);
var cs = JS.SpaceGroup.canonicalSeitzList[i];
return (cs == null ? JS.SpaceGroup.canonicalSeitzList[i] = JS.SpaceGroup.SG[i].dumpCanonicalSeitzList().toString() : cs);
}, "~N");
Clazz_defineMethod(c$, "setLattice", 
function(latticeCode, isCentrosymmetric){
this.latticeParameter = JS.HallTranslation.getLatticeIndex(latticeCode);
if (!isCentrosymmetric) this.latticeParameter = -this.latticeParameter;
}, "~S,~B");
c$.createSpaceGroupN = Clazz_defineMethod(c$, "createSpaceGroupN", 
function(name){
name = name.trim();
var sg = JS.SpaceGroup.determineSpaceGroupN(name);
var hallInfo;
if (sg == null) {
hallInfo =  new JS.HallInfo(name);
if (hallInfo.nRotations > 0) {
sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;" + name, true);
sg.hallInfo = hallInfo;
sg.hallSymbol = hallInfo.hallSymbol;
sg.setName("[" + sg.hallSymbol + "]");
sg.jmolId = null;
} else if (name.indexOf(",") >= 0) {
sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
sg.generateOperatorsFromXyzInfo(name);
}}if (sg != null) sg.generateAllOperators(null);
return sg;
}, "~S");
Clazz_defineMethod(c$, "addOperation", 
function(xyz0, opId, allowScaling){
if (xyz0 == null || xyz0.length < 3) {
this.init(false);
return -1;
}xyz0 = JU.PT.rep(xyz0, " ", "");
var isSpecial = (xyz0.charAt(0) == '=');
if (isSpecial) xyz0 = xyz0.substring(1);
var id = this.checkXYZlist(xyz0);
if (id >= 0) return id;
if (xyz0.startsWith("x1,x2,x3,x4") && this.modDim == 0) {
this.xyzList.clear();
this.operationCount = 0;
this.modDim = JU.PT.parseInt(xyz0.substring(xyz0.lastIndexOf("x") + 1)) - 3;
} else if (xyz0.indexOf("m") >= 0) {
xyz0 = JU.PT.rep(xyz0, "+m", "m");
if (xyz0.equals("x,y,z,m") || xyz0.equals("x,y,z(mx,my,mz)")) {
this.xyzList.clear();
this.operationCount = 0;
}}var op =  new JS.SymmetryOperation(null, opId, this.doNormalize);
if (!op.setMatrixFromXYZ(xyz0, this.modDim, allowScaling)) {
JU.Logger.error("couldn't interpret symmetry operation: " + xyz0);
return -1;
}if (xyz0.charAt(0) == '!') {
xyz0 = xyz0.substring(xyz0.lastIndexOf('!') + 1);
}return this.addOp(op, xyz0, isSpecial);
}, "~S,~N,~B");
Clazz_defineMethod(c$, "checkXYZlist", 
function(xyz){
return (this.xyzList.containsKey(xyz) ? this.xyzList.get(xyz).intValue() : -1);
}, "~S");
Clazz_defineMethod(c$, "addOp", 
function(op, xyz0, isSpecial){
var xyz = op.xyz;
if (!isSpecial) {
var id = this.checkXYZlist(xyz);
if (id >= 0) return id;
if (this.latticeOp < 0) {
var xxx = JU.PT.replaceAllCharacters(this.modDim > 0 ? JS.SymmetryOperation.replaceXn(xyz, this.modDim + 3) : xyz, "+123/", "");
if (this.xyzList.containsKey(xxx + "!")) {
this.latticeOp = this.operationCount;
} else {
this.xyzList.put(xxx + "!", Integer.$valueOf(this.operationCount));
}}this.xyzList.put(xyz, Integer.$valueOf(this.operationCount));
}if (!xyz.equals(xyz0)) this.xyzList.put(xyz0, Integer.$valueOf(this.operationCount));
if (this.operations == null) this.operations =  new Array(4);
if (this.operationCount == this.operations.length) this.operations = JU.AU.arrayCopyObject(this.operations, this.operationCount * 2);
this.operations[this.operationCount++] = op;
op.number = this.operationCount;
if (op.timeReversal != 0) this.operations[0].timeReversal = 1;
if (JU.Logger.debugging) JU.Logger.debug("\naddOperation " + this.operationCount + op.dumpInfo());
return this.operationCount - 1;
}, "JS.SymmetryOperation,~S,~B");
Clazz_defineMethod(c$, "generateOperatorsFromXyzInfo", 
function(xyzInfo){
this.init(true);
var terms = JU.PT.split(xyzInfo.toLowerCase(), ";");
for (var i = 0; i < terms.length; i++) this.addSymmetry(terms[i], 0, false);

}, "~S");
Clazz_defineMethod(c$, "generateAllOperators", 
function(h){
if (h == null) {
if (this.operationCount > 0) return;
if (this.hallSymbol.endsWith("?")) {
this.checkHallOperators();
return;
}h = this.hallInfo;
this.operations =  new Array(4);
if (this.hallInfo == null || this.hallInfo.nRotations == 0) h = this.hallInfo =  new JS.HallInfo(this.hallSymbol);
this.setLattice(this.hallInfo.latticeCode, this.hallInfo.isCentrosymmetric);
this.init(true);
}switch ((h.latticeCode).charCodeAt(0)) {
case 0:
case 83:
case 84:
case 80:
this.latticeType = 'P';
break;
default:
this.latticeType = h.latticeCode;
break;
}
var mat1 =  new JU.M4();
var operation =  new JU.M4();
var newOps =  new Array(7);
for (var i = 0; i < 7; i++) newOps[i] =  new JU.M4();

for (var i = 0; i < h.nRotations; i++) {
var rt = h.rotationTerms[i];
mat1.setM4(rt.seitzMatrix12ths);
var nRot = rt.order;
newOps[0].setIdentity();
var nOps = this.operationCount;
for (var j = 1; j <= nRot; j++) {
var m = newOps[j];
m.mul2(mat1, newOps[0]);
newOps[0].setM4(m);
for (var k = 0; k < nOps; k++) {
operation.mul2(m, this.operations[k]);
operation.m03 = (Clazz_floatToInt(operation.m03) + 12) % 12;
operation.m13 = (Clazz_floatToInt(operation.m13) + 12) % 12;
operation.m23 = (Clazz_floatToInt(operation.m23) + 12) % 12;
var xyz = JS.SymmetryOperation.getXYZFromMatrix(operation, true, true, false);
if (this.checkXYZlist(xyz) >= 0) continue;
this.addSymmetrySM("!nohalf!" + xyz, operation);
}
}
}
if (this.hmSymbol == null) {
this.hmSymbol = "--";
}if (this.hmSymbol.equals("--")) {
this.hallSymbol = h.hallSymbol;
this.nHallOperators = Integer.$valueOf(this.operationCount);
}if (this.nHallOperators != null && this.operationCount != this.nHallOperators.intValue()) JU.Logger.error("Operator mismatch " + this.operationCount + " for " + this);
}, "JS.HallInfo");
Clazz_defineMethod(c$, "addSymmetrySM", 
function(xyz, operation){
var iop = this.addOperation(xyz, 0, false);
if (iop >= 0) {
var symmetryOperation = this.operations[iop];
symmetryOperation.setM4(operation);
}return iop;
}, "~S,JU.M4");
c$.determineSpaceGroupN = Clazz_defineMethod(c$, "determineSpaceGroupN", 
function(name){
return JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, -1);
}, "~S");
c$.determineSpaceGroupNS = Clazz_defineMethod(c$, "determineSpaceGroupNS", 
function(name, sg){
return JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, sg.index);
}, "~S,JS.SpaceGroup");
c$.determineSpaceGroupNA = Clazz_defineMethod(c$, "determineSpaceGroupNA", 
function(name, unitCellParams){
return (unitCellParams == null ? JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, -1) : JS.SpaceGroup.determineSpaceGroup(name, unitCellParams[0], unitCellParams[1], unitCellParams[2], unitCellParams[3], unitCellParams[4], unitCellParams[5], -1));
}, "~S,~A");
c$.determineSpaceGroup = Clazz_defineMethod(c$, "determineSpaceGroup", 
function(name, a, b, c, alpha, beta, gamma, lastIndex){
var i = JS.SpaceGroup.determineSpaceGroupIndex(name, a, b, c, alpha, beta, gamma, lastIndex);
return (i >= 0 ? JS.SpaceGroup.SG[i] : null);
}, "~S,~N,~N,~N,~N,~N,~N,~N");
c$.isXYZList = Clazz_defineMethod(c$, "isXYZList", 
function(name){
return (name != null && name.indexOf(",") >= 0 && name.indexOf("(") < 0 && name.indexOf(":") < 0);
}, "~S");
c$.determineSpaceGroupIndex = Clazz_defineMethod(c$, "determineSpaceGroupIndex", 
function(name, a, b, c, alpha, beta, gamma, lastIndex){
if (JS.SpaceGroup.isXYZList(name)) return -1;
if (lastIndex < 0) lastIndex = JS.SpaceGroup.SG.length;
name = name.trim().toLowerCase();
if (name.startsWith("bilbao:")) {
name = name.substring(7);
}var pt = name.indexOf("hall:");
if (pt > 0) name = name.substring(pt);
var nameType = (name.startsWith("ita/") ? 4 : name.startsWith("hall:") ? 5 : name.startsWith("hm:") ? 3 : 0);
switch (nameType) {
case 3:
case 5:
case 4:
name = name.substring(nameType);
break;
case 0:
if (name.contains("[")) {
nameType = 5;
name = name.substring(0, name.indexOf("[")).trim();
} else if (name.indexOf(".") > 0) {
nameType = 4;
}}
var nameExt = name;
var i;
var haveExtension = false;
if (nameType == 4) {
} else {
name = name.$replace('_', ' ');
if (name.length >= 2) {
i = (name.indexOf("-") == 0 ? 2 : 1);
if (i < name.length && name.charAt(i) != ' ') name = name.substring(0, i) + " " + name.substring(i);
name = JS.SpaceGroup.toCap(name, 2);
}}var ext = "";
if ((i = name.indexOf(":")) > 0) {
ext = name.substring(i + 1);
name = name.substring(0, i).trim();
haveExtension = (ext.length > 0);
}if (nameType != 4 && nameType != 5 && !haveExtension && JU.PT.isOneOf(name, JS.SpaceGroup.ambiguousHMNames)) {
ext = "?";
haveExtension = true;
}var abbr = JU.PT.replaceAllCharacters(name, " ()", "");
var s;
switch (nameType) {
case 4:
if (haveExtension) for (i = 0; i < lastIndex; i++) {
if (nameExt.equalsIgnoreCase(JS.SpaceGroup.SG[i].itaIndex)) return i;
}
 else for (i = 0; i < lastIndex; i++) {
if (name.equalsIgnoreCase(JS.SpaceGroup.SG[i].itaIndex)) return i;
}
break;
case 5:
for (i = 0; i < lastIndex; i++) {
if (JS.SpaceGroup.SG[i].hallSymbol.equalsIgnoreCase(name)) return i;
}
break;
default:
case 3:
if (nameType != 3) for (i = 0; i < lastIndex; i++) if (JS.SpaceGroup.SG[i].jmolId.equalsIgnoreCase(nameExt)) return i;

for (i = 0; i < lastIndex; i++) if (JS.SpaceGroup.SG[i].hmSymbolFull.equalsIgnoreCase(nameExt)) return i;

for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAlternative != null && s.hmSymbolAlternative.equalsIgnoreCase(nameExt)) return i;

if (haveExtension) {
for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAbbr.equalsIgnoreCase(abbr) && s.jmolIdExt.equalsIgnoreCase(ext)) return i;

for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAbbrShort.equalsIgnoreCase(abbr) && s.jmolIdExt.equalsIgnoreCase(ext)) return i;

}var uniqueAxis = JS.SpaceGroup.determineUniqueAxis(a, b, c, alpha, beta, gamma);
if (!haveExtension || ext.charAt(0) == '?') for (i = 0; i < lastIndex; i++) if (((s = JS.SpaceGroup.SG[i]).hmSymbolAbbr.equalsIgnoreCase(abbr) || s.hmSymbolAbbrShort.equalsIgnoreCase(abbr) || s.itaNumber.equals(abbr))) switch ((s.ambiguityType).charCodeAt(0)) {
case 0:
return i;
case 97:
if (s.uniqueAxis == uniqueAxis || uniqueAxis == '\0') return i;
break;
case 111:
if (ext.length == 0) {
if (s.hmSymbolExt.equals("2")) return i;
} else if (s.hmSymbolExt.equalsIgnoreCase(ext)) return i;
break;
case 116:
if (ext.length == 0) {
if (s.axisChoice == 'h') return i;
} else if ((s.axisChoice + "").equalsIgnoreCase(ext)) return i;
break;
}

break;
}
if (ext.length == 0) for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).itaNumber.equals(nameExt)) return i;

return -1;
}, "~S,~N,~N,~N,~N,~N,~N,~N");
Clazz_defineMethod(c$, "setJmolCode", 
function(name){
this.jmolId = name;
var parts = JU.PT.split(name, ":");
this.itaNumber = parts[0];
this.jmolIdExt = (parts.length == 1 ? "" : parts[1]);
this.ambiguityType = '\0';
if (this.jmolIdExt.length > 0) {
var c = this.jmolIdExt.charAt(0);
if (this.jmolIdExt.equals("h") || this.jmolIdExt.equals("r")) {
this.ambiguityType = 't';
this.axisChoice = this.jmolIdExt.charAt(0);
} else if (c == '1' || c == '2') {
this.ambiguityType = 'o';
} else if (this.jmolIdExt.length <= 2 || this.jmolIdExt.length == 3 && c == '-') {
this.ambiguityType = 'a';
this.uniqueAxis = this.jmolIdExt.charAt(c == '-' ? 1 : 0);
} else if (this.jmolIdExt.contains("-")) {
this.ambiguityType = '-';
}}}, "~S");
c$.determineUniqueAxis = Clazz_defineMethod(c$, "determineUniqueAxis", 
function(a, b, c, alpha, beta, gamma){
if (a == b) return (b == c ? '\0' : 'c');
if (b == c) return 'a';
if (c == a) return 'b';
if (alpha == beta) return (beta == gamma ? '\0' : 'c');
if (beta == gamma) return 'a';
if (gamma == alpha) return 'b';
return '\0';
}, "~N,~N,~N,~N,~N,~N");
Clazz_defineMethod(c$, "buildSelf", 
function(sgLineData){
var terms = JU.PT.split(sgLineData.toLowerCase(), ";");
this.jmolId = terms[0].trim();
this.setJmolCode(this.jmolId);
var isAlternate = this.jmolId.endsWith("*");
if (isAlternate) this.jmolId = this.jmolId.substring(0, this.jmolId.length - 1);
this.itaIndex = terms[1].$replace('|', ';');
var s = terms[2];
this.itaTransform = (s.length == 0 || s.equals("--") ? "a,b,c" : JU.PT.rep(s, "ab", "a-b,a+b,c").$replace('|', ';'));
this.clegId = this.itaNumber + ":" + this.itaTransform;
if (terms[3].length > 0) {
this.nHallOperators = Integer.$valueOf(terms[3]);
var lst = JS.SpaceGroup.htByOpCount.get(this.nHallOperators);
if (lst == null) JS.SpaceGroup.htByOpCount.put(this.nHallOperators, lst =  new JU.Lst());
lst.addLast(this);
}this.crystalClass = JS.SpaceGroup.toCap(JU.PT.split(terms[4], "^")[0], 1);
var hm = terms[5];
if (hm.endsWith("*")) hm = hm.substring(0, hm.length - 1);
this.setHMSymbol(hm);
var info;
if ("xyz".equals(terms[6])) {
info = this.hmSymbol;
this.hallSymbol = "" + this.latticeType + "?";
} else {
this.hallSymbol = terms[6];
if (this.hallSymbol.length > 1) this.hallSymbol = JS.SpaceGroup.toCap(this.hallSymbol, 2);
if (isAlternate) {
this.hallSymbolAlt = this.hallSymbol;
this.hallSymbol = JS.SpaceGroup.lastHallSymbol;
}info = this.itaNumber + this.hallSymbol;
if (this.itaNumber.charAt(0) != '0' && info.equals(JS.SpaceGroup.lastInfo)) {
isAlternate = true;
JS.SpaceGroup.ambiguousHMNames += this.hmSymbol + ";";
}}JS.SpaceGroup.lastHallSymbol = this.hallSymbol;
JS.SpaceGroup.lastInfo = info;
this.name = "HM:" + this.hmSymbolFull + " " + (this.hallSymbol == null || this.hallSymbol === "?" ? "[" + this.hallSymbol + "]" : "") + " #" + this.itaIndex;
}, "~S");
Clazz_defineMethod(c$, "setHMSymbol", 
function(name){
var pt = name.indexOf("#");
if (pt >= 0) name = name.substring(0, pt).trim();
this.hmSymbolFull = JS.SpaceGroup.toCap(name, 1);
this.latticeType = this.hmSymbolFull.charAt(0);
var parts = JU.PT.split(this.hmSymbolFull, ":");
this.hmSymbol = parts[0];
this.hmSymbolExt = (parts.length == 1 ? "" : parts[1]);
pt = this.hmSymbol.indexOf(" -3");
if (pt >= 1) if ("admn".indexOf(this.hmSymbol.charAt(pt - 1)) >= 0) {
this.hmSymbolAlternative = (this.hmSymbol.substring(0, pt) + " 3" + this.hmSymbol.substring(pt + 3)).toLowerCase();
}this.hmSymbolAbbr = JU.PT.rep(this.hmSymbol, " ", "");
this.hmSymbolAbbrShort = (this.hmSymbol.length > 3 ? JU.PT.rep(this.hmSymbol, " 1", "") : this.hmSymbolAbbr);
this.hmSymbolAbbrShort = JU.PT.rep(this.hmSymbolAbbrShort, " ", "");
}, "~S");
c$.toCap = Clazz_defineMethod(c$, "toCap", 
function(s, n){
return s.substring(0, n).toUpperCase() + s.substring(n);
}, "~S,~N");
Clazz_defineMethod(c$, "toString", 
function(){
return this.asString();
});
Clazz_defineMethod(c$, "asString", 
function(){
return (this.strName == null ? (this.strName = (this.jmolId == null || this.jmolId.equals("0") ? this.name : this.jmolId + " HM:" + this.hmSymbolFull + " #" + this.clegId)) : this.strName);
});
Clazz_defineMethod(c$, "getDisplayName", 
function(){
if (this.displayName == null) {
var name = null;
if (this.jmolId == null || "--".equals(this.hallSymbol)) {
name = "";
if (this.hmSymbolFull != null && !"--".equals(this.hmSymbol)) name = this.hmSymbolFull + " #";
} else if (!this.jmolId.equals("0")) {
name = this.hmSymbolFull + " #";
}if (name == null) {
name = "[" + this.hallSymbol + "]";
} else {
name += this.clegId;
}if (name.endsWith("2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c")) name = JU.PT.rep(name, "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c", "r");
if (name.indexOf("-- [--]") >= 0) name = "";
if (name.endsWith(":a,b,c")) name = name.substring(0, name.length - 6);
this.displayName = name;
}return this.displayName;
});
c$.getSpaceGroups = Clazz_defineMethod(c$, "getSpaceGroups", 
function(){
if (JS.SpaceGroup.SG == null) {
var n = JS.SpaceGroup.STR_SG.length;
JS.SpaceGroup.nameToGroup =  new java.util.Hashtable();
var defs =  new Array(n);
for (var i = 0; i < n; i++) {
defs[i] =  new JS.SpaceGroup(i, JS.SpaceGroup.STR_SG[i], true);
JS.SpaceGroup.nameToGroup.put(defs[i].jmolId, defs[i]);
}
System.out.println("SpaceGroup - " + JS.SpaceGroup.nSG + " settings generated");
JS.SpaceGroup.STR_SG = null;
JS.SpaceGroup.SG = defs;
}return JS.SpaceGroup.SG;
});
Clazz_defineMethod(c$, "addLatticeVectors", 
function(lattvecs){
if (this.latticeOp >= 0 || lattvecs.size() == 0) return false;
var nOps = this.latticeOp = this.operationCount;
var isMagnetic = (lattvecs.get(0).length == this.modDim + 4);
var magRev = -2;
for (var j = 0; j < lattvecs.size(); j++) {
var data = lattvecs.get(j);
if (isMagnetic) {
magRev = Clazz_floatToInt(data[this.modDim + 3]);
data = JU.AU.arrayCopyF(data, this.modDim + 3);
}if (data.length > this.modDim + 3) return false;
for (var i = 0; i < nOps; i++) {
var newOp =  new JS.SymmetryOperation(null, 0, true);
newOp.modDim = this.modDim;
var op = this.operations[i];
newOp.divisor = op.divisor;
newOp.linearRotTrans = JU.AU.arrayCopyF(op.linearRotTrans, -1);
newOp.setFromMatrix(data, false);
if (magRev != -2) newOp.setTimeReversal(op.timeReversal * magRev);
newOp.xyzOriginal = newOp.xyz;
this.addOp(newOp, newOp.xyz, true);
}
}
return true;
}, "JU.Lst");
Clazz_defineMethod(c$, "getSiteMultiplicity", 
function(pt, unitCell){
var n = this.finalOperations.length;
var pts =  new JU.Lst();
for (var i = n; --i >= 0; ) {
var pt1 = JU.P3.newP(pt);
this.finalOperations[i].rotTrans(pt1);
unitCell.unitize(pt1);
for (var j = pts.size(); --j >= 0; ) {
var pt0 = pts.get(j);
if (pt1.distanceSquared(pt0) < 1.96E-6) {
pt1 = null;
break;
}}
if (pt1 != null) pts.addLast(pt1);
}
return Clazz_doubleToInt(n / pts.size());
}, "JU.P3,JS.UnitCell");
Clazz_defineMethod(c$, "setName", 
function(name){
this.name = name;
if (name != null && name.startsWith("HM:")) {
this.setHMSymbol(name.substring(3));
}this.strName = this.displayName = null;
}, "~S");
Clazz_defineMethod(c$, "getNameType", 
function(type, uc){
var ret = null;
if (type.equals("HM")) {
ret = this.hmSymbol;
} else if (type.equals("ITA")) {
ret = this.itaNumber;
} else if (type.equals("Hall")) {
ret = this.hallSymbol;
} else {
ret = "?";
}if (ret != null) return ret;
if (this.info == null) this.info = JS.SpaceGroup.getInfo(this, this.hmSymbol, uc.getUnitCellParams(), true, false);
if ((typeof(this.info)=='string')) return null;
var map = this.info;
var v = map.get(type.equals("Hall") ? "HallSymbol" : type.equals("ITA") ? "ita" : "HermannMauguinSymbol");
return (v == null ? null : v.toString());
}, "~S,J.api.SymmetryInterface");
c$.getSpaceGroupFromJmolClegOrITA = Clazz_defineMethod(c$, "getSpaceGroupFromJmolClegOrITA", 
function(name){
var n = JS.SpaceGroup.SG.length;
if (name.indexOf(":") >= 0) {
if (name.indexOf(",") >= 0) {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].clegId)) return JS.SpaceGroup.SG[i];

} else {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].jmolId)) return JS.SpaceGroup.SG[i];

}} else if (name.indexOf(".") >= 0) {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].itaIndex)) return JS.SpaceGroup.SG[i];

} else {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].itaNumber)) return JS.SpaceGroup.SG[i];

}return null;
}, "~S");
Clazz_defineMethod(c$, "checkHallOperators", 
function(){
if (this.nHallOperators != null && this.nHallOperators.intValue() != this.operationCount) {
if (this.hallInfo == null || this.hallInfo.nRotations > 0) {
this.generateAllOperators(this.hallInfo);
} else {
this.init(false);
this.doNormalize = false;
JS.SpaceGroup.transformSpaceGroup(this, JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(this.itaNumber), null, this.itaTransform, null);
this.hallInfo = null;
}}});
Clazz_defineMethod(c$, "getOpsCtr", 
function(transform){
var sg = JS.SpaceGroup.getNull(true, true, false);
JS.SpaceGroup.transformSpaceGroup(sg, this, null, "!" + transform, null);
sg.setFinalOperations();
var sg2 = JS.SpaceGroup.getNull(true, false, false);
JS.SpaceGroup.transformSpaceGroup(sg2, sg, null, transform, null);
sg2.setFinalOperations();
return sg2.finalOperations;
}, "~S");
c$.getSpaceGroupFromIndex = Clazz_defineMethod(c$, "getSpaceGroupFromIndex", 
function(i){
return (JS.SpaceGroup.SG != null && i >= 0 && i < JS.SpaceGroup.SG.length ? JS.SpaceGroup.SG[i] : null);
}, "~N");
Clazz_defineMethod(c$, "setITATableNames", 
function(jmolId, sg, set, tr){
this.itaNumber = sg;
this.itaIndex = (tr != null ? sg + ":" + tr : set.indexOf(".") >= 0 ? set : sg + "." + set);
this.itaTransform = tr;
this.clegId = sg + ":" + tr;
this.jmolId = jmolId;
if (jmolId == null) {
this.info = this.dumpInfoObj();
} else {
this.setJmolCode(jmolId);
}}, "~S,~S,~S,~S");
c$.transformCoords = Clazz_defineMethod(c$, "transformCoords", 
function(coord, trmInv, centering, t, v, coordt){
if (coordt == null) coordt =  new JU.Lst();
for (var j = 0, n = coord.size(); j < n; j++) {
var xyz = JS.SymmetryOperation.transformStr(coord.get(j), null, trmInv, t, v, null, centering, true, true);
if (!coordt.contains(xyz)) coordt.addLast(xyz);
}
return coordt;
}, "JU.Lst,JU.M4,JU.P3,JU.M4,~A,JU.Lst");
c$.getTransformRange = Clazz_defineMethod(c$, "getTransformRange", 
function(trm){
var t =  Clazz_newFloatArray (2, 3, 0);
var row =  Clazz_newFloatArray (4, 0);
for (var i = 0; i < 3; i++) {
trm.getRow(i, row);
for (var j = 0; j < 3; j++) {
var v = row[j];
if (v < 0) {
t[0][i] += -row[j];
} else if (v > 0) {
t[1][i] += row[j];
}}
}
var ignore = true;
for (var i = 0, dz = 0; i < 2; i++, dz++) {
for (var j = 0; j < 3; j++) {
var d = Clazz_doubleToInt(Math.ceil(t[i][j]));
if (d > dz) ignore = false;
t[i][j] = (i == 0 ? -d : d);
}
}
return (ignore ? null : t);
}, "JU.M4");
c$.getTransformedCentering = Clazz_defineMethod(c$, "getTransformedCentering", 
function(trm, cent){
var trmInv = JU.M4.newM4(trm);
trmInv.invert();
var n0 = cent.size();
var p =  new JU.P3();
var c = JS.SpaceGroup.getTransformRange(trm);
if (c != null) {
for (var i = Clazz_floatToInt(c[0][0]); i < c[1][0]; i++) {
for (var j = Clazz_floatToInt(c[0][1]); j <= c[1][1]; j++) {
for (var k = Clazz_floatToInt(c[0][2]); k <= c[1][2]; k++) {
p.set(i, j, k);
trmInv.rotTrans(p);
if (p.length() % 1 != 0) {
p.x = p.x % 1;
p.y = p.y % 1;
p.z = p.z % 1;
var s = JS.SymmetryOperation.norm3(p);
if (!s.equals("0,0,0") && !cent.contains(s)) cent.addLast(s);
}}
}
}
var n = cent.size();
if (n > 0) {
var a =  new Array(n);
cent.toArray(a);
java.util.Arrays.sort(a);
cent.clear();
for (var i = 0; i < n; i++) cent.addLast(a[i]);

}}for (var i = n0; --i >= 0; ) {
JS.SymmetryOperation.toPoint(cent.get(i), p);
trmInv.rotTrans(p);
if (p.x % 1 == 0 && p.y % 1 == 0 && p.z % 1 == 0) cent.remove(i);
}
return trmInv;
}, "JU.M4,JU.Lst");
c$.fillMoreData = Clazz_defineMethod(c$, "fillMoreData", 
function(map, clegId, itno, its0){
var pt = clegId.indexOf(':');
var transform = (pt < 0 ? "a,b,c" : clegId.substring(pt + 1));
var trm = JS.UnitCell.toTrm(transform, null);
var gp0 = its0.get("gp");
var wpos0 = its0.get("wpos");
var cent0 = wpos0.get("cent");
var cent =  new JU.Lst();
if (cent0 != null) cent.addAll(cent0);
var nctr0 = cent.size();
var trmInv = JS.SpaceGroup.getTransformedCentering(trm, cent);
var nctr = cent.size();
var pos0 = wpos0.get("pos");
var pos =  new JU.Lst();
var t =  new JU.M4();
var v =  Clazz_newFloatArray (16, 0);
var f = (nctr + 1) / (nctr0 + 1);
for (var i = 0, n = pos0.size(); i < n; i++) {
var p0 = pos0.get(i);
var p =  new java.util.Hashtable();
p.putAll(p0);
var coord = p0.get("coord");
if (coord != null) {
coord = JS.SpaceGroup.transformCoords(coord, trmInv, null, t, v, null);
p.put("coord", coord);
}var mult = (p0.get("mult")).intValue();
p.put("mult", Integer.$valueOf(Clazz_floatToInt(mult * f)));
pos.addLast(p);
}
var gp =  new JU.Lst();
JS.SpaceGroup.transformCoords(gp0, trmInv, null, t, v, gp);
if (nctr > 0) {
for (var i = 0; i < nctr; i++) {
var p =  new JU.P3();
JS.SpaceGroup.transformCoords(gp0, trmInv, JS.SymmetryOperation.toPoint(cent.get(i), p), t, v, gp);
}
}if (map == null) {
map =  new java.util.Hashtable();
map.put("sg", Integer.$valueOf(itno));
map.put("trm", transform);
map.put("clegId", itno + ":" + transform);
map.put("det", Float.$valueOf(trm.determinant3()));
} else {
map.remove("more");
}var wpos =  new java.util.Hashtable();
if (nctr > 0) wpos.put("cent", cent);
wpos.put("pos", pos);
map.put("wpos", wpos);
wpos.put("gp", gp);
gp =  new JU.Lst();
var base = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(clegId);
var sg = JS.SpaceGroup.transformSpaceGroup(null, base, gp0, transform,  new JU.M4());
for (var i = 0, n = sg.getOperationCount(); i < n; i++) {
gp.addLast((sg.getOperation(i)).xyz);
}
map.put("gp", gp);
return map;
}, "java.util.Map,~S,~N,java.util.Map");
c$.transformSpaceGroup = Clazz_defineMethod(c$, "transformSpaceGroup", 
function(sg, base, genPos, transform, trm){
if (genPos == null) {
base.setFinalOperations();
genPos =  new JU.Lst();
for (var i = 0, n = base.getOperationCount(); i < n; i++) {
genPos.addLast(base.getXyz(i, false));
}
}var normalize = (sg == null || sg.doNormalize);
var xyzList = JS.SpaceGroup.addTransformXYZList(sg, genPos, transform, trm, normalize);
if (sg == null) {
return JS.SpaceGroup.createITASpaceGroup(xyzList, base);
}if (transform == null) {
sg.setFrom(base, true);
} else {
sg.setITATableNames(sg.jmolId, sg.itaNumber, "1", transform);
}return sg;
}, "JS.SpaceGroup,JS.SpaceGroup,JU.Lst,~S,JU.M4");
c$.createITASpaceGroup = Clazz_defineMethod(c$, "createITASpaceGroup", 
function(genpos, base){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
for (var i = 0, n = genpos.size(); i < n; i++) {
var op =  new JS.SymmetryOperation(null, i, false);
var xyz = genpos.get(i);
op.setMatrixFromXYZ(xyz, 0, false);
sg.addOp(op, xyz, false);
}
if (base != null) sg.setFrom(base, true);
return sg;
}, "JU.Lst,JS.SpaceGroup");
c$.addTransformXYZList = Clazz_defineMethod(c$, "addTransformXYZList", 
function(sg, genPos, transform, trm, normalize){
var trmInv = null;
var t = null;
var v = null;
if (transform != null) {
if (transform.equals("r")) transform = "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c";
trm = JS.UnitCell.toTrm(transform, trm);
trmInv = JU.M4.newM4(trm);
trmInv.invert();
v =  Clazz_newFloatArray (16, 0);
t =  new JU.M4();
}var xyzList = JS.SpaceGroup.addTransformedOperations(sg, genPos, trm, trmInv, t, v, sg == null ?  new JU.Lst() : null, null, normalize);
if (sg == null) return xyzList;
var c = JS.SpaceGroup.getTransformRange(trm);
if (c != null) {
var p =  new JU.P3();
for (var i = Clazz_floatToInt(c[0][0]); i < c[1][0]; i++) {
for (var j = Clazz_floatToInt(c[0][1]); j <= c[1][1]; j++) {
for (var k = Clazz_floatToInt(c[0][2]); k <= c[1][2]; k++) {
if (i == 0 && j == 0 && k == 0) continue;
p.set(i, j, k);
JS.SpaceGroup.addTransformedOperations(sg, genPos, trm, trmInv, t, v, null, p, normalize);
}
}
}
}return null;
}, "JS.SpaceGroup,JU.Lst,~S,JU.M4,~B");
c$.addTransformedOperations = Clazz_defineMethod(c$, "addTransformedOperations", 
function(sg, genPos, trm, trmInv, t, v, retGenPos, centering, normalize){
if (sg != null) sg.latticeOp = 0;
for (var i = 0, c = genPos.size(); i < c; i++) {
var xyz = genPos.get(i);
if (trm != null && (i > 0 || centering != null)) {
xyz = JS.SymmetryOperation.transformStr(xyz, trm, trmInv, t, v, centering, null, normalize, false);
}if (sg == null) {
retGenPos.addLast(xyz);
} else {
sg.addOperation(xyz, 0, false);
}}
return retGenPos;
}, "JS.SpaceGroup,JU.Lst,JU.M4,JU.M4,JU.M4,~A,JU.Lst,JU.P3,~B");
c$.canonicalSeitzList = null;
c$.sgIndex = -1;
c$.lastInfo = null;
c$.ambiguousHMNames = "";
c$.lastHallSymbol = "";
c$.SG = null;
c$.htByOpCount =  new java.util.Hashtable();
c$.nameToGroup = null;
c$.nSG = 0;
c$.STR_SG =  Clazz_newArray(-1, ["1;1.1;;1;c1^1;p 1;p 1", "2;2.1;;2;ci^1;p -1;-p 1", "3:b;3.1;;2;c2^1;p 1 2 1;p 2y", "3:b;3.1;;2;c2^1;p 2;p 2y", "3:c;3.2;c,a,b;2;c2^1;p 1 1 2;p 2", "3:a;3.3;b,c,a;2;c2^1;p 2 1 1;p 2x", "4:b;4.1;;2;c2^2;p 1 21 1;p 2yb", "4:b;4.1;;2;c2^2;p 21;p 2yb", "4:b*;4.1;;2;c2^2;p 1 21 1*;p 2y1", "4:c;4.2;c,a,b;2;c2^2;p 1 1 21;p 2c", "4:c*;4.2;c,a,b;2;c2^2;p 1 1 21*;p 21", "4:a;4.3;b,c,a;2;c2^2;p 21 1 1;p 2xa", "4:a*;4.3;b,c,a;2;c2^2;p 21 1 1*;p 2x1", "5:b1;5.1;;4;c2^3;c 1 2 1;c 2y", "5:b1;5.1;;4;c2^3;c 2;c 2y", "5:b2;5.2;-a-c,b,a;4;c2^3;a 1 2 1;a 2y", "5:b3;5.3;c,b,-a-c;4;c2^3;i 1 2 1;i 2y", "5:c1;5.4;c,a,b;4;c2^3;a 1 1 2;a 2", "5:c2;5.5;a,-a-c,b;4;c2^3;b 1 1 2;b 2", "5:c3;5.6;-a-c,c,b;4;c2^3;i 1 1 2;i 2", "5:a1;5.7;b,c,a;4;c2^3;b 2 1 1;b 2x", "5:a2;5.8;b,a,-a-c;4;c2^3;c 2 1 1;c 2x", "5:a3;5.9;b,-a-c,c;4;c2^3;i 2 1 1;i 2x", "6:b;6.1;;2;cs^1;p 1 m 1;p -2y", "6:b;6.1;;2;cs^1;p m;p -2y", "6:c;6.2;c,a,b;2;cs^1;p 1 1 m;p -2", "6:a;6.3;b,c,a;2;cs^1;p m 1 1;p -2x", "7:b1;7.1;;2;cs^2;p 1 c 1;p -2yc", "7:b1;7.1;;2;cs^2;p c;p -2yc", "7:b2;7.2;-a-c,b,a;2;cs^2;p 1 n 1;p -2yac", "7:b2;7.2;-a-c,b,a;2;cs^2;p n;p -2yac", "7:b3;7.3;c,b,-a-c;2;cs^2;p 1 a 1;p -2ya", "7:b3;7.3;c,b,-a-c;2;cs^2;p a;p -2ya", "7:c1;7.4;c,a,b;2;cs^2;p 1 1 a;p -2a", "7:c2;7.5;a,-a-c,b;2;cs^2;p 1 1 n;p -2ab", "7:c3;7.6;-a-c,c,b;2;cs^2;p 1 1 b;p -2b", "7:a1;7.7;b,c,a;2;cs^2;p b 1 1;p -2xb", "7:a2;7.8;b,a,-a-c;2;cs^2;p n 1 1;p -2xbc", "7:a3;7.9;b,-a-c,c;2;cs^2;p c 1 1;p -2xc", "8:b1;8.1;;4;cs^3;c 1 m 1;c -2y", "8:b1;8.1;;4;cs^3;c m;c -2y", "8:b2;8.2;-a-c,b,a;4;cs^3;a 1 m 1;a -2y", "8:b3;8.3;c,b,-a-c;4;cs^3;i 1 m 1;i -2y", "8:b3;8.3;c,b,-a-c;4;cs^3;i m;i -2y", "8:c1;8.4;c,a,b;4;cs^3;a 1 1 m;a -2", "8:c2;8.5;a,-a-c,b;4;cs^3;b 1 1 m;b -2", "8:c3;8.6;-a-c,c,b;4;cs^3;i 1 1 m;i -2", "8:a1;8.7;b,c,a;4;cs^3;b m 1 1;b -2x", "8:a2;8.8;b,a,-a-c;4;cs^3;c m 1 1;c -2x", "8:a3;8.9;b,-a-c,c;4;cs^3;i m 1 1;i -2x", "9:b1;9.1;;4;cs^4;c 1 c 1;c -2yc", "9:b1;9.1;;4;cs^4;c c;c -2yc", "9:b2;9.2;-a-c,b,a;4;cs^4;a 1 n 1;a -2yab", "9:b3;9.3;c,b,-a-c;4;cs^4;i 1 a 1;i -2ya", "9:-b1;9.4;c,-b,a;4;cs^4;a 1 a 1;a -2ya", "9:-b2;9.5;a,-b,-a-c;4;cs^4;c 1 n 1;c -2yac", "9:-b3;9.6;-a-c,-b,c;4;cs^4;i 1 c 1;i -2yc", "9:c1;9.7;c,a,b;4;cs^4;a 1 1 a;a -2a", "9:c2;9.8;a,-a-c,b;4;cs^4;b 1 1 n;b -2ab", "9:c3;9.9;-a-c,c,b;4;cs^4;i 1 1 b;i -2b", "9:-c1;9.10;a,c,-b;4;cs^4;b 1 1 b;b -2b", "9:-c2;9.11;-a-c,a,-b;4;cs^4;a 1 1 n;a -2ab", "9:-c3;9.12;c,-a-c,-b;4;cs^4;i 1 1 a;i -2a", "9:a1;9.13;b,c,a;4;cs^4;b b 1 1;b -2xb", "9:a2;9.14;b,a,-a-c;4;cs^4;c n 1 1;c -2xac", "9:a3;9.15;b,-a-c,c;4;cs^4;i c 1 1;i -2xc", "9:-a1;9.16;-b,a,c;4;cs^4;c c 1 1;c -2xc", "9:-a2;9.17;-b,-a-c,a;4;cs^4;b n 1 1;b -2xab", "9:-a3;9.18;-b,c,-a-c;4;cs^4;i b 1 1;i -2xb", "10:b;10.1;;4;c2h^1;p 1 2/m 1;-p 2y", "10:b;10.1;;4;c2h^1;p 2/m;-p 2y", "10:c;10.2;c,a,b;4;c2h^1;p 1 1 2/m;-p 2", "10:a;10.3;b,c,a;4;c2h^1;p 2/m 1 1;-p 2x", "11:b;11.1;;4;c2h^2;p 1 21/m 1;-p 2yb", "11:b;11.1;;4;c2h^2;p 21/m;-p 2yb", "11:b*;11.1;;4;c2h^2;p 1 21/m 1*;-p 2y1", "11:c;11.2;c,a,b;4;c2h^2;p 1 1 21/m;-p 2c", "11:c*;11.2;c,a,b;4;c2h^2;p 1 1 21/m*;-p 21", "11:a;11.3;b,c,a;4;c2h^2;p 21/m 1 1;-p 2xa", "11:a*;11.3;b,c,a;4;c2h^2;p 21/m 1 1*;-p 2x1", "12:b1;12.1;;8;c2h^3;c 1 2/m 1;-c 2y", "12:b1;12.1;;8;c2h^3;c 2/m;-c 2y", "12:b2;12.2;-a-c,b,a;8;c2h^3;a 1 2/m 1;-a 2y", "12:b3;12.3;c,b,-a-c;8;c2h^3;i 1 2/m 1;-i 2y", "12:b3;12.3;c,b,-a-c;8;c2h^3;i 2/m;-i 2y", "12:c1;12.4;c,a,b;8;c2h^3;a 1 1 2/m;-a 2", "12:c2;12.5;a,-a-c,b;8;c2h^3;b 1 1 2/m;-b 2", "12:c3;12.6;-a-c,c,b;8;c2h^3;i 1 1 2/m;-i 2", "12:a1;12.7;b,c,a;8;c2h^3;b 2/m 1 1;-b 2x", "12:a2;12.8;b,a,-a-c;8;c2h^3;c 2/m 1 1;-c 2x", "12:a3;12.9;b,-a-c,c;8;c2h^3;i 2/m 1 1;-i 2x", "13:b1;13.1;;4;c2h^4;p 1 2/c 1;-p 2yc", "13:b1;13.1;;4;c2h^4;p 2/c;-p 2yc", "13:b2;13.2;-a-c,b,a;4;c2h^4;p 1 2/n 1;-p 2yac", "13:b2;13.2;-a-c,b,a;4;c2h^4;p 2/n;-p 2yac", "13:b3;13.3;c,b,-a-c;4;c2h^4;p 1 2/a 1;-p 2ya", "13:b3;13.3;c,b,-a-c;4;c2h^4;p 2/a;-p 2ya", "13:c1;13.4;c,a,b;4;c2h^4;p 1 1 2/a;-p 2a", "13:c2;13.5;a,-a-c,b;4;c2h^4;p 1 1 2/n;-p 2ab", "13:c3;13.6;-a-c,c,b;4;c2h^4;p 1 1 2/b;-p 2b", "13:a1;13.7;b,c,a;4;c2h^4;p 2/b 1 1;-p 2xb", "13:a2;13.8;b,a,-a-c;4;c2h^4;p 2/n 1 1;-p 2xbc", "13:a3;13.9;b,-a-c,c;4;c2h^4;p 2/c 1 1;-p 2xc", "14:b1;14.1;;4;c2h^5;p 1 21/c 1;-p 2ybc", "14:b1;14.1;;4;c2h^5;p 21/c;-p 2ybc", "14:b2;14.2;-a-c,b,a;4;c2h^5;p 1 21/n 1;-p 2yn", "14:b2;14.2;-a-c,b,a;4;c2h^5;p 21/n;-p 2yn", "14:b3;14.3;c,b,-a-c;4;c2h^5;p 1 21/a 1;-p 2yab", "14:b3;14.3;c,b,-a-c;4;c2h^5;p 21/a;-p 2yab", "14:c1;14.4;c,a,b;4;c2h^5;p 1 1 21/a;-p 2ac", "14:c2;14.5;a,-a-c,b;4;c2h^5;p 1 1 21/n;-p 2n", "14:c3;14.6;-a-c,c,b;4;c2h^5;p 1 1 21/b;-p 2bc", "14:a1;14.7;b,c,a;4;c2h^5;p 21/b 1 1;-p 2xab", "14:a2;14.8;b,a,-a-c;4;c2h^5;p 21/n 1 1;-p 2xn", "14:a3;14.9;b,-a-c,c;4;c2h^5;p 21/c 1 1;-p 2xac", "15:b1;15.1;;8;c2h^6;c 1 2/c 1;-c 2yc", "15:b1;15.1;;8;c2h^6;c 2/c;-c 2yc", "15:b2;15.2;-a-c,b,a;8;c2h^6;a 1 2/n 1;-a 2yab", "15:b3;15.3;c,b,-a-c;8;c2h^6;i 1 2/a 1;-i 2ya", "15:b3;15.3;c,b,-a-c;8;c2h^6;i 2/a;-i 2ya", "15:-b1;15.4;c,-b,a;8;c2h^6;a 1 2/a 1;-a 2ya", "15:-b2;15.5;a,-b,-a-c;8;c2h^6;c 1 2/n 1;-c 2yac", "15:-b2;15.5;a,-b,-a-c;8;c2h^6;c 2/n;-c 2yac", "15:-b3;15.6;-a-c,-b,c;8;c2h^6;i 1 2/c 1;-i 2yc", "15:-b3;15.6;-a-c,-b,c;8;c2h^6;i 2/c;-i 2yc", "15:c1;15.7;c,a,b;8;c2h^6;a 1 1 2/a;-a 2a", "15:c2;15.8;a,-a-c,b;8;c2h^6;b 1 1 2/n;-b 2ab", "15:c3;15.9;-a-c,c,b;8;c2h^6;i 1 1 2/b;-i 2b", "15:-c1;15.10;a,c,-b;8;c2h^6;b 1 1 2/b;-b 2b", "15:-c2;15.11;-a-c,a,-b;8;c2h^6;a 1 1 2/n;-a 2ab", "15:-c3;15.12;c,-a-c,-b;8;c2h^6;i 1 1 2/a;-i 2a", "15:a1;15.13;b,c,a;8;c2h^6;b 2/b 1 1;-b 2xb", "15:a2;15.14;b,a,-a-c;8;c2h^6;c 2/n 1 1;-c 2xac", "15:a3;15.15;b,-a-c,c;8;c2h^6;i 2/c 1 1;-i 2xc", "15:-a1;15.16;-b,a,c;8;c2h^6;c 2/c 1 1;-c 2xc", "15:-a2;15.17;-b,-a-c,a;8;c2h^6;b 2/n 1 1;-b 2xab", "15:-a3;15.18;-b,c,-a-c;8;c2h^6;i 2/b 1 1;-i 2xb", "16;16.1;;4;d2^1;p 2 2 2;p 2 2", "17;17.1;;4;d2^2;p 2 2 21;p 2c 2", "17*;17.1;;4;d2^2;p 2 2 21*;p 21 2", "17:cab;17.2;c,a,b;4;d2^2;p 21 2 2;p 2a 2a", "17:bca;17.3;b,c,a;4;d2^2;p 2 21 2;p 2 2b", "18;18.1;;4;d2^3;p 21 21 2;p 2 2ab", "18:cab;18.2;c,a,b;4;d2^3;p 2 21 21;p 2bc 2", "18:bca;18.3;b,c,a;4;d2^3;p 21 2 21;p 2ac 2ac", "19;19.1;;4;d2^4;p 21 21 21;p 2ac 2ab", "20;20.1;;8;d2^5;c 2 2 21;c 2c 2", "20*;20.1;;8;d2^5;c 2 2 21*;c 21 2", "20:cab;20.2;c,a,b;8;d2^5;a 21 2 2;a 2a 2a", "20:cab*;20.2;c,a,b;8;d2^5;a 21 2 2*;a 2a 21", "20:bca;20.3;b,c,a;8;d2^5;b 2 21 2;b 2 2b", "21;21.1;;8;d2^6;c 2 2 2;c 2 2", "21:cab;21.2;c,a,b;8;d2^6;a 2 2 2;a 2 2", "21:bca;21.3;b,c,a;8;d2^6;b 2 2 2;b 2 2", "22;22.1;;16;d2^7;f 2 2 2;f 2 2", "23;23.1;;8;d2^8;i 2 2 2;i 2 2", "24;24.1;;8;d2^9;i 21 21 21;i 2b 2c", "25;25.1;;4;c2v^1;p m m 2;p 2 -2", "25:cab;25.2;c,a,b;4;c2v^1;p 2 m m;p -2 2", "25:bca;25.3;b,c,a;4;c2v^1;p m 2 m;p -2 -2", "26;26.1;;4;c2v^2;p m c 21;p 2c -2", "26*;26.1;;4;c2v^2;p m c 21*;p 21 -2", "26:ba-c;26.2;b,a,-c;4;c2v^2;p c m 21;p 2c -2c", "26:ba-c*;26.2;b,a,-c;4;c2v^2;p c m 21*;p 21 -2c", "26:cab;26.3;c,a,b;4;c2v^2;p 21 m a;p -2a 2a", "26:-cba;26.4;-c,b,a;4;c2v^2;p 21 a m;p -2 2a", "26:bca;26.5;b,c,a;4;c2v^2;p b 21 m;p -2 -2b", "26:a-cb;26.6;a,-c,b;4;c2v^2;p m 21 b;p -2b -2", "27;27.1;;4;c2v^3;p c c 2;p 2 -2c", "27:cab;27.2;c,a,b;4;c2v^3;p 2 a a;p -2a 2", "27:bca;27.3;b,c,a;4;c2v^3;p b 2 b;p -2b -2b", "28;28.1;;4;c2v^4;p m a 2;p 2 -2a", "28*;28.1;;4;c2v^4;p m a 2*;p 2 -21", "28:ba-c;28.2;b,a,-c;4;c2v^4;p b m 2;p 2 -2b", "28:cab;28.3;c,a,b;4;c2v^4;p 2 m b;p -2b 2", "28:-cba;28.4;-c,b,a;4;c2v^4;p 2 c m;p -2c 2", "28:-cba*;28.4;-c,b,a;4;c2v^4;p 2 c m*;p -21 2", "28:bca;28.5;b,c,a;4;c2v^4;p c 2 m;p -2c -2c", "28:a-cb;28.6;a,-c,b;4;c2v^4;p m 2 a;p -2a -2a", "29;29.1;;4;c2v^5;p c a 21;p 2c -2ac", "29:ba-c;29.2;b,a,-c;4;c2v^5;p b c 21;p 2c -2b", "29:cab;29.3;c,a,b;4;c2v^5;p 21 a b;p -2b 2a", "29:-cba;29.4;-c,b,a;4;c2v^5;p 21 c a;p -2ac 2a", "29:bca;29.5;b,c,a;4;c2v^5;p c 21 b;p -2bc -2c", "29:a-cb;29.6;a,-c,b;4;c2v^5;p b 21 a;p -2a -2ab", "30;30.1;;4;c2v^6;p n c 2;p 2 -2bc", "30:ba-c;30.2;b,a,-c;4;c2v^6;p c n 2;p 2 -2ac", "30:cab;30.3;c,a,b;4;c2v^6;p 2 n a;p -2ac 2", "30:-cba;30.4;-c,b,a;4;c2v^6;p 2 a n;p -2ab 2", "30:bca;30.5;b,c,a;4;c2v^6;p b 2 n;p -2ab -2ab", "30:a-cb;30.6;a,-c,b;4;c2v^6;p n 2 b;p -2bc -2bc", "31;31.1;;4;c2v^7;p m n 21;p 2ac -2", "31:ba-c;31.2;b,a,-c;4;c2v^7;p n m 21;p 2bc -2bc", "31:cab;31.3;c,a,b;4;c2v^7;p 21 m n;p -2ab 2ab", "31:-cba;31.4;-c,b,a;4;c2v^7;p 21 n m;p -2 2ac", "31:bca;31.5;b,c,a;4;c2v^7;p n 21 m;p -2 -2bc", "31:a-cb;31.6;a,-c,b;4;c2v^7;p m 21 n;p -2ab -2", "32;32.1;;4;c2v^8;p b a 2;p 2 -2ab", "32:cab;32.2;c,a,b;4;c2v^8;p 2 c b;p -2bc 2", "32:bca;32.3;b,c,a;4;c2v^8;p c 2 a;p -2ac -2ac", "33;33.1;;4;c2v^9;p n a 21;p 2c -2n", "33*;33.1;;4;c2v^9;p n a 21*;p 21 -2n", "33:ba-c;33.2;b,a,-c;4;c2v^9;p b n 21;p 2c -2ab", "33:ba-c*;33.2;b,a,-c;4;c2v^9;p b n 21*;p 21 -2ab", "33:cab;33.3;c,a,b;4;c2v^9;p 21 n b;p -2bc 2a", "33:cab*;33.3;c,a,b;4;c2v^9;p 21 n b*;p -2bc 21", "33:-cba;33.4;-c,b,a;4;c2v^9;p 21 c n;p -2n 2a", "33:-cba*;33.4;-c,b,a;4;c2v^9;p 21 c n*;p -2n 21", "33:bca;33.5;b,c,a;4;c2v^9;p c 21 n;p -2n -2ac", "33:a-cb;33.6;a,-c,b;4;c2v^9;p n 21 a;p -2ac -2n", "34;34.1;;4;c2v^10;p n n 2;p 2 -2n", "34:cab;34.2;c,a,b;4;c2v^10;p 2 n n;p -2n 2", "34:bca;34.3;b,c,a;4;c2v^10;p n 2 n;p -2n -2n", "35;35.1;;8;c2v^11;c m m 2;c 2 -2", "35:cab;35.2;c,a,b;8;c2v^11;a 2 m m;a -2 2", "35:bca;35.3;b,c,a;8;c2v^11;b m 2 m;b -2 -2", "36;36.1;;8;c2v^12;c m c 21;c 2c -2", "36*;36.1;;8;c2v^12;c m c 21*;c 21 -2", "36:ba-c;36.2;b,a,-c;8;c2v^12;c c m 21;c 2c -2c", "36:ba-c*;36.2;b,a,-c;8;c2v^12;c c m 21*;c 21 -2c", "36:cab;36.3;c,a,b;8;c2v^12;a 21 m a;a -2a 2a", "36:cab*;36.3;c,a,b;8;c2v^12;a 21 m a*;a -2a 21", "36:-cba;36.4;-c,b,a;8;c2v^12;a 21 a m;a -2 2a", "36:-cba*;36.4;-c,b,a;8;c2v^12;a 21 a m*;a -2 21", "36:bca;36.5;b,c,a;8;c2v^12;b b 21 m;b -2 -2b", "36:a-cb;36.6;a,-c,b;8;c2v^12;b m 21 b;b -2b -2", "37;37.1;;8;c2v^13;c c c 2;c 2 -2c", "37:cab;37.2;c,a,b;8;c2v^13;a 2 a a;a -2a 2", "37:bca;37.3;b,c,a;8;c2v^13;b b 2 b;b -2b -2b", "38;38.1;;8;c2v^14;a m m 2;a 2 -2", "38:ba-c;38.2;b,a,-c;8;c2v^14;b m m 2;b 2 -2", "38:cab;38.3;c,a,b;8;c2v^14;b 2 m m;b -2 2", "38:-cba;38.4;-c,b,a;8;c2v^14;c 2 m m;c -2 2", "38:bca;38.5;b,c,a;8;c2v^14;c m 2 m;c -2 -2", "38:a-cb;38.6;a,-c,b;8;c2v^14;a m 2 m;a -2 -2", "39;39.1;;8;c2v^15;a e m 2;a 2 -2b", "39;39.1;;8;c2v^15;a b m 2;a 2 -2b", "39:ba-c;39.2;b,a,-c;8;c2v^15;b m e 2;b 2 -2a", "39:ba-c;39.2;b,a,-c;8;c2v^15;b m a 2;b 2 -2a", "39:cab;39.3;c,a,b;8;c2v^15;b 2 e m;b -2a 2", "39:cab;39.3;c,a,b;8;c2v^15;b 2 c m;b -2a 2", "39:-cba;39.4;-c,b,a;8;c2v^15;c 2 m e;c -2a 2", "39:-cba;39.4;-c,b,a;8;c2v^15;c 2 m b;c -2a 2", "39:bca;39.5;b,c,a;8;c2v^15;c m 2 e;c -2a -2a", "39:bca;39.5;b,c,a;8;c2v^15;c m 2 a;c -2a -2a", "39:a-cb;39.6;a,-c,b;8;c2v^15;a e 2 m;a -2b -2b", "39:a-cb;39.6;a,-c,b;8;c2v^15;a c 2 m;a -2b -2b", "40;40.1;;8;c2v^16;a m a 2;a 2 -2a", "40:ba-c;40.2;b,a,-c;8;c2v^16;b b m 2;b 2 -2b", "40:cab;40.3;c,a,b;8;c2v^16;b 2 m b;b -2b 2", "40:-cba;40.4;-c,b,a;8;c2v^16;c 2 c m;c -2c 2", "40:bca;40.5;b,c,a;8;c2v^16;c c 2 m;c -2c -2c", "40:a-cb;40.6;a,-c,b;8;c2v^16;a m 2 a;a -2a -2a", "41;41.1;;8;c2v^17;a e a 2;a 2 -2ab", "41;41.1;;8;c2v^17;a b a 2;a 2 -2ab", "41:ba-c;41.2;b,a,-c;8;c2v^17;b b e 2;b 2 -2ab", "41:ba-c;41.2;b,a,-c;8;c2v^17;b b a 2;b 2 -2ab", "41:cab;41.3;c,a,b;8;c2v^17;b 2 e b;b -2ab 2", "41:cab;41.3;c,a,b;8;c2v^17;b 2 c b;b -2ab 2", "41:-cba;41.4;-c,b,a;8;c2v^17;c 2 c e;c -2ac 2", "41:-cba;41.4;-c,b,a;8;c2v^17;c 2 c b;c -2ac 2", "41:bca;41.5;b,c,a;8;c2v^17;c c 2 e;c -2ac -2ac", "41:bca;41.5;b,c,a;8;c2v^17;c c 2 a;c -2ac -2ac", "41:a-cb;41.6;a,-c,b;8;c2v^17;a e 2 a;a -2ab -2ab", "41:a-cb;41.6;a,-c,b;8;c2v^17;a c 2 a;a -2ab -2ab", "42;42.1;;16;c2v^18;f m m 2;f 2 -2", "42:cab;42.2;c,a,b;16;c2v^18;f 2 m m;f -2 2", "42:bca;42.3;b,c,a;16;c2v^18;f m 2 m;f -2 -2", "43;43.1;;16;c2v^19;f d d 2;f 2 -2d", "43:cab;43.2;c,a,b;16;c2v^19;f 2 d d;f -2d 2", "43:bca;43.3;b,c,a;16;c2v^19;f d 2 d;f -2d -2d", "44;44.1;;8;c2v^20;i m m 2;i 2 -2", "44:cab;44.2;c,a,b;8;c2v^20;i 2 m m;i -2 2", "44:bca;44.3;b,c,a;8;c2v^20;i m 2 m;i -2 -2", "45;45.1;;8;c2v^21;i b a 2;i 2 -2c", "45:cab;45.2;c,a,b;8;c2v^21;i 2 c b;i -2a 2", "45:bca;45.3;b,c,a;8;c2v^21;i c 2 a;i -2b -2b", "46;46.1;;8;c2v^22;i m a 2;i 2 -2a", "46:ba-c;46.2;b,a,-c;8;c2v^22;i b m 2;i 2 -2b", "46:cab;46.3;c,a,b;8;c2v^22;i 2 m b;i -2b 2", "46:-cba;46.4;-c,b,a;8;c2v^22;i 2 c m;i -2c 2", "46:bca;46.5;b,c,a;8;c2v^22;i c 2 m;i -2c -2c", "46:a-cb;46.6;a,-c,b;8;c2v^22;i m 2 a;i -2a -2a", "47;47.1;;8;d2h^1;p m m m;-p 2 2", "48:2;48.1;;8;d2h^2;p n n n :2;-p 2ab 2bc", "48:1;48.2;a,b,c|1/4,1/4,1/4;8;d2h^2;p n n n :1;p 2 2 -1n", "49;49.1;;8;d2h^3;p c c m;-p 2 2c", "49:cab;49.2;c,a,b;8;d2h^3;p m a a;-p 2a 2", "49:bca;49.3;b,c,a;8;d2h^3;p b m b;-p 2b 2b", "50:2;50.1;;8;d2h^4;p b a n :2;-p 2ab 2b", "50:2cab;50.2;c,a,b;8;d2h^4;p n c b :2;-p 2b 2bc", "50:2bca;50.3;b,c,a;8;d2h^4;p c n a :2;-p 2a 2c", "50:1;50.4;a,b,c|1/4,1/4,0;8;d2h^4;p b a n :1;p 2 2 -1ab", "50:1cab;50.5;c,a,b|1/4,1/4,0;8;d2h^4;p n c b :1;p 2 2 -1bc", "50:1bca;50.6;b,c,a|1/4,1/4,0;8;d2h^4;p c n a :1;p 2 2 -1ac", "51;51.1;;8;d2h^5;p m m a;-p 2a 2a", "51:ba-c;51.2;b,a,-c;8;d2h^5;p m m b;-p 2b 2", "51:cab;51.3;c,a,b;8;d2h^5;p b m m;-p 2 2b", "51:-cba;51.4;-c,b,a;8;d2h^5;p c m m;-p 2c 2c", "51:bca;51.5;b,c,a;8;d2h^5;p m c m;-p 2c 2", "51:a-cb;51.6;a,-c,b;8;d2h^5;p m a m;-p 2 2a", "52;52.1;;8;d2h^6;p n n a;-p 2a 2bc", "52:ba-c;52.2;b,a,-c;8;d2h^6;p n n b;-p 2b 2n", "52:cab;52.3;c,a,b;8;d2h^6;p b n n;-p 2n 2b", "52:-cba;52.4;-c,b,a;8;d2h^6;p c n n;-p 2ab 2c", "52:bca;52.5;b,c,a;8;d2h^6;p n c n;-p 2ab 2n", "52:a-cb;52.6;a,-c,b;8;d2h^6;p n a n;-p 2n 2bc", "53;53.1;;8;d2h^7;p m n a;-p 2ac 2", "53:ba-c;53.2;b,a,-c;8;d2h^7;p n m b;-p 2bc 2bc", "53:cab;53.3;c,a,b;8;d2h^7;p b m n;-p 2ab 2ab", "53:-cba;53.4;-c,b,a;8;d2h^7;p c n m;-p 2 2ac", "53:bca;53.5;b,c,a;8;d2h^7;p n c m;-p 2 2bc", "53:a-cb;53.6;a,-c,b;8;d2h^7;p m a n;-p 2ab 2", "54;54.1;;8;d2h^8;p c c a;-p 2a 2ac", "54:ba-c;54.2;b,a,-c;8;d2h^8;p c c b;-p 2b 2c", "54:cab;54.3;c,a,b;8;d2h^8;p b a a;-p 2a 2b", "54:-cba;54.4;-c,b,a;8;d2h^8;p c a a;-p 2ac 2c", "54:bca;54.5;b,c,a;8;d2h^8;p b c b;-p 2bc 2b", "54:a-cb;54.6;a,-c,b;8;d2h^8;p b a b;-p 2b 2ab", "55;55.1;;8;d2h^9;p b a m;-p 2 2ab", "55:cab;55.2;c,a,b;8;d2h^9;p m c b;-p 2bc 2", "55:bca;55.3;b,c,a;8;d2h^9;p c m a;-p 2ac 2ac", "56;56.1;;8;d2h^10;p c c n;-p 2ab 2ac", "56:cab;56.2;c,a,b;8;d2h^10;p n a a;-p 2ac 2bc", "56:bca;56.3;b,c,a;8;d2h^10;p b n b;-p 2bc 2ab", "57;57.1;;8;d2h^11;p b c m;-p 2c 2b", "57:ba-c;57.2;b,a,-c;8;d2h^11;p c a m;-p 2c 2ac", "57:cab;57.3;c,a,b;8;d2h^11;p m c a;-p 2ac 2a", "57:-cba;57.4;-c,b,a;8;d2h^11;p m a b;-p 2b 2a", "57:bca;57.5;b,c,a;8;d2h^11;p b m a;-p 2a 2ab", "57:a-cb;57.6;a,-c,b;8;d2h^11;p c m b;-p 2bc 2c", "58;58.1;;8;d2h^12;p n n m;-p 2 2n", "58:cab;58.2;c,a,b;8;d2h^12;p m n n;-p 2n 2", "58:bca;58.3;b,c,a;8;d2h^12;p n m n;-p 2n 2n", "59:2;59.1;;8;d2h^13;p m m n :2;-p 2ab 2a", "59:2cab;59.2;c,a,b;8;d2h^13;p n m m :2;-p 2c 2bc", "59:2bca;59.3;b,c,a;8;d2h^13;p m n m :2;-p 2c 2a", "59:1;59.4;a,b,c|1/4,1/4,0;8;d2h^13;p m m n :1;p 2 2ab -1ab", "59:1cab;59.5;c,a,b|1/4,1/4,0;8;d2h^13;p n m m :1;p 2bc 2 -1bc", "59:1bca;59.6;b,c,a|1/4,1/4,0;8;d2h^13;p m n m :1;p 2ac 2ac -1ac", "60;60.1;;8;d2h^14;p b c n;-p 2n 2ab", "60:ba-c;60.2;b,a,-c;8;d2h^14;p c a n;-p 2n 2c", "60:cab;60.3;c,a,b;8;d2h^14;p n c a;-p 2a 2n", "60:-cba;60.4;-c,b,a;8;d2h^14;p n a b;-p 2bc 2n", "60:bca;60.5;b,c,a;8;d2h^14;p b n a;-p 2ac 2b", "60:a-cb;60.6;a,-c,b;8;d2h^14;p c n b;-p 2b 2ac", "61;61.1;;8;d2h^15;p b c a;-p 2ac 2ab", "61:ba-c;61.2;b,a,-c;8;d2h^15;p c a b;-p 2bc 2ac", "62;62.1;;8;d2h^16;p n m a;-p 2ac 2n", "62:ba-c;62.2;b,a,-c;8;d2h^16;p m n b;-p 2bc 2a", "62:cab;62.3;c,a,b;8;d2h^16;p b n m;-p 2c 2ab", "62:-cba;62.4;-c,b,a;8;d2h^16;p c m n;-p 2n 2ac", "62:bca;62.5;b,c,a;8;d2h^16;p m c n;-p 2n 2a", "62:a-cb;62.6;a,-c,b;8;d2h^16;p n a m;-p 2c 2n", "63;63.1;;16;d2h^17;c m c m;-c 2c 2", "63:ba-c;63.2;b,a,-c;16;d2h^17;c c m m;-c 2c 2c", "63:cab;63.3;c,a,b;16;d2h^17;a m m a;-a 2a 2a", "63:-cba;63.4;-c,b,a;16;d2h^17;a m a m;-a 2 2a", "63:bca;63.5;b,c,a;16;d2h^17;b b m m;-b 2 2b", "63:a-cb;63.6;a,-c,b;16;d2h^17;b m m b;-b 2b 2", "64;64.1;;16;d2h^18;c m c e;-c 2ac 2", "64;64.1;;16;d2h^18;c m c a;-c 2ac 2", "64:ba-c;64.2;b,a,-c;16;d2h^18;c c m e;-c 2ac 2ac", "64:ba-c;64.2;b,a,-c;16;d2h^18;c c m b;-c 2ac 2ac", "64:cab;64.3;c,a,b;16;d2h^18;a e m a;-a 2ab 2ab", "64:cab;64.3;c,a,b;16;d2h^18;a b m a;-a 2ab 2ab", "64:-cba;64.4;-c,b,a;16;d2h^18;a e a m;-a 2 2ab", "64:-cba;64.4;-c,b,a;16;d2h^18;a c a m;-a 2 2ab", "64:bca;64.5;b,c,a;16;d2h^18;b b e m;-b 2 2ab", "64:bca;64.5;b,c,a;16;d2h^18;b b c m;-b 2 2ab", "64:a-cb;64.6;a,-c,b;16;d2h^18;b m e b;-b 2ab 2", "64:a-cb;64.6;a,-c,b;16;d2h^18;b m a b;-b 2ab 2", "65;65.1;;16;d2h^19;c m m m;-c 2 2", "65:cab;65.2;c,a,b;16;d2h^19;a m m m;-a 2 2", "65:bca;65.3;b,c,a;16;d2h^19;b m m m;-b 2 2", "66;66.1;;16;d2h^20;c c c m;-c 2 2c", "66:cab;66.2;c,a,b;16;d2h^20;a m a a;-a 2a 2", "66:bca;66.3;b,c,a;16;d2h^20;b b m b;-b 2b 2b", "67;67.1;;16;d2h^21;c m m e;-c 2a 2", "67;67.1;;16;d2h^21;c m m a;-c 2a 2", "67:ba-c;67.2;b,a,-c;16;d2h^21;c m m b;-c 2a 2a", "67:cab;67.3;c,a,b;16;d2h^21;a b m m;-a 2b 2b", "67:-cba;67.4;-c,b,a;16;d2h^21;a c m m;-a 2 2b", "67:bca;67.5;b,c,a;16;d2h^21;b m c m;-b 2 2a", "67:a-cb;67.6;a,-c,b;16;d2h^21;b m a m;-b 2a 2", "68:2;68.1;;16;d2h^22;c c c e :2;-c 2a 2ac", "68:2;68.1;;16;d2h^22;c c c a :2;-c 2a 2ac", "68:2ba-c;68.2;b,a,-c;16;d2h^22;c c c b :2;-c 2a 2c", "68:2cab;68.3;c,a,b;16;d2h^22;a b a a :2;-a 2a 2b", "68:2-cba;68.4;-c,b,a;16;d2h^22;a c a a :2;-a 2ab 2b", "68:2bca;68.5;b,c,a;16;d2h^22;b b c b :2;-b 2ab 2b", "68:2a-cb;68.6;a,-c,b;16;d2h^22;b b a b :2;-b 2b 2ab", "68:1;68.7;a,b,c|0,1/4,1/4;16;d2h^22;c c c e :1;c 2 2 -1ac", "68:1;68.7;a,b,c|0,1/4,1/4;16;d2h^22;c c c a :1;c 2 2 -1ac", "68:1ba-c;68.8;b,a,-c|0,1/4,1/4;16;d2h^22;c c c b :1;c 2 2 -1ac", "68:1cab;68.9;c,a,b|0,1/4,1/4;16;d2h^22;a b a a :1;a 2 2 -1ab", "68:1-cba;68.10;-c,b,a|0,1/4,1/4;16;d2h^22;a c a a :1;a 2 2 -1ab", "68:1bca;68.11;b,c,a|0,1/4,1/4;16;d2h^22;b b c b :1;b 2 2 -1ab", "68:1a-cb;68.12;a,-c,b|0,1/4,1/4;16;d2h^22;b b a b :1;b 2 2 -1ab", "69;69.1;;32;d2h^23;f m m m;-f 2 2", "70:2;70.1;;32;d2h^24;f d d d :2;-f 2uv 2vw", "70:1;70.2;a,b,c|-1/8,-1/8,-1/8;32;d2h^24;f d d d :1;f 2 2 -1d", "71;71.1;;16;d2h^25;i m m m;-i 2 2", "72;72.1;;16;d2h^26;i b a m;-i 2 2c", "72:cab;72.2;c,a,b;16;d2h^26;i m c b;-i 2a 2", "72:bca;72.3;b,c,a;16;d2h^26;i c m a;-i 2b 2b", "73;73.1;;16;d2h^27;i b c a;-i 2b 2c", "73:ba-c;73.2;b,a,-c;16;d2h^27;i c a b;-i 2a 2b", "74;74.1;;16;d2h^28;i m m a;-i 2b 2", "74:ba-c;74.2;b,a,-c;16;d2h^28;i m m b;-i 2a 2a", "74:cab;74.3;c,a,b;16;d2h^28;i b m m;-i 2c 2c", "74:-cba;74.4;-c,b,a;16;d2h^28;i c m m;-i 2 2b", "74:bca;74.5;b,c,a;16;d2h^28;i m c m;-i 2 2a", "74:a-cb;74.6;a,-c,b;16;d2h^28;i m a m;-i 2c 2", "75;75.1;;4;c4^1;p 4;p 4", "75:c;75.2;ab;8;c4^1;c 4;c 4", "76;76.1;;4;c4^2;p 41;p 4w", "76*;76.1;;4;c4^2;p 41*;p 41", "76:c;76.2;ab;8;c4^2;c 41;c 4w", "77;77.1;;4;c4^3;p 42;p 4c", "77*;77.1;;4;c4^3;p 42*;p 42", "77:c;77.2;ab;8;c4^3;c 42;c 4c", "78;78.1;;4;c4^4;p 43;p 4cw", "78*;78.1;;4;c4^4;p 43*;p 43", "78:c;78.2;ab;8;c4^4;c 43;c 4cw", "79;79.1;;8;c4^5;i 4;i 4", "79:f;79.2;ab;16;c4^5;f 4;f 4", "80;80.1;;8;c4^6;i 41;i 4bw", "80:f;80.2;ab;16;c4^6;f 41;xyz", "81;81.1;;4;s4^1;p -4;p -4", "81:c;81.2;ab;8;s4^1;c -4;c -4", "82;82.1;;8;s4^2;i -4;i -4", "82:f;82.2;ab;16;s4^2;f -4;f -4", "83;83.1;;8;c4h^1;p 4/m;-p 4", "83:f;83.2;ab;16;c4h^1;c 4/m;-c 4", "84;84.1;;8;c4h^2;p 42/m;-p 4c", "84*;84.1;;8;c4h^2;p 42/m*;-p 42", "84:c;84.2;ab;16;c4h^2;c 42/m;-c 4c", "85:2;85.1;;8;c4h^3;p 4/n :2;-p 4a", "85:c2;85.2;ab;16;c4h^3;c 4/e :2;xyz", "85:1;85.3;a,b,c|-1/4,1/4,0;8;c4h^3;p 4/n :1;p 4ab -1ab", "85:c1;85.4;ab|-1/4,1/4,0;16;c4h^3;c 4/e :1;xyz", "86:2;86.1;;8;c4h^4;p 42/n :2;-p 4bc", "86:1;86.3;a,b,c|-1/4,-1/4,-1/4;8;c4h^4;p 42/n :1;p 4n -1n", "86:c1;86.4;ab|-1/4,-1/4,-1/4;16;c4h^4;c 42/e :1;xyz", "86:c2;86.2;ab;16;c4h^4;c 42/e :2;xyz", "87;87.1;;16;c4h^5;i 4/m;-i 4", "87:f;87.2;ab;32;c4h^5;f 4/m;xyz", "88:2;88.1;;16;c4h^6;i 41/a :2;-i 4ad", "88:f2;88.2;ab;32;c4h^6;f 41/d :2;xyz", "88:1;88.3;a,b,c|0,-1/4,-1/8;16;c4h^6;i 41/a :1;i 4bw -1bw", "88:f1;88.4;ab|0,-1/4,-1/8;32;c4h^6;f 41/d :1;xyz", "89;89.1;;8;d4^1;p 4 2 2;p 4 2", "89:c;89.2;ab;16;d4^1;c 4 2 2;xyz", "90;90.1;;8;d4^2;p 4 21 2;p 4ab 2ab", "90:c;90.2;ab;16;d4^2;c 4 2 21;xyz", "91;91.1;;8;d4^3;p 41 2 2;p 4w 2c", "91*;91.1;;8;d4^3;p 41 2 2*;p 41 2c", "91:c;91.2;ab;16;d4^3;c 41 2 2;xyz", "92;92.1;;8;d4^4;p 41 21 2;p 4abw 2nw", "92:c;92.2;ab;16;d4^4;c 41 2 21;xyz", "93;93.1;;8;d4^5;p 42 2 2;p 4c 2", "93*;93.1;;8;d4^5;p 42 2 2*;p 42 2", "93:c;93.2;ab;16;d4^5;c 42 2 2;xyz", "94;94.1;;8;d4^6;p 42 21 2;p 4n 2n", "94:c;94.2;ab;16;d4^6;c 42 2 21;xyz", "95;95.1;;8;d4^7;p 43 2 2;p 4cw 2c", "95*;95.1;;8;d4^7;p 43 2 2*;p 43 2c", "95:c;95.2;ab;16;d4^7;c 43 2 2;xyz", "96;96.1;;8;d4^8;p 43 21 2;p 4nw 2abw", "96:c;96.2;ab;16;d4^8;c 43 2 21;xyz", "97;97.1;;16;d4^9;i 4 2 2;i 4 2", "97:f;97.2;ab;32;d4^9;f 4 2 2;f 4 2", "98;98.1;;16;d4^10;i 41 2 2;i 4bw 2bw", "98:f;98.2;ab;32;d4^10;f 41 2 2;xyz", "99;99.1;;8;c4v^1;p 4 m m;p 4 -2", "99:c;99.2;ab;16;c4v^1;c 4 m m;c 4 -2", "100;100.1;;8;c4v^2;p 4 b m;p 4 -2ab", "100:c;100.2;ab;16;c4v^2;c 4 m g1;xyz", "101;101.1;;8;c4v^3;p 42 c m;p 4c -2c", "101*;101.1;;8;c4v^3;p 42 c m*;p 42 -2c", "101:c;101.2;ab;16;c4v^3;c 42 m c;xyz", "102;102.1;;8;c4v^4;p 42 n m;p 4n -2n", "102:c;102.2;ab;16;c4v^4;c 42 m g2;xyz", "103;103.1;;8;c4v^5;p 4 c c;p 4 -2c", "103:c;103.2;ab;16;c4v^5;c 4 c c;c 4 -2c", "104;104.1;;8;c4v^6;p 4 n c;p 4 -2n", "104:c;104.2;ab;16;c4v^6;c 4 c g2;xyz", "105;105.1;;8;c4v^7;p 42 m c;p 4c -2", "105*;105.1;;8;c4v^7;p 42 m c*;p 42 -2", "105:c;105.2;ab;16;c4v^7;c 42 c m;xyz", "106;106.1;;8;c4v^8;p 42 b c;p 4c -2ab", "106*;106.1;;8;c4v^8;p 42 b c*;p 42 -2ab", "106:c;106.2;ab;16;c4v^8;c 42 c g1;xyz", "107;107.1;;16;c4v^9;i 4 m m;i 4 -2", "107:f;107.2;ab;32;c4v^9;f 4 m m;f 4 -2", "108;108.1;;16;c4v^10;i 4 c m;i 4 -2c", "108:f;108.2;ab;32;c4v^10;f 4 m c;xyz", "109;109.1;;16;c4v^11;i 41 m d;i 4bw -2", "109:f;109.2;ab;32;c4v^11;f 41 d m;xyz", "110;110.1;;16;c4v^12;i 41 c d;i 4bw -2c", "110:f;110.2;ab;32;c4v^12;f 41 d c;xyz", "111;111.1;;8;d2d^1;p -4 2 m;p -4 2", "111:c;111.2;ab;16;d2d^1;c -4 m 2;xyz", "112;112.1;;8;d2d^2;p -4 2 c;p -4 2c", "112:c;112.2;ab;16;d2d^2;c -4 c 2;xyz", "113;113.1;;8;d2d^3;p -4 21 m;p -4 2ab", "113:c;113.2;ab;16;d2d^3;c -4 m 21;xyz", "114;114.1;;8;d2d^4;p -4 21 c;p -4 2n", "114:c;114.2;ab;16;d2d^4;c -4 c 21;xyz", "115;115.1;;8;d2d^5;p -4 m 2;p -4 -2", "115:c;115.2;ab;16;d2d^5;c -4 2 m;xyz", "116;116.1;;8;d2d^6;p -4 c 2;p -4 -2c", "116:c;116.2;ab;16;d2d^6;c -4 2 c;xyz", "117;117.1;;8;d2d^7;p -4 b 2;p -4 -2ab", "117:c;117.2;ab;16;d2d^7;c -4 2 g1;xyz", "118;118.1;;8;d2d^8;p -4 n 2;p -4 -2n", "118:c;118.2;ab;16;d2d^8;c -4 2 g2;xyz", "119;119.1;;16;d2d^9;i -4 m 2;i -4 -2", "119:f;119.2;ab;32;d2d^9;f -4 2 m;xyz", "120;120.1;;16;d2d^10;i -4 c 2;i -4 -2c", "120:f;120.2;ab;32;d2d^10;f -4 2 c;xyz", "121;121.1;;16;d2d^11;i -4 2 m;i -4 2", "121:f;121.2;ab;32;d2d^11;f -4 m 2;xyz", "122;122.1;;16;d2d^12;i -4 2 d;i -4 2bw", "122:f;122.2;ab;32;d2d^12;f -4 d 2;xyz", "123;123.1;;16;d4h^1;p 4/m m m;-p 4 2", "123:c;123.2;ab;32;d4h^1;c 4/m m m;xyz", "124;124.1;;16;d4h^2;p 4/m c c;-p 4 2c", "124:c;124.2;ab;32;d4h^2;c 4/m c c;xyz", "125:2;125.1;;16;d4h^3;p 4/n b m :2;-p 4a 2b", "125:c2;125.2;ab;32;d4h^3;c 4/e m g1 :2;xyz", "125:1;125.3;a,b,c|-1/4,-1/4,0;16;d4h^3;p 4/n b m :1;p 4 2 -1ab", "125:c1;125.4;ab|-1/4,-1/4,0;32;d4h^3;c 4/e m g1 :1;xyz", "126:2;126.1;;16;d4h^4;p 4/n n c :2;-p 4a 2bc", "126:c1;126.2;ab;32;d4h^4;c 4/e c g2 :2;xyz", "126:1;126.3;a,b,c|-1/4,-1/4,-1/4;16;d4h^4;p 4/n n c :1;p 4 2 -1n", "126:c4;126.4;ab|-1/4,-1/4,-1/4;32;d4h^4;c 4/e c g2 :1;xyz", "127;127.1;;16;d4h^5;p 4/m b m;-p 4 2ab", "127:c;127.2;ab;32;d4h^5;c 4/m m g1;xyz", "128;128.1;;16;d4h^6;p 4/m n c;-p 4 2n", "128:c;128.2;a+b,-a+b,c;32;d4h^6;c 4/m c g2;xyz", "129:2;129.1;;16;d4h^7;p 4/n m m :2;-p 4a 2a", "129:c2;129.2;ab;32;d4h^7;c 4/e m m :2;xyz", "129:1;129.3;a,b,c|-1/4,1/4,0;16;d4h^7;p 4/n m m :1;p 4ab 2ab -1ab", "129:c1;129.4;ab|-1/4,1/4,0;32;d4h^7;c 4/e m m :1;xyz", "130:2;130.1;;16;d4h^8;p 4/n c c :2;-p 4a 2ac", "130:c2;130.2;ab;32;d4h^8;c 4/e c c :2;xyz", "130:1;130.3;a,b,c|-1/4,1/4,0;16;d4h^8;p 4/n c c :1;p 4ab 2n -1ab", "130:c1;130.4;ab|-1/4,1/4,0;32;d4h^8;c 4/e c c :1;xyz", "131;131.1;;16;d4h^9;p 42/m m c;-p 4c 2", "131:c;131.2;ab;32;d4h^9;c 42/m c m;xyz", "132;132.1;;16;d4h^10;p 42/m c m;-p 4c 2c", "132:c;132.2;ab;32;d4h^10;c 42/m m c;xyz", "133:2;133.1;;16;d4h^11;p 42/n b c :2;-p 4ac 2b", "133:c1;133.2;ab;32;d4h^11;c 42/e c g1 :2;xyz", "133:1;133.3;a,b,c|-1/4,1/4,-1/4;16;d4h^11;p 42/n b c :1;p 4n 2c -1n", "133:c2;133.4;ab|-1/4,1/4,-1/4;32;d4h^11;c 42/e c g1 :1;xyz", "134:2;134.1;;16;d4h^12;p 42/n n m :2;-p 4ac 2bc", "134:c2;134.2;ab;32;d4h^12;c 42/e m g2 :2;xyz", "134:1;134.3;a,b,c|-1/4,1/4,-1/4;16;d4h^12;p 42/n n m :1;p 4n 2 -1n", "134:c1;134.4;ab|-1/4,1/4,-1/4;32;d4h^12;c 42/e m g2 :1;xyz", "135;135.1;;16;d4h^13;p 42/m b c;-p 4c 2ab", "135*;135.1;;16;d4h^13;p 42/m b c*;-p 42 2ab", "135:c;135.2;ab;32;d4h^13;c 42/m c g1;xyz", "136;136.1;;16;d4h^14;p 42/m n m;-p 4n 2n", "136:c;136.2;ab;32;d4h^14;c 42/m m g2;xyz", "137:2;137.1;;16;d4h^15;p 42/n m c :2;-p 4ac 2a", "137:c1;137.2;ab;32;d4h^15;c 42/e c m :2;xyz", "137:1;137.3;a,b,c|-1/4,1/4,-1/4;16;d4h^15;p 42/n m c :1;p 4n 2n -1n", "137:c2;137.4;ab|-1/4,1/4,-1/4;32;d4h^15;c 42/e c m :1;xyz", "138:2;138.1;;16;d4h^16;p 42/n c m :2;-p 4ac 2ac", "138:c2;138.2;ab;32;d4h^16;c 42/e m c :2;xyz", "138:1;138.3;a,b,c|-1/4,1/4,-1/4;16;d4h^16;p 42/n c m :1;p 4n 2ab -1n", "138:c1;138.4;ab|-1/4,1/4,-1/4;32;d4h^16;c 42/e m c :1;xyz", "139;139.1;;32;d4h^17;i 4/m m m;-i 4 2", "139:f;139.2;ab;64;d4h^17;f 4/m m m;xyz", "140;140.1;;32;d4h^18;i 4/m c m;-i 4 2c", "140:f;140.2;ab;64;d4h^18;f 4/m m c;xyz", "141:2;141.1;;32;d4h^19;i 41/a m d :2;-i 4bd 2", "141:f2;141.2;ab;64;d4h^19;f 41/d d m :2;xyz", "141:1;141.3;a,b,c|0,1/4,-1/8;32;d4h^19;i 41/a m d :1;i 4bw 2bw -1bw", "141:f1;141.4;ab|0,1/4,-1/8;64;d4h^19;f 41/d d m :1;xyz", "142:2;142.1;;32;d4h^20;i 41/a c d :2;-i 4bd 2c", "142:f2;142.2;ab;64;d4h^20;f 41/d d c :2;xyz", "142:1;142.3;a,b,c|0,1/4,-1/8;32;d4h^20;i 41/a c d :1;i 4bw 2aw -1bw", "142:f1;142.4;ab|0,1/4,-1/8;64;d4h^20;f 41/d d c :1;xyz", "143;143.1;;3;c3^1;p 3;p 3", "144;144.1;;3;c3^2;p 31;p 31", "145;145.1;;3;c3^3;p 32;p 32", "146:h;146.1;;9;c3^4;r 3 :h;r 3", "146:r;146.2;r;3;c3^4;r 3 :r;p 3*", "147;147.1;;6;c3i^1;p -3;-p 3", "148:h;148.1;;18;c3i^2;r -3 :h;-r 3", "148:r;148.2;r;6;c3i^2;r -3 :r;-p 3*", "149;149.1;;6;d3^1;p 3 1 2;p 3 2", "150;150.1;;6;d3^2;p 3 2 1;p 3 2\"", "151;151.1;;6;d3^3;p 31 1 2;p 31 2 (0 0 4)", "152;152.1;;6;d3^4;p 31 2 1;p 31 2\"", "152:_2;152:a,b,c|0,0,-1/3;a,b,c|0,0,-1/3;6;d3^4;p 31 2 1;p 31 2\" (0 0 -4)", "153;153.1;;6;d3^5;p 32 1 2;p 32 2 (0 0 2)", "154;154.1;;6;d3^6;p 32 2 1;p 32 2\"", "154:_2;154:a,b,c|0,0,-1/3;a,b,c|0,0,-1/3;6;d3^6;p 32 2 1;p 32 2\" (0 0 4)", "155:h;155.1;;18;d3^7;r 3 2 :h;r 3 2\"", "155:r;155.2;r;6;d3^7;r 3 2 :r;p 3* 2", "156;156.1;;6;c3v^1;p 3 m 1;p 3 -2\"", "157;157.1;;6;c3v^2;p 3 1 m;p 3 -2", "158;158.1;;6;c3v^3;p 3 c 1;p 3 -2\"c", "159;159.1;;6;c3v^4;p 3 1 c;p 3 -2c", "160:h;160.1;;18;c3v^5;r 3 m :h;r 3 -2\"", "160:r;160.2;r;6;c3v^5;r 3 m :r;p 3* -2", "161:h;161.1;;18;c3v^6;r 3 c :h;r 3 -2\"c", "161:r;161.2;r;6;c3v^6;r 3 c :r;p 3* -2n", "162;162.1;;12;d3d^1;p -3 1 m;-p 3 2", "163;163.1;;12;d3d^2;p -3 1 c;-p 3 2c", "164;164.1;;12;d3d^3;p -3 m 1;-p 3 2\"", "165;165.1;;12;d3d^4;p -3 c 1;-p 3 2\"c", "166:h;166.1;;36;d3d^5;r -3 m :h;-r 3 2\"", "166:r;166.2;r;12;d3d^5;r -3 m :r;-p 3* 2", "167:h;167.1;;36;d3d^6;r -3 c :h;-r 3 2\"c", "167:r;167.2;r;12;d3d^6;r -3 c :r;-p 3* 2n", "168;168.1;;6;c6^1;p 6;p 6", "169;169.1;;6;c6^2;p 61;p 61", "170;170.1;;6;c6^3;p 65;p 65", "171;171.1;;6;c6^4;p 62;p 62", "172;172.1;;6;c6^5;p 64;p 64", "173;173.1;;6;c6^6;p 63;p 6c", "173*;173.1;;6;c6^6;p 63*;p 63 ", "174;174.1;;6;c3h^1;p -6;p -6", "175;175.1;;12;c6h^1;p 6/m;-p 6", "176;176.1;;12;c6h^2;p 63/m;-p 6c", "176*;176.1;;12;c6h^2;p 63/m*;-p 63", "177;177.1;;12;d6^1;p 6 2 2;p 6 2", "178;178.1;;12;d6^2;p 61 2 2;p 61 2 (0 0 5)", "179;179.1;;12;d6^3;p 65 2 2;p 65 2 (0 0 1)", "180;180.1;;12;d6^4;p 62 2 2;p 62 2 (0 0 4)", "181;181.1;;12;d6^5;p 64 2 2;p 64 2 (0 0 2)", "182;182.1;;12;d6^6;p 63 2 2;p 6c 2c", "182*;182.1;;12;d6^6;p 63 2 2*;p 63 2c", "183;183.1;;12;c6v^1;p 6 m m;p 6 -2", "184;184.1;;12;c6v^2;p 6 c c;p 6 -2c", "185;185.1;;12;c6v^3;p 63 c m;p 6c -2", "185*;185.1;;12;c6v^3;p 63 c m*;p 63 -2", "186;186.1;;12;c6v^4;p 63 m c;p 6c -2c", "186*;186.1;;12;c6v^4;p 63 m c*;p 63 -2c", "187;187.1;;12;d3h^1;p -6 m 2;p -6 2", "188;188.1;;12;d3h^2;p -6 c 2;p -6c 2", "189;189.1;;12;d3h^3;p -6 2 m;p -6 -2", "190;190.1;;12;d3h^4;p -6 2 c;p -6c -2c", "191;191.1;;24;d6h^1;p 6/m m m;-p 6 2", "192;192.1;;24;d6h^2;p 6/m c c;-p 6 2c", "193;193.1;;24;d6h^3;p 63/m c m;-p 6c 2", "193*;193.1;;24;d6h^3;p 63/m c m*;-p 63 2", "194;194.1;;24;d6h^4;p 63/m m c;-p 6c 2c", "194*;194.1;;24;d6h^4;p 63/m m c*;-p 63 2c", "195;195.1;;12;t^1;p 2 3;p 2 2 3", "196;196.1;;48;t^2;f 2 3;f 2 2 3", "197;197.1;;24;t^3;i 2 3;i 2 2 3", "198;198.1;;12;t^4;p 21 3;p 2ac 2ab 3", "199;199.1;;24;t^5;i 21 3;i 2b 2c 3", "200;200.1;;24;th^1;p m -3;-p 2 2 3", "201:2;201.1;;24;th^2;p n -3 :2;-p 2ab 2bc 3", "201:1;201.2;a,b,c|-1/4,-1/4,-1/4;24;th^2;p n -3 :1;p 2 2 3 -1n", "202;202.1;;96;th^3;f m -3;-f 2 2 3", "203:2;203.1;;96;th^4;f d -3 :2;-f 2uv 2vw 3", "203:1;203.2;a,b,c|-1/8,-1/8,-1/8;96;th^4;f d -3 :1;f 2 2 3 -1d", "204;204.1;;48;th^5;i m -3;-i 2 2 3", "205;205.1;;24;th^6;p a -3;-p 2ac 2ab 3", "206;206.1;;48;th^7;i a -3;-i 2b 2c 3", "207;207.1;;24;o^1;p 4 3 2;p 4 2 3", "208;208.1;;24;o^2;p 42 3 2;p 4n 2 3", "209;209.1;;96;o^3;f 4 3 2;f 4 2 3", "210;210.1;;96;o^4;f 41 3 2;f 4d 2 3", "211;211.1;;48;o^5;i 4 3 2;i 4 2 3", "212;212.1;;24;o^6;p 43 3 2;p 4acd 2ab 3", "213;213.1;;24;o^7;p 41 3 2;p 4bd 2ab 3", "214;214.1;;48;o^8;i 41 3 2;i 4bd 2c 3", "215;215.1;;24;td^1;p -4 3 m;p -4 2 3", "216;216.1;;96;td^2;f -4 3 m;f -4 2 3", "217;217.1;;48;td^3;i -4 3 m;i -4 2 3", "218;218.1;;24;td^4;p -4 3 n;p -4n 2 3", "219;219.1;;96;td^5;f -4 3 c;f -4a 2 3", "220;220.1;;48;td^6;i -4 3 d;i -4bd 2c 3", "221;221.1;;48;oh^1;p m -3 m;-p 4 2 3", "222:2;222.1;;48;oh^2;p n -3 n :2;-p 4a 2bc 3", "222:1;222.2;a,b,c|-1/4,-1/4,-1/4;48;oh^2;p n -3 n :1;p 4 2 3 -1n", "223;223.1;;48;oh^3;p m -3 n;-p 4n 2 3", "224:2;224.1;;48;oh^4;p n -3 m :2;-p 4bc 2bc 3", "224:1;224.2;a,b,c|-1/4,-1/4,-1/4;48;oh^4;p n -3 m :1;p 4n 2 3 -1n", "225;225.1;;192;oh^5;f m -3 m;-f 4 2 3", "226;226.1;;192;oh^6;f m -3 c;-f 4a 2 3", "227:2;227.1;;192;oh^7;f d -3 m :2;-f 4vw 2vw 3", "227:1;227.2;a,b,c|-1/8,-1/8,-1/8;192;oh^7;f d -3 m :1;f 4d 2 3 -1d", "228:2;228.1;;192;oh^8;f d -3 c :2;-f 4ud 2vw 3", "228:1;228.2;a,b,c|-3/8,-3/8,-3/8;192;oh^8;f d -3 c :1;f 4d 2 3 -1ad", "229;229.1;;96;oh^9;i m -3 m;-i 4 2 3", "230;230.1;;96;oh^10;i a -3 d;-i 4bd 2c 3"]);
{
JS.SpaceGroup.getSpaceGroups();
}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.HallInfo", ["JU.P3i", "$.SB", "JS.HallRotationTerm", "$.HallTranslation", "JU.Logger"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.hallSymbol = null;
this.primitiveHallSymbol = null;
this.latticeCode = '\0';
this.latticeExtension = null;
this.isCentrosymmetric = false;
this.nRotations = 0;
this.rotationTerms = null;
this.vector12ths = null;
this.vectorCode = null;
Clazz_instantialize(this, arguments);}, JS, "HallInfo", null);
Clazz_prepareFields (c$, function(){
this.rotationTerms =  new Array(16);
});
Clazz_makeConstructor(c$, 
function(hallSymbol){
try {
if (hallSymbol.startsWith("Hall:")) hallSymbol = hallSymbol.substring(5).trim();
var str = this.hallSymbol = hallSymbol.trim();
str = this.extractLatticeInfo(str);
if (JS.HallTranslation.getLatticeIndex(this.latticeCode) == 0) return;
this.latticeExtension = JS.HallTranslation.getLatticeExtension(this.latticeCode, this.isCentrosymmetric);
str = this.extractVectorInfo(str) + this.latticeExtension;
if (JU.Logger.debugging) JU.Logger.debug("Hallinfo: " + hallSymbol + " " + str);
var prevOrder = 0;
var prevAxisType = '\u0000';
this.primitiveHallSymbol = "P";
while (str.length > 0 && this.nRotations < 16) {
str = this.extractRotationInfo(str, prevOrder, prevAxisType);
var r = this.rotationTerms[this.nRotations - 1];
prevOrder = r.order;
prevAxisType = r.axisType;
this.primitiveHallSymbol += " " + r.primitiveCode;
}
this.primitiveHallSymbol += this.vectorCode;
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
JU.Logger.error("Invalid Hall symbol " + e);
this.nRotations = 0;
} else {
throw e;
}
}
}, "~S");
Clazz_defineMethod(c$, "dumpInfo", 
function(){
var sb =  new JU.SB();
sb.append("\nHall symbol: ").append(this.hallSymbol).append("\nprimitive Hall symbol: ").append(this.primitiveHallSymbol).append("\nlattice type: ").append(this.getLatticeDesignation());
for (var i = 0; i < this.nRotations; i++) {
sb.append("\n\nrotation term ").appendI(i + 1).append(this.rotationTerms[i].dumpInfo(this.vectorCode));
}
return sb.toString();
});
Clazz_defineMethod(c$, "getLatticeDesignation", 
function(){
return JS.HallTranslation.getLatticeDesignation2(this.latticeCode, this.isCentrosymmetric);
});
Clazz_defineMethod(c$, "extractLatticeInfo", 
function(name){
var i = name.indexOf(" ");
if (i < 0) return "";
var term = name.substring(0, i).toUpperCase();
this.latticeCode = term.charAt(0);
if (this.latticeCode == '-') {
this.isCentrosymmetric = true;
this.latticeCode = term.charAt(1);
}return name.substring(i + 1).trim();
}, "~S");
Clazz_defineMethod(c$, "extractVectorInfo", 
function(name){
this.vector12ths =  new JU.P3i();
this.vectorCode = "";
var i = name.indexOf("(");
var j = name.indexOf(")", i);
if (i > 0 && j > i) {
var term = name.substring(i + 1, j);
this.vectorCode = " (" + term + ")";
name = name.substring(0, i).trim();
i = term.indexOf(" ");
if (i >= 0) {
this.vector12ths.x = Integer.parseInt(term.substring(0, i));
term = term.substring(i + 1).trim();
i = term.indexOf(" ");
if (i >= 0) {
this.vector12ths.y = Integer.parseInt(term.substring(0, i));
term = term.substring(i + 1).trim();
}}this.vector12ths.z = Integer.parseInt(term);
}return name;
}, "~S");
Clazz_defineMethod(c$, "extractRotationInfo", 
function(name, prevOrder, prevAxisType){
var i = name.indexOf(" ");
var code;
if (i >= 0) {
code = name.substring(0, i);
name = name.substring(i + 1).trim();
} else {
code = name;
name = "";
}this.rotationTerms[this.nRotations] =  new JS.HallRotationTerm(this, code, prevOrder, prevAxisType);
this.nRotations++;
return name;
}, "~S,~N,~S");
Clazz_overrideMethod(c$, "toString", 
function(){
return this.hallSymbol;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JU.M4"], "JS.HallRotationTerm", ["JU.SB", "JS.HallRotation", "$.HallTranslation", "$.SymmetryOperation", "JU.Logger"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.inputCode = null;
this.primitiveCode = null;
this.lookupCode = null;
this.translationString = null;
this.rotation = null;
this.translation = null;
this.seitzMatrix12ths = null;
this.isImproper = false;
this.order = 0;
this.axisType = '\0';
this.diagonalReferenceAxis = '\0';
this.allPositive = true;
Clazz_instantialize(this, arguments);}, JS, "HallRotationTerm", null);
Clazz_prepareFields (c$, function(){
this.seitzMatrix12ths =  new JU.M4();
});
Clazz_makeConstructor(c$, 
function(hallInfo, code, prevOrder, prevAxisType){
this.inputCode = code;
code += "   ";
if (code.charAt(0) == '-') {
this.isImproper = true;
code = code.substring(1);
}this.primitiveCode = "";
this.order = (code.charAt(0)).charCodeAt(0) - 48;
this.diagonalReferenceAxis = '\0';
this.axisType = '\0';
var ptr = 2;
var c;
switch ((c = code.charAt(1)).charCodeAt(0)) {
case 120:
case 121:
case 122:
switch ((code.charAt(2)).charCodeAt(0)) {
case 39:
case 34:
this.diagonalReferenceAxis = c;
c = code.charAt(2);
ptr++;
}
case 42:
this.axisType = c;
break;
case 39:
case 34:
this.axisType = c;
switch ((code.charAt(2)).charCodeAt(0)) {
case 120:
case 121:
case 122:
this.diagonalReferenceAxis = code.charAt(2);
ptr++;
break;
default:
this.diagonalReferenceAxis = prevAxisType;
}
break;
default:
this.axisType = (this.order == 1 ? '_' : hallInfo.nRotations == 0 ? 'z' : hallInfo.nRotations == 2 ? '*' : prevOrder == 2 || prevOrder == 4 ? 'x' : '\'');
code = code.substring(0, 1) + this.axisType + code.substring(1);
}
this.primitiveCode += (this.axisType == '_' ? "1" : code.substring(0, 2));
if (this.diagonalReferenceAxis != '\0') {
code = code.substring(0, 1) + this.diagonalReferenceAxis + this.axisType + code.substring(ptr);
this.primitiveCode += this.diagonalReferenceAxis;
ptr = 3;
}this.lookupCode = code.substring(0, ptr);
this.rotation = JS.HallRotation.lookup(this.lookupCode);
if (this.rotation == null) {
JU.Logger.error("Rotation lookup could not find " + this.inputCode + " ? " + this.lookupCode);
return;
}this.translation =  new JS.HallTranslation('\0', null);
this.translationString = "";
var len = code.length;
for (var i = ptr; i < len; i++) {
var translationCode = code.charAt(i);
var t = JS.HallTranslation.getHallTranslation(translationCode, this.order);
if (t != null) {
this.translationString += "" + t.translationCode;
this.translation.rotationShift12ths += t.rotationShift12ths;
this.translation.vectorShift12ths.add(t.vectorShift12ths);
}}
this.primitiveCode = (this.isImproper ? "-" : "") + this.primitiveCode + this.translationString;
this.seitzMatrix12ths.setM4(this.isImproper ? this.rotation.seitzMatrixInv : this.rotation.seitzMatrix);
this.seitzMatrix12ths.m03 = this.translation.vectorShift12ths.x;
this.seitzMatrix12ths.m13 = this.translation.vectorShift12ths.y;
this.seitzMatrix12ths.m23 = this.translation.vectorShift12ths.z;
switch ((this.axisType).charCodeAt(0)) {
case 120:
this.seitzMatrix12ths.m03 += this.translation.rotationShift12ths;
break;
case 121:
this.seitzMatrix12ths.m13 += this.translation.rotationShift12ths;
break;
case 122:
this.seitzMatrix12ths.m23 += this.translation.rotationShift12ths;
break;
}
if (hallInfo.vectorCode.length > 0) {
var m1 = JU.M4.newM4(null);
var m2 = JU.M4.newM4(null);
var v = hallInfo.vector12ths;
m1.m03 = v.x;
m1.m13 = v.y;
m1.m23 = v.z;
m2.m03 = -v.x;
m2.m13 = -v.y;
m2.m23 = -v.z;
this.seitzMatrix12ths.mul2(m1, this.seitzMatrix12ths);
this.seitzMatrix12ths.mul(m2);
}if (JU.Logger.debugging) {
JU.Logger.debug("code = " + code + "; primitive code =" + this.primitiveCode + "\n Seitz Matrix(12ths):" + this.seitzMatrix12ths);
}}, "JS.HallInfo,~S,~N,~S");
Clazz_defineMethod(c$, "dumpInfo", 
function(vectorCode){
var sb =  new JU.SB();
sb.append("\ninput code: ").append(this.inputCode).append("; primitive code: ").append(this.primitiveCode).append("\norder: ").appendI(this.order).append(this.isImproper ? " (improper axis)" : "");
if (this.axisType != '_') {
sb.append("; axisType: ").appendC(this.axisType);
if (this.diagonalReferenceAxis != '\0') sb.appendC(this.diagonalReferenceAxis);
}if (this.translationString.length > 0) sb.append("; translation: ").append(this.translationString);
if (vectorCode.length > 0) sb.append("; vector offset: ").append(vectorCode);
if (this.rotation != null) sb.append("\noperator: ").append(this.getXYZ(this.allPositive)).append("\nSeitz matrix:\n").append(JS.SymmetryOperation.dumpSeitz(this.seitzMatrix12ths, false));
return sb.toString();
}, "~S");
Clazz_defineMethod(c$, "getXYZ", 
function(allPositive){
return JS.SymmetryOperation.getXYZFromMatrix(this.seitzMatrix12ths, true, allPositive, true);
}, "~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JU.M4"], "JS.HallRotation", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.rotCode = null;
this.seitzMatrix = null;
this.seitzMatrixInv = null;
Clazz_instantialize(this, arguments);}, JS, "HallRotation", null);
Clazz_prepareFields (c$, function(){
this.seitzMatrix =  new JU.M4();
this.seitzMatrixInv =  new JU.M4();
});
Clazz_makeConstructor(c$, 
function(code, matrixData){
this.rotCode = code;
var data =  Clazz_newFloatArray (16, 0);
var dataInv =  Clazz_newFloatArray (16, 0);
data[15] = dataInv[15] = 1;
for (var i = 0, ipt = 0; ipt < 11; i++) {
var value = 0;
switch ((matrixData.charAt(i)).charCodeAt(0)) {
case 32:
ipt++;
continue;
case 43:
case 49:
value = 1;
break;
case 45:
value = -1;
break;
}
data[ipt] = value;
dataInv[ipt] = -value;
ipt++;
}
this.seitzMatrix.setA(data);
this.seitzMatrixInv.setA(dataInv);
}, "~S,~S");
c$.lookup = Clazz_defineMethod(c$, "lookup", 
function(code){
for (var i = JS.HallRotation.getHallTerms().length; --i >= 0; ) if (JS.HallRotation.hallRotationTerms[i].rotCode.equals(code)) return JS.HallRotation.hallRotationTerms[i];

return null;
}, "~S");
c$.getHallTerms = Clazz_defineMethod(c$, "getHallTerms", 
function(){
return (JS.HallRotation.hallRotationTerms == null ? JS.HallRotation.hallRotationTerms =  Clazz_newArray(-1, [ new JS.HallRotation("1_", "+00 0+0 00+"),  new JS.HallRotation("2x", "+00 0-0 00-"),  new JS.HallRotation("2y", "-00 0+0 00-"),  new JS.HallRotation("2z", "-00 0-0 00+"),  new JS.HallRotation("2'", "0-0 -00 00-"),  new JS.HallRotation("2\"", "0+0 +00 00-"),  new JS.HallRotation("2x'", "-00 00- 0-0"),  new JS.HallRotation("2x\"", "-00 00+ 0+0"),  new JS.HallRotation("2y'", "00- 0-0 -00"),  new JS.HallRotation("2y\"", "00+ 0-0 +00"),  new JS.HallRotation("2z'", "0-0 -00 00-"),  new JS.HallRotation("2z\"", "0+0 +00 00-"),  new JS.HallRotation("3x", "+00 00- 0+-"),  new JS.HallRotation("3y", "-0+ 0+0 -00"),  new JS.HallRotation("3z", "0-0 +-0 00+"),  new JS.HallRotation("3*", "00+ +00 0+0"),  new JS.HallRotation("4x", "+00 00- 0+0"),  new JS.HallRotation("4y", "00+ 0+0 -00"),  new JS.HallRotation("4z", "0-0 +00 00+"),  new JS.HallRotation("6x", "+00 0+- 0+0"),  new JS.HallRotation("6y", "00+ 0+0 -0+"),  new JS.HallRotation("6z", "+-0 +00 00+")]) : JS.HallRotation.hallRotationTerms);
});
c$.hallRotationTerms = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.HallTranslation", ["JU.P3i"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.translationCode = '\0';
this.rotationOrder = 0;
this.rotationShift12ths = 0;
this.vectorShift12ths = null;
Clazz_instantialize(this, arguments);}, JS, "HallTranslation", null);
Clazz_makeConstructor(c$, 
function(translationCode, params){
this.translationCode = translationCode;
if (params != null) {
if (params.z >= 0) {
this.vectorShift12ths = params;
return;
}this.rotationOrder = params.x;
this.rotationShift12ths = params.y;
}this.vectorShift12ths =  new JU.P3i();
}, "~S,JU.P3i");
c$.getHallLatticeEquivalent = Clazz_defineMethod(c$, "getHallLatticeEquivalent", 
function(latticeParameter){
var latticeCode = JS.HallTranslation.getLatticeCode(latticeParameter);
var isCentrosymmetric = (latticeParameter > 0);
return (isCentrosymmetric ? "-" : "") + latticeCode + " 1";
}, "~N");
c$.getLatticeIndex = Clazz_defineMethod(c$, "getLatticeIndex", 
function(latt){
for (var i = 1, ipt = 3; i <= JS.HallTranslation.nLatticeTypes; i++, ipt += 3) if (JS.HallTranslation.latticeTranslationData[ipt].charAt(0) == latt) return i;

return 0;
}, "~S");
c$.getLatticeCode = Clazz_defineMethod(c$, "getLatticeCode", 
function(latt){
if (latt < 0) latt = -latt;
return (latt == 0 ? '\0' : latt > JS.HallTranslation.nLatticeTypes ? JS.HallTranslation.getLatticeCode(JS.HallTranslation.getLatticeIndex(String.fromCharCode(latt))) : JS.HallTranslation.latticeTranslationData[latt * 3].charAt(0));
}, "~N");
c$.getLatticeDesignation = Clazz_defineMethod(c$, "getLatticeDesignation", 
function(latt){
var isCentrosymmetric = (latt > 0);
var str = (isCentrosymmetric ? "-" : "");
if (latt < 0) latt = -latt;
if (latt == 0 || latt > JS.HallTranslation.nLatticeTypes) return "";
return str + JS.HallTranslation.getLatticeCode(latt) + ": " + (isCentrosymmetric ? "centrosymmetric " : "") + JS.HallTranslation.latticeTranslationData[latt * 3 + 1];
}, "~N");
c$.getLatticeDesignation2 = Clazz_defineMethod(c$, "getLatticeDesignation2", 
function(latticeCode, isCentrosymmetric){
var latt = JS.HallTranslation.getLatticeIndex(latticeCode);
if (!isCentrosymmetric) latt = -latt;
return JS.HallTranslation.getLatticeDesignation(latt);
}, "~S,~B");
c$.getLatticeExtension = Clazz_defineMethod(c$, "getLatticeExtension", 
function(latt, isCentrosymmetric){
for (var i = 1, ipt = 3; i <= JS.HallTranslation.nLatticeTypes; i++, ipt += 3) if (JS.HallTranslation.latticeTranslationData[ipt].charAt(0) == latt) return JS.HallTranslation.latticeTranslationData[ipt + 2] + (isCentrosymmetric ? " -1" : "");

return "";
}, "~S,~B");
c$.getHallTerms = Clazz_defineMethod(c$, "getHallTerms", 
function(){
return (JS.HallTranslation.hallTranslationTerms == null ? JS.HallTranslation.hallTranslationTerms =  Clazz_newArray(-1, [ new JS.HallTranslation('a', JU.P3i.new3(6, 0, 0)),  new JS.HallTranslation('b', JU.P3i.new3(0, 6, 0)),  new JS.HallTranslation('c', JU.P3i.new3(0, 0, 6)),  new JS.HallTranslation('n', JU.P3i.new3(6, 6, 6)),  new JS.HallTranslation('u', JU.P3i.new3(3, 0, 0)),  new JS.HallTranslation('v', JU.P3i.new3(0, 3, 0)),  new JS.HallTranslation('w', JU.P3i.new3(0, 0, 3)),  new JS.HallTranslation('d', JU.P3i.new3(3, 3, 3)),  new JS.HallTranslation('1', JU.P3i.new3(2, 6, -1)),  new JS.HallTranslation('1', JU.P3i.new3(3, 4, -1)),  new JS.HallTranslation('2', JU.P3i.new3(3, 8, -1)),  new JS.HallTranslation('1', JU.P3i.new3(4, 3, -1)),  new JS.HallTranslation('3', JU.P3i.new3(4, 9, -1)),  new JS.HallTranslation('1', JU.P3i.new3(6, 2, -1)),  new JS.HallTranslation('2', JU.P3i.new3(6, 4, -1)),  new JS.HallTranslation('4', JU.P3i.new3(6, 8, -1)),  new JS.HallTranslation('5', JU.P3i.new3(6, 10, -1)),  new JS.HallTranslation('r', JU.P3i.new3(4, 8, 8)),  new JS.HallTranslation('s', JU.P3i.new3(8, 8, 4)),  new JS.HallTranslation('t', JU.P3i.new3(8, 4, 8))]) : JS.HallTranslation.hallTranslationTerms);
});
c$.getHallTranslation = Clazz_defineMethod(c$, "getHallTranslation", 
function(translationCode, order){
var ht = null;
for (var i = JS.HallTranslation.getHallTerms().length; --i >= 0; ) {
var h = JS.HallTranslation.hallTranslationTerms[i];
if (h.translationCode == translationCode) {
if (h.rotationOrder == 0 || h.rotationOrder == order) {
ht =  new JS.HallTranslation(translationCode, null);
ht.translationCode = translationCode;
ht.rotationShift12ths = h.rotationShift12ths;
ht.vectorShift12ths = h.vectorShift12ths;
return ht;
}}}
return ht;
}, "~S,~N");
c$.latticeTranslationData =  Clazz_newArray(-1, ["\0", "unknown", "", "P", "primitive", "", "I", "body-centered", " 1n", "R", "rhombohedral", " 1r 1r", "F", "face-centered", " 1ab 1bc 1ac", "A", "A-centered", " 1bc", "B", "B-centered", " 1ac", "C", "C-centered", " 1ab", "S", "rhombohedral(S)", " 1s 1s", "T", "rhombohedral(T)", " 1t 1t"]);
c$.nLatticeTypes = Clazz_doubleToInt(JS.HallTranslation.latticeTranslationData.length / 3) - 1;
c$.hallTranslationTerms = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JU.M4", "$.P3"], "JS.SymmetryOperation", ["java.util.Hashtable", "JU.Lst", "$.Matrix", "$.Measure", "$.P4", "$.PT", "$.SB", "$.V3", "JS.UnitCell", "JU.BoxInfo", "$.Logger", "$.Parser"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.xyzOriginal = null;
this.xyzCanonical = null;
this.xyz = null;
this.doNormalize = true;
this.isFinalized = false;
this.opId = 0;
this.centering = null;
this.info = null;
this.opType = -1;
this.opOrder = 0;
this.opTrans = null;
this.opGlide = null;
this.opPoint = null;
this.opPoint2 = null;
this.opAxis = null;
this.opPlane = null;
this.opIsCCW = null;
this.isIrrelevant = false;
this.iCoincident = 0;
this.myLabels = null;
this.modDim = 0;
this.linearRotTrans = null;
this.rsvs = null;
this.isBio = false;
this.sigma = null;
this.number = 0;
this.subsystemCode = null;
this.timeReversal = 0;
this.unCentered = false;
this.isCenteringOp = false;
this.magOp = 2147483647;
this.divisor = 12;
this.opX = null;
this.opAxisCode = null;
this.opIsLong = false;
Clazz_instantialize(this, arguments);}, JS, "SymmetryOperation", JU.M4);
Clazz_makeConstructor(c$, 
function(op, id, doNormalize){
Clazz_superConstructor (this, JS.SymmetryOperation, []);
this.doNormalize = doNormalize;
if (op == null) {
this.opId = id;
return;
}this.xyzOriginal = op.xyzOriginal;
this.xyz = op.xyz;
this.divisor = op.divisor;
this.opId = op.opId;
this.modDim = op.modDim;
this.myLabels = op.myLabels;
this.number = op.number;
this.linearRotTrans = op.linearRotTrans;
this.sigma = op.sigma;
this.subsystemCode = op.subsystemCode;
this.timeReversal = op.timeReversal;
this.setMatrix(false);
if (!op.isFinalized) this.doFinalize();
}, "JS.SymmetryOperation,~N,~B");
Clazz_defineMethod(c$, "getOpName", 
function(opMode){
if (this.opType == -1) this.setOpTypeAndOrder();
switch (this.opType) {
case 0:
return "I";
case 1:
return "Trans" + JS.SymmetryOperation.op48(this.opTrans);
case 2:
return "Rot" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + this.opIsCCW;
case 4:
return "Inv" + JS.SymmetryOperation.op48(this.opPoint);
case 8:
return (opMode == 0 ? "" : "Plane") + this.opPlane;
case 3:
return (opMode == 0 ? "S" + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) : "Screw" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + JS.SymmetryOperation.op48(this.opTrans) + this.opIsCCW);
case 6:
return "Nbar" + this.opOrder + JS.SymmetryOperation.op48(this.opPoint) + JS.SymmetryOperation.op48(this.opAxis) + this.opIsCCW;
case 9:
return (opMode == 0 ? "" : "Glide") + this.opPlane + (opMode == 2 ? JS.SymmetryOperation.op48(this.opTrans) : "");
}
System.out.println("SymmetryOperation REJECTED TYPE FOR " + this);
return "";
}, "~N");
Clazz_defineMethod(c$, "getOpTitle", 
function(){
if (this.opType == -1) this.setOpTypeAndOrder();
switch (this.opType) {
case 0:
return "identity ";
case 1:
return "translation " + JS.SymmetryOperation.opFrac(this.opTrans);
case 2:
return "rotation " + this.opOrder;
case 4:
return "inversion center " + JS.SymmetryOperation.opFrac(this.opPoint);
case 8:
return "reflection ";
case 3:
return "screw rotation " + this.opOrder + (this.opIsCCW == null ? "" : this.opIsCCW === Boolean.TRUE ? "(+) " : "(-) ") + JS.SymmetryOperation.opFrac(this.opTrans);
case 6:
return this.opOrder + "-bar " + (this.opIsCCW == null ? "" : this.opIsCCW === Boolean.TRUE ? "(+) " : "(-) ") + JS.SymmetryOperation.opFrac(this.opPoint);
case 9:
return "glide reflection " + JS.SymmetryOperation.opFrac(this.opTrans);
}
return "";
});
c$.opFrac = Clazz_defineMethod(c$, "opFrac", 
function(p){
return "{" + JS.SymmetryOperation.opF(p.x) + " " + JS.SymmetryOperation.opF(p.y) + " " + JS.SymmetryOperation.opF(p.z) + "}";
}, "JU.T3");
c$.opF = Clazz_defineMethod(c$, "opF", 
function(x){
if (x == 0) return "0";
var neg = (x < 0);
if (neg) {
x = -x;
}var n = 0;
if (x >= 1) {
n = Clazz_floatToInt(x);
x -= n;
}var n48 = Math.round(x * 48);
if (JU.PT.approx(n48 / 48 - x, 1000) != 0) return "" + JU.PT.approx(x, 1000);
var div;
if (n48 % 48 == 0) {
div = 1;
} else if (n48 % 24 == 0) {
div = 2;
} else if (n48 % 16 == 0) {
div = 3;
} else if (n48 % 12 == 0) {
div = 4;
} else if (n48 % 8 == 0) {
div = 6;
} else if (n48 % 6 == 0) {
div = 8;
} else if (n48 % 4 == 0) {
div = 12;
} else if (n48 % 3 == 0) {
div = 16;
} else if (n48 % 2 == 0) {
div = 24;
} else {
div = 48;
}return (neg ? "-" : "") + (n * div + Clazz_doubleToInt(n48 * div / 48)) + (div == 1 ? "" : "/" + div);
}, "~N");
c$.op48 = Clazz_defineMethod(c$, "op48", 
function(p){
if (p == null) {
System.err.println("SymmetryOperation.op48 null");
return "(null)";
}return "{" + Math.round(p.x * 48) + " " + Math.round(p.y * 48) + " " + Math.round(p.z * 48) + "}";
}, "JU.T3");
Clazz_defineMethod(c$, "setSigma", 
function(subsystemCode, sigma){
this.subsystemCode = subsystemCode;
this.sigma = sigma;
}, "~S,JU.Matrix");
Clazz_defineMethod(c$, "setGamma", 
function(isReverse){
var n = 3 + this.modDim;
var a = (this.rsvs =  new JU.Matrix(null, n + 1, n + 1)).getArray();
var t =  Clazz_newDoubleArray (n, 0);
var pt = 0;
for (var i = 0; i < n; i++) {
for (var j = 0; j < n; j++) a[i][j] = this.linearRotTrans[pt++];

t[i] = (isReverse ? -1 : 1) * this.linearRotTrans[pt++];
}
a[n][n] = 1;
if (isReverse) this.rsvs = this.rsvs.inverse();
for (var i = 0; i < n; i++) a[i][n] = t[i];

a = this.rsvs.getSubmatrix(0, 0, 3, 3).getArray();
for (var i = 0; i < 3; i++) for (var j = 0; j < 4; j++) this.setElement(i, j, (j < 3 ? a[i][j] : t[i]));


this.setElement(3, 3, 1);
}, "~B");
Clazz_defineMethod(c$, "doFinalize", 
function(){
JS.SymmetryOperation.div12(this, this.divisor);
if (this.modDim > 0) {
var a = this.rsvs.getArray();
for (var i = a.length - 1; --i >= 0; ) a[i][3 + this.modDim] = JS.SymmetryOperation.finalizeD(a[i][3 + this.modDim], this.divisor);

}this.isFinalized = true;
});
c$.div12 = Clazz_defineMethod(c$, "div12", 
function(op, divisor){
op.m03 = JS.SymmetryOperation.finalizeF(op.m03, divisor);
op.m13 = JS.SymmetryOperation.finalizeF(op.m13, divisor);
op.m23 = JS.SymmetryOperation.finalizeF(op.m23, divisor);
return op;
}, "JU.M4,~N");
c$.finalizeF = Clazz_defineMethod(c$, "finalizeF", 
function(m, divisor){
if (divisor == 0) {
if (m == 0) return 0;
var n = Clazz_floatToInt(m);
return ((n >> 8) * 1 / (n & 255));
}return m / divisor;
}, "~N,~N");
c$.finalizeD = Clazz_defineMethod(c$, "finalizeD", 
function(m, divisor){
if (divisor == 0) {
if (m == 0) return 0;
var n = Clazz_doubleToInt(m);
return ((n >> 8) * 1 / (n & 255));
}return m / divisor;
}, "~N,~N");
Clazz_defineMethod(c$, "getXyz", 
function(normalized){
return (normalized && this.modDim == 0 || this.xyzOriginal == null ? this.xyz : this.xyzOriginal);
}, "~B");
Clazz_defineMethod(c$, "getxyzTrans", 
function(t){
var m = JU.M4.newM4(this);
m.add(t);
return JS.SymmetryOperation.getXYZFromMatrix(m, false, false, false);
}, "JU.T3");
Clazz_defineMethod(c$, "dumpInfo", 
function(){
return "\n" + this.xyz + "\ninternal matrix representation:\n" + this.toString();
});
c$.dumpSeitz = Clazz_defineMethod(c$, "dumpSeitz", 
function(s, isCanonical){
var sb =  new JU.SB();
var r =  Clazz_newFloatArray (4, 0);
for (var i = 0; i < 3; i++) {
s.getRow(i, r);
sb.append("[\t");
for (var j = 0; j < 3; j++) sb.appendI(Clazz_floatToInt(r[j])).append("\t");

var trans = r[3];
trans *= (trans == Clazz_floatToInt(trans) ? 4 : 48);
sb.append(JS.SymmetryOperation.twelfthsOf(isCanonical ? JS.SymmetryOperation.normalizeTwelfths(trans / 48, 48, true) : Clazz_floatToInt(trans))).append("\t]\n");
}
return sb.toString();
}, "JU.M4,~B");
Clazz_defineMethod(c$, "setMatrixFromXYZ", 
function(xyz, modDim, allowScaling){
if (xyz == null) return false;
this.xyzOriginal = xyz;
this.divisor = JS.SymmetryOperation.setDivisor(xyz);
xyz = xyz.toLowerCase();
this.setModDim(modDim);
var isReverse = false;
var halfOrLess = true;
if (xyz.startsWith("!")) {
if (xyz.startsWith("!nohalf!")) {
halfOrLess = false;
xyz = xyz.substring(8);
this.xyzOriginal = xyz;
} else {
isReverse = false;
xyz = xyz.substring(1);
}}if (xyz.indexOf("xyz matrix:") == 0) {
this.xyz = xyz;
JU.Parser.parseStringInfestedFloatArray(xyz, null, this.linearRotTrans);
return this.setFromMatrix(null, isReverse);
}if (xyz.indexOf("[[") == 0) {
xyz = xyz.$replace('[', ' ').$replace(']', ' ').$replace(',', ' ');
JU.Parser.parseStringInfestedFloatArray(xyz, null, this.linearRotTrans);
for (var i = this.linearRotTrans.length; --i >= 0; ) if (Float.isNaN(this.linearRotTrans[i])) return false;

this.setMatrix(isReverse);
this.isFinalized = true;
this.isBio = (xyz.indexOf("bio") >= 0);
this.xyz = (this.isBio ? (this.xyzOriginal = Clazz_superCall(this, JS.SymmetryOperation, "toString", [])) : JS.SymmetryOperation.getXYZFromMatrix(this, false, false, false));
return true;
}if (modDim == 0 && xyz.indexOf("x4") >= 0) {
for (var i = 14; --i >= 4; ) {
if (xyz.indexOf("x" + i) >= 0) {
this.setModDim(i - 3);
break;
}}
}var mxyz = null;
if (xyz.endsWith("m")) {
this.timeReversal = (xyz.indexOf("-m") >= 0 ? -1 : 1);
allowScaling = true;
} else if (xyz.indexOf("mz)") >= 0) {
var pt = xyz.indexOf("(");
mxyz = xyz.substring(pt + 1, xyz.length - 1);
xyz = xyz.substring(0, pt);
allowScaling = false;
}var strOut = JS.SymmetryOperation.getMatrixFromString(this, xyz, this.linearRotTrans, allowScaling, halfOrLess, true);
if (strOut == null) return false;
this.xyzCanonical = strOut;
if (mxyz != null) {
var isProper = (JU.M4.newA16(this.linearRotTrans).determinant3() == 1);
this.timeReversal = (((xyz.indexOf("-x") < 0) == (mxyz.indexOf("-mx") < 0)) == isProper ? 1 : -1);
}this.setMatrix(isReverse);
this.xyz = (isReverse ? JS.SymmetryOperation.getXYZFromMatrix(this, true, false, false) : this.doNormalize ? strOut : xyz);
if (this.timeReversal != 0) this.xyz += (this.timeReversal == 1 ? ",m" : ",-m");
if (JU.Logger.debugging) JU.Logger.debug("" + this);
return true;
}, "~S,~N,~B");
c$.setDivisor = Clazz_defineMethod(c$, "setDivisor", 
function(xyz){
var pt = xyz.indexOf('/');
var len = xyz.length;
while (pt > 0 && pt < len - 1) {
var c = xyz.charAt(pt + 1);
if ("2346".indexOf(c) < 0 || pt < len - 2 && Character.isDigit(xyz.charAt(pt + 2))) {
return 0;
}pt = xyz.indexOf('/', pt + 1);
}
return 12;
}, "~S");
Clazz_defineMethod(c$, "setModDim", 
function(dim){
var n = (dim + 4) * (dim + 4);
this.modDim = dim;
if (dim > 0) this.myLabels = JS.SymmetryOperation.labelsXn;
this.linearRotTrans =  Clazz_newFloatArray (n, 0);
}, "~N");
Clazz_defineMethod(c$, "setMatrix", 
function(isReverse){
if (this.linearRotTrans.length > 16) {
this.setGamma(isReverse);
} else {
this.setA(this.linearRotTrans);
if (isReverse) {
var p3 = JU.P3.new3(this.m03, this.m13, this.m23);
this.invert();
this.rotate(p3);
p3.scale(-1);
this.setTranslation(p3);
}}}, "~B");
Clazz_defineMethod(c$, "setFromMatrix", 
function(offset, isReverse){
var v = 0;
var pt = 0;
this.myLabels = (this.modDim == 0 ? JS.SymmetryOperation.labelsXYZ : JS.SymmetryOperation.labelsXn);
var rowPt = 0;
var n = 3 + this.modDim;
for (var i = 0; rowPt < n; i++) {
if (Float.isNaN(this.linearRotTrans[i])) return false;
v = this.linearRotTrans[i];
if (Math.abs(v) < 0.00001) v = 0;
var isTrans = ((i + 1) % (n + 1) == 0);
if (isTrans) {
var denom = (this.divisor == 0 ? (Clazz_floatToInt(v)) & 255 : this.divisor);
if (denom == 0) denom = 12;
v = JS.SymmetryOperation.finalizeF(v, this.divisor);
if (offset != null) {
if (pt < offset.length) v += offset[pt++];
}v = JS.SymmetryOperation.normalizeTwelfths(((v < 0 ? -1 : 1) * Math.abs(v * denom) / denom), denom, this.doNormalize);
if (this.divisor == 0) v = JS.SymmetryOperation.toDivisor(v, denom);
rowPt++;
}this.linearRotTrans[i] = v;
}
this.linearRotTrans[this.linearRotTrans.length - 1] = this.divisor;
this.setMatrix(isReverse);
this.isFinalized = (offset == null);
this.xyz = JS.SymmetryOperation.getXYZFromMatrix(this, true, false, false);
return true;
}, "~A,~B");
c$.getMatrixFromXYZ = Clazz_defineMethod(c$, "getMatrixFromXYZ", 
function(xyz, v, halfOrLess){
if (v == null) v =  Clazz_newFloatArray (16, 0);
xyz = JS.SymmetryOperation.getMatrixFromString(null, xyz, v, false, halfOrLess, true);
if (xyz == null) return null;
var m =  new JU.M4();
m.setA(v);
return JS.SymmetryOperation.div12(m, JS.SymmetryOperation.setDivisor(xyz));
}, "~S,~A,~B");
c$.getJmolCanonicalXYZ = Clazz_defineMethod(c$, "getJmolCanonicalXYZ", 
function(xyz){
try {
return JS.SymmetryOperation.getMatrixFromString(null, xyz, null, false, true, true);
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "~S");
c$.getMatrixFromString = Clazz_defineMethod(c$, "getMatrixFromString", 
function(op, xyz, linearRotTrans, allowScaling, halfOrLess, retString){
var isDenominator = false;
var isDecimal = false;
var isNegative = false;
xyz = JU.PT.rep(xyz, "[bio[", "");
var modDim = (op == null ? 0 : op.modDim);
var nRows = 4 + modDim;
var divisor = (op == null ? JS.SymmetryOperation.setDivisor(xyz) : op.divisor);
var doNormalize = halfOrLess && (op == null ? !xyz.startsWith("!") : op.doNormalize);
var dimOffset = (modDim > 0 ? 3 : 0);
if (linearRotTrans != null) {
var n = linearRotTrans.length - 1;
for (var i = n; --i >= 0; ) linearRotTrans[i] = 0;

linearRotTrans[n] = 1;
}var transPt = xyz.indexOf(';') + 1;
if (transPt != 0) {
allowScaling = true;
if (transPt == xyz.length) xyz += "0,0,0";
}var rotPt = -1;
var myLabels = (op == null || modDim == 0 ? null : op.myLabels);
if (myLabels == null) myLabels = JS.SymmetryOperation.labelsXYZ;
xyz = xyz.toLowerCase() + ",";
xyz = xyz.$replace('(', ',');
if (modDim > 0) xyz = JS.SymmetryOperation.replaceXn(xyz, modDim + 3);
var xpt = 0;
var tpt0 = 0;
var rowPt = 0;
var ch;
var iValue = 0;
var denom = 0;
var numer = 0;
var decimalMultiplier = 1;
var strT = "";
var strOut = (retString ? "" : null);
var ret =  Clazz_newIntArray (1, 0);
var len = xyz.length;
for (var i = 0; i < len; i++) {
switch ((ch = xyz.charAt(i)).charCodeAt(0)) {
case 59:
break;
case 39:
case 32:
case 123:
case 125:
case 33:
continue;
case 45:
isNegative = true;
continue;
case 43:
isNegative = false;
continue;
case 47:
denom = 0;
isDenominator = true;
continue;
case 120:
case 121:
case 122:
case 97:
case 98:
case 99:
case 100:
case 101:
case 102:
case 103:
case 104:
tpt0 = rowPt * nRows;
var ipt = (ch >= 'x' ? ch.charCodeAt(0) - 120 : ch.charCodeAt(0) - 97 + dimOffset);
xpt = tpt0 + ipt;
var val = (isNegative ? -1 : 1);
if (allowScaling && iValue != 0) {
if (linearRotTrans != null) linearRotTrans[xpt] = iValue;
val = Clazz_floatToInt(iValue);
iValue = 0;
} else if (linearRotTrans != null) {
linearRotTrans[xpt] = val;
}if (strOut != null) strT += JS.SymmetryOperation.plusMinus(strT, val, myLabels[ipt], false);
break;
case 44:
if (transPt != 0) {
if (transPt > 0) {
rotPt = i;
i = transPt - 1;
transPt = -i;
iValue = 0;
denom = 0;
continue;
}transPt = i + 1;
i = rotPt;
}iValue = JS.SymmetryOperation.normalizeTwelfths(iValue, denom == 0 ? 12 : divisor == 0 ? denom : divisor, doNormalize);
if (linearRotTrans != null) linearRotTrans[tpt0 + nRows - 1] = (divisor == 0 && denom > 0 ? iValue = JS.SymmetryOperation.toDivisor(numer, denom) : iValue);
if (strOut != null) {
strT += JS.SymmetryOperation.xyzFraction12(iValue, (divisor == 0 ? denom : divisor), false, halfOrLess);
strOut += (strOut === "" ? "" : ",") + strT;
}if (rowPt == nRows - 2) return (retString ? strOut : "ok");
iValue = 0;
numer = 0;
denom = 0;
strT = "";
tpt0 += 4;
if (rowPt++ > 2 && modDim == 0) {
JU.Logger.warn("Symmetry Operation? " + xyz);
return null;
}break;
case 46:
isDecimal = true;
decimalMultiplier = 1;
continue;
case 48:
if (!isDecimal && divisor == 12 && (isDenominator || !allowScaling)) continue;
default:
var ich = ch.charCodeAt(0) - 48;
if (ich >= 0 && ich <= 9) {
if (isDecimal) {
decimalMultiplier /= 10;
if (iValue < 0) isNegative = true;
iValue += decimalMultiplier * ich * (isNegative ? -1 : 1);
continue;
}if (isDenominator) {
ret[0] = i;
denom = JU.PT.parseIntNext(xyz, ret);
if (denom < 0) return null;
i = ret[0] - 1;
if (iValue == 0) {
if (linearRotTrans != null) linearRotTrans[xpt] /= denom;
} else {
numer = Clazz_floatToInt(iValue);
iValue /= denom;
}} else {
iValue = iValue * 10 + (isNegative ? -1 : 1) * ich;
isNegative = false;
}} else {
JU.Logger.warn("symmetry character?" + ch);
}}
isDecimal = isDenominator = isNegative = false;
}
return null;
}, "JS.SymmetryOperation,~S,~A,~B,~B,~B");
c$.replaceXn = Clazz_defineMethod(c$, "replaceXn", 
function(xyz, n){
for (var i = n; --i >= 0; ) xyz = JU.PT.rep(xyz, JS.SymmetryOperation.labelsXn[i], JS.SymmetryOperation.labelsXnSub[i]);

return xyz;
}, "~S,~N");
c$.toDivisor = Clazz_defineMethod(c$, "toDivisor", 
function(numer, denom){
var n = Clazz_floatToInt(numer);
if (n != numer) {
var f = numer - n;
denom = Clazz_floatToInt(Math.abs(denom / f));
n = Clazz_floatToInt(Math.abs(numer) / f);
}return ((n << 8) + denom);
}, "~N,~N");
c$.xyzFraction12 = Clazz_defineMethod(c$, "xyzFraction12", 
function(n12ths, denom, allPositive, halfOrLess){
if (n12ths == 0) return "";
var n = n12ths;
if (denom != 12) {
var $in = Clazz_floatToInt(n);
denom = ($in & 255);
n = $in >> 8;
}var half = (Clazz_doubleToInt(denom / 2));
if (allPositive) {
while (n < 0) n += denom;

} else if (halfOrLess) {
while (n > half) n -= denom;

while (n < -half) n += denom;

}var s = (denom == 12 ? JS.SymmetryOperation.twelfthsOf(n) : n == 0 ? "0" : n + "/" + denom);
return (s.charAt(0) == '0' ? "" : n > 0 ? "+" + s : s);
}, "~N,~N,~B,~B");
c$.twelfthsOf = Clazz_defineMethod(c$, "twelfthsOf", 
function(n12ths){
var str = "";
if (n12ths < 0) {
n12ths = -n12ths;
str = "-";
}var m = 12;
var n = Math.round(n12ths);
if (Math.abs(n - n12ths) > 0.01) {
var f = n12ths / 12;
var max = 20;
for (m = 3; m < max; m++) {
var fm = f * m;
n = Math.round(fm);
if (Math.abs(n - fm) < 0.01) break;
}
if (m == max) return str + f;
} else {
if (n == 12) return str + "1";
if (n < 12) return str + JS.SymmetryOperation.twelfths[n % 12];
switch (n % 12) {
case 0:
return str + Clazz_doubleToInt(n / 12);
case 2:
case 10:
m = 6;
break;
case 3:
case 9:
m = 4;
break;
case 4:
case 8:
m = 3;
break;
case 6:
m = 2;
break;
default:
break;
}
n = (Clazz_doubleToInt(n * m / 12));
}return str + n + "/" + m;
}, "~N");
c$.plusMinus = Clazz_defineMethod(c$, "plusMinus", 
function(strT, x, sx, allowFractions){
var a;
return (x == 0 ? "" : (x < 0 ? "-" : strT.length == 0 ? "" : "+") + (x == 1 || x == -1 ? "" : (a = Math.abs(x)) < 1 && allowFractions ? JS.SymmetryOperation.twelfthsOf(a * 12) : "" + Clazz_floatToInt(a))) + sx;
}, "~S,~N,~S,~B");
c$.normalizeTwelfths = Clazz_defineMethod(c$, "normalizeTwelfths", 
function(iValue, divisor, doNormalize){
iValue *= divisor;
var half = Clazz_doubleToInt(divisor / 2);
if (doNormalize) {
while (iValue > half) iValue -= divisor;

while (iValue <= -half) iValue += divisor;

}return iValue;
}, "~N,~N,~B");
c$.getXYZFromMatrix = Clazz_defineMethod(c$, "getXYZFromMatrix", 
function(mat, is12ths, allPositive, halfOrLess){
return JS.SymmetryOperation.getXYZFromMatrixFrac(mat, is12ths, allPositive, halfOrLess, false);
}, "JU.M4,~B,~B,~B");
c$.getXYZFromMatrixFrac = Clazz_defineMethod(c$, "getXYZFromMatrixFrac", 
function(mat, is12ths, allPositive, halfOrLess, allowFractions){
var str = "";
var op = (Clazz_instanceOf(mat,"JS.SymmetryOperation") ? mat : null);
if (op != null && op.modDim > 0) return JS.SymmetryOperation.getXYZFromRsVs(op.rsvs.getRotation(), op.rsvs.getTranslation(), is12ths);
var row =  Clazz_newFloatArray (4, 0);
var denom = Clazz_floatToInt(mat.getElement(3, 3));
if (denom == 1) denom = 12;
 else mat.setElement(3, 3, 1);
for (var i = 0; i < 3; i++) {
var lpt = (i < 3 ? 0 : 3);
mat.getRow(i, row);
var term = "";
for (var j = 0; j < 3; j++) {
var x = row[j];
if (JS.SymmetryOperation.approx(x) != 0) {
term += JS.SymmetryOperation.plusMinus(term, x, JS.SymmetryOperation.labelsXYZ[j + lpt], allowFractions);
}}
if ((is12ths ? row[3] : JS.SymmetryOperation.approx(row[3])) != 0) {
var f = JS.SymmetryOperation.xyzFraction12((is12ths ? row[3] : row[3] * denom), denom, allPositive, halfOrLess);
if (term === "") f = (f.charAt(0) == '+' ? f.substring(1) : f);
term += f;
}str += "," + (term === "" ? "0" : term);
}
return str.substring(1);
}, "JU.M4,~B,~B,~B,~B");
Clazz_defineMethod(c$, "rotateAxes", 
function(vectors, unitcell, ptTemp, mTemp){
var vRot =  new Array(3);
this.getRotationScale(mTemp);
for (var i = vectors.length; --i >= 0; ) {
ptTemp.setT(vectors[i]);
unitcell.toFractional(ptTemp, true);
mTemp.rotate(ptTemp);
unitcell.toCartesian(ptTemp, true);
vRot[i] = JU.V3.newV(ptTemp);
}
return vRot;
}, "~A,JS.UnitCell,JU.P3,JU.M3");
c$.fcoord = Clazz_defineMethod(c$, "fcoord", 
function(p, sep){
return JS.SymmetryOperation.opF(p.x) + sep + JS.SymmetryOperation.opF(p.y) + sep + JS.SymmetryOperation.opF(p.z);
}, "JU.T3,~S");
c$.approx = Clazz_defineMethod(c$, "approx", 
function(f){
return JU.PT.approx(f, 100);
}, "~N");
c$.approx6 = Clazz_defineMethod(c$, "approx6", 
function(f){
return JU.PT.approx(f, 1000000);
}, "~N");
c$.getXYZFromRsVs = Clazz_defineMethod(c$, "getXYZFromRsVs", 
function(rs, vs, is12ths){
var ra = rs.getArray();
var va = vs.getArray();
var d = ra.length;
var s = "";
for (var i = 0; i < d; i++) {
s += ",";
for (var j = 0; j < d; j++) {
var r = ra[i][j];
if (r != 0) {
s += (r < 0 ? "-" : s.endsWith(",") ? "" : "+") + (Math.abs(r) == 1 ? "" : "" + Math.abs(r)) + "x" + (j + 1);
}}
s += JS.SymmetryOperation.xyzFraction12(Clazz_doubleToInt(va[i][0] * (is12ths ? 1 : 12)), 12, false, true);
}
return JU.PT.rep(s.substring(1), ",+", ",");
}, "JU.Matrix,JU.Matrix,~B");
Clazz_defineMethod(c$, "toString", 
function(){
return (this.rsvs == null ? Clazz_superCall(this, JS.SymmetryOperation, "toString", []) : Clazz_superCall(this, JS.SymmetryOperation, "toString", []) + " " + this.rsvs.toString());
});
Clazz_defineMethod(c$, "getMagneticOp", 
function(){
return (this.magOp == 2147483647 ? this.magOp = Clazz_floatToInt(this.determinant3() * this.timeReversal) : this.magOp);
});
Clazz_defineMethod(c$, "setTimeReversal", 
function(magRev){
this.timeReversal = magRev;
if (this.xyz.indexOf("m") >= 0) this.xyz = this.xyz.substring(0, this.xyz.indexOf("m"));
if (magRev != 0) {
this.xyz += (magRev == 1 ? ",m" : ",-m");
}}, "~N");
Clazz_defineMethod(c$, "getCentering", 
function(){
if (!this.isFinalized) this.doFinalize();
if (this.centering == null && !this.unCentered) {
if (this.modDim == 0 && this.m00 == 1 && this.m11 == 1 && this.m22 == 1 && this.m01 == 0 && this.m02 == 0 && this.m10 == 0 && this.m12 == 0 && this.m20 == 0 && this.m21 == 0 && (this.m03 != 0 || this.m13 != 0 || this.m23 != 0)) {
this.isCenteringOp = true;
this.centering = JU.V3.new3(this.m03, this.m13, this.m23);
} else {
this.unCentered = true;
this.centering = null;
}}return this.centering;
});
Clazz_defineMethod(c$, "fixMagneticXYZ", 
function(m, xyz, addMag){
if (this.timeReversal == 0) return xyz;
var pt = xyz.indexOf("m");
pt -= Clazz_doubleToInt((3 - this.timeReversal) / 2);
xyz = (pt < 0 ? xyz : xyz.substring(0, pt));
if (!addMag) return xyz + (this.timeReversal > 0 ? " +1" : " -1");
var m2 = JU.M4.newM4(m);
m2.m03 = m2.m13 = m2.m23 = 0;
if (this.getMagneticOp() < 0) m2.scale(-1);
xyz += "(" + JU.PT.rep(JU.PT.rep(JU.PT.rep(JS.SymmetryOperation.getXYZFromMatrix(m2, false, false, false), "x", "mx"), "y", "my"), "z", "mz") + ")";
return xyz;
}, "JU.M4,~S,~B");
Clazz_defineMethod(c$, "getInfo", 
function(){
if (this.info == null) {
this.info =  new java.util.Hashtable();
this.info.put("xyz", this.xyz);
if (this.centering != null) this.info.put("centering", this.centering);
this.info.put("index", Integer.$valueOf(this.number - 1));
this.info.put("isCenteringOp", Boolean.$valueOf(this.isCenteringOp));
if (this.linearRotTrans != null) this.info.put("linearRotTrans", this.linearRotTrans);
this.info.put("modulationDimension", Integer.$valueOf(this.modDim));
this.info.put("matrix", JU.M4.newM4(this));
if (this.magOp != 3.4028235E38) this.info.put("magOp", Float.$valueOf(this.magOp));
this.info.put("id", Integer.$valueOf(this.opId));
this.info.put("timeReversal", Integer.$valueOf(this.timeReversal));
if (this.xyzOriginal != null) this.info.put("xyzOriginal", this.xyzOriginal);
}return this.info;
});
c$.normalizeOperationToCentroid = Clazz_defineMethod(c$, "normalizeOperationToCentroid", 
function(dim, m, fracPts, i0, n){
if (n <= 0) return;
var x = 0;
var y = 0;
var z = 0;
if (JS.SymmetryOperation.atomTest == null) JS.SymmetryOperation.atomTest =  new JU.P3();
for (var i = i0, i2 = i + n; i < i2; i++) {
m.rotTrans2(fracPts[i], JS.SymmetryOperation.atomTest);
x += JS.SymmetryOperation.atomTest.x;
y += JS.SymmetryOperation.atomTest.y;
z += JS.SymmetryOperation.atomTest.z;
}
x /= n;
y /= n;
z /= n;
while (x < -0.001 || x >= 1.001) {
m.m03 += (x < 0 ? 1 : -1);
x += (x < 0 ? 1 : -1);
}
if (dim > 1) while (y < -0.001 || y >= 1.001) {
m.m13 += (y < 0 ? 1 : -1);
y += (y < 0 ? 1 : -1);
}
if (dim > 2) while (z < -0.001 || z >= 1.001) {
m.m23 += (z < 0 ? 1 : -1);
z += (z < 0 ? 1 : -1);
}
}, "~N,JU.M4,~A,~N,~N");
c$.getLatticeCentering = Clazz_defineMethod(c$, "getLatticeCentering", 
function(ops){
var list =  new JU.Lst();
for (var i = 0; i < ops.length; i++) {
var c = (ops[i] == null ? null : ops[i].getCentering());
if (c != null) list.addLast(JU.P3.newP(c));
}
return list;
}, "~A");
Clazz_defineMethod(c$, "getOpIsCCW", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opIsCCW;
});
Clazz_defineMethod(c$, "getOpType", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opType;
});
Clazz_defineMethod(c$, "getOpOrder", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opOrder;
});
Clazz_defineMethod(c$, "getOpPoint", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opPoint;
});
Clazz_defineMethod(c$, "getOpAxis", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return this.opAxis;
});
Clazz_defineMethod(c$, "getOpPoint2", 
function(){
return this.opPoint2;
});
Clazz_defineMethod(c$, "getOpTrans", 
function(){
if (this.opType == -1) {
this.setOpTypeAndOrder();
}return (this.opTrans == null ? (this.opTrans =  new JU.V3()) : this.opTrans);
});
c$.opGet3code = Clazz_defineMethod(c$, "opGet3code", 
function(m){
var c = 0;
var row =  Clazz_newFloatArray (4, 0);
for (var r = 0; r < 3; r++) {
m.getRow(r, row);
for (var i = 0; i < 3; i++) {
switch (Clazz_floatToInt(row[i])) {
case 1:
c |= (i + 1) << ((2 - r) << 3);
break;
case -1:
c |= (0x10 + i + 1) << ((2 - r) << 3);
break;
}
}
}
return c;
}, "JU.M4");
c$.opGet3x = Clazz_defineMethod(c$, "opGet3x", 
function(m){
if (m.m22 != 0) return JS.SymmetryOperation.x;
var c = JS.SymmetryOperation.opGet3code(m);
for (var i = 0; i < 8; i++) if (c == JS.SymmetryOperation.C3codes[i]) {
if (JS.SymmetryOperation.xneg == null) {
JS.SymmetryOperation.xneg = JU.V3.newV(JS.SymmetryOperation.x);
JS.SymmetryOperation.xneg.scale(-1);
}return JS.SymmetryOperation.xneg;
}
return JS.SymmetryOperation.x;
}, "JU.M4");
Clazz_defineMethod(c$, "setOpTypeAndOrder", 
function(){
this.clearOp();
var det = Math.round(this.determinant3());
var trace = Math.round(this.m00 + this.m11 + this.m22);
var order = 0;
var angle = 0;
var px = JS.SymmetryOperation.x;
switch (trace) {
case 3:
if (JS.SymmetryOperation.hasTrans(this)) {
this.opType = 1;
this.opTrans =  new JU.V3();
this.getTranslation(this.opTrans);
this.opOrder = 2;
} else {
this.opType = 0;
this.opOrder = 1;
}return;
case -3:
this.opType = 4;
order = 2;
break;
default:
order = trace * det + 3;
if (order == 5) order = 6;
if (det > 0) {
this.opType = 2;
angle = Clazz_doubleToInt(Math.acos((trace - 1) / 2) * 180 / 3.141592653589793);
if (angle == 120) {
if (this.opX == null) this.opX = JS.SymmetryOperation.opGet3x(this);
px = this.opX;
}} else {
if (order == 2) {
this.opType = 8;
} else {
this.opType = 6;
if (order == 3) order = 6;
angle = Clazz_doubleToInt(Math.acos((-trace - 1) / 2) * 180 / 3.141592653589793);
if (angle == 120) {
if (this.opX == null) this.opX = JS.SymmetryOperation.opGet3x(this);
px = this.opX;
}}}break;
}
this.opOrder = order;
var m4 =  new JU.M4();
var p1 =  new JU.P3();
var p2 = JU.P3.newP(px);
m4.setM4(this);
var p1sum =  new JU.P3();
var p2sum = JU.P3.newP(p2);
var p2odd =  new JU.P3();
var p2even = JU.P3.newP(p2);
var p21 =  new JU.P3();
for (var i = 1; i < order; i++) {
m4.mul(this);
this.rotTrans(p1);
this.rotTrans(p2);
if (i == 1) p21.setT(p2);
p1sum.add(p1);
p2sum.add(p2);
if (this.opType == 6) {
if (i % 2 == 0) {
p2even.add(p2);
} else {
p2odd.add(p2);
}}}
this.opTrans =  new JU.V3();
m4.getTranslation(this.opTrans);
this.opTrans.scale(1 / order);
var d = JS.SymmetryOperation.approx6(this.opTrans.length());
this.opPoint =  new JU.P3();
var v = null;
var isOK = true;
switch (this.opType) {
case 4:
p2sum.add2(p2, px);
p2sum.scale(0.5);
this.opPoint = JU.P3.newP(JS.SymmetryOperation.opClean6(p2sum));
isOK = JS.SymmetryOperation.checkOpPoint(this.opPoint);
break;
case 6:
p2odd.scale(2 / order);
p2even.scale(2 / order);
v = JU.V3.newVsub(p2odd, p2even);
v.normalize();
this.opAxis = JS.SymmetryOperation.opClean6(v);
p1sum.add2(p2odd, p2even);
p2sum.scale(1 / order);
this.opPoint.setT(JS.SymmetryOperation.opClean6(p2sum));
isOK = JS.SymmetryOperation.checkOpPoint(this.opPoint);
if (angle != 180) {
p2.cross(px, p2);
this.opIsCCW = Boolean.$valueOf(p2.dot(v) < 0);
}break;
case 2:
v = JU.V3.newVsub(p2sum, p1sum);
v.normalize();
this.opAxis = JS.SymmetryOperation.opClean6(v);
p1sum.scale(1 / order);
p1.setT(p1sum);
if (d > 0) {
p1sum.sub(this.opTrans);
}this.opPoint.setT(p1sum);
JS.SymmetryOperation.opClean6(this.opPoint);
if (angle != 180) {
p2.cross(px, p2);
this.opIsCCW = Boolean.$valueOf(p2.dot(v) < 0);
}isOK = new Boolean (isOK & JS.SymmetryOperation.checkOpAxis(p1, (d == 0 ? this.opAxis : this.opTrans), p1sum,  new JU.V3(),  new JU.V3(), null)).valueOf();
if (isOK) {
this.opPoint.setT(p1sum);
if (JS.SymmetryOperation.checkOpAxis(this.opPoint, this.opAxis, p2,  new JU.V3(),  new JU.V3(), this.opPoint)) {
this.opPoint2 = JU.P3.newP(p2);
}if (d > 0) {
p1sum.scaleAdd2(0.5, this.opTrans, this.opPoint);
isOK = JS.SymmetryOperation.checkOpPoint(p1sum);
if (this.opPoint2 != null) {
p1sum.scaleAdd2(0.5, this.opTrans, this.opPoint2);
if (!JS.SymmetryOperation.checkOpPoint(p1sum)) this.opPoint2 = null;
}if (v.dot(p1) < 0) {
isOK = false;
}}}break;
case 8:
p1.sub(this.opTrans);
p1.scale(0.5);
this.opPoint.setT(p1);
p21.sub(this.opTrans);
this.opAxis = JU.V3.newVsub(p21, px);
p2.scaleAdd2(0.5, this.opAxis, px);
this.opAxis.normalize();
this.opPlane =  new JU.P4();
p1.set(px.x + 1.1, px.y + 1.7, px.z + 2.1);
p1.scale(0.5);
this.rotTrans(p1);
p1.sub(this.opTrans);
p1.scaleAdd2(0.5, px, p1);
p1.scale(0.5);
v =  new JU.V3();
isOK = JS.SymmetryOperation.checkOpPlane(this.opPoint, p1, p2, this.opPlane, v,  new JU.V3());
JS.SymmetryOperation.opClean6(this.opPlane);
if (JS.SymmetryOperation.approx6(this.opPlane.w) == 0) this.opPlane.w = 0;
JS.SymmetryOperation.approx6Pt(this.opAxis);
JS.SymmetryOperation.normalizePlane(this.opPlane);
break;
}
if (d > 0) {
JS.SymmetryOperation.opClean6(this.opTrans);
var dmax = 1;
if (this.opType == 8) {
if (this.opTrans.z == 0 && this.opTrans.lengthSquared() == 1.25 || this.opTrans.z == 0.5 && this.opTrans.lengthSquared() == 1.5) {
dmax = 1.25;
this.opIsLong = true;
} else {
dmax = 0.78;
}this.opGlide = JU.V3.newV(this.opTrans);
this.fixNegTrans(this.opGlide);
if (this.opGlide.length() == 0) this.opGlide = null;
if ((this.opTrans.x == 1 || this.opTrans.y == 1 || this.opTrans.z == 1) && this.m22 == -1) isOK = false;
} else {
if (this.opTrans.z == 0 && this.opTrans.lengthSquared() == 1.25) {
dmax = 1.25;
this.opIsLong = true;
}}this.opType |= 1;
if (Math.abs(JS.SymmetryOperation.approx(this.opTrans.x)) >= dmax || Math.abs(JS.SymmetryOperation.approx(this.opTrans.y)) >= dmax || Math.abs(JS.SymmetryOperation.approx(this.opTrans.z)) >= dmax) {
isOK = false;
}} else {
this.opTrans = null;
}if (!isOK) {
this.isIrrelevant = true;
}});
Clazz_defineMethod(c$, "fixNegTrans", 
function(t){
t.x = JS.SymmetryOperation.normHalf(t.x);
t.y = JS.SymmetryOperation.normHalf(t.y);
t.z = JS.SymmetryOperation.normHalf(t.z);
}, "JU.V3");
c$.normalizePlane = Clazz_defineMethod(c$, "normalizePlane", 
function(plane){
JS.SymmetryOperation.approx6Pt(plane);
plane.w = JS.SymmetryOperation.approx6(plane.w);
if (plane.w > 0 || plane.w == 0 && (plane.x < 0 || plane.x == 0 && plane.y < 0 || plane.y == 0 && plane.z < 0)) {
plane.scale4(-1);
}JS.SymmetryOperation.opClean6(plane);
plane.w = JS.SymmetryOperation.approx6(plane.w);
}, "JU.P4");
c$.isCoaxial = Clazz_defineMethod(c$, "isCoaxial", 
function(v){
return (Math.abs(JS.SymmetryOperation.approx(v.x)) == 1 || Math.abs(JS.SymmetryOperation.approx(v.y)) == 1 || Math.abs(JS.SymmetryOperation.approx(v.z)) == 1);
}, "JU.T3");
Clazz_defineMethod(c$, "clearOp", 
function(){
if (!this.isFinalized) this.doFinalize();
this.isIrrelevant = false;
this.opTrans = null;
this.opPoint = this.opPoint2 = null;
this.opPlane = null;
this.opIsCCW = null;
this.opIsLong = false;
});
c$.hasTrans = Clazz_defineMethod(c$, "hasTrans", 
function(m4){
return (JS.SymmetryOperation.approx6(m4.m03) != 0 || JS.SymmetryOperation.approx6(m4.m13) != 0 || JS.SymmetryOperation.approx6(m4.m23) != 0);
}, "JU.M4");
c$.checkOpAxis = Clazz_defineMethod(c$, "checkOpAxis", 
function(pt, axis, ptRet, t1, t2, ptNot){
if (JS.SymmetryOperation.opPlanes == null) {
JS.SymmetryOperation.opPlanes = JU.BoxInfo.getBoxFacesFromOABC(null);
}var map = JU.BoxInfo.faceOrder;
var f = (ptNot == null ? 1 : -1);
for (var i = 0; i < 6; i++) {
var p = JU.Measure.getIntersection(pt, axis, JS.SymmetryOperation.opPlanes[map[i]], ptRet, t1, t2);
if (p != null && JS.SymmetryOperation.checkOpPoint(p) && axis.dot(t1) * f < 0 && (ptNot == null || JS.SymmetryOperation.approx(ptNot.distance(p) - 0.5) >= 0)) {
return true;
}}
return false;
}, "JU.P3,JU.V3,JU.P3,JU.V3,JU.V3,JU.P3");
c$.opClean6 = Clazz_defineMethod(c$, "opClean6", 
function(t){
if (JS.SymmetryOperation.approx6(t.x) == 0) t.x = 0;
if (JS.SymmetryOperation.approx6(t.y) == 0) t.y = 0;
if (JS.SymmetryOperation.approx6(t.z) == 0) t.z = 0;
return t;
}, "JU.T3");
c$.checkOpPoint = Clazz_defineMethod(c$, "checkOpPoint", 
function(pt){
return JS.SymmetryOperation.checkOK(pt.x, 0) && JS.SymmetryOperation.checkOK(pt.y, 0) && JS.SymmetryOperation.checkOK(pt.z, 0);
}, "JU.T3");
c$.checkOK = Clazz_defineMethod(c$, "checkOK", 
function(p, a){
return (a != 0 || JS.SymmetryOperation.approx(p) >= 0 && JS.SymmetryOperation.approx(p) <= 1);
}, "~N,~N");
c$.checkOpPlane = Clazz_defineMethod(c$, "checkOpPlane", 
function(p1, p2, p3, plane, vtemp1, vtemp2){
JU.Measure.getPlaneThroughPoints(p1, p2, p3, vtemp1, vtemp2, plane);
var pts = JU.BoxInfo.unitCubePoints;
var nPos = 0;
var nNeg = 0;
for (var i = 8; --i >= 0; ) {
var d = JU.Measure.getPlaneProjection(pts[i], plane, p1, vtemp1);
switch (Clazz_floatToInt(Math.signum(JS.SymmetryOperation.approx6(d)))) {
case 1:
if (nNeg > 0) return true;
nPos++;
break;
case 0:
break;
case -1:
if (nPos > 0) return true;
nNeg++;
}
}
return !(nNeg == 8 || nPos == 8);
}, "JU.P3,JU.P3,JU.P3,JU.P4,JU.V3,JU.V3");
c$.getAdditionalOperations = Clazz_defineMethod(c$, "getAdditionalOperations", 
function(ops){
var n = ops.length;
var lst =  new JU.Lst();
var xyzLst =  new JU.SB();
var mapPlanes =  new java.util.Hashtable();
var vTemp =  new JU.V3();
for (var i = 0; i < n; i++) {
var op = ops[i];
lst.addLast(op);
var s = op.getOpName(1);
xyzLst.append(s).appendC(';');
if ((op.getOpType() & 8) != 0) JS.SymmetryOperation.addCoincidentMap(mapPlanes, op, 8, vTemp);
 else if (op.getOpType() == 3) JS.SymmetryOperation.addCoincidentMap(mapPlanes, op, 3, null);
}
for (var i = 1; i < n; i++) {
ops[i].addOps(xyzLst, lst, mapPlanes, n, i, vTemp);
}
return lst.toArray( new Array(lst.size()));
}, "~A");
Clazz_defineMethod(c$, "addOps", 
function(xyzList, lst, mapCoincident, n0, isym, vTemp){
var t0 =  new JU.V3();
this.getTranslation(t0);
var isPlane = ((this.getOpType() & 8) == 8);
var isScrew = (this.getOpType() == 3);
var t =  new JU.V3();
var opTemp = null;
for (var i = 3; --i >= -3; ) {
for (var j = 3; --j >= -3; ) {
for (var k = 3; --k >= -3; ) {
if (opTemp == null) opTemp =  new JS.SymmetryOperation(null, 0, false);
t.set(i, j, k);
if (this.checkOpSimilar(t, vTemp)) continue;
if (opTemp.opCheckAdd(this, t0, n0, t, xyzList, lst, isym + 1)) {
if (isPlane) JS.SymmetryOperation.addCoincidentMap(mapCoincident, opTemp, 8, vTemp);
 else if (isScrew) JS.SymmetryOperation.addCoincidentMap(mapCoincident, opTemp, 3, null);
opTemp = null;
}}
}
}
}, "JU.SB,JU.Lst,java.util.Map,~N,~N,JU.V3");
c$.addCoincidentMap = Clazz_defineMethod(c$, "addCoincidentMap", 
function(mapCoincident, op, opType, vTemp){
if (op.isIrrelevant) return;
var s = op.getOpName(0);
var l = mapCoincident.get(s);
op.iCoincident = 0;
var isRotation = (opType == 3);
if (l == null) {
mapCoincident.put(s, l =  new JU.Lst());
} else if (isRotation) {
if (op.opOrder == 6) {
for (var i = l.size(); --i >= 0; ) {
var op1 = l.get(i);
if (!op1.isIrrelevant) switch (op1.opOrder) {
case 3:
op1.isIrrelevant = true;
break;
case 6:
break;
}
}
}op.iCoincident = 1;
} else {
var op0 = null;
for (var i = l.size(); --i >= 0; ) {
op0 = l.get(i);
if (op.opGlide != null && op0.opGlide != null) {
vTemp.sub2(op.opGlide, op0.opGlide);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.add2(op.opGlide, op0.opGlide);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.add2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}} else if (op.opGlide == null && op0.opGlide == null) {
vTemp.add2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}vTemp.sub2(op.opAxis, op0.opAxis);
if (vTemp.lengthSquared() < 1e-6) {
op.isIrrelevant = true;
return;
}}}
if (op0.iCoincident == 0) {
op.iCoincident = 1;
op0.iCoincident = -1;
} else {
op.iCoincident = -op0.iCoincident;
}}l.addLast(op);
}, "java.util.Map,JS.SymmetryOperation,~N,JU.V3");
Clazz_defineMethod(c$, "checkOpSimilar", 
function(t, vTemp){
switch (this.getOpType() & -2) {
default:
return false;
case 0:
return true;
case 2:
return (JS.SymmetryOperation.approx6(t.dot(this.opAxis) - t.length()) == 0);
case 8:
vTemp.cross(t, this.opAxis);
return (JS.SymmetryOperation.approx6(vTemp.length()) == 0 ? false : JS.SymmetryOperation.approx6(t.dot(this.opAxis)) == 0);
}
}, "JU.V3,JU.V3");
Clazz_defineMethod(c$, "opCheckAdd", 
function(opThis, t0, n0, t, xyzList, lst, itno){
this.setM4(opThis);
var t1 = JU.V3.newV(t);
t1.add(t0);
this.setTranslation(t1);
this.isFinalized = true;
this.setOpTypeAndOrder();
if (this.isIrrelevant || this.opType == 0 || this.opType == 1) return false;
var s = this.getOpName(1) + ";";
if ((this.opType & 8) == 0 && xyzList.indexOf(s) >= 0) {
return false;
}xyzList.append(s);
lst.addLast(this);
this.isFinalized = true;
this.xyz = JS.SymmetryOperation.getXYZFromMatrix(this, false, false, false);
return true;
}, "JS.SymmetryOperation,JU.V3,~N,JU.V3,JU.SB,JU.Lst,~N");
c$.approx6Pt = Clazz_defineMethod(c$, "approx6Pt", 
function(pt){
if (pt != null) {
pt.x = JS.SymmetryOperation.approx6(pt.x);
pt.y = JS.SymmetryOperation.approx6(pt.y);
pt.z = JS.SymmetryOperation.approx6(pt.z);
}}, "JU.T3");
c$.normalize12ths = Clazz_defineMethod(c$, "normalize12ths", 
function(vtrans){
vtrans.x = JU.PT.approx(vtrans.x, 12);
vtrans.y = JU.PT.approx(vtrans.y, 12);
vtrans.z = JU.PT.approx(vtrans.z, 12);
}, "JU.V3");
Clazz_defineMethod(c$, "getCode", 
function(){
if (this.opAxisCode != null) {
return this.opAxisCode;
}var t = this.getOpName(2).charAt(0);
var o = this.opOrder;
var ccw = (this.opIsCCW == null ? 0 : this.opIsCCW === Boolean.TRUE ? 1 : 2);
var g = "";
var m = "";
switch ((t).charCodeAt(0)) {
case 71:
t = JS.SymmetryOperation.getGlideFromTrans(this.opTrans, this.opPlane);
case 80:
if (!JS.SymmetryOperation.isCoaxial(this.opAxis)) {
t = (t == 'P' ? 'p' : String.fromCharCode(t.charCodeAt(0) - 32));
}break;
case 83:
var d = this.opTrans.length();
if (this.opIsCCW != null && (d < (d > 1 ? 6 : 0.5)) == (this.opIsCCW === Boolean.TRUE)) t = 'w';
break;
case 82:
if (!JS.SymmetryOperation.isCoaxial(this.opAxis)) {
t = 'o';
}if (this.opPoint.length() == 0) t = (t == 'o' ? 'q' : 'Q');
break;
default:
break;
}
var s = g + m + t + "." + (String.fromCharCode(48 + o)) + "." + ccw + ".";
return this.opAxisCode = s;
});
c$.getGlideFromTrans = Clazz_defineMethod(c$, "getGlideFromTrans", 
function(ftrans, ax1){
var fx = Math.abs(JS.SymmetryOperation.approx(ftrans.x * 12));
var fy = Math.abs(JS.SymmetryOperation.approx(ftrans.y * 12));
var fz = Math.abs(JS.SymmetryOperation.approx(ftrans.z * 12));
if (fx == 9) fx = 3;
if (fy == 9) fy = 3;
if (fz == 9) fz = 3;
var nonzero = 3;
if (fx == 0) nonzero--;
if (fy == 0) nonzero--;
if (fz == 0) nonzero--;
var sum = Clazz_floatToInt(fx + fy + fz);
switch (nonzero) {
default:
case 1:
return (fx != 0 ? 'a' : fy != 0 ? 'b' : 'c');
case 2:
switch (sum) {
case 6:
return 'd';
case 12:
var n = JU.P3.newP(ax1);
n.normalize();
if (JS.SymmetryOperation.approx(n.x + n.y + n.z) == 1) return 'n';
}
break;
case 3:
switch (sum) {
case 9:
return 'd';
case 18:
return 'n';
}
break;
}
return 'g';
}, "JU.T3,JU.T3");
c$.rotateAndTranslatePoint = Clazz_defineMethod(c$, "rotateAndTranslatePoint", 
function(m, src, ta, tb, tc, dest){
m.rotTrans2(src, dest);
dest.add3(ta, tb, tc);
}, "JU.M4,JU.P3,~N,~N,~N,JU.P3");
c$.transformStr = Clazz_defineMethod(c$, "transformStr", 
function(xyz, trm, trmInv, t, v, centering, targetCentering, normalize, allowFractions){
if (trmInv == null) {
trmInv = JU.M4.newM4(trm);
trmInv.invert();
}if (t == null) t =  new JU.M4();
if (v == null) v =  Clazz_newFloatArray (16, 0);
var op = JS.SymmetryOperation.getMatrixFromXYZ(xyz, v, true);
if (centering != null) op.add(centering);
t.setM4(trmInv);
t.mul(op);
if (trm != null) t.mul(trm);
if (targetCentering != null) op.add(targetCentering);
if (normalize) {
t.getColumn(3, v);
for (var i = 0; i < 3; i++) {
v[i] = v[i] % 1;
}
t.setColumnA(3, v);
}return JS.SymmetryOperation.getXYZFromMatrixFrac(t, false, true, false, allowFractions);
}, "~S,JU.M4,JU.M4,JU.M4,~A,JU.T3,JU.T3,~B,~B");
c$.transformXyzT = Clazz_defineMethod(c$, "transformXyzT", 
function(xyz, transform){
return (JS.SymmetryOperation.transformStr(xyz, JS.UnitCell.toTrm(transform, null), null, null, null, null, null, true, false));
}, "~S,~S");
c$.stringToMatrix = Clazz_defineMethod(c$, "stringToMatrix", 
function(xyz){
var divisor = JS.SymmetryOperation.setDivisor(xyz);
var a =  Clazz_newFloatArray (16, 0);
JS.SymmetryOperation.getMatrixFromString(null, xyz, a, true, false, false);
return JS.SymmetryOperation.div12(JU.M4.newA16(a), divisor);
}, "~S");
c$.getTransformABC = Clazz_defineMethod(c$, "getTransformABC", 
function(transform, normalize){
if (transform == null) return "a,b,c";
var t = transform;
var m = JU.M4.newM4(t);
var tr =  new JU.V3();
m.getTranslation(tr);
tr.scale(-1);
m.add(tr);
m.transpose();
var s = JS.SymmetryOperation.getXYZFromMatrixFrac(m, false, true, false, true).$replace('x', 'a').$replace('y', 'b').$replace('z', 'c');
if (tr.lengthSquared() < 1e-12) return s;
tr.scale(-1);
return s + ";" + (normalize ? JS.SymmetryOperation.norm3(tr) : JS.SymmetryOperation.opF(tr.x) + "," + JS.SymmetryOperation.opF(tr.y) + "," + JS.SymmetryOperation.opF(tr.z));
}, "~O,~B");
c$.norm3 = Clazz_defineMethod(c$, "norm3", 
function(tr){
return JS.SymmetryOperation.norm(tr.x) + "," + JS.SymmetryOperation.norm(tr.y) + "," + JS.SymmetryOperation.norm(tr.z);
}, "JU.T3");
c$.norm = Clazz_defineMethod(c$, "norm", 
function(d){
return JS.SymmetryOperation.opF(JS.SymmetryOperation.normHalf(d));
}, "~N");
c$.normHalf = Clazz_defineMethod(c$, "normHalf", 
function(d){
while (d <= -0.5) {
d += 1;
}
while (d > 0.5) {
d -= 1;
}
return d;
}, "~N");
c$.toPoint = Clazz_defineMethod(c$, "toPoint", 
function(xyz, p){
if (p == null) p =  new JU.P3();
var s = JU.PT.split(xyz, ",");
p.set(JU.PT.parseFloatFraction(s[0]), JU.PT.parseFloatFraction(s[1]), JU.PT.parseFloatFraction(s[2]));
return p;
}, "~S,JU.P3");
c$.atomTest = null;
c$.twelfths =  Clazz_newArray(-1, ["0", "1/12", "1/6", "1/4", "1/3", "5/12", "1/2", "7/12", "2/3", "3/4", "5/6", "11/12"]);
c$.labelsXYZ =  Clazz_newArray(-1, ["x", "y", "z"]);
c$.labelsXn =  Clazz_newArray(-1, ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13"]);
c$.labelsXnSub =  Clazz_newArray(-1, ["x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]);
c$.x = JU.P3.new3(3.141592653589793, 2.718281828459045, (8.539734222673566));
c$.C3codes =  Clazz_newIntArray(-1, [0x031112, 0x121301, 0x130112, 0x021311, 0x130102, 0x020311, 0x031102, 0x120301]);
c$.xneg = null;
c$.opPlanes = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.SymmetryInfo", ["JU.PT", "JS.SpaceGroup", "$.SymmetryOperation", "JU.SimpleUnitCell"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.isCurrentCell = true;
this.displayName = null;
this.coordinatesAreFractional = false;
this.isMultiCell = false;
this.sgName = null;
this.sgTitle = null;
this.symmetryOperations = null;
this.additionalOperations = null;
this.infoStr = null;
this.cellRange = null;
this.latticeType = 'P';
this.intlTableNo = null;
this.intlTableJmolID = null;
this.spaceGroupIndex = 0;
this.spaceGroupF2CTitle = null;
this.spaceGroupF2C = null;
this.spaceGroupF2CParams = null;
this.strSUPERCELL = null;
this.intlTableIndex = null;
this.intlTableTransform = null;
this.sgDerived = null;
Clazz_instantialize(this, arguments);}, JS, "SymmetryInfo", null);
/*LV!1824 unnec constructor*/Clazz_defineMethod(c$, "setSymmetryInfoFromModelkit", 
function(sg){
this.cellRange = null;
this.sgName = sg.getName();
this.intlTableJmolID = sg.jmolId;
this.intlTableNo = sg.itaNumber;
this.latticeType = sg.latticeType;
this.symmetryOperations = sg.finalOperations;
this.coordinatesAreFractional = true;
this.setInfo(sg.getOperationCount());
}, "JS.SpaceGroup");
Clazz_defineMethod(c$, "setSymmetryInfoFromFile", 
function(modelInfo, unitCellParams){
this.spaceGroupIndex = (modelInfo.remove("spaceGroupIndex")).intValue();
this.cellRange = modelInfo.remove("ML_unitCellRange");
this.sgName = modelInfo.get("spaceGroup");
this.spaceGroupF2C = modelInfo.remove("f2c");
this.spaceGroupF2CTitle = modelInfo.remove("f2cTitle");
this.spaceGroupF2CParams = modelInfo.remove("f2cParams");
this.sgTitle = modelInfo.remove("spaceGroupTitle");
this.strSUPERCELL = modelInfo.remove("supercell");
if (this.sgName == null || this.sgName === "") this.sgName = "spacegroup unspecified";
this.intlTableNo = modelInfo.get("intlTableNo");
this.intlTableIndex = modelInfo.get("intlTableIndex");
this.intlTableTransform = modelInfo.get("intlTableTransform");
this.intlTableJmolID = modelInfo.remove("intlTableJmolID");
var s = modelInfo.get("latticeType");
this.latticeType = (s == null ? 'P' : s.charAt(0));
this.symmetryOperations = modelInfo.remove("symmetryOps");
this.coordinatesAreFractional = modelInfo.containsKey("coordinatesAreFractional") ? (modelInfo.get("coordinatesAreFractional")).booleanValue() : false;
this.isMultiCell = (this.coordinatesAreFractional && this.symmetryOperations != null);
if (unitCellParams == null) unitCellParams = modelInfo.get("unitCellParams");
unitCellParams = (JU.SimpleUnitCell.isValid(unitCellParams) ? unitCellParams : null);
if (unitCellParams == null) {
this.coordinatesAreFractional = false;
this.symmetryOperations = null;
this.cellRange = null;
this.infoStr = "";
modelInfo.remove("unitCellParams");
}var symmetryCount = modelInfo.containsKey("symmetryCount") ? (modelInfo.get("symmetryCount")).intValue() : 0;
this.setInfo(symmetryCount);
return unitCellParams;
}, "java.util.Map,~A");
Clazz_defineMethod(c$, "setInfo", 
function(symmetryCount){
var info = "Spacegroup: " + this.sgName;
if (this.symmetryOperations != null) {
var c = "";
var s = "\nNumber of symmetry operations: " + (symmetryCount == 0 ? 1 : symmetryCount) + "\nSymmetry Operations:";
for (var i = 0; i < symmetryCount; i++) {
var op = this.symmetryOperations[i];
s += "\n" + op.fixMagneticXYZ(op, op.xyz, true);
if (op.isCenteringOp) c += " (" + JU.PT.rep(JU.PT.replaceAllCharacters(op.xyz, "xyz", "0"), "0+", "") + ")";
}
if (c.length > 0) info += "\nCentering: " + c;
info += s;
info += "\n";
}this.infoStr = info;
}, "~N");
Clazz_defineMethod(c$, "getAdditionalOperations", 
function(){
if (this.additionalOperations == null && this.symmetryOperations != null) {
this.additionalOperations = JS.SymmetryOperation.getAdditionalOperations(this.symmetryOperations);
}return this.additionalOperations;
});
Clazz_defineMethod(c$, "getDerivedSpaceGroup", 
function(){
if (this.sgDerived == null) {
this.sgDerived = JS.SpaceGroup.getSpaceGroupFromIndex(this.spaceGroupIndex);
}return this.sgDerived;
});
Clazz_defineMethod(c$, "setIsCurrentCell", 
function(TF){
return (this.isCurrentCell != TF && (this.isCurrentCell = TF) == true);
}, "~B");
Clazz_defineMethod(c$, "getSpaceGroupTitle", 
function(){
return (this.isCurrentCell && this.spaceGroupF2CTitle != null ? this.spaceGroupF2CTitle : this.sgName.startsWith("cell=") ? this.sgName : this.sgTitle);
});
Clazz_defineMethod(c$, "getDisplayName", 
function(sym){
if (this.displayName == null) {
var isPolymer = sym.isPolymer();
var isSlab = sym.isSlab();
var sgName = (isPolymer ? "polymer" : isSlab ? "slab" : this.getSpaceGroupTitle());
if (sgName == null) return null;
if (sgName.startsWith("cell=!")) sgName = "cell=inverse[" + sgName.substring(6) + "]";
sgName = JU.PT.rep(sgName, ";0,0,0", "");
if (sgName.indexOf("#") < 0) {
var trm = this.intlTableTransform;
var intTab = this.intlTableIndex;
if (!isSlab && !isPolymer && intTab != null) {
if (trm != null) {
var pt = sgName.indexOf(trm);
if (pt >= 0) {
sgName = JU.PT.rep(sgName, "(" + trm + ")", "");
}if (intTab.indexOf(trm) < 0) {
pt = intTab.indexOf(".");
if (pt > 0) intTab = intTab.substring(0, pt);
intTab += ":" + trm;
}}sgName = (sgName.startsWith("0") ? "" : sgName.equals("unspecified!") ? "#" : sgName + " #") + intTab;
}}if (sgName.indexOf("-- [--]") >= 0) sgName = "";
this.displayName = sgName;
}return this.displayName;
}, "JS.Symmetry");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JU.P3", "$.V3"], "JS.SymmetryDesc", ["java.util.Hashtable", "JU.A4", "$.BS", "$.Lst", "$.M3", "$.M4", "$.Measure", "$.P4", "$.PT", "$.Quat", "$.SB", "JS.T", "JS.SpaceGroup", "$.Symmetry", "$.SymmetryOperation", "JU.Escape", "$.Logger"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.modelSet = null;
this.drawID = null;
Clazz_instantialize(this, arguments);}, JS, "SymmetryDesc", null);
/*LV!1824 unnec constructor*/Clazz_defineMethod(c$, "set", 
function(modelSet){
this.modelSet = modelSet;
return this;
}, "JM.ModelSet");
c$.getType = Clazz_defineMethod(c$, "getType", 
function(id){
var type;
if (id == null) return 1073742001;
if (id.equalsIgnoreCase("matrix")) return 12;
if (id.equalsIgnoreCase("description")) return 1825200146;
if (id.equalsIgnoreCase("axispoint")) return 134217751;
if (id.equalsIgnoreCase("time")) return 268441089;
if (id.equalsIgnoreCase("info")) return 1275068418;
if (id.equalsIgnoreCase("element")) return 1086326789;
if (id.equalsIgnoreCase("invariant")) return 36868;
type = JS.T.getTokFromName(id);
if (type != 0) return type;
type = JS.SymmetryDesc.getKeyType(id);
return (type < 0 ? type : 1073742327);
}, "~S");
c$.getKeyType = Clazz_defineMethod(c$, "getKeyType", 
function(id){
if ("type".equals(id)) id = "_type";
for (var type = 0; type < JS.SymmetryDesc.keys.length; type++) if (id.equalsIgnoreCase(JS.SymmetryDesc.keys[type])) return -1 - type;

return 0;
}, "~S");
c$.nullReturn = Clazz_defineMethod(c$, "nullReturn", 
function(type){
switch (type) {
case 135176:
return ";draw ID sym* delete;draw ID sg* delete;";
case 1073741961:
case 1825200146:
case 1073741974:
case 1145047049:
case 1145047053:
case 11:
case 1073742078:
return "";
case 1153433601:
return  new JU.BS();
default:
return null;
}
}, "~N");
c$.getInfo = Clazz_defineMethod(c$, "getInfo", 
function(io, type){
if (io.length == 0) return "";
if (type < 0 && -type <= JS.SymmetryDesc.keys.length && -type <= io.length) return io[-1 - type];
switch (type) {
case 1073742327:
case 1073741982:
return io;
case 1275068418:
var lst =  new java.util.Hashtable();
for (var j = 0, n = io.length; j < n; j++) {
var key = (j == 3 ? "draw" : j == 7 ? "axispoint" : JS.SymmetryDesc.keys[j]);
if (io[j] != null) lst.put(key, io[j]);
}
return lst;
case 1073741961:
return io[0] + "  \t" + io[2];
case 1145047049:
return io[0];
case 1145047053:
return io[19];
case 1073742078:
return io[1];
default:
case 1825200146:
return io[2];
case 134217764:
if (!JU.Logger.debugging) return io[3];
case 135176:
return io[3] + "\nprint " + JU.PT.esc(io[0] + " " + io[2]);
case 1145047050:
return io[4];
case 1073742178:
return io[5];
case 12289:
return io[6];
case 134217751:
return io[7];
case 1073741854:
return io[8];
case 134217729:
return io[9];
case 12:
return io[10];
case 1814695966:
return io[11];
case 4160:
return io[12];
case 268441089:
return io[13];
case 134217750:
return io[14];
case 1140850696:
return io[15];
case 1073741974:
return io[16];
case 1086326789:
return  Clazz_newArray(-1, [io[6], io[7], io[8], io[14], io[5]]);
case 36868:
return (io[6] != null ? io[6] : io[8] != null ?  Clazz_newArray(-1, [io[7], io[8], io[5]]) : io[5] != null ? "none" : io[14] != null ? io[14] : "identity");
}
}, "~A,~N");
c$.getInfoBS = Clazz_defineMethod(c$, "getInfoBS", 
function(type){
var bsInfo =  new JU.BS();
if (type < 0 && -type <= JS.SymmetryDesc.keys.length) {
bsInfo.set(-1 - type);
return bsInfo;
}switch (type) {
case 0:
case 1153433601:
case 1073742001:
case 1073742327:
case 1073741982:
case 1275068418:
bsInfo.setBits(0, JS.SymmetryDesc.keys.length);
break;
case 1073741961:
bsInfo.set(0);
bsInfo.set(2);
break;
case 1145047049:
bsInfo.set(0);
break;
case 1145047053:
bsInfo.set(19);
break;
case 1073742078:
bsInfo.set(1);
break;
default:
case 1825200146:
bsInfo.set(2);
break;
case 135176:
bsInfo.set(0);
bsInfo.set(2);
bsInfo.set(3);
break;
case 1145047050:
bsInfo.set(4);
break;
case 1073742178:
bsInfo.set(5);
break;
case 12289:
bsInfo.set(6);
break;
case 134217751:
bsInfo.set(7);
break;
case 1073741854:
bsInfo.set(8);
break;
case 134217729:
bsInfo.set(9);
break;
case 12:
bsInfo.set(10);
break;
case 1814695966:
bsInfo.set(11);
break;
case 4160:
bsInfo.set(12);
break;
case 268441089:
bsInfo.set(13);
break;
case 134217750:
bsInfo.set(14);
break;
case 1140850696:
bsInfo.set(15);
break;
case 1073741974:
bsInfo.set(16);
break;
case 1086326789:
case 36868:
bsInfo.set(5);
bsInfo.set(6);
bsInfo.set(7);
bsInfo.set(8);
bsInfo.set(14);
bsInfo.set(22);
break;
}
return bsInfo;
}, "~N");
Clazz_defineMethod(c$, "createInfoArray", 
function(op, uc, ptFrom, ptTarget, id, scaleFactor, options, haveTranslation, bsInfo, isSpaceGroup, isSpaceGroupAll){
if (!op.isFinalized) op.doFinalize();
var matrixOnly = (bsInfo.cardinality() == 1 && bsInfo.get(10));
var isTimeReversed = (op.timeReversal == -1);
if (scaleFactor == 0) scaleFactor = 1;
JS.SymmetryDesc.vtrans.set(0, 0, 0);
var plane = null;
var pta00 = (ptFrom == null || Float.isNaN(ptFrom.x) ? uc.getCartesianOffset() : ptFrom);
if (ptTarget != null) {
JS.SymmetryDesc.pta01.setT(pta00);
JS.SymmetryDesc.pta02.setT(ptTarget);
uc.toFractional(JS.SymmetryDesc.pta01, false);
uc.toFractional(JS.SymmetryDesc.pta02, false);
op.rotTrans(JS.SymmetryDesc.pta01);
JS.SymmetryDesc.ptemp.setT(JS.SymmetryDesc.pta01);
uc.unitize(JS.SymmetryDesc.pta01);
JS.SymmetryDesc.vtrans.setT(JS.SymmetryDesc.pta02);
uc.unitize(JS.SymmetryDesc.pta02);
if (JS.SymmetryDesc.pta01.distanceSquared(JS.SymmetryDesc.pta02) >= 1.96E-6) return null;
JS.SymmetryDesc.vtrans.sub(JS.SymmetryDesc.ptemp);
}var m2 = JU.M4.newM4(op);
m2.add(JS.SymmetryDesc.vtrans);
if (bsInfo.get(10) && ptTarget != null && pta00.equals(ptTarget)) {
m2.m00 = Math.round(m2.m00);
m2.m01 = Math.round(m2.m01);
m2.m02 = Math.round(m2.m02);
m2.m03 = Math.round(m2.m03);
m2.m10 = Math.round(m2.m10);
m2.m11 = Math.round(m2.m11);
m2.m12 = Math.round(m2.m12);
m2.m13 = Math.round(m2.m13);
m2.m20 = Math.round(m2.m20);
m2.m21 = Math.round(m2.m21);
m2.m22 = Math.round(m2.m22);
m2.m23 = Math.round(m2.m23);
}var isMagnetic = (op.timeReversal != 0);
if (matrixOnly && !isMagnetic) {
var im = JS.SymmetryDesc.getKeyType("matrix");
var o =  new Array(-im);
o[-1 - im] = m2;
return o;
}var ftrans =  new JU.V3();
JS.SymmetryDesc.pta01.set(1, 0, 0);
JS.SymmetryDesc.pta02.set(0, 1, 0);
var pta03 = JU.P3.new3(0, 0, 1);
JS.SymmetryDesc.pta01.add(pta00);
JS.SymmetryDesc.pta02.add(pta00);
pta03.add(pta00);
var pt0 = JS.SymmetryDesc.rotTransCart(op, uc, pta00, JS.SymmetryDesc.vtrans);
var pt1 = JS.SymmetryDesc.rotTransCart(op, uc, JS.SymmetryDesc.pta01, JS.SymmetryDesc.vtrans);
var pt2 = JS.SymmetryDesc.rotTransCart(op, uc, JS.SymmetryDesc.pta02, JS.SymmetryDesc.vtrans);
var pt3 = JS.SymmetryDesc.rotTransCart(op, uc, pta03, JS.SymmetryDesc.vtrans);
var vt1 = JU.V3.newVsub(pt1, pt0);
var vt2 = JU.V3.newVsub(pt2, pt0);
var vt3 = JU.V3.newVsub(pt3, pt0);
JS.SymmetryOperation.approx6Pt(JS.SymmetryDesc.vtrans);
var vtemp =  new JU.V3();
vtemp.cross(vt1, vt2);
var haveInversion = (vtemp.dot(vt3) < 0);
if (haveInversion) {
pt1.sub2(pt0, vt1);
pt2.sub2(pt0, vt2);
pt3.sub2(pt0, vt3);
}var q = JU.Quat.getQuaternionFrame(pt0, pt1, pt2).div(JU.Quat.getQuaternionFrame(pta00, JS.SymmetryDesc.pta01, JS.SymmetryDesc.pta02));
var qF = JU.Quat.new4(q.q1, q.q2, q.q3, q.q0);
var info = JU.Measure.computeHelicalAxis(pta00, pt0, qF);
var pa1 = JU.P3.newP(info[0]);
var ax1 = JU.P3.newP(info[1]);
var ang1 = Clazz_floatToInt(Math.abs(JU.PT.approx((info[3]).x, 1)));
var pitch1 = JS.SymmetryOperation.approx((info[3]).y);
if (haveInversion) {
pt1.add2(pt0, vt1);
pt2.add2(pt0, vt2);
pt3.add2(pt0, vt3);
}var trans = JU.V3.newVsub(pt0, pta00);
if (trans.length() < 0.1) trans = null;
var ptinv = null;
var ipt = null;
var ptref = null;
var w = 0;
var margin = 0;
var isTranslation = (ang1 == 0);
var isRotation = !isTranslation;
var isInversionOnly = false;
var isMirrorPlane = false;
var isTranslationOnly = !isRotation && !haveInversion;
if (isRotation || haveInversion) {
trans = null;
}if (haveInversion && isTranslation) {
ipt = JU.P3.newP(pta00);
ipt.add(pt0);
ipt.scale(0.5);
ptinv = pt0;
isInversionOnly = true;
} else if (haveInversion) {
var d = (pitch1 == 0 ?  new JU.V3() : ax1);
var f = 0;
switch (ang1) {
case 60:
f = 0.6666667;
break;
case 120:
f = 2;
break;
case 90:
f = 1;
break;
case 180:
ptref = JU.P3.newP(pta00);
ptref.add(d);
pa1.scaleAdd2(0.5, d, pta00);
if (ptref.distance(pt0) > 0.1) {
trans = JU.V3.newVsub(pt0, ptref);
ftrans.setT(trans);
uc.toFractional(ftrans, true);
} else {
trans = null;
}vtemp.setT(ax1);
vtemp.normalize();
w = -vtemp.x * pa1.x - vtemp.y * pa1.y - vtemp.z * pa1.z;
plane = JU.P4.new4(vtemp.x, vtemp.y, vtemp.z, w);
margin = (Math.abs(w) < 0.01 && vtemp.x * vtemp.y > 0.4 ? 1.30 : 1.05);
isRotation = false;
haveInversion = false;
isMirrorPlane = true;
break;
default:
haveInversion = false;
break;
}
if (f != 0) {
vtemp.sub2(pta00, pa1);
vtemp.add(pt0);
vtemp.sub(pa1);
vtemp.sub(d);
vtemp.scale(f);
pa1.add(vtemp);
ipt =  new JU.P3();
ipt.scaleAdd2(0.5, d, pa1);
ptinv =  new JU.P3();
ptinv.scaleAdd2(-2, ipt, pt0);
ptinv.scale(-1);
}} else if (trans != null) {
JS.SymmetryDesc.ptemp.setT(trans);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
ftrans.setT(JS.SymmetryDesc.ptemp);
uc.toCartesian(JS.SymmetryDesc.ptemp, false);
trans.setT(JS.SymmetryDesc.ptemp);
}var ang = ang1;
JS.SymmetryDesc.approx0(ax1);
if (isRotation) {
var ptr =  new JU.P3();
vtemp.setT(ax1);
var ang2 = ang1;
var p0;
if (haveInversion) {
ptr.setT(ptinv);
p0 = ptinv;
} else if (pitch1 == 0) {
p0 = pt0;
ptr.setT(pa1);
} else {
p0 = pt0;
ptr.scaleAdd2(0.5, vtemp, pa1);
}JS.SymmetryDesc.ptemp.add2(pa1, vtemp);
ang2 = Math.round(JU.Measure.computeTorsion(pta00, pa1, JS.SymmetryDesc.ptemp, p0, true));
if (JS.SymmetryOperation.approx(ang2) != 0) {
ang1 = ang2;
if (ang1 < 0) ang1 = 360 + ang1;
}}var info1 = null;
var type = null;
var glideType = String.fromCharCode(0);
var isIrrelevant = op.isIrrelevant;
var order = op.getOpOrder();
op.isIrrelevant = new Boolean (op.isIrrelevant | isIrrelevant).valueOf();
var isccw = op.getOpIsCCW();
var screwDir = 0;
var nrot = 0;
if (bsInfo.get(2) || bsInfo.get(15)) {
info1 = type = "identity";
if (isInversionOnly) {
JS.SymmetryDesc.ptemp.setT(ipt);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
info1 = "Ci: " + JS.SymmetryDesc.strCoord(JS.SymmetryDesc.ptemp, op.isBio);
type = "inversion center";
} else if (isRotation) {
var screwtype = "";
if (isccw != null) {
screwtype = (isccw === Boolean.TRUE ? "(+)" : "(-)");
screwDir = (isccw === Boolean.TRUE ? 1 : -1);
if (haveInversion && screwDir == -1) isIrrelevant = true;
}nrot = Clazz_doubleToInt(360 / ang);
if (haveInversion) {
info1 = nrot + "-bar" + screwtype + " axis";
} else if (pitch1 != 0) {
JS.SymmetryDesc.ptemp.setT(ax1);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
info1 = nrot + screwtype + " (" + JS.SymmetryDesc.strCoord(JS.SymmetryDesc.ptemp, op.isBio) + ") screw axis";
} else {
info1 = nrot + screwtype + " axis";
if (order % 2 == 0) screwDir *= Clazz_doubleToInt(order / 2);
}type = info1;
} else if (trans != null) {
var s = " " + JS.SymmetryDesc.strCoord(ftrans, op.isBio);
if (isTranslation) {
type = info1 = "translation";
info1 += ":" + s;
} else if (isMirrorPlane) {
if (isSpaceGroup) {
JS.SymmetryDesc.fixGlideTrans(ftrans);
trans.setT(ftrans);
uc.toCartesian(trans, true);
}s = " " + JS.SymmetryDesc.strCoord(ftrans, op.isBio);
glideType = JS.SymmetryOperation.getGlideFromTrans(ftrans, ax1);
type = info1 = glideType + "-glide plane";
info1 += "|translation:" + s;
}} else if (isMirrorPlane) {
type = info1 = "mirror plane";
}if (haveInversion && !isInversionOnly) {
JS.SymmetryDesc.ptemp.setT(ipt);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
info1 += "|at " + JS.SymmetryDesc.strCoord(JS.SymmetryDesc.ptemp, op.isBio);
}if (isTimeReversed) {
info1 += "|time-reversed";
type += " (time-reversed)";
}}var isRightHand = true;
var isScrew = (isRotation && !haveInversion && pitch1 != 0);
if (!isScrew) {
screwDir = 0;
isRightHand = JS.SymmetryDesc.checkHandedness(uc, ax1);
if (!isRightHand) {
ang1 = -ang1;
if (ang1 < 0) ang1 = 360 + ang1;
ax1.scale(-1);
}}var ignore = false;
var cmds = null;
if (id != null && bsInfo.get(3)) {
if (op.getOpType() == 0 || isSpaceGroupAll && op.isIrrelevant) {
if (JU.Logger.debugging) System.out.println("!!SD irrelevent " + op.getOpTitle() + op.getOpPoint());
cmds = "";
} else {
var opType = null;
this.drawID = "\ndraw ID \"" + id;
var drawSB =  new JU.SB();
drawSB.append(this.getDrawID("*")).append(" delete");
if (!isSpaceGroup) {
this.drawLine(drawSB, "frame1X", 0.15, pta00, JS.SymmetryDesc.pta01, "red");
this.drawLine(drawSB, "frame1Y", 0.15, pta00, JS.SymmetryDesc.pta02, "green");
this.drawLine(drawSB, "frame1Z", 0.15, pta00, pta03, "blue");
}var color;
var planeCenter = null;
var nPC = 0;
var isSpecial = (pta00.distance(pt0) < 0.2);
var title = (isSpaceGroup ? "<hover>" + id + ": " + op.xyz + "|" + info1 + "</hover>" : null);
if (isRotation) {
color = (nrot == 2 ? "red" : nrot == 3 ? "[xA00040]" : nrot == 4 ? "[x800080]" : "[x4000A0]");
ang = ang1;
var scale = 1;
vtemp.setT(ax1);
var wp = "";
if (isSpaceGroup) {
pa1.setT(op.getOpPoint());
uc.toCartesian(pa1, false);
}var ptr =  new JU.P3();
if (pitch1 != 0 && !haveInversion) {
opType = "screw";
color = (isccw === Boolean.TRUE ? "orange" : isccw === Boolean.FALSE ? "blue" : order == 4 ? "lightgray" : "grey");
if (!isSpaceGroup) {
this.drawLine(drawSB, "rotLine1", 0.1, pta00, pa1, "red");
JS.SymmetryDesc.ptemp.add2(pa1, vtemp);
this.drawLine(drawSB, "rotLine2", 0.1, pt0, JS.SymmetryDesc.ptemp, "red");
ptr.scaleAdd2(0.5, vtemp, pa1);
}} else {
ptr.setT(pa1);
if (!isRightHand) {
if (!isSpecial && !isSpaceGroup) pa1.sub2(pa1, vtemp);
}if (haveInversion) {
opType = "bar";
if (isSpaceGroup) {
vtemp.normalize();
if (isccw === Boolean.TRUE) {
vtemp.scale(-1);
}} else {
if (pitch1 == 0) {
ptr.setT(ipt);
vtemp.scale(3 * scaleFactor);
if (isSpecial) {
JS.SymmetryDesc.ptemp.scaleAdd2(0.25, vtemp, pa1);
pa1.scaleAdd2(-0.2, vtemp, pa1);
ptr.scaleAdd2(0.31, vtemp, ptr);
color = "cyan";
} else {
JS.SymmetryDesc.ptemp.scaleAdd2(-1, vtemp, pa1);
this.drawLine(drawSB, "rotLine1", 0.1, pta00, ipt, "red");
this.drawLine(drawSB, "rotLine2", 0.1, ptinv, ipt, "red");
}} else if (!isSpecial) {
scale = pta00.distance(ptr);
this.drawLine(drawSB, "rotLine1", 0.1, pta00, ptr, "red");
this.drawLine(drawSB, "rotLine2", 0.1, ptinv, ptr, "red");
}}} else {
opType = "rot";
vtemp.scale(3 * scaleFactor);
if (isSpecial) {
} else {
if (!isSpaceGroup) {
this.drawLine(drawSB, "rotLine1", 0.1, pta00, ptr, "red");
this.drawLine(drawSB, "rotLine2", 0.1, pt0, ptr, "red");
}}ptr.setT(pa1);
if (pitch1 == 0 && isSpecial) ptr.scaleAdd2(0.25, vtemp, ptr);
}}if (!isSpaceGroup) {
if (ang > 180) {
ang = 180 - ang;
}JS.SymmetryDesc.ptemp.add2(ptr, vtemp);
drawSB.append(this.getDrawID("rotRotArrow")).append(" arrow width 0.1 scale " + JU.PT.escF(scale) + " arc ").append(JU.Escape.eP(ptr)).append(JU.Escape.eP(JS.SymmetryDesc.ptemp));
JS.SymmetryDesc.ptemp.setT(pta00);
if (JS.SymmetryDesc.ptemp.distance(pt0) < 0.1) JS.SymmetryDesc.ptemp.set(Math.random(), Math.random(), Math.random());
drawSB.append(JU.Escape.eP(JS.SymmetryDesc.ptemp));
JS.SymmetryDesc.ptemp.set(0, ang - 5 * Math.signum(ang), 0);
drawSB.append(JU.Escape.eP(JS.SymmetryDesc.ptemp)).append(" color red");
}var d;
var opTransLength = 0;
if (!op.opIsLong && (isSpaceGroupAll && pitch1 > 0 && !haveInversion)) {
ignore = ((opTransLength = op.getOpTrans().length()) > (order == 2 ? 0.71 : order == 3 ? 0.578 : order == 4 ? 0.51 : 0.51));
}if (ignore && JU.Logger.debugging) {
System.out.println("SD ignoring " + op.getOpTrans().length() + " " + op.getOpTitle() + op.xyz);
}var p2 = null;
if (pitch1 == 0 && !haveInversion) {
JS.SymmetryDesc.ptemp.scaleAdd2(0.5, vtemp, pa1);
pa1.scaleAdd2(isSpaceGroup ? -0.5 : -0.45, vtemp, pa1);
if (isSpaceGroupAll && (p2 = op.getOpPoint2()) != null) {
ptr.setT(p2);
uc.toCartesian(ptr, false);
ptr.scaleAdd2(-0.5, vtemp, ptr);
}if (isSpaceGroup) {
this.scaleByOrder(vtemp, order, isccw);
}} else if (isSpaceGroupAll && pitch1 != 0 && !haveInversion && (d = op.getOpTrans().length()) > 0.4) {
if (isccw === Boolean.TRUE) {
} else if (isccw == null) {
} else if (d == 0.5) {
ignore = true;
}} else if (isSpaceGroup && haveInversion) {
this.scaleByOrder(vtemp, order, isccw);
wp = "80";
}if (pitch1 > 0 && !haveInversion) {
wp = "" + (90 - Clazz_floatToInt(vtemp.length() / pitch1 * 90));
}if (!ignore) {
if (screwDir != 0) {
switch (order) {
case 2:
break;
case 3:
break;
case 4:
if (opTransLength > 0.49) screwDir = -2;
break;
case 6:
if (opTransLength > 0.49) screwDir = -3;
 else if (opTransLength > 0.33) screwDir *= 2;
break;
}
color = (screwDir < 0 ? "blue" : "orange");
}var name = opType + "_" + nrot + "rotvector1";
this.drawOrderVector(drawSB, name, "vector", "0.1" + wp, pa1, nrot, screwDir, haveInversion && isSpaceGroupAll, isccw === Boolean.TRUE, vtemp, isTimeReversed ? "gray" : color, title, isSpaceGroupAll);
if (p2 != null) {
this.drawOrderVector(drawSB, name + "2", "vector", "0.1" + wp, ptr, order, screwDir, haveInversion, isccw === Boolean.TRUE, vtemp, isTimeReversed ? "gray" : color, title, isSpaceGroupAll);
}}} else if (isMirrorPlane) {
JS.SymmetryDesc.ptemp.sub2(ptref, pta00);
if (!isSpaceGroup && pta00.distance(ptref) > 0.2) this.drawVector(drawSB, "planeVector", "vector", "0.05", pta00, JS.SymmetryDesc.ptemp, isTimeReversed ? "gray" : "cyan", null);
opType = "plane";
if (trans == null) {
color = "magenta";
} else {
opType = "glide";
switch ((glideType).charCodeAt(0)) {
case 97:
color = "[x4080ff]";
break;
case 98:
color = "blue";
break;
case 99:
color = "cyan";
break;
case 110:
color = "orange";
break;
case 100:
color = "grey";
break;
case 103:
default:
color = "lightgreen";
break;
}
if (!isSpaceGroup) {
this.drawFrameLine("X", ptref, vt1, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "red");
this.drawFrameLine("Y", ptref, vt2, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "green");
this.drawFrameLine("Z", ptref, vt3, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "blue");
}}var points = uc.getCanonicalCopy(margin, true);
var v = this.modelSet.vwr.getTriangulator().intersectPlane(plane, points, 3);
if (v != null) {
var iCoincident = (isSpaceGroup ? op.iCoincident : 0);
planeCenter =  new JU.P3();
for (var i = 0, iv = 0, n = v.size(); i < n; i++) {
var pts = v.get(i);
drawSB.append(this.getDrawID((trans == null ? "mirror_" : glideType + "_g") + "planep" + i)).append(JU.Escape.eP(pts[0])).append(JU.Escape.eP(pts[1]));
if (pts.length == 3) {
if (iCoincident == 0 || (iv % 2 == 0) != (iCoincident == 1)) {
drawSB.append(JU.Escape.eP(pts[2]));
}iv++;
} else {
planeCenter.add(pts[0]);
planeCenter.add(pts[1]);
nPC += 2;
}drawSB.append(" color translucent ").append(color);
if (title != null) drawSB.append(" ").append(JU.PT.esc(title));
}
}if (v == null || v.size() == 0) {
if (isSpaceGroupAll) {
ignore = true;
} else {
JS.SymmetryDesc.ptemp.add2(pa1, ax1);
drawSB.append(this.getDrawID("planeCircle")).append(" scale 2.0 circle ").append(JU.Escape.eP(pa1)).append(JU.Escape.eP(JS.SymmetryDesc.ptemp)).append(" color translucent ").append(color).append(" mesh fill");
if (title != null) drawSB.append(" ").append(JU.PT.esc(title));
}}}if (haveInversion) {
opType = "inv";
if (isInversionOnly) {
drawSB.append(this.getDrawID("inv_point")).append(" diameter 0.4 ").append(JU.Escape.eP(ipt));
if (title != null) drawSB.append(" ").append(JU.PT.esc(title));
JS.SymmetryDesc.ptemp.sub2(ptinv, pta00);
if (!isSpaceGroup) {
this.drawVector(drawSB, "Arrow", "vector", "0.05", pta00, JS.SymmetryDesc.ptemp, isTimeReversed ? "gray" : "cyan", null);
}} else {
if (order == 4) {
drawSB.append(this.getDrawID("RotPoint")).append(" diameter 0.3 color red").append(JU.Escape.eP(ipt));
if (title != null) drawSB.append(" ").append(JU.PT.esc(title));
}if (!isSpaceGroup) {
drawSB.append(" color cyan");
if (!isSpecial) {
JS.SymmetryDesc.ptemp.sub2(pt0, ptinv);
this.drawVector(drawSB, "Arrow", "vector", "0.05", ptinv, JS.SymmetryDesc.ptemp, isTimeReversed ? "gray" : "cyan", null);
}if (options != 1073742066) {
vtemp.setT(vt1);
vtemp.scale(-1);
this.drawFrameLine("X", ptinv, vtemp, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "red");
vtemp.setT(vt2);
vtemp.scale(-1);
this.drawFrameLine("Y", ptinv, vtemp, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "green");
vtemp.setT(vt3);
vtemp.scale(-1);
this.drawFrameLine("Z", ptinv, vtemp, 0.15, JS.SymmetryDesc.ptemp, drawSB, opType, "blue");
}}}}if (trans != null) {
if (isMirrorPlane && isSpaceGroup) {
if (planeCenter != null) {
ptref = planeCenter;
ptref.scale(1 / nPC);
ptref.scaleAdd2(-0.5, trans, ptref);
}} else if (ptref == null) {
ptref = (isSpaceGroup ? pta00 : JU.P3.newP(pta00));
}if (ptref != null && !ignore) {
var isCentered = (glideType == '\0');
color = (isTimeReversed && !haveInversion && !isMirrorPlane && !isRotation ? "darkGray" : "gold");
this.drawVector(drawSB, (isCentered ? "centering_" : glideType + "_g") + "trans_vector", "vector", (isTranslationOnly ? "0.1" : "0.05"), ptref, trans, color, title);
if (isSpaceGroup && !isCentered && !isTranslationOnly) {
JS.SymmetryDesc.ptemp.setT(ptref);
JS.SymmetryDesc.ptemp.add(trans);
JS.SymmetryDesc.ptemp2.setT(trans);
JS.SymmetryDesc.ptemp2.scale(-1);
this.drawVector(drawSB, glideType + "_g" + "trans_vector2", "vector", "0.05", JS.SymmetryDesc.ptemp, JS.SymmetryDesc.ptemp2, color, title);
}}}if (!isSpaceGroup) {
JS.SymmetryDesc.ptemp2.setT(pt0);
JS.SymmetryDesc.ptemp.sub2(pt1, pt0);
JS.SymmetryDesc.ptemp.scaleAdd2(0.9, JS.SymmetryDesc.ptemp, JS.SymmetryDesc.ptemp2);
this.drawLine(drawSB, "frame2X", 0.2, JS.SymmetryDesc.ptemp2, JS.SymmetryDesc.ptemp, "red");
JS.SymmetryDesc.ptemp.sub2(pt2, pt0);
JS.SymmetryDesc.ptemp.scaleAdd2(0.9, JS.SymmetryDesc.ptemp, JS.SymmetryDesc.ptemp2);
this.drawLine(drawSB, "frame2Y", 0.2, JS.SymmetryDesc.ptemp2, JS.SymmetryDesc.ptemp, "green");
JS.SymmetryDesc.ptemp.sub2(pt3, pt0);
JS.SymmetryDesc.ptemp.scaleAdd2(0.9, JS.SymmetryDesc.ptemp, JS.SymmetryDesc.ptemp2);
this.drawLine(drawSB, "frame2Z", 0.2, JS.SymmetryDesc.ptemp2, JS.SymmetryDesc.ptemp, "purple");
drawSB.append("\nsym_point = " + JU.Escape.eP(pta00));
drawSB.append("\nvar p0 = " + JU.Escape.eP(JS.SymmetryDesc.ptemp2));
if (Clazz_instanceOf(pta00,"JM.Atom")) {
drawSB.append("\nvar set2 = within(0.2,p0);if(!set2){set2 = within(0.2,p0.uxyz.xyz)}");
drawSB.append("\n set2 &= {_" + (pta00).getElementSymbol() + "}");
} else {
drawSB.append("\nvar set2 = p0.uxyz");
}drawSB.append("\nsym_target = set2;if (set2) {");
if (!isSpecial && options != 1073742066 && ptTarget == null && !haveTranslation) {
drawSB.append(this.getDrawID("offsetFrameX")).append(" diameter 0.20 @{set2.xyz} @{set2.xyz + ").append(JU.Escape.eP(vt1)).append("*0.9} color red");
drawSB.append(this.getDrawID("offsetFrameY")).append(" diameter 0.20 @{set2.xyz} @{set2.xyz + ").append(JU.Escape.eP(vt2)).append("*0.9} color green");
drawSB.append(this.getDrawID("offsetFrameZ")).append(" diameter 0.20 @{set2.xyz} @{set2.xyz + ").append(JU.Escape.eP(vt3)).append("*0.9} color purple");
}drawSB.append("\n}\n");
}cmds = drawSB.toString();
if (JU.Logger.debugging) JU.Logger.info(cmds);
drawSB = null;
}}if (trans == null) ftrans = null;
if (isScrew) {
trans = JU.V3.newV(ax1);
JS.SymmetryDesc.ptemp.setT(trans);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
ftrans = JU.V3.newV(JS.SymmetryDesc.ptemp);
}if (isMirrorPlane) {
ang1 = 0;
}if (haveInversion) {
if (isInversionOnly) {
pa1 = null;
ax1 = null;
trans = null;
ftrans = null;
}} else if (isTranslation) {
pa1 = null;
ax1 = null;
}if (ax1 != null) ax1.normalize();
var xyzNew = null;
if (bsInfo.get(0) || bsInfo.get(17)) {
xyzNew = (op.isBio ? m2.toString() : op.modDim > 0 ? op.xyzOriginal : JS.SymmetryOperation.getXYZFromMatrix(m2, false, false, false));
if (isMagnetic) xyzNew = op.fixMagneticXYZ(m2, xyzNew, true);
}var ret =  new Array(20);
for (var i = bsInfo.nextSetBit(0); i >= 0; i = bsInfo.nextSetBit(i + 1)) {
switch (i) {
case 0:
ret[i] = xyzNew;
break;
case 19:
if (ptFrom != null && ptTarget == null && !op.isBio && op.modDim == 0) {
var xyzN;
JS.SymmetryDesc.pta02.setT(ptFrom);
uc.toFractional(JS.SymmetryDesc.pta02, true);
m2.rotTrans(JS.SymmetryDesc.pta02);
JS.SymmetryDesc.ptemp.setT(JS.SymmetryDesc.pta02);
uc.unitize(JS.SymmetryDesc.pta02);
JS.SymmetryDesc.vtrans.sub2(JS.SymmetryDesc.pta02, JS.SymmetryDesc.ptemp);
m2 = JU.M4.newM4(op);
m2.add(JS.SymmetryDesc.vtrans);
xyzN = JS.SymmetryOperation.getXYZFromMatrix(m2, false, false, false);
if (isMagnetic) xyzN = op.fixMagneticXYZ(m2, xyzN, true);
ret[i] = xyzN;
}break;
case 1:
ret[i] = op.xyzOriginal;
break;
case 2:
ret[i] = info1;
break;
case 3:
ret[i] = cmds;
break;
case 4:
ret[i] = JS.SymmetryDesc.approx0(ftrans);
break;
case 5:
ret[i] = JS.SymmetryDesc.approx0(trans);
break;
case 6:
ret[i] = JS.SymmetryDesc.approx0(ipt);
break;
case 7:
ret[i] = JS.SymmetryDesc.approx0(pa1 != null && bsInfo.get(22) ? pta00 : pa1);
break;
case 8:
ret[i] = (plane == null ? JS.SymmetryDesc.approx0(ax1) : null);
break;
case 9:
ret[i] = (ang1 != 0 ? Integer.$valueOf(ang1) : null);
break;
case 10:
ret[i] = m2;
break;
case 11:
ret[i] = (JS.SymmetryDesc.vtrans.lengthSquared() > 0 ? JS.SymmetryDesc.vtrans : null);
break;
case 12:
ret[i] = op.getCentering();
break;
case 13:
ret[i] = Integer.$valueOf(op.timeReversal);
break;
case 14:
if (plane != null && bsInfo.get(22)) {
var d = JU.Measure.distanceToPlane(plane, pta00);
plane.w -= d;
}ret[i] = plane;
break;
case 15:
ret[i] = type;
break;
case 16:
ret[i] = Integer.$valueOf(op.number);
break;
case 17:
var cift = null;
if (!op.isBio && !xyzNew.equals(op.xyzOriginal)) {
if (op.number > 0) {
var orig = JS.SymmetryOperation.getMatrixFromXYZ(op.xyzOriginal, null, false);
orig.sub(m2);
cift =  new JU.P3();
orig.getTranslation(cift);
}}var cifi = (op.number < 0 ? 0 : op.number);
ret[i] = cifi + (cift == null ? " [0 0 0]" : " [" + Clazz_floatToInt(-cift.x) + " " + Clazz_floatToInt(-cift.y) + " " + Clazz_floatToInt(-cift.z) + "]");
break;
case 18:
ret[i] = op.xyzCanonical;
break;
}
}
return ret;
}, "JS.SymmetryOperation,J.api.SymmetryInterface,JU.P3,JU.P3,~S,~N,~N,~B,JU.BS,~B,~B");
c$.fixGlideTrans = Clazz_defineMethod(c$, "fixGlideTrans", 
function(ftrans){
ftrans.x = JS.SymmetryDesc.fixGlideX(ftrans.x);
ftrans.y = JS.SymmetryDesc.fixGlideX(ftrans.y);
ftrans.z = JS.SymmetryDesc.fixGlideX(ftrans.z);
}, "JU.V3");
c$.fixGlideX = Clazz_defineMethod(c$, "fixGlideX", 
function(x){
var n48 = Math.round(x * 48.001);
switch (n48) {
case 36:
return -0.25;
case -36:
return 0.25;
default:
return x;
}
}, "~N");
Clazz_defineMethod(c$, "scaleByOrder", 
function(v, order, isccw){
v.scale(1 + (0.3 / order) + (isccw == null ? 0 : isccw === Boolean.TRUE ? 0.02 : -0.02));
}, "JU.V3,~N,Boolean");
c$.checkHandedness = Clazz_defineMethod(c$, "checkHandedness", 
function(uc, ax1){
var a;
var b;
var c;
JS.SymmetryDesc.ptemp.set(1, 0, 0);
uc.toCartesian(JS.SymmetryDesc.ptemp, false);
a = JS.SymmetryDesc.approx0d(JS.SymmetryDesc.ptemp.dot(ax1));
JS.SymmetryDesc.ptemp.set(0, 1, 0);
uc.toCartesian(JS.SymmetryDesc.ptemp, false);
b = JS.SymmetryDesc.approx0d(JS.SymmetryDesc.ptemp.dot(ax1));
JS.SymmetryDesc.ptemp.set(0, 0, 1);
uc.toCartesian(JS.SymmetryDesc.ptemp, false);
c = JS.SymmetryDesc.approx0d(JS.SymmetryDesc.ptemp.dot(ax1));
return (a == 0 ? (b == 0 ? c > 0 : b > 0) : c == 0 ? a > 0 : (b == 0 ? c > 0 : a * b * c > 0));
}, "J.api.SymmetryInterface,JU.P3");
Clazz_defineMethod(c$, "drawLine", 
function(s, id, diameter, pt0, pt1, color){
s.append(this.getDrawID(id)).append(" diameter ").appendD(diameter).append(JU.Escape.eP(pt0)).append(JU.Escape.eP(pt1)).append(" color ").append(color);
}, "JU.SB,~S,~N,JU.P3,JU.P3,~S");
Clazz_defineMethod(c$, "drawFrameLine", 
function(xyz, pt, v, width, ptemp, sb, key, color){
ptemp.setT(pt);
ptemp.add(v);
this.drawLine(sb, key + "Pt" + xyz, width, pt, ptemp, "translucent " + color);
}, "~S,JU.P3,JU.V3,~N,JU.P3,JU.SB,~S,~S");
Clazz_defineMethod(c$, "drawVector", 
function(sb, label, type, d, pt1, v, color, title){
if (type.equals("vline")) {
JS.SymmetryDesc.ptemp2.add2(pt1, v);
type = "";
v = JS.SymmetryDesc.ptemp2;
}d += " ";
sb.append(this.getDrawID(label)).append(" diameter ").append(d).append(type).append(JU.Escape.eP(pt1)).append(JU.Escape.eP(v)).append(" color ").append(color);
if (title != null) sb.append(" \"" + title + "\"");
}, "JU.SB,~S,~S,~S,JU.T3,JU.T3,~S,~S");
Clazz_defineMethod(c$, "drawOrderVector", 
function(sb, label, type, d, pt, order, screwDir, haveInversion, isCCW, vtemp, color, title, isSpaceGroupAll){
this.drawVector(sb, label, type, d, pt, vtemp, color, title);
if (order == 2 || haveInversion && !isCCW) return;
var poly = JS.SymmetryDesc.getPolygon(order, !haveInversion ? 0 : isCCW ? 1 : -1, haveInversion, pt, vtemp);
var l = poly[0];
sb.append(this.getDrawID(label + "_key")).append(" POLYGON ").appendI(l.size());
for (var i = 0, n = l.size(); i < n; i++) sb.appendO(l.get(i));

sb.append(" color ").append(color);
if (screwDir != 0 && isSpaceGroupAll) {
poly = JS.SymmetryDesc.getPolygon(order, screwDir, haveInversion, pt, vtemp);
sb.append(this.getDrawID(label + "_key2"));
l = poly[0];
sb.append(" POLYGON ").appendI(l.size());
for (var i = 0, n = l.size(); i < n; i++) sb.appendO(l.get(i));

l = poly[1];
sb.appendI(l.size());
for (var i = 0, n = l.size(); i < n; i++) sb.appendO(JU.PT.toJSON(null, l.get(i)));

sb.append(" color ").append(color);
}}, "JU.SB,~S,~S,~S,JU.P3,~N,~N,~B,~B,JU.V3,~S,~S,~B");
c$.getPolygon = Clazz_defineMethod(c$, "getPolygon", 
function(order, screwDir, haveInversion, pt0, v){
var scale = (haveInversion ? 0.6 : 0.4);
var pts =  new JU.Lst();
var faces =  new JU.Lst();
var offset = JU.V3.newV(v);
offset.scale(0);
offset.add(pt0);
var vZ = JU.V3.new3(0, 0, 1);
var vperp =  new JU.V3();
var m =  new JU.M3();
vperp.cross(vZ, v);
if (vperp.length() < 0.01) {
m.m00 = m.m11 = m.m22 = 1;
} else {
vperp.normalize();
var a = vZ.angle(v);
m.setAA(JU.A4.newVA(vperp, a));
}var rad = (6.283185307179586 / order * (screwDir < 0 ? -1 : 1));
var vt =  new JU.V3();
var ptLast = null;
for (var plast = 0, p = 0, i = 0, n = (screwDir == 0 ? order : order + 1); i < n; i++) {
var pt =  new JU.P3();
pt.x = Math.cos(rad * i) * scale;
pt.y = Math.sin(rad * i) * scale;
m.rotate(pt);
pt.add(offset);
if (i < order) {
pts.addLast(pt);
}if (!haveInversion && screwDir != 0 && (i % screwDir == 0) && ptLast != null) {
vt.sub2(pt, ptLast);
var p2 = (i < order ? p++ : 0);
var pt1 = JU.P3.newP(pt);
pt1.scaleAdd2(1, pt, pt1);
pt1.scaleAdd2(-1, offset, pt1);
pts.addLast(pt1);
faces.addLast( Clazz_newIntArray(-1, [plast, p++, p2, 0]));
plast = p2;
} else {
plast = p++;
}ptLast = pt;
}
return  Clazz_newArray(-1, [pts, faces]);
}, "~N,~N,~B,JU.P3,JU.V3");
c$.rotTransCart = Clazz_defineMethod(c$, "rotTransCart", 
function(op, uc, pt00, vtrans){
var p0 = JU.P3.newP(pt00);
uc.toFractional(p0, false);
op.rotTrans(p0);
p0.add(vtrans);
uc.toCartesian(p0, false);
return p0;
}, "JS.SymmetryOperation,J.api.SymmetryInterface,JU.P3,JU.V3");
c$.strCoord = Clazz_defineMethod(c$, "strCoord", 
function(p, isBio){
JS.SymmetryDesc.approx0(p);
return (isBio ? "(" + p.x + " " + p.y + " " + p.z + ")" : JS.SymmetryOperation.fcoord(p, " "));
}, "JU.T3,~B");
c$.approx0 = Clazz_defineMethod(c$, "approx0", 
function(pt){
if (pt != null) {
pt.x = JS.SymmetryDesc.approx0d(pt.x);
pt.y = JS.SymmetryDesc.approx0d(pt.y);
pt.z = JS.SymmetryDesc.approx0d(pt.z);
}return pt;
}, "JU.T3");
c$.approx0d = Clazz_defineMethod(c$, "approx0d", 
function(x){
return (Math.abs(x) < 0.0001 ? 0 : x);
}, "~N");
Clazz_defineMethod(c$, "getSymmetryInfo", 
function(iModel, iatom, uc, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, isSpaceGroup){
var returnType = 0;
var nullRet = JS.SymmetryDesc.nullReturn(type);
switch (type) {
case 1073741994:
return "" + uc.getLatticeType();
case 1073742001:
returnType = 1825200146;
break;
case 135176:
returnType = 135176;
break;
case 1275068418:
returnType = JS.SymmetryDesc.getType(id);
switch (returnType) {
case 1153433601:
case 1073741961:
case 1073742001:
case 134217751:
case 1086326789:
case 36868:
type = returnType;
break;
default:
returnType = JS.SymmetryDesc.getKeyType(id);
break;
}
break;
}
var bsInfo = JS.SymmetryDesc.getInfoBS(returnType);
var isSpaceGroupAll = (nth == -2);
var iop = op;
var offset = (options == 1073742066 && (type == 1153433601 || type == 134217751) ? pt2 : null);
if (offset != null) pt2 = null;
var info = null;
var xyzOriginal = null;
var ops = null;
if (pt2 == null) {
if (xyz == null) {
ops = (isSpaceGroupAll ? uc.getAdditionalOperations() : uc.getSymmetryOperations());
if (ops == null || Math.abs(op) > ops.length) return nullRet;
if (op == 0) return nullRet;
iop = Math.abs(op) - 1;
xyz = (translation == null ? ops[iop].xyz : ops[iop].getxyzTrans(translation));
xyzOriginal = ops[iop].xyzOriginal;
} else {
iop = op = 0;
}var symTemp =  new JS.Symmetry();
symTemp.setSpaceGroup(false);
var isBio = (uc != null && uc.isBio());
var i = (isBio ? symTemp.addBioMoleculeOperation((uc.getSpaceGroup()).finalOperations[iop], op < 0) : symTemp.addSpaceGroupOperation((op < 0 ? "!" : "=") + xyz, Math.abs(op)));
if (i < 0) return nullRet;
var opTemp = symTemp.getSpaceGroupOperation(i);
if (isSpaceGroup) {
opTemp.iCoincident = ops[iop].iCoincident;
}if (isSpaceGroupAll) {
opTemp.isIrrelevant = ops[iop].isIrrelevant;
}if (xyzOriginal != null) opTemp.xyzOriginal = xyzOriginal;
opTemp.number = op;
if (!isBio) opTemp.getCentering();
if (pt == null && iatom >= 0) pt = this.modelSet.at[iatom];
if (type == 134217751 || type == 1153433601) {
if (isBio || pt == null) return nullRet;
symTemp.setUnitCell(uc);
JS.SymmetryDesc.ptemp.setT(pt);
uc.toFractional(JS.SymmetryDesc.ptemp, false);
if (Float.isNaN(JS.SymmetryDesc.ptemp.x)) return nullRet;
var sympt =  new JU.P3();
symTemp.newSpaceGroupPoint(JS.SymmetryDesc.ptemp, i, null, 0, 0, 0, sympt);
if (options == 1073742066) {
uc.unitize(sympt);
sympt.add(offset);
}symTemp.toCartesian(sympt, false);
var ret = sympt;
return (type == 1153433601 ? this.getAtom(uc, iModel, iatom, ret) : ret);
}info = this.createInfoArray(opTemp, uc, pt, null, (id == null ? "sym" : id), scaleFactor, options, (translation != null), bsInfo, isSpaceGroup, isSpaceGroupAll);
if (type == 1275068418 && id != null) {
returnType = JS.SymmetryDesc.getKeyType(id);
}} else {
var stype = "info";
var asString = false;
switch (type) {
case 1275068418:
returnType = JS.SymmetryDesc.getKeyType(id);
id = stype = null;
if (nth == 0) nth = -1;
break;
case 1073742001:
id = stype = null;
if (nth == 0) nth = -1;
asString = true;
bsInfo.set(21);
bsInfo.set(0);
bsInfo.set(19);
break;
case 135176:
if (id == null) id = (isSpaceGroup ? "sg" : "sym");
stype = "all";
asString = true;
break;
case 1153433601:
id = stype = null;
default:
if (nth == 0) nth = 1;
}
var ret1 = this.getSymopInfoForPoints(uc, iModel, op, translation, pt, pt2, id, stype, scaleFactor, nth, options, bsInfo);
if (asString) {
return ret1;
}if ((typeof(ret1)=='string')) return nullRet;
info = ret1;
if (type == 1153433601) {
if (!(Clazz_instanceOf(pt,"JM.Atom")) && !(Clazz_instanceOf(pt2,"JM.Atom"))) iatom = -1;
return (info == null ? nullRet : this.getAtom(uc, iModel, iatom, info[7]));
}}if (info == null) return nullRet;
var isList = (info.length > 0 && Clazz_instanceOf(info[0],Array));
if (nth < 0 && op <= 0 && xyz == null && (type == 1275068418 || isList)) {
if (type == 1275068418 && info.length > 0 && !(Clazz_instanceOf(info[0],Array))) info =  Clazz_newArray(-1, [info]);
var lst =  new JU.Lst();
for (var i = 0; i < info.length; i++) lst.addLast(JS.SymmetryDesc.getInfo(info[i], returnType < 0 ? returnType : type));

return lst;
} else if (returnType < 0 && (nth >= 0 || op > 0 || xyz != null)) {
type = returnType;
}if (nth > 0 && isList) info = info[0];
if (type == 135176 && isSpaceGroup && nth == -2) type = 134217764;
return JS.SymmetryDesc.getInfo(info, type);
}, "~N,~N,J.api.SymmetryInterface,~S,~N,JU.P3,JU.P3,JU.P3,~S,~N,~N,~N,~N,~B");
Clazz_defineMethod(c$, "getAtom", 
function(uc, iModel, iAtom, sympt){
var bsElement = null;
if (iAtom >= 0) this.modelSet.getAtomBitsMDa(1094715402, Integer.$valueOf(this.modelSet.at[iAtom].getElementNumber()), bsElement =  new JU.BS());
var bsResult =  new JU.BS();
this.modelSet.getAtomsWithin(0.02, sympt, bsResult, iModel);
if (bsElement != null) bsResult.and(bsElement);
if (bsResult.isEmpty()) {
sympt = JU.P3.newP(sympt);
uc.toUnitCell(sympt, null);
uc.toCartesian(sympt, false);
this.modelSet.getAtomsWithin(0.02, sympt, bsResult, iModel);
if (bsElement != null) bsResult.and(bsElement);
}return bsResult;
}, "J.api.SymmetryInterface,~N,~N,JU.T3");
Clazz_defineMethod(c$, "getSymopInfoForPoints", 
function(sym, modelIndex, symOp, translation, pt1, pt2, drawID, stype, scaleFactor, nth, options, bsInfo){
var asString = (bsInfo.get(21) || bsInfo.get(3) && bsInfo.cardinality() == 3);
bsInfo.clear(21);
var ret = (asString ? "" : null);
var sginfo = this.getSpaceGroupInfo(sym, modelIndex, null, symOp, pt1, pt2, drawID, scaleFactor, nth, false, true, options, null, bsInfo);
if (sginfo == null) return ret;
var infolist = sginfo.get("operations");
if (infolist == null) return ret;
var sb = (asString ?  new JU.SB() : null);
symOp--;
var isAll = (!asString && symOp < 0);
var strOperations = sginfo.get("symmetryInfo");
var labelOnly = "label".equals(stype);
var n = 0;
for (var i = 0; i < infolist.length; i++) {
if (infolist[i] == null || symOp >= 0 && symOp != i) continue;
if (!asString) {
if (!isAll) return infolist[i];
infolist[n++] = infolist[i];
continue;
}if (drawID != null) return (infolist[i][3]) + "\nprint " + JU.PT.esc(strOperations);
if (sb.length() > 0) sb.appendC('\n');
if (!labelOnly) {
if (symOp < 0) sb.appendI(i + 1).appendC('\t');
sb.append(infolist[i][0]).appendC('\t');
}sb.append(infolist[i][2]);
}
if (!asString) {
var a =  new Array(n);
for (var i = 0; i < n; i++) a[i] = infolist[i];

return a;
}if (sb.length() == 0) return (drawID != null ? "draw ID \"" + drawID + "*\" delete" : ret);
return sb.toString();
}, "J.api.SymmetryInterface,~N,~N,JU.P3,JU.P3,JU.P3,~S,~S,~N,~N,~N,JU.BS");
Clazz_defineMethod(c$, "getDrawID", 
function(id){
return this.drawID + id + "\" ";
}, "~S");
Clazz_defineMethod(c$, "getSymopInfo", 
function(iAtom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList){
if (type == 0) type = JS.SymmetryDesc.getType(id);
var ret = (type == 1153433601 ?  new JU.BS() : "");
var iModel = (iAtom >= 0 ? this.modelSet.at[iAtom].mi : this.modelSet.vwr.am.cmi);
if (iModel < 0) return ret;
var uc = this.modelSet.am[iModel].biosymmetry;
if (uc == null && (uc = this.modelSet.getUnitCell(iModel)) == null) {
uc =  new JS.Symmetry().setUnitCellFromParams(null, false, NaN);
}if (type != 135176 || op != 2147483647 && opList == null) {
return this.getSymmetryInfo(iModel, iAtom, uc, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, false);
}if (uc == null) return ret;
var isSpaceGroup = (xyz == null && nth < 0 && opList == null);
var s = "";
var ops = (isSpaceGroup && nth == -2 ? uc.getAdditionalOperations() : uc.getSymmetryOperations());
if (ops != null) {
if (id == null) id = "sg";
var n = ops.length;
if (pt != null && pt2 == null || opList != null) {
if (opList == null) opList = uc.getInvariantSymops(pt, null);
n = opList.length;
for (var i = 0; i < n; i++) {
if (nth > 0 && nth != i + 1) continue;
op = opList[i];
s += this.getSymmetryInfo(iModel, iAtom, uc, xyz, op, translation, pt, pt2, id + op, 135176, scaleFactor, nth, options, pt == null);
}
} else {
for (op = 1; op <= n; op++) s += this.getSymmetryInfo(iModel, iAtom, uc, xyz, op, translation, pt, pt2, id + op, 135176, scaleFactor, nth, options, true);

}}return s;
}, "~N,~S,~N,JU.P3,JU.P3,JU.P3,~S,~N,~N,~N,~N,~A");
Clazz_defineMethod(c$, "getSpaceGroupInfo", 
function(sym, modelIndex, sgName, symOp, pt1, pt2, drawID, scaleFactor, nth, isFull, isForModel, options, cellInfo, bsInfo){
if (bsInfo == null) {
bsInfo =  new JU.BS();
bsInfo.setBits(0, JS.SymmetryDesc.keys.length);
bsInfo.clear(19);
}var matrixOnly = (bsInfo.cardinality() == 1 && bsInfo.get(10));
var info = null;
var isStandard = (!matrixOnly && pt1 == null && drawID == null && nth <= 0 && bsInfo.cardinality() >= JS.SymmetryDesc.keys.length);
var isBio = false;
var sgNote = null;
var haveName = (sgName != null && sgName.length > 0);
var haveRawName = (haveName && sgName.indexOf("[--]") >= 0);
if (isForModel || !haveName) {
var saveModelInfo = (isStandard && symOp == 0);
if (matrixOnly) {
cellInfo = sym;
} else {
if (modelIndex < 0) modelIndex = (Clazz_instanceOf(pt1,"JM.Atom") ? (pt1).mi : this.modelSet.vwr.am.cmi);
if (modelIndex < 0) sgNote = "no single current model";
 else if (cellInfo == null && !(isBio = (cellInfo = this.modelSet.am[modelIndex].biosymmetry) != null) && (cellInfo = this.modelSet.getUnitCell(modelIndex)) == null) sgNote = "not applicable";
if (sgNote != null) {
info =  new java.util.Hashtable();
info.put("spaceGroupInfo", "");
info.put("spaceGroupNote", sgNote);
info.put("symmetryInfo", "");
} else if (isStandard) {
info = this.modelSet.getInfo(modelIndex, "spaceGroupInfo");
}if (info != null) return info;
sgName = cellInfo.getSpaceGroupName();
}info =  new java.util.Hashtable();
var ops = cellInfo.getSymmetryOperations();
var sg = (isBio ? (cellInfo).spaceGroup : null);
var slist = (haveRawName ? "" : null);
var opCount = 0;
if (ops != null) {
if (!matrixOnly) {
if (isBio) sym.setSpaceGroupTo(JS.SpaceGroup.getNull(false, false, false));
 else sym.setSpaceGroup(false);
}if (ops[0].timeReversal != 0) (sym.getSpaceGroupOperation(0)).timeReversal = 1;
var infolist =  new Array(ops.length);
var sops = "";
var i0 = (drawID == null || pt1 == null || pt2 == null && nth < 0 ? 0 : 1);
for (var i = i0, nop = 0; i < ops.length && nop != nth; i++) {
var op = ops[i];
var xyzOriginal = op.xyzOriginal;
var iop;
if (matrixOnly) {
iop = i;
} else {
var isNewIncomm = (i == 0 && op.xyz.indexOf("x4") >= 0);
iop = (!isNewIncomm && sym.getSpaceGroupOperation(i) != null ? i : isBio ? sym.addBioMoleculeOperation(sg.finalOperations[i], false) : sym.addSpaceGroupOperation("=" + op.xyz, i + 1));
if (iop < 0) continue;
op = sym.getSpaceGroupOperation(i);
if (op == null) continue;
op.xyzOriginal = xyzOriginal;
}if (op.timeReversal != 0 || op.modDim > 0) isStandard = false;
if (slist != null) slist += ";" + op.xyz;
var ret = (symOp > 0 && symOp - 1 != iop ? null : this.createInfoArray(op, cellInfo, pt1, pt2, drawID, scaleFactor, options, false, bsInfo, false, false));
if (ret != null) {
nop++;
if (nth > 0 && nop != nth) continue;
infolist[i] = ret;
if (!matrixOnly) sops += "\n" + (i + 1) + (drawID != null && nop == 1 ? "*" : "") + "\t" + ret[bsInfo.get(19) ? 19 : 0] + "\t  " + ret[2];
opCount++;
if (symOp > 0) break;
}}
info.put("operations", infolist);
if (!matrixOnly) info.put("symmetryInfo", (sops.length == 0 ? "" : sops.substring(1)));
}if (matrixOnly) {
return info;
}sgNote = (opCount == 0 ? "\n no symmetry operations" : nth <= 0 && symOp <= 0 ? "\n" + opCount + " symmetry operation" + (opCount == 1 ? ":\n" : "s:\n") : "");
if (slist != null) sgName = slist.substring(slist.indexOf(";") + 1);
if (saveModelInfo) this.modelSet.setInfo(modelIndex, "spaceGroupInfo", info);
} else {
info =  new java.util.Hashtable();
}info.put("spaceGroupName", sgName);
info.put("spaceGroupNote", sgNote == null ? "" : sgNote);
var data;
if (isBio) {
data = sgName;
} else {
if (haveName && !haveRawName) sym.setSpaceGroupName(sgName);
data = sym.getSpaceGroupInfoObj(sgName, (cellInfo == null ? null : cellInfo.getUnitCellParams()), isFull, !isForModel);
if (data == null || data.equals("?")) {
data = "?";
info.put("spaceGroupNote", "could not identify space group from name: " + sgName + "\nformat: show spacegroup \"2\" or \"P 2c\" " + "or \"C m m m\" or \"x, y, z;-x ,-y, -z\"");
}}info.put("spaceGroupInfo", data);
return info;
}, "J.api.SymmetryInterface,~N,~S,~N,JU.P3,JU.P3,~S,~N,~N,~B,~B,~N,J.api.SymmetryInterface,JU.BS");
Clazz_defineMethod(c$, "getTransform", 
function(uc, ops, fracA, fracB, best){
if (JS.SymmetryDesc.pta01 == null) {
JS.SymmetryDesc.pta01 =  new JU.P3();
JS.SymmetryDesc.pta02 =  new JU.P3();
JS.SymmetryDesc.ptemp =  new JU.P3();
JS.SymmetryDesc.vtrans =  new JU.V3();
}JS.SymmetryDesc.pta02.setT(fracB);
JS.SymmetryDesc.vtrans.setT(JS.SymmetryDesc.pta02);
uc.unitize(JS.SymmetryDesc.pta02);
var dmin = 3.4028235E38;
var imin = -1;
for (var i = 0, n = ops.length; i < n; i++) {
var op = ops[i];
JS.SymmetryDesc.pta01.setT(fracA);
op.rotTrans(JS.SymmetryDesc.pta01);
JS.SymmetryDesc.ptemp.setT(JS.SymmetryDesc.pta01);
uc.unitize(JS.SymmetryDesc.pta01);
var d = JS.SymmetryDesc.pta01.distanceSquared(JS.SymmetryDesc.pta02);
if (d < 1.96E-6) {
JS.SymmetryDesc.vtrans.sub(JS.SymmetryDesc.ptemp);
JS.SymmetryOperation.normalize12ths(JS.SymmetryDesc.vtrans);
var m2 = JU.M4.newM4(op);
m2.add(JS.SymmetryDesc.vtrans);
JS.SymmetryDesc.pta01.setT(fracA);
m2.rotTrans(JS.SymmetryDesc.pta01);
uc.unitize(JS.SymmetryDesc.pta01);
d = JS.SymmetryDesc.pta01.distanceSquared(JS.SymmetryDesc.pta02);
if (d >= 1.96E-6) {
continue;
}return m2;
}if (d < dmin) {
dmin = d;
imin = i;
}}
if (best) {
var op = ops[imin];
JS.SymmetryDesc.pta01.setT(fracA);
op.rotTrans(JS.SymmetryDesc.pta01);
uc.unitize(JS.SymmetryDesc.pta01);
}return null;
}, "JS.UnitCell,~A,JU.P3,JU.P3,~B");
c$.keys =  Clazz_newArray(-1, ["xyz", "xyzOriginal", "label", null, "fractionalTranslation", "cartesianTranslation", "inversionCenter", null, "axisVector", "rotationAngle", "matrix", "unitTranslation", "centeringVector", "timeReversal", "plane", "_type", "id", "cif2", "xyzCanonical", "xyzNormalized"]);
c$.ptemp =  new JU.P3();
c$.ptemp2 =  new JU.P3();
c$.pta01 =  new JU.P3();
c$.pta02 =  new JU.P3();
c$.vtrans =  new JU.V3();
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JU.SimpleUnitCell", "JU.P3", "JV.JC"], "JS.UnitCell", ["java.util.Hashtable", "JU.AU", "$.Lst", "$.M3", "$.M4", "$.P4", "$.PT", "$.Quat", "$.V3", "J.api.Interface", "JS.Symmetry", "JU.BoxInfo", "$.Escape"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.moreInfo = null;
this.name = "";
this.vertices = null;
this.fractionalOffset = null;
this.allFractionalRelative = false;
this.cartesianOffset = null;
this.unitCellMultiplier = null;
this.unitCellMultiplied = null;
this.f2c = null;
Clazz_instantialize(this, arguments);}, JS, "UnitCell", JU.SimpleUnitCell, Cloneable);
Clazz_prepareFields (c$, function(){
this.cartesianOffset =  new JU.P3();
});
c$.fromOABC = Clazz_defineMethod(c$, "fromOABC", 
function(oabc, setRelative){
var c =  new JS.UnitCell();
if (oabc.length == 3) oabc =  Clazz_newArray(-1, [ new JU.P3(), oabc[0], oabc[1], oabc[2]]);
var parameters =  Clazz_newFloatArray(-1, [-1, 0, 0, 0, 0, 0, oabc[1].x, oabc[1].y, oabc[1].z, oabc[2].x, oabc[2].y, oabc[2].z, oabc[3].x, oabc[3].y, oabc[3].z]);
c.init(parameters);
c.allFractionalRelative = setRelative;
c.initUnitcellVertices();
c.setCartesianOffset(oabc[0]);
return c;
}, "~A,~B");
c$.fromParams = Clazz_defineMethod(c$, "fromParams", 
function(params, setRelative, slop){
var c =  new JS.UnitCell();
c.init(params);
c.initUnitcellVertices();
c.allFractionalRelative = setRelative;
c.setPrecision(slop);
if (params.length > 26) params[26] = slop;
return c;
}, "~A,~B,~N");
c$.cloneUnitCell = Clazz_defineMethod(c$, "cloneUnitCell", 
function(uc){
var ucnew = null;
try {
ucnew = uc.clone();
} catch (e) {
if (Clazz_exceptionOf(e,"CloneNotSupportedException")){
} else {
throw e;
}
}
return ucnew;
}, "JS.UnitCell");
Clazz_defineMethod(c$, "checkDistance", 
function(f1, f2, distance, dx, iRange, jRange, kRange, ptOffset){
var p1 = JU.P3.newP(f1);
this.toCartesian(p1, true);
for (var i = -iRange; i <= iRange; i++) for (var j = -jRange; j <= jRange; j++) for (var k = -kRange; k <= kRange; k++) {
ptOffset.set(f2.x + i, f2.y + j, f2.z + k);
this.toCartesian(ptOffset, true);
var d = p1.distance(ptOffset);
if (dx > 0 ? Math.abs(d - distance) <= dx : d <= distance && d > 0.1) {
ptOffset.set(i, j, k);
return true;
}}


return false;
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz_defineMethod(c$, "checkPeriodic", 
function(pt){
switch (this.dimension) {
case 3:
if (pt.z < -this.slop || pt.z > 1 - this.slop) return false;
case 2:
if (pt.y < -this.slop || pt.y > 1 - this.slop) return false;
case 1:
if (pt.x < -this.slop || pt.x > 1 - this.slop) return false;
}
return true;
}, "JU.P3");
Clazz_defineMethod(c$, "dumpInfo", 
function(isDebug, multiplied){
var m = (multiplied ? this.getUnitCellMultiplied() : this);
if (m !== this) return m.dumpInfo(isDebug, false);
return "a=" + this.a + ", b=" + this.b + ", c=" + this.c + ", alpha=" + this.alpha + ", beta=" + this.beta + ", gamma=" + this.gamma + "\noabc=" + JU.Escape.eAP(this.getUnitCellVectors()) + "\nvolume=" + this.volume + (isDebug ? "\nfractional to cartesian: " + this.matrixFractionalToCartesian + "\ncartesian to fractional: " + this.matrixCartesianToFractional : "");
}, "~B,~B");
Clazz_defineMethod(c$, "fix000", 
function(x){
return (Math.abs(x) < 0.001 ? 0 : x);
}, "~N");
Clazz_defineMethod(c$, "fixFloor", 
function(d){
return (d == 1 ? 0 : d);
}, "~N");
Clazz_defineMethod(c$, "getCanonicalCopy", 
function(scale, withOffset){
var pts = this.getScaledCell(withOffset);
return JU.BoxInfo.getCanonicalCopy(pts, scale);
}, "~N,~B");
Clazz_defineMethod(c$, "getCanonicalCopyTrimmed", 
function(frac, scale){
var pts = this.getScaledCellMult(frac, true);
return JU.BoxInfo.getCanonicalCopy(pts, scale);
}, "JU.P3,~N");
Clazz_defineMethod(c$, "getCartesianOffset", 
function(){
return this.cartesianOffset;
});
Clazz_defineMethod(c$, "getCellWeight", 
function(pt){
var f = 1;
if (pt.x <= this.slop || pt.x >= 1 - this.slop) f /= 2;
if (pt.y <= this.slop || pt.y >= 1 - this.slop) f /= 2;
if (pt.z <= this.slop || pt.z >= 1 - this.slop) f /= 2;
return f;
}, "JU.P3");
Clazz_defineMethod(c$, "getConventionalUnitCell", 
function(latticeType, primitiveToCrystal){
var oabc = this.getUnitCellVectors();
if (!latticeType.equals("P") || primitiveToCrystal != null) this.toFromPrimitive(false, latticeType.charAt(0), oabc, primitiveToCrystal);
return oabc;
}, "~S,JU.M3");
Clazz_defineMethod(c$, "getEquivPoints", 
function(pt, flags, ops, list, i0, n0, dup0){
var fromfractional = (flags.indexOf("fromfractional") >= 0);
var tofractional = (flags.indexOf("tofractional") >= 0);
var packed = (flags.indexOf("packed") >= 0);
if (list == null) list =  new JU.Lst();
var pf = JU.P3.newP(pt);
if (!fromfractional) this.toFractional(pf, true);
var n = list.size();
for (var i = 0, nops = ops.length; i < nops; i++) {
var p = JU.P3.newP(pf);
ops[i].rotTrans(p);
p.x = this.fixFloor(p.x - Math.floor(p.x));
p.y = this.fixFloor(p.y - Math.floor(p.y));
p.z = this.fixFloor(p.z - Math.floor(p.z));
list.addLast(p);
n++;
}
if (packed) {
for (var i = n0; i < n; i++) {
pf.setT(list.get(i));
this.unitizeRnd(pf);
if (pf.x == 0) {
list.addLast(JU.P3.new3(0, pf.y, pf.z));
list.addLast(JU.P3.new3(1, pf.y, pf.z));
if (pf.y == 0) {
list.addLast(JU.P3.new3(1, 1, pf.z));
list.addLast(JU.P3.new3(0, 0, pf.z));
if (pf.z == 0) {
list.addLast(JU.P3.new3(1, 1, 1));
list.addLast(JU.P3.new3(0, 0, 0));
}}}if (pf.y == 0) {
list.addLast(JU.P3.new3(pf.x, 0, pf.z));
list.addLast(JU.P3.new3(pf.x, 1, pf.z));
if (pf.z == 0) {
list.addLast(JU.P3.new3(pf.x, 0, 0));
list.addLast(JU.P3.new3(pf.x, 1, 1));
}}if (pf.z == 0) {
list.addLast(JU.P3.new3(pf.x, pf.y, 0));
list.addLast(JU.P3.new3(pf.x, pf.y, 1));
if (pf.x == 0) {
list.addLast(JU.P3.new3(0, pf.y, 0));
list.addLast(JU.P3.new3(1, pf.y, 1));
}}}
}JS.UnitCell.removeDuplicates(list, i0, dup0, -1);
if (!tofractional) {
for (var i = list.size(); --i >= n0; ) this.toCartesian(list.get(i), true);

}return list;
}, "JU.P3,~S,~A,JU.Lst,~N,~N,~N");
Clazz_defineMethod(c$, "getFractionalOffset", 
function(){
return this.fractionalOffset;
});
Clazz_defineMethod(c$, "getInfo", 
function(){
var m = this.getUnitCellMultiplied();
if (m !== this) return m.getInfo();
var info =  new java.util.Hashtable();
info.put("params", this.unitCellParams);
info.put("oabc", this.getUnitCellVectors());
info.put("volume", Double.$valueOf(this.volume));
info.put("matFtoC", this.matrixFractionalToCartesian);
info.put("matCtoF", this.matrixCartesianToFractional);
return info;
});
Clazz_defineMethod(c$, "getQuaternionRotation", 
function(abc){
var a = JU.V3.newVsub(this.vertices[4], this.vertices[0]);
var b = JU.V3.newVsub(this.vertices[2], this.vertices[0]);
var c = JU.V3.newVsub(this.vertices[1], this.vertices[0]);
var x =  new JU.P3();
var v =  new JU.P3();
var mul = (abc.charAt(0) == '-' ? -1 : 1);
if (mul < 0) abc = abc.substring(1);
var abc0 = abc;
abc = JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(abc, "ab", "A"), "bc", "B"), "ca", "C"), "ba", "D"), "cb", "E"), "ac", "F");
var isFace = !abc0.equals(abc);
var quadrant = (isFace ? 1 : 0);
if (abc.length == 2) {
quadrant = (abc.charAt(1)).charCodeAt(0) - 48;
abc = abc.substring(0, 1);
}var isEven = (quadrant % 2 == 0);
var axis = "abcABCDEF".indexOf(abc);
var v1;
var v2;
var P3;
switch (axis) {
case 7:
mul = -mul;
case 4:
a.cross(c, b);
quadrant = ((5 - quadrant) % 4) + 1;
case 0:
default:
v1 = a;
v2 = c;
P3 = b;
break;
case 8:
mul = -mul;
case 5:
mul = -mul;
b.cross(c, a);
quadrant = ((2 + quadrant) % 4) + 1;
case 1:
v1 = b;
v2 = a;
P3 = c;
mul = -mul;
break;
case 3:
mul = -mul;
case 6:
c.cross(a, b);
if (isEven) quadrant = 6 - quadrant;
case 2:
v1 = c;
v2 = a;
P3 = b;
if (!isFace && quadrant > 0) {
quadrant = 5 - quadrant;
}break;
}
if (quadrant > 0) {
if (mul > 0 != isEven) {
v2 = P3;
v1.scale(-1);
}}switch (quadrant) {
case 0:
default:
case 1:
break;
case 2:
v1.scale(-1);
v2.scale(-1);
break;
case 3:
v2.scale(-1);
break;
case 4:
v1.scale(-1);
break;
}
x.cross(v1, v2);
v.cross(x, v1);
return JU.Quat.getQuaternionFrame(null, v, x).inv();
}, "~S");
Clazz_defineMethod(c$, "getScaledCell", 
function(withOffset){
return this.getScaledCellMult(null, withOffset);
}, "~B");
Clazz_defineMethod(c$, "getScaledCellMult", 
function(mult, withOffset){
var pts =  new Array(8);
var cell0 = null;
var cell1 = null;
var isFrac = (mult != null);
if (!isFrac) mult = this.unitCellMultiplier;
if (withOffset && mult != null && mult.z == 0) {
cell0 =  new JU.P3();
cell1 =  new JU.P3();
JU.SimpleUnitCell.ijkToPoint3f(Clazz_floatToInt(mult.x), cell0, 0, 0);
JU.SimpleUnitCell.ijkToPoint3f(Clazz_floatToInt(mult.y), cell1, 0, 0);
cell1.sub(cell0);
}var scale = (isFrac || mult == null || mult.z == 0 ? 1 : Math.abs(mult.z));
for (var i = 0; i < 8; i++) {
var pt = pts[i] = JU.P3.newP(JU.BoxInfo.unitCubePoints[i]);
if (cell0 != null) {
pts[i].add3(cell0.x + cell1.x * pt.x, cell0.y + cell1.y * pt.y, cell0.z + cell1.z * pt.z);
} else if (isFrac) {
pt.scaleT(mult);
}pts[i].scale(scale);
this.matrixFractionalToCartesian.rotTrans(pt);
if (!withOffset) pt.sub(this.cartesianOffset);
}
return pts;
}, "JU.T3,~B");
Clazz_defineMethod(c$, "getState", 
function(){
var s = "";
if (this.fractionalOffset != null && this.fractionalOffset.lengthSquared() != 0) s += "  unitcell offset " + JU.Escape.eP(this.fractionalOffset) + ";\n";
if (this.unitCellMultiplier != null) s += "  unitcell range " + JU.SimpleUnitCell.escapeMultiplier(this.unitCellMultiplier) + ";\n";
return s;
});
Clazz_defineMethod(c$, "getTensor", 
function(vwr, parBorU){
var t = (J.api.Interface.getUtil("Tensor", vwr, "file"));
if (parBorU[0] == 0 && parBorU[1] == 0 && parBorU[2] == 0) {
var f = parBorU[7];
var eigenValues =  Clazz_newFloatArray(-1, [f, f, f]);
return t.setFromEigenVectors(JS.UnitCell.unitVectors, eigenValues, "iso", "Uiso=" + f, null);
}t.parBorU = parBorU;
var Bcart =  Clazz_newDoubleArray (6, 0);
var ortepType = Clazz_floatToInt(parBorU[6]);
if (ortepType == 12) {
Bcart[0] = parBorU[0] * 19.739208802178716;
Bcart[1] = parBorU[1] * 19.739208802178716;
Bcart[2] = parBorU[2] * 19.739208802178716;
Bcart[3] = parBorU[3] * 19.739208802178716 * 2;
Bcart[4] = parBorU[4] * 19.739208802178716 * 2;
Bcart[5] = parBorU[5] * 19.739208802178716 * 2;
parBorU[7] = (parBorU[0] + parBorU[1] + parBorU[3]) / 3;
} else {
var isFractional = (ortepType == 4 || ortepType == 5 || ortepType == 8 || ortepType == 9);
var cc = 2 - (ortepType % 2);
var dd = (ortepType == 8 || ortepType == 9 || ortepType == 10 ? 19.739208802178716 : ortepType == 4 || ortepType == 5 ? 0.25 : ortepType == 2 || ortepType == 3 ? Math.log(2) : 1);
var B11 = parBorU[0] * dd * (isFractional ? this.a_ * this.a_ : 1);
var B22 = parBorU[1] * dd * (isFractional ? this.b_ * this.b_ : 1);
var B33 = parBorU[2] * dd * (isFractional ? this.c_ * this.c_ : 1);
var B12 = parBorU[3] * dd * (isFractional ? this.a_ * this.b_ : 1) * cc;
var B13 = parBorU[4] * dd * (isFractional ? this.a_ * this.c_ : 1) * cc;
var B23 = parBorU[5] * dd * (isFractional ? this.b_ * this.c_ : 1) * cc;
parBorU[7] = Math.pow(B11 / 19.739208802178716 / this.a_ / this.a_ * B22 / 19.739208802178716 / this.b_ / this.b_ * B33 / 19.739208802178716 / this.c_ / this.c_, 0.3333);
Bcart[0] = this.a * this.a * B11 + this.b * this.b * this.cosGamma * this.cosGamma * B22 + this.c * this.c * this.cosBeta * this.cosBeta * B33 + this.a * this.b * this.cosGamma * B12 + this.b * this.c * this.cosGamma * this.cosBeta * B23 + this.a * this.c * this.cosBeta * B13;
Bcart[1] = this.b * this.b * this.sinGamma * this.sinGamma * B22 + this.c * this.c * this.cA_ * this.cA_ * B33 + this.b * this.c * this.cA_ * this.sinGamma * B23;
Bcart[2] = this.c * this.c * this.cB_ * this.cB_ * B33;
Bcart[3] = 2 * this.b * this.b * this.cosGamma * this.sinGamma * B22 + 2 * this.c * this.c * this.cA_ * this.cosBeta * B33 + this.a * this.b * this.sinGamma * B12 + this.b * this.c * (this.cA_ * this.cosGamma + this.sinGamma * this.cosBeta) * B23 + this.a * this.c * this.cA_ * B13;
Bcart[4] = 2 * this.c * this.c * this.cB_ * this.cosBeta * B33 + this.b * this.c * this.cosGamma * B23 + this.a * this.c * this.cB_ * B13;
Bcart[5] = 2 * this.c * this.c * this.cA_ * this.cB_ * B33 + this.b * this.c * this.cB_ * this.sinGamma * B23;
}return t.setFromThermalEquation(Bcart, JU.Escape.eAF(parBorU));
}, "JV.Viewer,~A");
Clazz_defineMethod(c$, "getUnitCellMultiplied", 
function(){
if (this.unitCellMultiplier == null || this.unitCellMultiplier.z > 0 && this.unitCellMultiplier.z == Clazz_floatToInt(this.unitCellMultiplier.z)) return this;
if (this.unitCellMultiplied == null) {
var pts = JU.BoxInfo.toOABC(this.getScaledCell(true), null);
this.unitCellMultiplied = JS.UnitCell.fromOABC(pts, false);
}return this.unitCellMultiplied;
});
Clazz_defineMethod(c$, "getUnitCellMultiplier", 
function(){
return this.unitCellMultiplier;
});
Clazz_defineMethod(c$, "isStandard", 
function(){
return (this.unitCellMultiplier == null || this.unitCellMultiplier.x == this.unitCellMultiplier.y);
});
Clazz_defineMethod(c$, "getUnitCellVectors", 
function(){
var m = this.matrixFractionalToCartesian;
return  Clazz_newArray(-1, [JU.P3.newP(this.cartesianOffset), JU.P3.new3(this.fix000(m.m00), this.fix000(m.m10), this.fix000(m.m20)), JU.P3.new3(this.fix000(m.m01), this.fix000(m.m11), this.fix000(m.m21)), JU.P3.new3(this.fix000(m.m02), this.fix000(m.m12), this.fix000(m.m22))]);
});
c$.toTrm = Clazz_defineMethod(c$, "toTrm", 
function(transform, trm){
if (trm == null) trm =  new JU.M4();
JS.UnitCell.getMatrixAndUnitCell(null, transform, trm);
return trm;
}, "~S,JU.M4");
c$.getMatrixAndUnitCell = Clazz_defineMethod(c$, "getMatrixAndUnitCell", 
function(uc, def, retMatrix){
if (def == null) def = "a,b,c";
var m;
var pts =  new Array(4);
var pt = pts[0] = JU.P3.new3(0, 0, 0);
pts[1] = JU.P3.new3(1, 0, 0);
pts[2] = JU.P3.new3(0, 1, 0);
pts[3] = JU.P3.new3(0, 0, 1);
var m3 =  new JU.M3();
if (JU.AU.isAD(def)) {
return JU.SimpleUnitCell.setAbcFromParams(def, pts);
}var isString = (typeof(def)=='string');
if (isString) {
var sdef = def;
var strans;
var strans2 = null;
if (sdef.indexOf("a=") == 0) return JU.SimpleUnitCell.setAbc(sdef, null, pts);
var ret =  new Array(1);
var ptc = sdef.indexOf(";");
if (ptc >= 0) {
strans = sdef.substring(ptc + 1).trim();
sdef = sdef.substring(0, ptc);
ret[0] = sdef;
strans2 = JS.UnitCell.fixABC(ret);
if (sdef !== ret[0]) {
sdef = ret[0];
}} else if (sdef.equals("a,b,c")) {
strans = null;
} else {
ret[0] = sdef;
strans = JS.UnitCell.fixABC(ret);
sdef = ret[0];
}sdef += ";0,0,0";
while (sdef.startsWith("!!")) sdef = sdef.substring(2);

var isRev = sdef.startsWith("!");
if (isRev) sdef = sdef.substring(1);
if (sdef.startsWith("r;")) sdef = "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c" + sdef.substring(1);
var symTemp =  new JS.Symmetry();
symTemp.setSpaceGroup(false);
var i = symTemp.addSpaceGroupOperation("=" + sdef, 0);
if (i < 0) return null;
m = symTemp.getSpaceGroupOperation(i);
(m).doFinalize();
var t =  new JU.P3();
JS.UnitCell.addTrans(strans, t);
JS.UnitCell.addTrans(strans2, t);
m.setTranslation(t);
var isABC = (sdef.indexOf("c") >= 0);
if (isABC) {
m.transpose33();
}if (isRev) {
m.invert();
}if (retMatrix != null) {
retMatrix.setM4(m);
}if (uc == null) return pts;
} else if (retMatrix != null || uc == null) {
return null;
} else if (Clazz_instanceOf(def,"JU.M3")) {
m = JU.M4.newMV(def,  new JU.P3());
} else if (Clazz_instanceOf(def,"JU.M4")) {
m = def;
} else {
m = (def)[0];
m.getRotationScale(m3);
m.rotTrans(pt);
uc.toCartesian(pt, false);
for (var i = 1; i < 4; i++) {
m3.rotate(pts[i]);
uc.toCartesian(pts[i], true);
}
return pts;
}m.getRotationScale(m3);
m.getTranslation(pt);
uc.toCartesian(pt, false);
for (var i = 1; i < 4; i++) {
m3.rotate(pts[i]);
uc.toCartesian(pts[i], true);
}
return pts;
}, "JU.SimpleUnitCell,~O,JU.M4");
c$.addTrans = Clazz_defineMethod(c$, "addTrans", 
function(strans, t){
if (strans == null) return;
var atrans = JU.PT.split(strans, ",");
var ftrans =  Clazz_newFloatArray (3, 0);
if (atrans.length == 3) {
for (var j = 0; j < 3; j++) {
var s = atrans[j];
var sfpt = s.indexOf("/");
if (sfpt >= 0) {
ftrans[j] = JU.PT.parseFloat(s.substring(0, sfpt)) / JU.PT.parseFloat(s.substring(sfpt + 1));
} else {
ftrans[j] = JU.PT.parseFloat(s);
}}
}t.add3(ftrans[0], ftrans[1], ftrans[2]);
}, "~S,JU.P3");
c$.fixABC = Clazz_defineMethod(c$, "fixABC", 
function(ret){
var tokens = JU.PT.split(ret[0], ",");
if (tokens.length != 3) return null;
var trans = "";
var abc = "";
var haveT = false;
for (var i = 0; i < 3; i++) {
var a = tokens[i];
var p;
var n = 0;
for (p = a.length; --p >= 0; ) {
var c = a.charAt(p);
switch ((c).charCodeAt(0)) {
default:
if (c >= 'a') p = 0;
break;
case 43:
n = 1;
case 45:
p = -p;
break;
}
}
p = -1 - p;
if (p == 0) {
trans += ",0";
abc += "," + a;
} else {
haveT = true;
trans += "," + a.substring(p + n);
abc += "," + a.substring(0, p);
}}
ret[0] = abc.substring(1);
return (haveT ? trans.substring(1) : null);
}, "~A");
Clazz_defineMethod(c$, "getVertices", 
function(){
return this.vertices;
});
Clazz_defineMethod(c$, "hasOffset", 
function(){
return (this.fractionalOffset != null && this.fractionalOffset.lengthSquared() != 0);
});
Clazz_defineMethod(c$, "initOrientation", 
function(mat){
if (mat == null) return;
var m =  new JU.M4();
m.setToM3(mat);
this.matrixFractionalToCartesian.mul2(m, this.matrixFractionalToCartesian);
this.matrixCartesianToFractional.setM4(this.matrixFractionalToCartesian).invert();
this.initUnitcellVertices();
}, "JU.M3");
Clazz_defineMethod(c$, "initUnitcellVertices", 
function(){
if (this.matrixFractionalToCartesian == null) return;
this.matrixCtoFNoOffset = JU.M4.newM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset = JU.M4.newM4(this.matrixFractionalToCartesian);
this.vertices =  new Array(8);
for (var i = 8; --i >= 0; ) this.vertices[i] = this.matrixFractionalToCartesian.rotTrans2(JU.BoxInfo.unitCubePoints[i],  new JU.P3());

});
Clazz_defineMethod(c$, "isSameAs", 
function(f2c2){
if (f2c2 == null) return false;
var f2c = this.getF2C();
for (var i = 0; i < 3; i++) {
for (var j = 0; j < 4; j++) {
if (!JU.SimpleUnitCell.approx0(f2c[i][j] - f2c2[i][j])) return false;
}
}
return true;
}, "~A");
Clazz_defineMethod(c$, "getF2C", 
function(){
if (this.f2c == null) {
this.f2c =  Clazz_newFloatArray (3, 4, 0);
for (var i = 0; i < 3; i++) this.matrixFractionalToCartesian.getRow(i, this.f2c[i]);

}return this.f2c;
});
Clazz_defineMethod(c$, "isWithinUnitCell", 
function(a, b, c, pt){
switch (this.dimension) {
case 3:
if (pt.z < c - 1 - this.slop || pt.z > c + this.slop) return false;
case 2:
if (pt.y < b - 1 - this.slop || pt.y > b + this.slop) return false;
case 1:
if (pt.x < a - 1 - this.slop || pt.x > a + this.slop) return false;
}
return true;
}, "~N,~N,~N,JU.P3");
Clazz_defineMethod(c$, "setCartesianOffset", 
function(origin){
this.cartesianOffset.setT(origin);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
var wasOffset = this.hasOffset();
this.fractionalOffset = JU.P3.newP(this.cartesianOffset);
this.matrixCartesianToFractional.rotate(this.fractionalOffset);
this.matrixCartesianToFractional.m03 = -this.fractionalOffset.x;
this.matrixCartesianToFractional.m13 = -this.fractionalOffset.y;
this.matrixCartesianToFractional.m23 = -this.fractionalOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4(this.matrixFractionalToCartesian);
}if (!wasOffset && this.fractionalOffset.lengthSquared() == 0) this.fractionalOffset = null;
this.f2c = null;
}, "JU.T3");
Clazz_defineMethod(c$, "setOffset", 
function(pt){
if (pt == null) return;
this.unitCellMultiplied = null;
var pt4 = (Clazz_instanceOf(pt,"JU.T4") ? pt : null);
var w = (pt4 == null ? 1.4E-45 : pt4.w);
var isCell555P4 = (w > 999999);
if (pt4 != null ? w <= 0 || isCell555P4 : pt.x >= 100 || pt.y >= 100) {
this.unitCellMultiplier = (pt.z == 0 && pt.x == pt.y && !isCell555P4 ? null : isCell555P4 ? JU.P4.newPt(pt4) : JU.P3.newP(pt));
this.unitCellMultiplied = null;
if (pt4 == null || pt4.w == 0 || isCell555P4) return;
}if (this.hasOffset() || pt.lengthSquared() > 0) {
this.fractionalOffset = JU.P3.newP(pt);
}this.matrixCartesianToFractional.m03 = -pt.x;
this.matrixCartesianToFractional.m13 = -pt.y;
this.matrixCartesianToFractional.m23 = -pt.z;
this.cartesianOffset.setT(pt);
this.matrixFractionalToCartesian.rotate(this.cartesianOffset);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4(this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4(this.matrixFractionalToCartesian);
}this.f2c = null;
}, "JU.T3");
Clazz_defineMethod(c$, "toFromPrimitive", 
function(toPrimitive, type, uc, primitiveToCrystal){
var offset = uc.length - 3;
var mf = null;
if (type == 'r' || primitiveToCrystal == null) {
switch ((type).charCodeAt(0)) {
default:
return false;
case 114:
JU.SimpleUnitCell.getReciprocal(uc, uc, 1);
return true;
case 80:
toPrimitive = true;
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [1, 0, 0, 0, 1, 0, 0, 0, 1]));
break;
case 65:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [1, 0, 0, 0, 0.5, 0.5, 0, -0.5, 0.5]));
break;
case 66:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [0.5, 0, 0.5, 0, 1, 0, -0.5, 0, 0.5]));
break;
case 67:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [0.5, 0.5, 0, -0.5, 0.5, 0, 0, 0, 1]));
break;
case 82:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [0.6666667, -0.33333334, -0.33333334, 0.33333334, 0.33333334, -0.6666667, 0.33333334, 0.33333334, 0.33333334]));
break;
case 73:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [-0.5, .5, .5, .5, -0.5, .5, .5, .5, -0.5]));
break;
case 70:
mf = JU.M3.newA9( Clazz_newFloatArray(-1, [0, 0.5, 0.5, 0.5, 0, 0.5, 0.5, 0.5, 0]));
break;
}
if (!toPrimitive) mf.invert();
} else {
mf = JU.M3.newM3(primitiveToCrystal);
if (toPrimitive) mf.invert();
}for (var i = uc.length; --i >= offset; ) {
var p = uc[i];
this.toFractional(p, true);
mf.rotate(p);
this.toCartesian(p, true);
}
return true;
}, "~B,~S,~A,JU.M3");
Clazz_defineMethod(c$, "toUnitCell", 
function(pt, offset){
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans(pt);
this.unitize(pt);
this.matrixFractionalToCartesian.rotTrans(pt);
} else {
this.matrixCtoFNoOffset.rotTrans(pt);
this.unitize(pt);
pt.add(offset);
this.matrixFtoCNoOffset.rotTrans(pt);
}}, "JU.T3,JU.T3");
Clazz_defineMethod(c$, "toUnitCellRnd", 
function(pt, offset){
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans(pt);
this.unitizeRnd(pt);
this.matrixFractionalToCartesian.rotTrans(pt);
} else {
this.matrixCtoFNoOffset.rotTrans(pt);
this.unitizeRnd(pt);
pt.add(offset);
this.matrixFtoCNoOffset.rotTrans(pt);
}}, "JU.T3,JU.T3");
Clazz_defineMethod(c$, "unitize", 
function(pt){
this.unitizeDim(this.dimension, pt);
}, "JU.T3");
Clazz_defineMethod(c$, "unitizeRnd", 
function(pt){
JU.SimpleUnitCell.unitizeDimRnd(this.dimension, pt, this.slop);
}, "JU.T3");
c$.createCompatibleUnitCell = Clazz_defineMethod(c$, "createCompatibleUnitCell", 
function(sg, params, newParams, allowSame){
if (newParams == null) newParams = params;
var a = params[0];
var b = params[1];
var c = params[2];
var alpha = params[3];
var beta = params[4];
var gamma = params[5];
var n = (sg == null || sg.itaNumber == null ? 0 : JU.PT.parseInt(sg.itaNumber));
var toHex = (n != 0 && JS.UnitCell.isHexagonalSG(n, null));
var isHex = (toHex && JS.UnitCell.isHexagonalSG(-1, params));
var toRhom = (n != 0 && sg.axisChoice == 'r');
var isRhom = (toRhom && JU.SimpleUnitCell.isRhombohedral(params));
if (toHex && isHex || toRhom && isRhom) {
allowSame = true;
}if (n > (allowSame ? 2 : 0)) {
var absame = JU.SimpleUnitCell.approx0(a - b);
var bcsame = JU.SimpleUnitCell.approx0(b - c);
var acsame = JU.SimpleUnitCell.approx0(c - a);
var albesame = JU.SimpleUnitCell.approx0(alpha - beta);
var begasame = JU.SimpleUnitCell.approx0(beta - gamma);
var algasame = JU.SimpleUnitCell.approx0(gamma - alpha);
if (!allowSame) {
if (a > b) {
var d = a;
a = b;
b = d;
}bcsame = JU.SimpleUnitCell.approx0(b - c);
if (bcsame) c = b * 1.5;
absame = JU.SimpleUnitCell.approx0(a - b);
if (absame) b = a * 1.2;
acsame = JU.SimpleUnitCell.approx0(c - a);
if (acsame) c = a * 1.1;
if (JU.SimpleUnitCell.approx0(alpha - 90)) {
alpha = 80;
}if (JU.SimpleUnitCell.approx0(beta - 90)) {
beta = 100;
}if (JU.SimpleUnitCell.approx0(gamma - 90)) {
gamma = 110;
}if (alpha > beta) {
var d = alpha;
alpha = beta;
beta = d;
}albesame = JU.SimpleUnitCell.approx0(alpha - beta);
begasame = JU.SimpleUnitCell.approx0(beta - gamma);
algasame = JU.SimpleUnitCell.approx0(gamma - alpha);
if (albesame) {
beta = alpha * 1.2;
}if (begasame) {
gamma = beta * 1.3;
}if (algasame) {
gamma = alpha * 1.4;
}}if (toHex) {
if (toRhom ? isRhom : isHex) {
} else if (sg.axisChoice == 'r') {
c = b = a;
if (!allowSame && alpha > 85 && alpha < 95) alpha = 80;
gamma = beta = alpha;
} else {
b = a;
alpha = beta = 90;
gamma = 120;
}} else if (n >= 195) {
c = b = a;
alpha = beta = gamma = 90;
} else if (n >= 75) {
b = a;
if (acsame && !allowSame) c = a * 1.5;
alpha = beta = gamma = 90;
} else if (n >= 16) {
alpha = beta = gamma = 90;
} else if (n >= 3) {
switch ((sg.uniqueAxis).charCodeAt(0)) {
case 97:
beta = gamma = 90;
break;
default:
case 98:
alpha = gamma = 90;
break;
case 99:
alpha = beta = 90;
break;
}
}}var isNew = !(a == params[0] && b == params[1] && c == params[2] && alpha == params[3] && beta == params[4] && gamma == params[5]);
newParams[0] = a;
newParams[1] = b;
newParams[2] = c;
newParams[3] = alpha;
newParams[4] = beta;
newParams[5] = gamma;
return isNew;
}, "JS.SpaceGroup,~A,~A,~B");
c$.isHexagonalSG = Clazz_defineMethod(c$, "isHexagonalSG", 
function(n, params){
return (n < 1 ? JU.SimpleUnitCell.isHexagonal(params) : n >= 143 && n <= 194);
}, "~N,~A");
c$.isMonoclinicSG = Clazz_defineMethod(c$, "isMonoclinicSG", 
function(n){
return (n >= 3 && n <= 15);
}, "~N");
c$.isTetragonalSG = Clazz_defineMethod(c$, "isTetragonalSG", 
function(n){
return (n >= 75 && n <= 142);
}, "~N");
c$.isPolarSG = Clazz_defineMethod(c$, "isPolarSG", 
function(n){
return (n == 1 || n >= 3 && n <= 5 || n >= 6 && n <= 9 || n >= 25 && n <= 46 || n >= 75 && n <= 80 || n >= 99 && n <= 110 || n >= 143 && n <= 146 || n >= 156 && n <= 161 || n >= 168 && n <= 173 || n >= 183 && n <= 186);
}, "~N");
c$.removeDuplicates = Clazz_defineMethod(c$, "removeDuplicates", 
function(list, i0, n0, n){
if (n < 0) n = list.size();
for (var i = i0; i < n; i++) {
var p = list.get(i);
for (var j = Math.max(i + 1, n0); j < n; j++) {
if (list.get(j).distanceSquared(p) < 1.96E-6) {
list.removeItemAt(j);
n--;
j--;
}}
}
}, "JU.Lst,~N,~N,~N");
c$.unitVectors =  Clazz_newArray(-1, [JV.JC.axisX, JV.JC.axisY, JV.JC.axisZ]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
})(Clazz
,Clazz.getClassName
,Clazz.newLongArray
,Clazz.doubleToByte
,Clazz.doubleToInt
,Clazz.doubleToLong
,Clazz.declarePackage
,Clazz.instanceOf
,Clazz.load
,Clazz.instantialize
,Clazz.decorateAsClass
,Clazz.floatToInt
,Clazz.floatToLong
,Clazz.makeConstructor
,Clazz.defineEnumConstant
,Clazz.exceptionOf
,Clazz.newIntArray
,Clazz.newFloatArray
,Clazz.declareType
,Clazz.prepareFields
,Clazz.superConstructor
,Clazz.newByteArray
,Clazz.declareInterface
,Clazz.newShortArray
,Clazz.innerTypeInstance
,Clazz.isClassDefined
,Clazz.prepareCallback
,Clazz.newArray
,Clazz.castNullAs
,Clazz.floatToShort
,Clazz.superCall
,Clazz.decorateAsType
,Clazz.newBooleanArray
,Clazz.newCharArray
,Clazz.implementOf
,Clazz.newDoubleArray
,Clazz.overrideConstructor
,Clazz.clone
,Clazz.doubleToShort
,Clazz.getInheritedLevel
,Clazz.getParamsType
,Clazz.isAF
,Clazz.isAB
,Clazz.isAI
,Clazz.isAS
,Clazz.isASS
,Clazz.isAP
,Clazz.isAFloat
,Clazz.isAII
,Clazz.isAFF
,Clazz.isAFFF
,Clazz.tryToSearchAndExecute
,Clazz.getStackTrace
,Clazz.inheritArgs
,Clazz.alert
,Clazz.defineMethod
,Clazz.overrideMethod
,Clazz.declareAnonymous
//,Clazz.checkPrivateMethod
,Clazz.cloneFinals
);
