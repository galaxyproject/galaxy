Clazz.declarePackage("JS");
Clazz.load(["JU.JmolMolecule", "JU.BS", "$.Lst"], "JS.SmilesSearch", ["java.util.Hashtable", "JU.AU", "$.SB", "JS.InvalidSmilesException", "$.SmilesAromatic", "$.SmilesAtom", "$.SmilesBond", "$.SmilesMeasure", "$.SmilesParser", "$.SmilesStereo", "$.VTemp", "JU.BSUtil", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.isSmarts = false;
this.top = null;
this.target = null;
this.pattern = null;
this.patternAtoms = null;
this.v = null;
this.targetSet = false;
this.aromaticOpen = false;
this.aromaticStrict = false;
this.aromaticPlanar = false;
this.aromaticDouble = false;
this.aromaticMMFF94 = false;
this.aromaticDefined = false;
this.aromaticUnknown = false;
this.noAromatic = false;
this.ignoreAtomClass = false;
this.ignoreElement = false;
this.ignoreStereochemistry = false;
this.invertStereochemistry = false;
this.exitFirstMatch = false;
this.groupByModel = false;
this.setAtropicity = false;
this.patternAromatic = false;
this.haveSmilesTarget = false;
this.isTopology = false;
this.patternBioSequence = false;
this.subSearches = null;
this.haveSelected = false;
this.haveBondStereochemistry = false;
this.stereo = null;
this.needRingData = false;
this.needAromatic = true;
this.needRingMemberships = false;
this.nDouble = 0;
this.ringDataMax = -2147483648;
this.measures = null;
this.flags = 0;
this.atropKeys = null;
this.lastChainAtom = null;
this.asVector = false;
this.getMaps = false;
this.retBoolean = false;
this.isNormalized = false;
this.haveComponents = false;
this.isSilent = false;
this.isRingCheck = false;
this.bsFound = null;
this.htNested = null;
this.nNested = 0;
this.nestedBond = null;
this.vReturn = null;
this.uniqueList = null;
this.bsReturn = null;
this.bsCheck = null;
this.mapUnique = false;
this.polyhedronStereo = null;
this.polyAtom = null;
this.autoAddImplicitH = true;
this.pattern0 = null;
Clazz.instantialize(this, arguments);}, JS, "SmilesSearch", JU.JmolMolecule);
Clazz.prepareFields (c$, function(){
this.patternAtoms =  new Array(16);
this.measures =  new JU.Lst();
this.bsFound =  new JU.BS();
this.bsReturn =  new JU.BS();
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JS.SmilesSearch, []);
this.top = this;
this.target =  new JS.SmilesSearch.SmilesTarget();
this.v =  new JS.VTemp();
});
c$.isRingBond = Clazz.defineMethod(c$, "isRingBond", 
function(ringSets, bsAromaticRings, a1, a2){
if (ringSets != null) {
for (var i = ringSets.size(); --i >= 0; ) {
var bsRing = ringSets.get(i);
if (bsRing.get(a1) && bsRing.get(a2)) {
if (bsAromaticRings == null || bsAromaticRings.get(i)) return true;
}}
}return false;
}, "JU.Lst,JU.BS,~N,~N");
Clazz.defineMethod(c$, "setTarget", 
function(s){
this.target = s.target;
this.targetSet = true;
}, "JS.SmilesSearch");
Clazz.defineMethod(c$, "setTop", 
function(parent){
while (parent.top !== parent) parent = parent.top;

this.top = parent;
}, "JS.SmilesSearch");
c$.addFlags = Clazz.defineMethod(c$, "addFlags", 
function(flags, strFlags){
if (strFlags.indexOf("OPEN") >= 0) flags |= 5;
if (strFlags.indexOf("BIO") >= 0) flags |= 1048576;
if (strFlags.indexOf("HYDROGEN2") >= 0) flags |= 8192;
 else if (strFlags.indexOf("HYDROGEN") >= 0) flags |= 4096;
if (strFlags.indexOf("FIRSTMATCHONLY") >= 0) flags |= 8;
if (strFlags.indexOf("STRICT") >= 0) flags |= 256;
if (strFlags.indexOf("PLANAR") >= 0) flags |= 1024;
if (strFlags.indexOf("NOAROMATIC") >= 0 || strFlags.indexOf("NONAROMATIC") >= 0) flags |= 16;
if (strFlags.indexOf("AROMATICDOUBLE") >= 0) flags |= 512;
if (strFlags.indexOf("AROMATICDEFINED") >= 0) flags |= 128;
if (strFlags.indexOf("MMFF94") >= 0) flags |= 768;
if (strFlags.indexOf("ALLCOMPONENTS") >= 0) flags |= 32768;
if (strFlags.indexOf("TOPOLOGY") >= 0) flags |= 16384;
if (strFlags.indexOf("NOATOMCLASS") >= 0) flags |= 2048;
if (strFlags.indexOf("NOSTEREO") >= 0) {
flags |= 32;
} else if (strFlags.indexOf("INVERTSTEREO") >= 0) {
if ((flags & 64) != 0) flags &= -65;
 else flags |= 64;
}if (strFlags.indexOf("ATOMCOMMENT") >= 0) flags |= 131072;
if (strFlags.indexOf("GROUPBYMODEL") >= 0) flags |= 67108864;
if ((flags & 1048576) == 1048576) {
if (strFlags.indexOf("NOCOMMENT") >= 0) flags |= 34603008;
if (strFlags.indexOf("UNMATCHED") >= 0) flags |= 3145728;
if (strFlags.indexOf("COVALENT") >= 0) flags |= 5242880;
if (strFlags.indexOf("HBOND") >= 0) flags |= 9437184;
}return flags;
}, "~N,~S");
Clazz.defineMethod(c$, "setFlags", 
function(flags){
this.flags = flags;
this.exitFirstMatch = new Boolean (this.exitFirstMatch | ((flags & 8) == 8)).valueOf();
this.aromaticOpen = ((flags & 5) == 5);
this.aromaticStrict = ((flags & 256) == 256);
this.aromaticPlanar = ((flags & 1024) == 1024);
this.aromaticMMFF94 = ((flags & 768) == 768);
this.aromaticDouble = ((flags & 512) == 512);
this.aromaticDefined = ((flags & 128) == 128);
this.noAromatic = new Boolean (this.noAromatic | ((flags & 16) == 16)).valueOf();
this.aromaticUnknown = !this.noAromatic && !this.aromaticOpen && !this.aromaticDouble && !this.aromaticStrict && !this.aromaticPlanar && !this.aromaticMMFF94 && !this.aromaticDefined;
this.groupByModel = ((flags & 67108864) == 67108864);
this.ignoreAtomClass = ((flags & 2048) == 2048);
this.ignoreStereochemistry = ((flags & 32) == 32);
this.invertStereochemistry = !this.ignoreStereochemistry && ((flags & 64) == 64);
this.ignoreElement = ((flags & 16384) == 16384);
}, "~N");
Clazz.defineMethod(c$, "set", 
function(){
if (this.patternAtoms.length > this.ac) this.patternAtoms = JU.AU.arrayCopyObject(this.patternAtoms, this.ac);
this.nodes = this.patternAtoms;
this.isTopology = true;
this.patternAromatic = false;
this.patternBioSequence = true;
for (var i = this.ac; --i >= 0; ) {
var atom = this.patternAtoms[i];
if (this.isTopology && atom.isDefined()) this.isTopology = false;
if (!atom.isBioResidue) this.patternBioSequence = false;
if (atom.isAromatic) this.patternAromatic = true;
atom.setBondArray();
if (this.autoAddImplicitH && !this.isSmarts && atom.bioType == '\0' && !atom.setHydrogenCount()) throw  new JS.InvalidSmilesException("unbracketed atoms must be one of: B, C, N, O, P, S, F, Cl, Br, I, *,");
}
if (this.haveComponents) {
for (var i = this.ac; --i >= 0; ) {
var a = this.patternAtoms[i];
var bonds = a.bonds;
var ia = a.component;
for (var j = a.bondCount; --j >= 0; ) {
var b = bonds[j];
var ib;
if (b.isConnection && b.atom2 === a && (ib = b.atom1.component) != ia) {
for (var k = this.ac; --k >= 0; ) if (this.patternAtoms[k].component == ia) this.patternAtoms[k].component = ib;

}}
}
}});
Clazz.defineMethod(c$, "addAtom", 
function(){
return this.appendAtom( new JS.SmilesAtom());
});
Clazz.defineMethod(c$, "appendAtom", 
function(sAtom){
if (this.ac >= this.patternAtoms.length) this.patternAtoms = JU.AU.doubleLength(this.patternAtoms);
return this.patternAtoms[this.ac] = sAtom.setIndex(this.ac++);
}, "JS.SmilesAtom");
Clazz.defineMethod(c$, "addNested", 
function(pattern){
if (this.htNested == null) this.htNested =  new java.util.Hashtable();
this.setNested(++this.nNested, pattern);
return this.nNested;
}, "~S");
Clazz.defineMethod(c$, "clear", 
function(){
this.bsReturn.clearAll();
this.nNested = 0;
this.htNested = null;
this.nestedBond = null;
this.clearBsFound(-1);
});
Clazz.defineMethod(c$, "clearBsFound", 
function(iAtom){
if (iAtom < 0) {
if (this.bsCheck == null) {
this.bsFound.clearAll();
}} else this.bsFound.clear(iAtom);
}, "~N");
Clazz.defineMethod(c$, "setNested", 
function(iNested, o){
this.top.htNested.put("_" + iNested, o);
}, "~N,~O");
Clazz.defineMethod(c$, "getNested", 
function(iNested){
return this.top.htNested.get("_" + iNested);
}, "~N");
Clazz.defineMethod(c$, "getMissingHydrogenCount", 
function(){
var n = 0;
var nH;
for (var i = 0; i < this.ac; i++) if ((nH = this.patternAtoms[i].explicitHydrogenCount) >= 0) n += nH;

return n;
});
Clazz.defineMethod(c$, "setRingData", 
function(bsA, vRings, doProcessAromatic){
if (this.isTopology || this.patternBioSequence) this.needAromatic = false;
this.needAromatic = new Boolean (this.needAromatic &( new Boolean ((bsA == null) & !this.noAromatic).valueOf())).valueOf();
if (this.needAromatic) this.needRingData = true;
if (!this.needAromatic) {
this.target.bsAromatic.clearAll();
if (bsA != null) this.target.bsAromatic.or(bsA);
if (!this.needRingMemberships && !this.needRingData) return;
}this.getRingData(vRings, this.needRingData, doProcessAromatic);
}, "JU.BS,~A,~B");
Clazz.defineMethod(c$, "getRingData", 
function(vRings, needRingData, doTestAromatic){
var isStrict = (this.needAromatic && (this.aromaticStrict || !this.aromaticOpen && !this.aromaticPlanar));
if (isStrict && this.aromaticUnknown) {
if (this.target.ac > 0 && this.target.nodes[this.target.bsSelected.nextSetBit(0)].modelIsRawPDB()) isStrict = false;
}var isOpenNotStrict = (this.needAromatic && this.aromaticOpen && !this.aromaticStrict);
var checkExplicit = (this.needAromatic && !isStrict);
var doFinalize = (this.needAromatic && doTestAromatic && (isStrict || isOpenNotStrict));
var setAromatic = (this.needAromatic && !this.aromaticDefined);
var aromaticMax = 7;
var lstAromatic = (vRings == null ?  new JU.Lst() : (vRings[3] =  new JU.Lst()));
var lstSP2 = (doFinalize ?  new JU.Lst() : null);
var strictness = (!isStrict ? 0 : this.aromaticMMFF94 ? 2 : 1);
if (this.needAromatic && this.aromaticDefined) {
this.target.checkAromaticDefined();
strictness = 0;
}this.ringDataMax = this.target.setRingData(strictness, needRingData, this.ringDataMax);
if (this.target.selectedAtomCount < 3) return;
var s = "****";
var max = this.ringDataMax;
while (s.length < max) s += s;

var eCounts = (doFinalize && setAromatic ?  Clazz.newIntArray (this.target.ac, 0) : null);
var justCheckBonding = (setAromatic && Clazz.instanceOf(this.target.nodes[0],"JS.SmilesAtom"));
for (var i = 3; i <= max; i++) {
if (i > this.target.ac) break;
var smarts = "*1" + s.substring(0, i - 2) + "*1";
var search = JS.SmilesParser.newSearch(smarts, true, true);
var vR = this.subsearch(search, 2);
if (vRings != null && i <= 5) {
var v =  new JU.Lst();
for (var j = vR.size(); --j >= 0; ) v.addLast(vR.get(j));

vRings[i - 3] = v;
}if (vR.size() == 0) continue;
if (setAromatic && i >= 4 && i <= aromaticMax) {
JS.SmilesAromatic.setAromatic(i, this.target.nodes, this.target.bsSelected, vR, this.target.bsAromatic, strictness, isOpenNotStrict, justCheckBonding, checkExplicit, this.v, lstAromatic, lstSP2, eCounts, doTestAromatic);
}if (needRingData) {
this.target.ringData[i] =  new JU.BS();
for (var k = vR.size(); --k >= 0; ) {
var r = vR.get(k);
this.target.ringData[i].or(r);
for (var j = r.nextSetBit(0); j >= 0; j = r.nextSetBit(j + 1)) this.target.ringCounts[j]++;

}
}}
if (this.needAromatic) {
if (doFinalize) JS.SmilesAromatic.finalizeAromatic(this.target.nodes, this.target.bsAromatic, lstAromatic, lstSP2, eCounts, isOpenNotStrict, isStrict);
this.target.finalizeAromatic(lstAromatic);
}if (needRingData) {
this.target.finalizeRingData();
}}, "~A,~B,~B");
Clazz.defineMethod(c$, "subsearch", 
function(search, submode){
search.mapUnique = this.mapUnique;
search.target = this.target;
search.htNested = this.htNested;
search.haveSmilesTarget = this.haveSmilesTarget;
search.bsCheck = this.bsCheck;
search.isSmarts = true;
switch (submode) {
case 1:
search.exitFirstMatch = false;
break;
case 2:
search.isRingCheck = true;
search.isSilent = true;
search.asVector = true;
break;
case 3:
search.ignoreAtomClass = this.ignoreAtomClass;
search.aromaticDouble = this.aromaticDouble;
search.haveSelected = this.haveSelected;
search.exitFirstMatch = this.exitFirstMatch;
search.getMaps = this.getMaps;
search.retBoolean = this.retBoolean;
search.asVector = this.asVector;
search.vReturn = this.vReturn;
search.bsReturn = this.bsReturn;
search.haveBondStereochemistry = this.haveBondStereochemistry;
break;
}
return search.search2(submode == 1);
}, "JS.SmilesSearch,~N");
Clazz.defineMethod(c$, "search", 
function(){
this.bsReturn.clearAll();
return this.search2(false);
});
Clazz.defineMethod(c$, "search2", 
function(firstAtomOnly){
this.setFlags(this.flags);
if (!this.isRingCheck && JU.Logger.debuggingHigh && !this.isSilent) JU.Logger.debug("SmilesSearch processing " + this.pattern);
if (this.vReturn == null && (this.asVector || this.getMaps)) this.vReturn =  new JU.Lst();
if (this.subSearches != null) {
for (var i = 0; i < this.subSearches.length; i++) {
if (this.subSearches[i] == null) continue;
this.subsearch(this.subSearches[i], 3);
if (this.exitFirstMatch) {
if (this.vReturn == null ? this.bsReturn.nextSetBit(0) >= 0 : this.vReturn.size() > 0) break;
}}
} else if (this.ac > 0 && this.ac <= this.target.selectedAtomCount) {
if (this.nestedBond == null) {
this.clearBsFound(-1);
} else {
this.bsReturn.clearAll();
}this.nextPatternAtom(-1, -1, firstAtomOnly, -1);
}return (this.asVector || this.getMaps ? this.vReturn : !this.retBoolean ? this.bsReturn : Boolean.$valueOf(!this.bsReturn.isEmpty()));
}, "~B");
Clazz.defineMethod(c$, "nextPatternAtom", 
function(atomNum, iAtom, firstAtomOnly, c){
var jmolAtom;
var jmolBonds;
if (++atomNum < this.ac) {
var newPatternAtom = this.patternAtoms[atomNum];
var newPatternBond = (iAtom >= 0 ? newPatternAtom.getBondTo(null) : atomNum == 0 ? this.nestedBond : null);
if (newPatternBond == null) {
var bs = JU.BSUtil.copy(this.bsFound);
var bs0 = JU.BSUtil.copy(this.bsFound);
if (newPatternAtom.notBondedIndex >= 0) {
var pa = this.patternAtoms[newPatternAtom.notBondedIndex];
var a = pa.getMatchingAtom();
if (pa.isBioAtom) {
var ii = a.getOffsetResidueAtom("\0", 1);
if (ii >= 0) bs.set(ii);
ii = a.getOffsetResidueAtom("\0", -1);
if (ii >= 0) bs.set(ii);
} else if (pa === this.polyAtom) {
bs.set(pa.getMatchingAtomIndex());
} else {
jmolBonds = a.getEdges();
for (var k = 0; k < jmolBonds.length; k++) bs.set(jmolBonds[k].getOtherNode(a).getIndex());

}}var skipGroup = ((newPatternAtom.isBioAtomWild));
var j1 = this.target.bsSelected.nextSetBit(0);
j1 = (skipGroup && j1 >= 0 ? this.target.nodes[j1].getOffsetResidueAtom("\0", j1) : j1);
var oldJmolComponent;
var oldPatternComponent = (atomNum > 0 ? this.patternAtoms[atomNum - 1] : newPatternAtom).component;
var thisPatternComponent = newPatternAtom.component;
var checkComponents = this.haveComponents && thisPatternComponent != -2147483648;
for (var j = j1; j >= 0; j = this.target.bsSelected.nextSetBit(j + 1)) {
if (!bs.get(j) && !this.bsFound.get(j)) {
jmolAtom = this.target.nodes[j];
if (checkComponents && !this.isRingCheck) {
c = (this.groupByModel ? jmolAtom.getModelIndex() : jmolAtom.getMoleculeNumber(false));
oldJmolComponent = (atomNum > 0 ? this.patternAtoms[atomNum - 1].matchingComponent : c);
if ((oldPatternComponent == thisPatternComponent) != (oldJmolComponent == c)) continue;
}if (!this.nextTargetAtom(newPatternAtom, jmolAtom, atomNum, j, firstAtomOnly, c)) return false;
}if (skipGroup) {
j1 = this.target.nodes[j].getOffsetResidueAtom(newPatternAtom.bioAtomName, 1);
if (j1 >= 0) j = j1 - 1;
}}
this.bsFound = bs0;
return true;
}jmolAtom = newPatternBond.atom1.getMatchingAtom();
switch (newPatternBond.order) {
case 96:
var nextGroupAtom = jmolAtom.getOffsetResidueAtom(newPatternAtom.bioAtomName, 1);
if (nextGroupAtom >= 0) {
var bs = JU.BSUtil.copy(this.bsFound);
jmolAtom.getGroupBits(this.bsFound);
if (this.doCheckAtom(nextGroupAtom) && !this.nextTargetAtom(newPatternAtom, this.target.nodes[nextGroupAtom], atomNum, nextGroupAtom, firstAtomOnly, c)) return false;
this.bsFound = bs;
}return true;
case 112:
var vLinks =  new JU.Lst();
jmolAtom.getCrossLinkVector(vLinks, true, true);
var bs = JU.BSUtil.copy(this.bsFound);
jmolAtom.getGroupBits(this.bsFound);
for (var j = 2; j < vLinks.size(); j += 3) {
var ia = vLinks.get(j).intValue();
if (this.doCheckAtom(ia) && !this.nextTargetAtom(newPatternAtom, this.target.nodes[ia], atomNum, ia, firstAtomOnly, c)) return false;
}
this.bsFound = bs;
return true;
}
jmolBonds = jmolAtom.getEdges();
if (jmolBonds != null) for (var j = 0; j < jmolBonds.length; j++) {
var ia = jmolAtom.getBondedAtomIndex(j);
if (this.doCheckAtom(ia) && !this.nextTargetAtom(newPatternAtom, this.target.nodes[ia], atomNum, ia, firstAtomOnly, c)) return false;
}
this.clearBsFound(iAtom);
return true;
}if (!this.ignoreStereochemistry && !this.isRingCheck) {
if (JU.Logger.debuggingHigh) {
for (var i = 0; i < atomNum; i++) JU.Logger.debug("pattern atoms " + this.patternAtoms[i] + " " + this.patternAtoms[i].matchingComponent);

JU.Logger.debug("--ss-- " + this.bsFound.cardinality());
}if (!this.checkStereochemistry()) return true;
}var bs =  new JU.BS();
var nMatch = 0;
for (var j = 0; j < this.ac; j++) {
var i = this.patternAtoms[j].getMatchingAtomIndex();
if (!firstAtomOnly && this.top.haveSelected && !this.patternAtoms[j].selected) continue;
nMatch++;
bs.set(i);
if (this.patternAtoms[j].isBioAtomWild) this.target.nodes[i].getGroupBits(bs);
if (firstAtomOnly) break;
if (!this.isSmarts) if (!this.setAtropicity && this.patternAtoms[j].explicitHydrogenCount > 0) {
var atom = this.target.nodes[i];
for (var k = 0, n = atom.getEdges().length; k < n; k++) {
var ia = atom.getBondedAtomIndex(k);
if (this.target.nodes[ia].getElementNumber() == 1) bs.set(ia);
}
}}
if (!this.isSmarts && bs.cardinality() != this.target.selectedAtomCount) return true;
if (this.bsCheck != null) {
if (firstAtomOnly) {
this.bsCheck.clearAll();
for (var j = 0; j < this.ac; j++) {
this.bsCheck.set(this.patternAtoms[j].getMatchingAtomIndex());
}
if (this.bsCheck.cardinality() != this.ac) return true;
} else {
if (bs.cardinality() != this.ac) return true;
}}this.bsReturn.or(bs);
if (this.getMaps) {
if (this.mapUnique) {
if (this.uniqueList == null) this.uniqueList =  new JU.Lst();
for (var j = this.uniqueList.size(); --j >= 0; ) if (this.uniqueList.get(j).equals(bs)) return true;

this.uniqueList.addLast(bs);
}var map =  Clazz.newIntArray (nMatch, 0);
for (var j = 0, nn = 0; j < this.ac; j++) {
if (!firstAtomOnly && this.top.haveSelected && !this.patternAtoms[j].selected) continue;
map[nn++] = this.patternAtoms[j].getMatchingAtomIndex();
}
this.vReturn.addLast(map);
return !this.exitFirstMatch;
}if (this.asVector) {
var isOK = true;
for (var j = this.vReturn.size(); --j >= 0 && isOK; ) isOK = !((this.vReturn.get(j)).equals(bs));

if (!isOK) return true;
this.vReturn.addLast(bs);
}if (this.isRingCheck) {
var bsRing =  new JU.BS();
for (var k = atomNum * 3 + 2; --k > atomNum; ) bsRing.set(this.patternAtoms[(k <= atomNum * 2 ? atomNum * 2 - k + 1 : k - 1) % atomNum].getMatchingAtomIndex());

this.target.ringSets.addLast(bsRing);
return true;
}if (this.exitFirstMatch) return false;
return (bs.cardinality() != this.target.selectedAtomCount);
}, "~N,~N,~B,~N");
Clazz.defineMethod(c$, "doCheckAtom", 
function(j){
return this.target.bsSelected.get(j) && !this.bsFound.get(j);
}, "~N");
Clazz.defineMethod(c$, "nextTargetAtom", 
function(patternAtom, jmolAtom, atomNum, iAtom, firstAtomOnly, c){
var jmolBonds;
if (!this.isRingCheck && !this.isTopology) {
if (patternAtom.subAtoms == null) {
if (!this.checkPrimitiveAtom(patternAtom, iAtom)) return true;
} else if (patternAtom.isAND) {
for (var i = 0; i < patternAtom.nSubAtoms; i++) if (!this.checkPrimitiveAtom(patternAtom.subAtoms[i], iAtom)) return true;

} else {
for (var i = 0; i < patternAtom.nSubAtoms; i++) if (!this.nextTargetAtom(patternAtom.subAtoms[i], jmolAtom, atomNum, iAtom, firstAtomOnly, c)) return false;

return true;
}}jmolBonds = jmolAtom.getEdges();
for (var i = patternAtom.getBondCount(); --i >= 0; ) {
var patternBond = patternAtom.getBond(i);
if (patternBond.getAtomIndex2() != patternAtom.index) continue;
var atom1 = patternBond.atom1;
var matchingAtom = atom1.getMatchingAtomIndex();
switch (patternBond.order) {
case 96:
case 112:
if (!this.checkMatchBond(patternAtom, atom1, patternBond, iAtom, matchingAtom, null)) return true;
break;
default:
var k = 0;
var jmolBond = null;
for (; k < jmolBonds.length; k++) if ((jmolBond = jmolBonds[k]).isCovalent() && (jmolBond.getAtomIndex1() == matchingAtom || jmolBond.getAtomIndex2() == matchingAtom)) break;

if (k == jmolBonds.length) return true;
if (!this.checkMatchBond(patternAtom, atom1, patternBond, iAtom, matchingAtom, jmolBond)) return true;
}
}
patternAtom = this.patternAtoms[patternAtom.index];
patternAtom.setMatchingAtom(this.target.nodes[iAtom], iAtom);
patternAtom.matchingComponent = c;
this.bsFound.set(iAtom);
if (!this.nextPatternAtom(atomNum, iAtom, firstAtomOnly, c)) return false;
if (iAtom >= 0) this.clearBsFound(iAtom);
return true;
}, "JS.SmilesAtom,JU.Node,~N,~N,~B,~N");
Clazz.defineMethod(c$, "checkPrimitiveAtom", 
function(patternAtom, iTarget){
if (patternAtom.nSubAtoms > 0) {
for (var i = 0; i < patternAtom.nSubAtoms; i++) if (this.checkPrimitiveAtom(patternAtom.subAtoms[i], iTarget)) return true;

return false;
}var targetAtom = this.target.nodes[iTarget];
var foundAtom = patternAtom.not;
while (true) {
if (patternAtom.iNested > 0) {
var o = this.getNested(patternAtom.iNested);
if (Clazz.instanceOf(o,"JS.SmilesSearch")) {
var search = o;
if (patternAtom.isBioAtom) search.nestedBond = patternAtom.getBondTo(null);
o = this.subsearch(search, 1);
if (o == null) o =  new JU.BS();
if (!patternAtom.isBioAtom) this.setNested(patternAtom.iNested, o);
}foundAtom = (patternAtom.not != ((o).get(iTarget)));
break;
}var na = targetAtom.getElementNumber();
var n = patternAtom.elementNumber;
if (na >= 0 && n >= 0 && n != na && !this.ignoreElement) break;
if (patternAtom.isBioResidue) {
var a = targetAtom;
if (patternAtom.bioAtomName != null && (patternAtom.isLeadAtom() ? !a.isLeadAtom() : !patternAtom.bioAtomName.equals(a.getAtomName().toUpperCase()))) break;
if (patternAtom.residueName != null && !patternAtom.residueName.equals(a.getGroup3(false).toUpperCase())) break;
if (patternAtom.residueNumber != -2147483648 && patternAtom.residueNumber != a.getResno()) break;
if (patternAtom.insCode != '\0' && patternAtom.insCode != a.getInsertionCode()) break;
if (patternAtom.residueChar != null || patternAtom.elementNumber == -2) {
var atype = a.getBioSmilesType();
var ptype = patternAtom.getBioSmilesType();
var ok = true;
var isNucleic = false;
switch ((ptype).charCodeAt(0)) {
case 0:
case 42:
ok = true;
break;
case 110:
ok = (atype == 'r' || atype == 'c');
isNucleic = true;
break;
case 114:
case 99:
isNucleic = true;
default:
ok = (atype == ptype);
break;
}
if (!ok) break;
var s = a.getGroup1('\0').toUpperCase();
var resChar = (patternAtom.residueChar == null ? '*' : patternAtom.residueChar.charAt(0));
var isOK = (resChar == s.charAt(0));
switch ((resChar).charCodeAt(0)) {
case 42:
isOK = true;
break;
case 78:
isOK = isNucleic ? (atype == 'r' || atype == 'c') : isOK;
break;
case 82:
isOK = isNucleic ? a.isPurine() : isOK;
break;
case 89:
isOK = isNucleic ? a.isPyrimidine() : isOK;
break;
}
if (!isOK) break;
}if (patternAtom.isBioAtom) {
if (patternAtom.notCrossLinked && a.getCrossLinkVector(null, true, true)) break;
}} else {
if (patternAtom.atomNumber != -2147483648 && patternAtom.atomNumber != targetAtom.getAtomNumber()) break;
if (patternAtom.jmolIndex >= 0 && targetAtom.getIndex() != patternAtom.jmolIndex) break;
if (patternAtom.atomType != null && !patternAtom.atomType.equals(targetAtom.getAtomType())) break;
if ((n = patternAtom.getAtomicMass()) != -2147483648 && (n >= 0 && n != (na = targetAtom.getIsotopeNumber()) || n < 0 && na != 0 && -n != na)) break;
if (!this.noAromatic && !patternAtom.aromaticAmbiguous && patternAtom.isAromatic != this.target.bsAromatic.get(iTarget)) break;
if ((n = patternAtom.getCharge()) != -2147483648 && n != targetAtom.getFormalCharge()) break;
n = patternAtom.getCovalentHydrogenCount() + patternAtom.explicitHydrogenCount;
if (n >= 0 && n != targetAtom.getTotalHydrogenCount()) break;
if ((n = patternAtom.implicitHydrogenCount) != -2147483648) {
na = targetAtom.getImplicitHydrogenCount();
if (n == -1 ? na == 0 : n != na) break;
}if (patternAtom.degree > 0 && patternAtom.degree != targetAtom.getCovalentBondCount()) break;
if (patternAtom.nonhydrogenDegree > 0 && patternAtom.nonhydrogenDegree != targetAtom.getCovalentBondCount() - targetAtom.getCovalentHydrogenCount()) break;
if (this.isSmarts && patternAtom.valence > 0 && patternAtom.valence != targetAtom.getTotalValence()) break;
if (patternAtom.connectivity > 0 && patternAtom.connectivity != targetAtom.getCovalentBondCountPlusMissingH()) break;
if (patternAtom.atomNumber != -2147483648 && patternAtom.atomNumber != targetAtom.getAtomNumber()) break;
if (patternAtom.jmolIndex >= 0 && targetAtom.getIndex() != patternAtom.jmolIndex) break;
if (patternAtom.atomType != null && !patternAtom.atomType.equals(targetAtom.getAtomType())) break;
if (!this.ignoreAtomClass || this.isSmarts) {
if (!Float.isNaN(patternAtom.atomClass) && patternAtom.atomClass != targetAtom.getFloatProperty("property_atomclass")) break;
}if (this.target.ringData != null) {
if (patternAtom.ringSize >= -1) {
if (patternAtom.ringSize <= 0) {
if ((this.target.ringCounts[iTarget] == 0) != (patternAtom.ringSize == 0)) break;
} else {
var rd = this.target.ringData[patternAtom.ringSize == 500 ? 5 : patternAtom.ringSize == 600 ? 6 : patternAtom.ringSize];
if (rd == null || !rd.get(iTarget)) break;
if (!this.noAromatic) if (patternAtom.ringSize == 500) {
if (!this.target.bsAromatic5.get(iTarget)) break;
} else if (patternAtom.ringSize == 600) {
if (!this.target.bsAromatic6.get(iTarget)) break;
}}}if (patternAtom.ringMembership >= -1) {
if (patternAtom.ringMembership == -1 ? this.target.ringCounts[iTarget] == 0 : this.target.ringCounts[iTarget] != patternAtom.ringMembership) break;
}if (patternAtom.ringConnectivity >= 0) {
n = this.target.ringConnections[iTarget];
if (patternAtom.ringConnectivity == -1 && n == 0 || patternAtom.ringConnectivity != -1 && n != patternAtom.ringConnectivity) break;
}}}foundAtom = !foundAtom;
break;
}
return foundAtom;
}, "JS.SmilesAtom,~N");
Clazz.defineMethod(c$, "checkMatchBond", 
function(patternAtom, atom1, patternBond, iAtom, matchingAtom, bond){
if (patternBond.bondsOr != null) {
for (var ii = 0; ii < patternBond.nBondsOr; ii++) if (this.checkMatchBond(patternAtom, atom1, patternBond.bondsOr[ii], iAtom, matchingAtom, bond)) return true;

return false;
}if (!this.isRingCheck && !this.isTopology) if (patternBond.nPrimitives == 0) {
if (!this.checkPrimitiveBond(patternBond, iAtom, matchingAtom, bond)) return false;
} else {
for (var i = 0; i < patternBond.nPrimitives; i++) {
var prim = patternBond.setPrimitive(i);
if (!this.checkPrimitiveBond(prim, iAtom, matchingAtom, bond)) return false;
}
}patternBond.matchingBond = bond;
return true;
}, "JS.SmilesAtom,JS.SmilesAtom,JS.SmilesBond,~N,~N,JU.Edge");
Clazz.defineMethod(c$, "checkPrimitiveBond", 
function(patternBond, iAtom1, iAtom2, bond){
var bondFound = false;
switch (patternBond.order) {
case 96:
return (patternBond.isNot != (this.target.nodes[iAtom2].getOffsetResidueAtom("\0", 1) == this.target.nodes[iAtom1].getOffsetResidueAtom("\0", 0)));
case 112:
return (patternBond.isNot != this.target.nodes[iAtom1].isCrossLinked(this.target.nodes[iAtom2]));
}
var isAromatic1 = (!this.noAromatic && this.target.bsAromatic.get(iAtom1));
var isAromatic2 = (!this.noAromatic && this.target.bsAromatic.get(iAtom2));
var order = bond.getCovalentOrder();
var patternOrder = patternBond.order;
if (isAromatic1 && isAromatic2) {
switch (patternOrder) {
case 17:
case 65:
bondFound = JS.SmilesSearch.isRingBond(this.target.ringSets, null, iAtom1, iAtom2);
break;
case 1:
bondFound = !this.isSmarts || !JS.SmilesSearch.isRingBond(this.target.ringSets, this.target.getBSAromaticRings(), iAtom1, iAtom2);
break;
case 2:
bondFound = this.isNormalized || order == 81 || this.aromaticDouble && (order == 2 || order == 514);
break;
case 65537:
case 65538:
bondFound = !patternBond.isNot;
break;
case 81:
case -1:
bondFound = true;
break;
}
} else {
switch (patternOrder) {
case 17:
if (!this.noAromatic) break;
case 81:
case -1:
bondFound = true;
break;
case 1:
case 1025:
case 1041:
switch (order) {
case 1:
case 1025:
case 1041:
bondFound = true;
break;
}
break;
case 65537:
case 65538:
switch (order) {
case 1:
case 65537:
case 65538:
bondFound = !patternBond.isNot;
break;
}
break;
case 2:
case 3:
case 4:
bondFound = (order == patternOrder);
break;
case 65:
bondFound = JS.SmilesSearch.isRingBond(this.target.ringSets, null, iAtom1, iAtom2);
break;
}
}return bondFound != patternBond.isNot;
}, "JS.SmilesBond,~N,~N,JU.Edge");
Clazz.defineMethod(c$, "checkStereochemistry", 
function(){
for (var i = 0; i < this.measures.size(); i++) if (!this.measures.get(i).check()) return false;

if (this.stereo != null && !this.stereo.checkStereoChemistry(this, this.v)) return false;
if (!this.haveBondStereochemistry) return true;
var lstAtrop = null;
var b = null;
for (var k = 0; k < this.ac; k++) {
var sAtom1 = this.patternAtoms[k];
var sAtom2 = null;
var sAtomDirected1 = null;
var sAtomDirected2 = null;
var dir1 = 0;
var dir2 = 0;
var bondType = 0;
var nBonds = sAtom1.getBondCount();
var isAtropisomer = false;
var indexOrder = true;
for (var j = 0; j < nBonds; j++) {
b = sAtom1.getBond(j);
var isAtom2 = (b.atom2 === sAtom1);
indexOrder = (b.atom1.index < b.atom2.index);
var type = b.getBondType();
switch (type) {
case 65537:
case 65538:
if (!indexOrder) continue;
case 2:
if (isAtom2) continue;
sAtom2 = b.atom2;
bondType = type;
isAtropisomer = (type != 2);
if (isAtropisomer) dir1 = (b.isNot ? -1 : 1);
break;
case 1025:
case 1041:
sAtomDirected1 = (isAtom2 ? b.atom1 : b.atom2);
dir1 = (isAtom2 != (type == 1025) ? 1 : -1);
break;
}
}
if (isAtropisomer) {
if (this.setAtropicity) {
if (lstAtrop == null) lstAtrop =  new JU.Lst();
lstAtrop.addLast(b);
continue;
}var b1 = sAtom1.getBond(b.atropType[0]);
if (b1 == null) return false;
sAtomDirected1 = b1.getOtherAtom(sAtom1);
b1 = sAtom2.getBond(b.atropType[1]);
if (b1 == null) return false;
sAtomDirected2 = b1.getOtherAtom(sAtom2);
if (JU.Logger.debugging) JU.Logger.info("atropisomer check for atoms " + sAtomDirected1 + sAtom1 + " " + sAtom2 + sAtomDirected2);
} else {
if (sAtom2 == null || dir1 == 0) continue;
var a10 = sAtom1;
var nCumulene = 0;
while (sAtom2.getBondCount() == 2 && sAtom2.getValence() == 4) {
nCumulene++;
var e2 = sAtom2.getEdges();
var e = e2[e2[0].getOtherNode(sAtom2) === a10 ? 1 : 0];
a10 = sAtom2;
sAtom2 = e.getOtherNode(sAtom2);
}
if (nCumulene % 2 == 1) continue;
nBonds = sAtom2.getBondCount();
for (var j = 0; j < nBonds && dir2 == 0; j++) {
b = sAtom2.getBond(j);
var type = b.getBondType();
switch (type) {
case 1025:
case 1041:
var isAtom2 = (b.atom2 === sAtom2);
sAtomDirected2 = (isAtom2 ? b.atom1 : b.atom2);
dir2 = (isAtom2 != (type == 1025) ? 1 : -1);
break;
}
}
if (dir2 == 0) continue;
}var dbAtom1 = sAtom1.getMatchingAtom();
var dbAtom2 = sAtom2.getMatchingAtom();
var dbAtom1a = sAtomDirected1.getMatchingAtom();
var dbAtom2a = sAtomDirected2.getMatchingAtom();
if (dbAtom1a == null || dbAtom2a == null) return false;
if (this.haveSmilesTarget) JS.SmilesSearch.setTopoCoordinates(dbAtom1, dbAtom2, dbAtom1a, dbAtom2a, bondType);
var d = JS.SmilesMeasure.setTorsionData(dbAtom1a, dbAtom1, dbAtom2, dbAtom2a, this.v, isAtropisomer);
if (isAtropisomer) {
d *= dir1 * (bondType == 65537 ? 1 : -1) * (indexOrder ? 1 : -1) * 1 * -1;
if (JU.Logger.debugging) JU.Logger.info("atrop dihedral " + d + " " + sAtom1 + " " + sAtom2 + " " + b);
if (d < 1) return false;
} else {
if (this.v.vTemp1.dot(this.v.vTemp2) * dir1 * dir2 < 0) return false;
}}
if (this.setAtropicity) {
this.atropKeys = "";
for (var i = 0; i < lstAtrop.size(); i++) this.atropKeys += "," + this.getAtropIndex(lstAtrop.get(i));

}return true;
});
Clazz.defineMethod(c$, "getAtropIndex", 
function(b){
var nodes =  new Array(4);
var s = "";
nodes[1] = b.atom1.getMatchingAtom();
nodes[2] = b.atom2.getMatchingAtom();
var b1 = b.atom1.bonds;
var a;
for (var i = b.atom1.getBondCount(); --i >= 0; ) {
if ((a = b1[i].getOtherNode(b.atom1)) !== b.atom2) {
s += (i + 1);
nodes[0] = a.getMatchingAtom();
break;
}}
b1 = b.atom2.bonds;
for (var i = 0; i <= b.atom2.getBondCount(); i++) {
if ((a = b1[i].getOtherNode(b.atom2)) !== b.atom1) {
s += (i + 1);
nodes[3] = a.getMatchingAtom();
break;
}}
if (s.equals("22")) s = "";
s = (JS.SmilesStereo.getAtropicStereoFlag(nodes) == 1 ? "" : "^") + s;
return (s + "   ").substring(0, 3);
}, "JS.SmilesBond");
c$.setTopoCoordinates = Clazz.defineMethod(c$, "setTopoCoordinates", 
function(dbAtom1, dbAtom2, dbAtom1a, dbAtom2a, bondType){
dbAtom1.set(-1, 0, 0);
dbAtom2.set(1, 0, 0);
if (bondType != 2) {
var bond = dbAtom1.getBondTo(dbAtom2);
var ok1 = dbAtom1.getBondedAtomIndex(bond.atropType[0]) == dbAtom1a.index;
var ok2 = dbAtom2.getBondedAtomIndex(bond.atropType[1]) == dbAtom2a.index;
var dir = (bond.order == 65537 ? 1 : -1) * (ok1 == ok2 ? 1 : -1);
dbAtom1a.set(-1, 1, 0);
dbAtom2a.set(1, 1, dir / 2.0 * 1 * -1);
return;
}var nBonds = 0;
var dir1 = 0;
var bonds = dbAtom1.getEdges();
for (var k = bonds.length; --k >= 0; ) {
var bond = bonds[k];
if (bond.order == 2) continue;
var atom = bond.getOtherNode(dbAtom1);
(atom).set(-1, (nBonds++ == 0) ? -1 : 1, 0);
var mode = (bond.getAtomIndex2() == dbAtom1.getIndex() ? nBonds : -nBonds);
switch (bond.order) {
case 1025:
dir1 = mode;
break;
case 1041:
dir1 = -mode;
}
}
var dir2 = 0;
nBonds = 0;
var atoms =  new Array(2);
bonds = dbAtom2.getEdges();
for (var k = bonds.length; --k >= 0; ) {
var bond = bonds[k];
if (bond.order == 2) continue;
var atom = bond.getOtherNode(dbAtom2);
atoms[nBonds] = atom;
(atom).set(1, (nBonds++ == 0) ? 1 : -1, 0);
var mode = (bond.getAtomIndex2() == dbAtom2.getIndex() ? nBonds : -nBonds);
switch (bond.order) {
case 1025:
dir2 = mode;
break;
case 1041:
dir2 = -mode;
}
}
if ((dir1 * dir2 > 0) == (Math.abs(dir1) % 2 == Math.abs(dir2) % 2)) {
var y = (atoms[0]).y;
(atoms[0]).y = (atoms[1]).y;
(atoms[1]).y = y;
}}, "JS.SmilesAtom,JS.SmilesAtom,JS.SmilesAtom,JS.SmilesAtom,~N");
Clazz.defineMethod(c$, "createTopoMap", 
function(bsAro){
var isForMF = (bsAro == null);
var nAtomsMissing = (this.autoAddImplicitH ? this.getMissingHydrogenCount() : 0);
var totalAtoms = this.ac + nAtomsMissing;
var atoms =  new Array(totalAtoms);
this.target.nodes = atoms;
for (var i = 0, ptAtom = 0; i < this.ac; i++, ptAtom++) {
var sAtom = this.patternAtoms[i];
var n = sAtom.explicitHydrogenCount;
if (n < 0 || !this.autoAddImplicitH) n = 0;
var atom = atoms[ptAtom] =  new JS.SmilesAtom().setTopoAtom(sAtom.component, ptAtom, sAtom.symbol, sAtom.getCharge(), i);
atom.implicitHydrogenCount = n;
if (isForMF) continue;
atom.mapIndex = i;
atom.stereo = sAtom.stereo;
atom.setAtomicMass(sAtom.getAtomicMass());
atom.bioAtomName = sAtom.bioAtomName;
atom.residueName = sAtom.residueName;
atom.residueChar = sAtom.residueChar;
atom.residueNumber = sAtom.residueNumber;
atom.atomNumber = sAtom.residueNumber;
atom.insCode = sAtom.insCode;
atom.hasDoubleBond = sAtom.hasDoubleBond;
atom.isAromatic = sAtom.isAromatic;
atom.atomClass = sAtom.atomClass;
atom.explicitHydrogenCount = 0;
atom.isBioAtom = sAtom.isBioAtom;
atom.bioType = sAtom.bioType;
atom.$isLeadAtom = sAtom.$isLeadAtom;
if (!isForMF && sAtom.isAromatic) bsAro.set(ptAtom);
sAtom.setMatchingAtom(null, ptAtom);
var bonds =  new Array(sAtom.getBondCount() + n);
atom.setBonds(bonds);
while (--n >= 0) {
var atomH = atoms[++ptAtom] =  new JS.SmilesAtom().setTopoAtom(atom.component, ptAtom, "H", 0, -1);
atomH.mapIndex = -i - 1;
atomH.setBonds( new Array(1));
var b =  new JS.SmilesBond(atom, atomH, 1, false);
if (JU.Logger.debugging) JU.Logger.info("" + b);
}
}
if (isForMF) return;
for (var i = 0; i < this.ac; i++) {
var sAtom = this.patternAtoms[i];
var i1 = sAtom.getMatchingAtomIndex();
var atom1 = atoms[i1];
var n = sAtom.getBondCount();
for (var j = 0; j < n; j++) {
var sBond = sAtom.getBond(j);
var firstAtom = (sBond.atom1 === sAtom);
if (firstAtom) {
var order = 1;
switch (sBond.order) {
case 1:
case 2:
case 3:
case 4:
case 1025:
case 1041:
case 65537:
case 65538:
case 112:
case 96:
order = sBond.order;
break;
case 17:
order = 514;
break;
}
var atom2 = atoms[sBond.atom2.getMatchingAtomIndex()];
var b =  new JS.SmilesBond(atom1, atom2, order, false);
b.isConnection = sBond.isConnection;
b.atropType = sBond.atropType;
b.isNot = sBond.isNot;
atom2.bondCount--;
if (JU.Logger.debugging) JU.Logger.info("" + b);
} else {
var atom2 = atoms[sBond.atom1.getMatchingAtomIndex()];
var b = atom2.getBondTo(atom1);
atom1.addBond(b);
}}
}
for (var i = 0; i < totalAtoms; i++) {
var a = atoms[i];
var bonds = a.bonds;
if (bonds.length < 2 || bonds[0].isFromPreviousTo(a)) continue;
for (var k = bonds.length; --k >= 1; ) if (bonds[k].isFromPreviousTo(a)) {
var b = bonds[k];
bonds[k] = bonds[0];
bonds[0] = b;
break;
}
}
if (!this.ignoreStereochemistry) for (var i = this.ac; --i >= 0; ) {
var sAtom = this.patternAtoms[i];
if (sAtom.stereo != null) sAtom.stereo.fixStereo(sAtom);
}
}, "JU.BS");
Clazz.defineMethod(c$, "normalizeAromaticity", 
function(bsAromatic){
var atoms = this.patternAtoms;
var ss =  new JS.SmilesSearch();
ss.noAromatic = this.noAromatic;
ss.setFlags(this.flags);
ss.target.nodes = atoms;
ss.target.ac = atoms.length;
ss.target.bsSelected = JU.BSUtil.newBitSet2(0, atoms.length);
var vRings = JU.AU.createArrayOfArrayList(4);
ss.setRingData(null, vRings, true);
bsAromatic.or(ss.target.bsAromatic);
if (!bsAromatic.isEmpty()) {
var lst = vRings[3];
if (lst != null) for (var i = lst.size(); --i >= 0; ) {
var bs = lst.get(i);
for (var j = bs.nextSetBit(0); j >= 0; j = bs.nextSetBit(j + 1)) {
var a = atoms[j];
if (a.isAromatic || a.elementNumber == -2 || a.elementNumber == 0) continue;
a.setSymbol(a.symbol.toLowerCase());
}
}
}}, "JU.BS");
Clazz.defineMethod(c$, "getSelections", 
function(){
var ht = this.top.htNested;
if (ht == null || this.target.nodes.length == 0) return;
var htNew =  new java.util.Hashtable();
for (var entry, $entry = ht.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
var key = entry.getValue().toString();
if (key.startsWith("select")) {
var bs = (htNew.containsKey(key) ? htNew.get(key) : this.target.nodes[0].findAtomsLike(key.substring(6)));
if (bs == null) bs =  new JU.BS();
htNew.put(key, bs);
entry.setValue(bs);
}}
});
Clazz.defineMethod(c$, "findImplicitHydrogen", 
function(atom){
var edges = atom.getEdges();
for (var i = edges.length; --i >= 0; ) {
var k = atom.getBondedAtomIndex(i);
if (this.target.nodes[k].getElementNumber() == 1 && !this.bsFound.get(k)) return this.target.nodes[k];
}
return null;
}, "JU.Node");
Clazz.defineMethod(c$, "toString", 
function(){
if (this.pattern0 != null) return this.pattern0;
if (this.targetSet) {
return "molecular formula: " + this.target.getMolecularFormula(true, null, false);
}var sb =  new JU.SB().append(this.pattern);
sb.append("\nmolecular formula: " + this.getMolecularFormula(true, null, false));
return sb.toString();
});
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.bsSelected = null;
this.selectedAtomCount = 0;
this.ringSets = null;
this.ringCount = 0;
this.ringData = null;
this.ringDataMax = 0;
this.ringCounts = null;
this.ringConnections = null;
this.bsAromatic = null;
this.bsAromatic5 = null;
this.bsAromatic6 = null;
this.bsAromaticRings = null;
this.$hasRingData = false;
this.flags = -1;
Clazz.instantialize(this, arguments);}, JS.SmilesSearch, "SmilesTarget", JU.JmolMolecule);
Clazz.prepareFields (c$, function(){
this.bsAromatic =  new JU.BS();
this.bsAromatic5 =  new JU.BS();
this.bsAromatic6 =  new JU.BS();
});
Clazz.defineMethod(c$, "hasRingData", 
function(flags){
if (flags != this.flags) {
this.flags = flags;
this.$hasRingData = false;
}var ret = this.$hasRingData;
this.$hasRingData = true;
return ret;
}, "~N");
Clazz.defineMethod(c$, "setAtoms", 
function(atoms, ac, bs){
this.$hasRingData = false;
this.nodes = atoms;
this.ac = ac;
this.selectedAtomCount = (bs == null ? ac : bs.cardinality());
if (bs == null) {
bs = JU.BS.newN(ac);
bs.setBits(0, ac);
}this.bsSelected = bs;
}, "~A,~N,JU.BS");
Clazz.defineMethod(c$, "checkAromaticDefined", 
function(){
JS.SmilesAromatic.checkAromaticDefined(this.nodes, this.bsSelected, this.bsAromatic);
});
Clazz.defineMethod(c$, "getBSAromaticRings", 
function(){
if (this.bsAromaticRings == null) {
this.bsAromaticRings =  new JU.BS();
if (this.ringSets != null && this.bsAromatic != null) {
for (var i = this.ringSets.size(); --i >= 0; ) {
var bsRing = this.ringSets.get(i).clone();
bsRing.andNot(this.bsAromatic);
if (bsRing.isEmpty()) this.bsAromaticRings.set(i);
}
}}return this.bsAromaticRings;
});
Clazz.defineMethod(c$, "setRingData", 
function(strictness, needRingData, ringDataMax){
if (ringDataMax < 0) ringDataMax = 8;
if (strictness > 0 && ringDataMax < 6) ringDataMax = 6;
if (needRingData) {
this.ringCounts =  Clazz.newIntArray (this.ac, 0);
this.ringConnections =  Clazz.newIntArray (this.ac, 0);
this.ringData =  new Array(ringDataMax + 1);
}this.ringSets =  new JU.Lst();
return this.ringDataMax = ringDataMax;
}, "~N,~B,~N");
Clazz.defineMethod(c$, "finalizeAromatic", 
function(lstAromatic){
this.bsAromatic5.clearAll();
this.bsAromatic6.clearAll();
for (var i = lstAromatic.size(); --i >= 0; ) {
var bs = lstAromatic.get(i);
bs.and(this.bsAromatic);
switch (bs.cardinality()) {
case 5:
this.bsAromatic5.or(bs);
break;
case 6:
this.bsAromatic6.or(bs);
break;
}
}
}, "JU.Lst");
Clazz.defineMethod(c$, "finalizeRingData", 
function(){
for (var i = this.bsSelected.nextSetBit(0); i >= 0; i = this.bsSelected.nextSetBit(i + 1)) {
var atom = this.nodes[i];
var nb = atom.getBondCount();
for (var k = nb; --k >= 0; ) {
if (this.ringCounts[atom.getBondedAtomIndex(k)] > 0) this.ringConnections[i]++;
}
}
});
Clazz.defineMethod(c$, "hasDoubleBonds", 
function(){
for (var i = 0; i < this.nodes.length; i++) if (this.bsSelected == null || this.bsSelected.get(i)) {
var n = this.nodes[i];
if (n.getElementNumber() == 1) {
continue;
}var nb = n.getBondCount();
var edges = n.getEdges();
for (var j = 0; j < nb; j++) {
if (edges[j].isCovalent() && edges[j].getBondType() != 1) return true;
}
}
return false;
});
/*eoif3*/})();
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
