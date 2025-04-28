Clazz.declarePackage("JS");
Clazz.load(["J.api.SmilesMatcherInterface"], "JS.SmilesMatcher", ["JU.AU", "$.BS", "$.PT", "JS.InvalidSmilesException", "$.SmilesAtom", "$.SmilesBond", "$.SmilesGenerator", "$.SmilesParser", "$.SmilesSearch", "JU.BSUtil", "$.Elements", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.okMF = true;
Clazz.instantialize(this, arguments);}, JS, "SmilesMatcher", null, J.api.SmilesMatcherInterface);
Clazz.overrideMethod(c$, "getLastException", 
function(){
return (this.okMF == true ? JS.InvalidSmilesException.getLastError() : "MF_FAILED");
});
Clazz.overrideMethod(c$, "getMolecularFormula", 
function(pattern, isSmarts, isEmpirical){
this.clearExceptions();
var search = JS.SmilesParser.newSearch("/nostereo/" + pattern, isSmarts, true);
search.createTopoMap(null);
search.nodes = search.target.nodes;
return search.getMolecularFormula(!isSmarts, null, isEmpirical);
}, "~S,~B,~B");
Clazz.defineMethod(c$, "clearExceptions", 
function(){
JS.InvalidSmilesException.clear();
});
Clazz.overrideMethod(c$, "getSmiles", 
function(atoms, ac, bsSelected, bioComment, flags){
this.clearExceptions();
return ( new JS.SmilesGenerator()).getSmiles(this, atoms, ac, bsSelected, bioComment, flags);
}, "~A,~N,JU.BS,~S,~N");
Clazz.overrideMethod(c$, "areEqual", 
function(smiles1, smiles2){
this.clearExceptions();
var isWild = (smiles1.indexOf("*") >= 0);
if (!isWild && smiles1.equals(smiles2)) return 1;
var flags = (isWild ? 2 : 1) | 8;
var result = this.matchPriv(smiles1, null, 0, null, null, false, flags, 2, JS.SmilesParser.newSearch(smiles2, false, true));
return (result == null ? -1 : result.length);
}, "~S,~S");
Clazz.defineMethod(c$, "areEqualTest", 
function(smiles, search){
search.set();
var ret = this.matchPriv(smiles, null, 0, null, null, false, 9, 2, search);
return (ret != null && ret.length == 1);
}, "~S,JS.SmilesSearch");
Clazz.overrideMethod(c$, "find", 
function(pattern, target, flags){
this.clearExceptions();
target = JS.SmilesParser.cleanPattern(target);
pattern = JS.SmilesParser.cleanPattern(pattern);
var search = JS.SmilesParser.newSearch(target, false, true);
var array = this.matchPriv(pattern, null, 0, null, null, false, flags, 3, search);
for (var i = array.length; --i >= 0; ) {
var a = array[i];
for (var j = a.length; --j >= 0; ) a[j] = (search.target.nodes[a[j]]).mapIndex;

}
return array;
}, "~S,~S,~N");
Clazz.overrideMethod(c$, "getAtoms", 
function(target){
this.clearExceptions();
target = JS.SmilesParser.cleanPattern(target);
var search = JS.SmilesParser.newSearch(target, false, true);
search.createTopoMap( new JU.BS());
return search.target.nodes;
}, "~S");
Clazz.overrideMethod(c$, "getRelationship", 
function(smiles1, smiles2){
if (smiles1 == null || smiles2 == null || smiles1.length == 0 || smiles2.length == 0) return "";
var mf1 = this.getMolecularFormula(smiles1, false, false);
var mf2 = this.getMolecularFormula(smiles2, false, false);
if (!mf1.equals(mf2)) return "none";
var check;
var n1 = JU.PT.countChar(JU.PT.rep(smiles1, "@@", "@"), '@');
var n2 = JU.PT.countChar(JU.PT.rep(smiles2, "@@", "@"), '@');
check = (n1 == n2 && this.areEqual(smiles2, smiles1) > 0);
if (!check) {
var s = smiles1 + smiles2;
if (s.indexOf("/") >= 0 || s.indexOf("\\") >= 0 || s.indexOf("@") >= 0) {
if (n1 == n2 && n1 > 0 && s.indexOf("@SP") < 0) {
check = (this.areEqual("/invertstereo/" + smiles2, smiles1) > 0);
if (check) return "enantiomers";
}check = (this.areEqual("/nostereo/" + smiles2, smiles1) > 0);
if (check) return (n1 == n2 ? "diastereomers" : "ambiguous stereochemistry!");
}return "constitutional isomers";
}return "identical";
}, "~S,~S");
Clazz.overrideMethod(c$, "reverseChirality", 
function(smiles){
smiles = JU.PT.rep(smiles, "@@", "!@");
smiles = JU.PT.rep(smiles, "@", "@@");
smiles = JU.PT.rep(smiles, "!@@", "@");
return smiles;
}, "~S");
Clazz.overrideMethod(c$, "getSubstructureSet", 
function(pattern, target, ac, bsSelected, flags){
var atoms = (Clazz.instanceOf(target,"JS.SmilesSearch") ? null : target);
return this.matchPriv(pattern, atoms, ac, bsSelected, null, true, flags | JS.SmilesParser.getFlags(pattern.toString()), 1, (atoms == null ? target : null));
}, "~O,~O,~N,JU.BS,~N");
Clazz.overrideMethod(c$, "getMMFF94AtomTypes", 
function(smarts, atoms, ac, bsSelected, ret, vRings){
this.clearExceptions();
var sp =  new JS.SmilesParser(true, true);
var search = null;
var flags = (770);
search = sp.parse("");
search.exitFirstMatch = false;
search.target.setAtoms(atoms, Math.abs(ac), bsSelected);
search.flags = flags;
search.getRingData(vRings, true, true);
search.asVector = false;
search.subSearches =  new Array(1);
search.getSelections();
var bsDone =  new JU.BS();
for (var i = 0; i < smarts.length; i++) {
if (smarts[i] == null || smarts[i].length == 0 || smarts[i].startsWith("#")) {
ret.addLast(null);
continue;
}search.clear();
search.subSearches[0] = sp.getSubsearch(search, JS.SmilesParser.cleanPattern(smarts[i]), flags);
var bs = JU.BSUtil.copy(search.search());
ret.addLast(bs);
bsDone.or(bs);
if (bsDone.cardinality() == ac) return;
}
}, "~A,~A,~N,JU.BS,JU.Lst,~A");
Clazz.overrideMethod(c$, "getSubstructureSetArray", 
function(pattern, atoms, ac, bsSelected, bsAromatic, flags){
return this.matchPriv(pattern, atoms, ac, bsSelected, bsAromatic, true, flags, 2, null);
}, "~S,~A,~N,JU.BS,JU.BS,~N");
Clazz.defineMethod(c$, "getAtropisomerKeys", 
function(pattern, atoms, ac, bsSelected, bsAromatic, flags){
return this.matchPriv(pattern, atoms, ac, bsSelected, bsAromatic, false, flags, 4, null);
}, "~S,~A,~N,JU.BS,JU.BS,~N");
Clazz.overrideMethod(c$, "polyhedronToSmiles", 
function(center, faces, atomCount, points, flags, details){
var atoms =  new Array(atomCount);
for (var i = 0; i < atomCount; i++) {
atoms[i] =  new JS.SmilesAtom();
var pt = (points == null ? null : points[i]);
if (Clazz.instanceOf(pt,"JU.Node")) {
atoms[i].elementNumber = (pt).getElementNumber();
atoms[i].bioAtomName = (pt).getAtomName();
atoms[i].atomNumber = (pt).getAtomNumber();
atoms[i].setT(pt);
} else {
atoms[i].elementNumber = (Clazz.instanceOf(pt,"JU.Point3fi") ? (pt).sD : -2);
if (pt != null) atoms[i].setT(pt);
}atoms[i].index = i;
}
var nBonds = 0;
for (var i = faces.length; --i >= 0; ) {
var face = faces[i];
var n = face.length;
var iatom;
var iatom2;
for (var j = n; --j >= 0; ) {
if ((iatom = face[j]) >= atomCount || (iatom2 = face[(j + 1) % n]) >= atomCount) continue;
if (atoms[iatom].getBondTo(atoms[iatom2]) == null) {
var b =  new JS.SmilesBond(atoms[iatom], atoms[iatom2], 1, false);
b.index = nBonds++;
}}
}
for (var i = 0; i < atomCount; i++) {
var n = atoms[i].bondCount;
if (n == 0 || n != atoms[i].bonds.length) atoms[i].bonds = JU.AU.arrayCopyObject(atoms[i].bonds, n);
}
var s = null;
var g =  new JS.SmilesGenerator();
if (points != null) g.polySmilesCenter = center;
this.clearExceptions();
s = g.getSmiles(this, atoms, atomCount, JU.BSUtil.newBitSet2(0, atomCount), null, flags | 4096 | 16 | 32);
if ((flags & 65536) == 65536) {
s = ((flags & 131072) == 0 ? "" : "//* " + center + " *//\t") + "[" + JU.Elements.elementSymbolFromNumber(center.getElementNumber()) + "@PH" + atomCount + (details == null ? "" : "/" + details + "/") + "]." + s;
}return s;
}, "JU.Node,~A,~N,~A,~N,~S");
Clazz.overrideMethod(c$, "getCorrelationMaps", 
function(pattern, atoms, atomCount, bsSelected, flags){
return this.matchPriv(pattern, atoms, atomCount, bsSelected, null, true, flags, 3, null);
}, "~S,~A,~N,JU.BS,~N");
Clazz.defineMethod(c$, "matchPriv", 
function(pattern, atoms, ac, bsSelected, bsAromatic, doTestAromatic, flags, mode, searchTarget){
this.clearExceptions();
try {
var isCompiled = (Clazz.instanceOf(pattern,"JS.SmilesSearch"));
if (isCompiled) flags |= 2;
var isSmarts = ((flags & 2) == 2);
var search = (isCompiled ? pattern : JS.SmilesParser.newSearch(pattern == null ? null : pattern.toString(), isSmarts, false));
if (searchTarget != null) searchTarget.setFlags(searchTarget.flags | JS.SmilesParser.getFlags(pattern.toString()));
return this.matchPattern(search, atoms, ac, bsSelected, bsAromatic, doTestAromatic, flags, mode, searchTarget);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (JU.Logger.debugging) e.printStackTrace();
if (JS.InvalidSmilesException.getLastError() == null) this.clearExceptions();
throw  new JS.InvalidSmilesException(JS.InvalidSmilesException.getLastError());
} else {
throw e;
}
}
}, "~O,~A,~N,JU.BS,JU.BS,~B,~N,~N,JS.SmilesSearch");
Clazz.defineMethod(c$, "matchPattern", 
function(search, atoms, ac, bsSelected, bsAromatic, doTestAromatic, flags, mode, searchTarget){
var isSmarts = ((flags & 2) == 2);
this.okMF = true;
if (searchTarget != null) {
if (searchTarget.targetSet) {
search.setTarget(searchTarget);
} else {
search.haveSmilesTarget = true;
bsAromatic =  new JU.BS();
searchTarget.createTopoMap(bsAromatic);
atoms = searchTarget.target.nodes;
ac = searchTarget.target.nodes.length;
if (isSmarts) {
var a1 = searchTarget.elementCounts;
var a2 = search.elementCounts;
var n = search.elementNumberMax;
if (n <= searchTarget.elementNumberMax) {
for (var i = 1; i <= n; i++) {
if (a1[i] < a2[i]) {
this.okMF = false;
break;
}}
} else {
this.okMF = false;
}} else {
var mf = search.getMFArray(true, null, false);
var mft = searchTarget.getMFArray(true, null, false);
var n = searchTarget.elementNumberMax;
if (n == search.elementNumberMax) {
for (var i = 2; i <= n; i++) {
if (mf[i] != mft[i]) {
this.okMF = false;
break;
}}
} else {
this.okMF = false;
}}}}if (this.okMF) {
if (!isSmarts && !search.patternAromatic) {
if (bsAromatic == null) bsAromatic =  new JU.BS();
search.normalizeAromaticity(bsAromatic);
search.isNormalized = true;
}if (!search.targetSet) search.target.setAtoms(atoms, ac, bsSelected);
if (search.targetSet || ac != 0 && (bsSelected == null || !bsSelected.isEmpty())) {
var is3D = search.targetSet || !(Clazz.instanceOf(atoms[0],"JS.SmilesAtom"));
search.getSelections();
if (!doTestAromatic) search.target.bsAromatic = bsAromatic;
if (!search.target.hasRingData(flags)) search.setRingData(null, null, is3D || doTestAromatic || search.patternAromatic);
search.exitFirstMatch = ((flags & 8) == 8);
search.mapUnique = ((flags & 128) == 128);
}}switch (mode) {
case 1:
search.asVector = false;
return (this.okMF ? search.search() :  new JU.BS());
case 2:
if (!this.okMF) return  new Array(0);
search.asVector = true;
var vb = search.search();
return vb.toArray( new Array(vb.size()));
case 4:
if (!this.okMF) return "";
search.exitFirstMatch = true;
search.setAtropicity = true;
search.search();
return search.atropKeys;
case 3:
if (!this.okMF) return  Clazz.newIntArray (0, 0, 0);
search.getMaps = true;
search.setFlags(flags | search.flags);
var vl = search.search();
return vl.toArray(JU.AU.newInt2(vl.size()));
case 5:
if (!this.okMF) return Boolean.FALSE;
search.retBoolean = true;
search.setFlags(flags | search.flags);
return search.search();
}
return null;
}, "JS.SmilesSearch,~A,~N,JU.BS,JU.BS,~B,~N,~N,JS.SmilesSearch");
Clazz.overrideMethod(c$, "cleanSmiles", 
function(smiles){
return JS.SmilesParser.cleanPattern(smiles);
}, "~S");
Clazz.overrideMethod(c$, "getMapForJME", 
function(jme, at, bsAtoms){
try {
var molecule = JS.SmilesMatcher.jmeToMolecule(jme);
var bs = JU.BSUtil.newBitSet2(0, molecule.ac);
var s = this.getSmiles(molecule.patternAtoms, molecule.ac, bs, null, 34);
var map = this.getCorrelationMaps(s, molecule.patternAtoms, molecule.ac, bs, 42);
var map2 = this.getCorrelationMaps(s, at, bsAtoms.cardinality(), bsAtoms, 42);
return  Clazz.newArray(-1, [map[0], map2[0]]);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
} else {
throw e;
}
}
return null;
}, "~S,~A,JU.BS");
c$.jmeToMolecule = Clazz.defineMethod(c$, "jmeToMolecule", 
function(jme){
var molecule =  new JS.SmilesSearch();
var tokens = JU.PT.getTokens(jme);
var nAtoms = JU.PT.parseInt(tokens[0]);
var nBonds = JU.PT.parseInt(tokens[1]);
var pt = 2;
for (var i = 0; i < nAtoms; i++, pt += 3) {
var sa = tokens[pt];
var a = molecule.addAtom();
var ic = sa.indexOf("+");
var charge = 0;
if (ic >= 0) {
charge = (ic == sa.length - 1 ? 1 : JU.PT.parseInt(sa.substring(ic + 1)));
} else if ((ic = sa.indexOf("-")) >= 0) {
charge = JU.PT.parseInt(sa.substring(ic));
}a.setCharge(charge);
a.setSymbol(ic < 0 ? sa : sa.substring(0, ic));
}
for (var i = 0; i < nBonds; i++) {
var ia = JU.PT.parseInt(tokens[pt++]) - 1;
var ib = JU.PT.parseInt(tokens[pt++]) - 1;
var iorder = JU.PT.parseInt(tokens[pt++]);
var a1 = molecule.patternAtoms[ia];
var a2 = molecule.patternAtoms[ib];
var order = 1;
switch (iorder) {
default:
case 1:
break;
case 2:
order = 2;
break;
case 3:
order = 3;
break;
}
 new JS.SmilesBond(a1, a2, order, false).index = i;
}
molecule.isSmarts = true;
molecule.set();
return molecule;
}, "~S");
Clazz.overrideMethod(c$, "getSmilesFromJME", 
function(jme){
try {
var molecule = JS.SmilesMatcher.jmeToMolecule(jme);
var bs = JU.BSUtil.newBitSet2(0, molecule.ac);
return this.getSmiles(molecule.patternAtoms, molecule.ac, bs, null, 1);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "~S");
Clazz.overrideMethod(c$, "compileSmartsPattern", 
function(pattern){
pattern = JS.SmilesParser.cleanPattern(pattern);
return JS.SmilesParser.newSearch(pattern, true, false);
}, "~S");
Clazz.overrideMethod(c$, "compileSearchTarget", 
function(atoms, atomCount, bsSelected){
var ss =  new JS.SmilesSearch();
ss.target.setAtoms(atoms, atomCount, bsSelected);
ss.targetSet = true;
return ss;
}, "~A,~N,JU.BS");
Clazz.overrideMethod(c$, "hasStructure", 
function(pattern, smilesSet, flags){
var ret =  Clazz.newIntArray (smilesSet.length, 0);
if ((flags & 1) != 1) {
flags = flags | 2;
}this.clearExceptions();
pattern = JS.SmilesParser.cleanPattern(pattern);
try {
var search = JS.SmilesParser.newSearch(pattern, true, false);
for (var i = 0; i < smilesSet.length; i++) {
var smiles = JS.SmilesParser.cleanPattern(smilesSet[i]);
var searchTarget = JS.SmilesParser.newSearch(smiles, false, true);
searchTarget.setFlags(searchTarget.flags | JS.SmilesParser.getFlags(pattern));
try {
this.clearExceptions();
ret[i] = (this.matchPattern(search, null, 0, null, null, false, flags | 8, 5, searchTarget) === Boolean.TRUE ? 1 : 0);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
ret[i] = -1;
e.printStackTrace();
} else {
throw e;
}
}
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (JU.Logger.debugging) e.printStackTrace();
if (JS.InvalidSmilesException.getLastError() == null) this.clearExceptions();
throw  new JS.InvalidSmilesException(JS.InvalidSmilesException.getLastError());
} else {
throw e;
}
}
return ret;
}, "~S,~A,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
