Clazz.declarePackage("JS");
Clazz.load(["JU.BS"], "JS.CIPChirality", ["java.util.Arrays", "$.Collections", "$.Hashtable", "JU.Lst", "$.PT", "JU.Elements", "$.Logger", "JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.currentRule = 1;
this.root = null;
this.data = null;
this.doTrack = false;
this.isAux = false;
this.bsNeedRule = null;
this.havePseudoAuxiliary = false;
this.ptIDLogger = 0;
if (!Clazz.isClassDefined("JS.CIPChirality.CIPAtom")) {
JS.CIPChirality.$CIPChirality$CIPAtom$ ();
}
Clazz.instantialize(this, arguments);}, JS, "CIPChirality", null);
Clazz.prepareFields (c$, function(){
this.bsNeedRule =  new JU.BS();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "getRuleName", 
function(rule){
return JS.CIPChirality.ruleNames[rule];
}, "~N");
Clazz.defineMethod(c$, "getChiralityForAtoms", 
function(data){
if (data.bsAtoms.isEmpty()) return;
this.data = data;
this.doTrack = data.isTracker();
this.ptIDLogger = 0;
var bsToDo = data.bsMolecule.clone();
var haveAlkenes = this.preFilterAtomList(data.atoms, bsToDo, data.bsEnes);
if (!data.bsEnes.isEmpty()) data.getEneKekule();
this.logInfo("bsKekule:" + data.bsKekuleAmbiguous);
bsToDo = data.bsAtoms.clone();
for (var i = bsToDo.nextSetBit(0); i >= 0; i = bsToDo.nextSetBit(i + 1)) {
var a = data.atoms[i];
a.setCIPChirality(0);
this.ptIDLogger = 0;
var c = this.getAtomChiralityLimited(a, null, null);
a.setCIPChirality(c == 0 ? 3 : c | ((this.currentRule - 1) << 5));
if (this.doTrack && c != 0) data.getRootTrackerResult(this.root);
}
if (haveAlkenes) {
var lstEZ =  new JU.Lst();
for (var i = bsToDo.nextSetBit(0); i >= 0; i = bsToDo.nextSetBit(i + 1)) this.getAtomBondChirality(data.atoms[i], lstEZ, bsToDo);

if (data.lstSmallRings.length > 0 && lstEZ.size() > 0) this.clearSmallRingEZ(data.atoms, lstEZ);
this.setStereoFromSmiles(data.bsHelixM, 17, data.atoms);
this.setStereoFromSmiles(data.bsHelixP, 18, data.atoms);
}if (JU.Logger.debugging) {
this.logInfo("Kekule ambiguous = " + data.bsKekuleAmbiguous);
this.logInfo("small rings = " + JU.PT.toJSON(null, data.lstSmallRings));
}}, "JS.CIPData");
Clazz.defineMethod(c$, "setStereoFromSmiles", 
function(bsHelix, stereo, atoms){
if (bsHelix != null) for (var i = bsHelix.nextSetBit(0); i >= 0; i = bsHelix.nextSetBit(i + 1)) atoms[i].setCIPChirality(stereo);

}, "JU.BS,~N,~A");
Clazz.defineMethod(c$, "preFilterAtomList", 
function(atoms, bsToDo, bsEnes){
var haveAlkenes = false;
for (var i = bsToDo.nextSetBit(0); i >= 0; i = bsToDo.nextSetBit(i + 1)) {
if (!this.data.couldBeChiralAtom(atoms[i])) {
bsToDo.clear(i);
continue;
}switch (this.data.couldBeChiralAlkene(atoms[i], null)) {
case -1:
break;
case 13:
bsEnes.set(i);
case 17:
haveAlkenes = true;
break;
}
}
return haveAlkenes;
}, "~A,JU.BS,JU.BS");
c$.isFirstRow = Clazz.defineMethod(c$, "isFirstRow", 
function(a){
var n = a.getElementNumber();
return (n > 2 && n <= 10);
}, "JU.SimpleNode");
Clazz.defineMethod(c$, "clearSmallRingEZ", 
function(atoms, lstEZ){
for (var j = this.data.lstSmallRings.length; --j >= 0; ) this.data.lstSmallRings[j].andNot(this.data.bsAtropisomeric);

for (var i = lstEZ.size(); --i >= 0; ) {
var ab = lstEZ.get(i);
for (var j = this.data.lstSmallRings.length; --j >= 0; ) {
var ring = this.data.lstSmallRings[j];
if (ring.get(ab[0]) && ring.get(ab[1])) {
atoms[ab[0]].setCIPChirality(3);
atoms[ab[1]].setCIPChirality(3);
}}
}
}, "~A,JU.Lst");
Clazz.defineMethod(c$, "getAtomBondChirality", 
function(atom, lstEZ, bsToDo){
var index = atom.getIndex();
var bonds = atom.getEdges();
var c = 0;
var isAtropic = this.data.bsAtropisomeric.get(index);
for (var j = bonds.length; --j >= 0; ) {
var bond = bonds[j];
var atom1;
var index1;
if (isAtropic) {
atom1 = bonds[j].getOtherNode(atom);
index1 = atom1.getIndex();
if (!this.data.bsAtropisomeric.get(index1)) continue;
c = this.setBondChirality(atom, atom1, atom, atom1, true);
} else if (this.data.getBondOrder(bond) == 2) {
atom1 = this.getLastCumuleneAtom(bond, atom, null, null);
index1 = atom1.getIndex();
if (index1 < index) continue;
c = this.getBondChiralityLimited(bond, atom);
} else {
continue;
}if (c != 0) {
if (!isAtropic) lstEZ.addLast( Clazz.newIntArray(-1, [index, index1]));
bsToDo.clear(index);
bsToDo.clear(index1);
}if (isAtropic) break;
}
}, "JU.SimpleNode,JU.Lst,JU.BS");
Clazz.defineMethod(c$, "getLastCumuleneAtom", 
function(bond, atom, nSP2, parents){
var atom2 = bond.getOtherNode(atom);
if (parents != null) {
parents[0] = atom2;
parents[1] = atom;
}if (nSP2 != null) nSP2[0] = 2;
var ppt = 0;
while (true) {
if (atom2.getCovalentBondCount() != 2) return atom2;
var edges = atom2.getEdges();
for (var i = edges.length; --i >= 0; ) {
var atom3 = (bond = edges[i]).getOtherNode(atom2);
if (atom3 === atom) continue;
if (this.data.getBondOrder(bond) != 2) return atom2;
if (parents != null) {
if (ppt == 0) {
parents[0] = atom2;
ppt = 1;
}parents[1] = atom2;
}if (nSP2 != null) nSP2[0]++;
atom = atom2;
atom2 = atom3;
break;
}
}
}, "JU.SimpleEdge,JU.SimpleNode,~A,~A");
Clazz.defineMethod(c$, "getAtomChiralityLimited", 
function(atom, cipAtom, parentAtom){
var rs = 0;
this.bsNeedRule.clearAll();
this.bsNeedRule.set(1);
try {
var isAlkeneEndCheck = (atom == null);
if (isAlkeneEndCheck) {
atom = (this.root = cipAtom).atom;
cipAtom.htPathPoints = (cipAtom.parent = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(parentAtom, null, true, false, false)).htPathPoints;
} else {
if (!(this.root = cipAtom = (cipAtom == null ? Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(atom, null, false, false, false) : cipAtom)).isSP3) {
return 0;
}}if (cipAtom.setNode()) {
for (this.currentRule = 1; this.currentRule <= 9; this.currentRule++) {
var nPrioritiesPrev = cipAtom.nPriorities;
switch (this.currentRule) {
case 3:
if (cipAtom.rule6refIndex >= 0) this.bsNeedRule.set(3);
break;
case 4:
this.isAux = true;
this.doTrack = false;
this.havePseudoAuxiliary = false;
cipAtom.createAuxiliaryDescriptors(null, null);
this.doTrack = this.data.isTracker();
this.isAux = false;
break;
case 5:
if (!this.bsNeedRule.get(5)) {
this.currentRule = 8;
continue;
}case 6:
case 7:
cipAtom.sortSubstituents(-2147483648);
this.bsNeedRule.set(this.currentRule);
break;
case 8:
if (this.havePseudoAuxiliary) cipAtom.clearRule4Lists();
cipAtom.sortSubstituents(-2147483648);
this.bsNeedRule.set(this.currentRule);
break;
case 9:
this.bsNeedRule.setBitTo(9, (cipAtom.rule6refIndex < 0 && (rs = cipAtom.getRule6Descriptor(false)) != 0));
break;
}
if (!this.bsNeedRule.get(this.currentRule)) continue;
if (rs == 0 && cipAtom.sortSubstituents(0)) {
if (JU.Logger.debuggingHigh && cipAtom.h1Count < 2) {
for (var i = 0; i < cipAtom.bondCount; i++) {
if (cipAtom.atoms[i] != null) this.logInfo(cipAtom.atoms[i] + " " + cipAtom.priorities[i]);
}
}if (isAlkeneEndCheck) return cipAtom.getEneTop();
rs = this.data.checkHandedness(cipAtom);
if (this.currentRule == 8) {
if (cipAtom.nPriorities == 4 && nPrioritiesPrev == 2) cipAtom.isRule5Pseudo = !cipAtom.isRule5Pseudo;
if (cipAtom.isRule5Pseudo) rs |= 8;
}if (JU.Logger.debugging) this.logInfo(atom + " " + JV.JC.getCIPChiralityName(rs) + " by Rule " + this.getRuleName(this.currentRule) + "\n----------------------------------");
return rs;
}}
}} catch (e) {
System.out.println(e + " in CIPChirality " + this.currentRule);
{
alert(e);
}return 3;
}
return rs;
}, "JU.SimpleNode,JS.CIPChirality.CIPAtom,JU.SimpleNode");
Clazz.defineMethod(c$, "getBondChiralityLimited", 
function(bond, a){
if (a == null) a = bond.getOtherNode(null);
if (this.data.couldBeChiralAlkene(a, bond) == -1) return 0;
var nSP2 =  Clazz.newIntArray (1, 0);
var parents =  new Array(2);
var b = this.getLastCumuleneAtom(bond, a, nSP2, parents);
var isAxial = nSP2[0] % 2 == 1;
if (!isAxial && this.data.bsAromatic.get(a.getIndex())) return -1;
var c = this.setBondChirality(a, parents[0], parents[1], b, isAxial);
if (JU.Logger.debugging) this.logInfo("get Bond Chirality " + JV.JC.getCIPChiralityName(c) + " " + bond);
return c;
}, "JU.SimpleEdge,JU.SimpleNode");
Clazz.defineMethod(c$, "setBondChirality", 
function(a, pa, pb, b, isAxial){
var a1 = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(a, null, true, false, false);
var b2 = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(b, null, true, false, false);
var atop = this.getAtomChiralityLimited(null, a1, pa) - 1;
var ruleA = this.currentRule;
var btop = this.getAtomChiralityLimited(null, b2, pb) - 1;
var ruleB = this.currentRule;
if (isAxial && a1.nRootDuplicates > 3 && atop < 0 && btop < 0) {
ruleA = ruleB = this.currentRule = 9;
b2.rule6refIndex = a1.atoms[atop = a1.getEneTop() - 1].atomIndex;
if (b2.sortSubstituents(0)) btop = b2.getEneTop() - 1;
}var c = (atop >= 0 && btop >= 0 ? this.getEneChirality(b2.atoms[btop], b2, a1, a1.atoms[atop], isAxial, true) : 0);
if (c != 0 && (isAxial || !this.data.bsAtropisomeric.get(a.getIndex()) && !this.data.bsAtropisomeric.get(b.getIndex()))) {
if (isAxial == (ruleA == 8) == (ruleB == 8)) c &= -9;
 else c |= 8;
a.setCIPChirality(c | ((ruleA - 1) << 5));
b.setCIPChirality(c | ((ruleB - 1) << 5));
if (JU.Logger.debugging) this.logInfo(a + "-" + b + " " + JV.JC.getCIPChiralityName(c));
}return c;
}, "JU.SimpleNode,JU.SimpleNode,JU.SimpleNode,JU.SimpleNode,~B");
Clazz.defineMethod(c$, "getEneChirality", 
function(winner1, end1, end2, winner2, isAxial, allowPseudo){
return (winner1 == null || winner2 == null || winner1.atom == null || winner2.atom == null ? 0 : isAxial ? this.data.isPositiveTorsion(winner1, end1, end2, winner2) : this.data.isCis(winner1, end1, end2, winner2));
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,~B,~B");
Clazz.defineMethod(c$, "logInfo", 
function(msg){
JU.Logger.info(msg);
}, "~S");
c$.$CIPChirality$CIPAtom$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.isRule5Pseudo = true;
this.id = 0;
this.sphere = 0;
this.rootDistance = 0;
this.isSet = false;
this.isDuplicate = true;
this.isTerminal = false;
this.isAlkene = false;
this.atom = null;
this.atomIndex = -1;
this.bondCount = 0;
this.elemNo = 0;
this.mass = -1;
this.parent = null;
this.rootSubstituent = null;
this.h1Count = 0;
this.atoms = null;
this.nAtoms = 0;
this.bsPath = null;
this.myPath = "";
this.oldPriorities = null;
this.priorities =  Clazz.newIntArray (4, 0);
this.oldNPriorities = 0;
this.nPriorities = 0;
this.priority = 0;
this.chiralPath = null;
this.nRootDuplicates = 0;
this.htPathPoints = null;
this.rule6refIndex = -1;
this.bsRule6Subs = null;
this.alkeneParent = null;
this.alkeneChild = null;
this.isAlkeneAtom2 = false;
this.isKekuleAmbiguous = false;
this.nextSP2 = null;
this.multipleBondDuplicate = false;
this.isEvenEne = true;
this.auxEZ = -1;
this.isSP3 = true;
this.auxChirality = '~';
this.nextChiralBranch = null;
this.isChiralPath = false;
this.rule4Type = 0;
this.bsTemp = null;
this.rule4Ref = 0;
this.listRS = null;
Clazz.instantialize(this, arguments);}, JS.CIPChirality, "CIPAtom", null, [Comparable, Cloneable]);
Clazz.prepareFields (c$, function(){
this.atoms =  new Array(4);
this.bsTemp =  new JU.BS();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "create", 
function(atom, parent, isAlkene, isDuplicate, isParentBond){
this.id = ++this.b$["JS.CIPChirality"].ptIDLogger;
this.parent = parent;
if (atom == null) return this;
this.isAlkene = isAlkene;
this.atom = atom;
this.atomIndex = atom.getIndex();
if (atom.getIsotopeNumber() > 0) this.b$["JS.CIPChirality"].bsNeedRule.set(3);
this.isDuplicate = this.multipleBondDuplicate = isDuplicate;
this.isKekuleAmbiguous = (this.b$["JS.CIPChirality"].data.bsKekuleAmbiguous != null && this.b$["JS.CIPChirality"].data.bsKekuleAmbiguous.get(this.atomIndex));
this.elemNo = (isDuplicate && this.isKekuleAmbiguous ? parent.getKekuleElementNumber() : atom.getElementNumber());
this.bondCount = atom.getCovalentBondCount();
this.isSP3 = (this.bondCount == 4 || this.bondCount == 3 && !isAlkene && (this.elemNo > 10 || this.b$["JS.CIPChirality"].data.bsAzacyclic != null && this.b$["JS.CIPChirality"].data.bsAzacyclic.get(this.atomIndex)));
if (parent != null) this.sphere = parent.sphere + 1;
if (this.sphere == 1) {
this.rootSubstituent = this;
} else if (parent != null && parent.htPathPoints != null) {
this.rootSubstituent = parent.rootSubstituent;
this.htPathPoints = (parent.htPathPoints).clone();
}if (this.htPathPoints == null) this.htPathPoints =  new java.util.Hashtable();
this.bsPath = (parent == null ?  new JU.BS() : parent.bsPath.clone());
if (isDuplicate) this.b$["JS.CIPChirality"].bsNeedRule.set(4);
this.rootDistance = this.sphere;
if (parent == null) {
this.bsPath.set(this.atomIndex);
} else if (this.multipleBondDuplicate) {
this.rootDistance--;
} else if (this.bsPath.get(this.atomIndex)) {
this.b$["JS.CIPChirality"].bsNeedRule.setBitTo(2, (this.isDuplicate = true));
if ((this.rootDistance = (atom === this.b$["JS.CIPChirality"].root.atom ? 0 : isParentBond ? parent.sphere : this.htPathPoints.get(Integer.$valueOf(this.atomIndex)).intValue())) == 0) {
this.b$["JS.CIPChirality"].root.nRootDuplicates++;
}} else {
this.bsPath.set(this.atomIndex);
this.htPathPoints.put(Integer.$valueOf(this.atomIndex), Integer.$valueOf(this.rootDistance));
}if (this.b$["JS.CIPChirality"].doTrack) {
if (this.sphere < 50) this.myPath = (parent != null ? parent.myPath + "-" : "") + this;
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo("new CIPAtom " + this.myPath);
}return this;
}, "JU.SimpleNode,JS.CIPChirality.CIPAtom,~B,~B,~B");
Clazz.defineMethod(c$, "getEneTop", 
function(){
return (this.atoms[0].isDuplicate ? 2 : 1);
});
Clazz.defineMethod(c$, "getRule6Descriptor", 
function(isAux){
if (this.nPriorities > 2 || (isAux ? this.countAuxDuplicates(this.atomIndex) : this.nRootDuplicates) <= 2) return 0;
var i1 = (this.priorities[0] == this.priorities[1] ? 0 : 1);
var i2 = (this.priorities[2] != this.priorities[3] ? 3 : 4);
var istep = (this.priorities[2] == this.priorities[1] ? 1 : 2);
var rsRM = 0;
var rsSP = 0;
var bsSubs =  new JU.BS();
for (var i = i1; i < i2; i++) bsSubs.set(this.atoms[i].atomIndex);

if (this.nPriorities == 1) i2 = 2;
var cipAtom = null;
var rs;
for (var i = i1; i < i2; i += istep) {
if (this.b$["JS.CIPChirality"].data.testRule6Full) {
cipAtom = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(this.atom, null, false, false, false);
cipAtom.rule6refIndex = this.atoms[i].atomIndex;
cipAtom.setNode();
for (var j = 0; j < 4; j++) {
cipAtom.atoms[j] = this.atoms[j].clone();
cipAtom.priorities[j] = this.priorities[j];
}
cipAtom.bsRule6Subs = bsSubs;
rs = this.b$["JS.CIPChirality"].getAtomChiralityLimited(this.atom, cipAtom, null);
this.b$["JS.CIPChirality"].currentRule = 9;
if (rs == 0) return 0;
} else {
this.b$["JS.CIPChirality"].root.bsRule6Subs =  new JU.BS();
this.b$["JS.CIPChirality"].root.rule6refIndex = this.atoms[i].atomIndex;
this.saveRestorePriorities(false);
this.sortSubstituents(-2147483648);
if (!this.sortSubstituents(0)) return 0;
rs = this.b$["JS.CIPChirality"].data.checkHandedness(this);
this.saveRestorePriorities(true);
}if ((rs & 8) == 0) {
if (rs == 1 || rs == 17) {
if (rsRM == 0) {
rsRM = rs;
continue;
}} else if (rsSP == 0) {
rsSP = rs;
continue;
}}return rs;
}
return 0;
}, "~B");
Clazz.defineMethod(c$, "saveRestorePriorities", 
function(isRestore){
if (isRestore) {
this.priorities = this.oldPriorities;
this.nPriorities = this.oldNPriorities;
} else {
this.oldPriorities =  Clazz.newIntArray(-1, [this.priorities[0], this.priorities[1], this.priorities[2], this.priorities[3]]);
this.oldNPriorities = this.nPriorities;
}for (var i = 0; i < this.nAtoms; i++) this.atoms[i].saveRestorePriorities(isRestore);

}, "~B");
Clazz.defineMethod(c$, "countAuxDuplicates", 
function(index){
var n = 0;
for (var i = 0; i < 4; i++) {
if (this.atoms[i] == null) continue;
if (this.atoms[i].isDuplicate) {
if (this.atoms[i].atomIndex == index) n++;
} else {
n += this.atoms[i].countAuxDuplicates(index);
}}
return n;
}, "~N");
Clazz.defineMethod(c$, "getMass", 
function(){
if (this.isDuplicate) return 0;
if (this.mass == -1) {
if (this.isDuplicate || (this.mass = this.atom.getMass()) != Clazz.floatToInt(this.mass) || this.isType(";9Be;19F;23Na;27Al;31P;45Sc;55Mn;59Co;75As;89Y;93Nb;98Tc;103Rh;127I;133Cs;141Pr;145Pm;159Tb;165Ho;169Tm;197Au;209Bi;209Po;210At;222Rn;223Fr;226Ra;227Ac;231Pa;232Th;and all > U (atomno > 92)")) return (this.mass == -1 ? this.mass = JU.Elements.getAtomicMass(Clazz.floatToInt(this.elemNo)) : this.mass);
if (this.isType(";16O;52Cr;96Mo;175Lu;")) this.mass -= 0.1;
}return this.mass;
});
Clazz.defineMethod(c$, "isType", 
function(rule2Type){
return JU.PT.isOneOf(Clazz.floatToInt(this.mass) + JU.Elements.elementSymbolFromNumber(Clazz.floatToInt(this.elemNo)), rule2Type);
}, "~S");
Clazz.defineMethod(c$, "getKekuleElementNumber", 
function(){
var edges = this.atom.getEdges();
var bond;
var ave = 0;
var n = 0;
for (var i = edges.length; --i >= 0; ) if ((bond = edges[i]).isCovalent()) {
var other = bond.getOtherNode(this.atom);
if (this.b$["JS.CIPChirality"].data.bsKekuleAmbiguous.get(other.getIndex())) {
n++;
ave += other.getElementNumber();
}}
return ave / n;
});
Clazz.defineMethod(c$, "setNode", 
function(){
if (this.isSet || (this.isSet = true) && this.isDuplicate) return true;
var index = this.atom.getIndex();
var bonds = this.atom.getEdges();
var nBonds = bonds.length;
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo("set " + this);
var pt = 0;
for (var i = 0; i < nBonds; i++) {
var bond = bonds[i];
if (!bond.isCovalent()) continue;
var other = bond.getOtherNode(this.atom);
var isParentBond = (this.parent != null && this.parent.atom === other);
var order = this.b$["JS.CIPChirality"].data.getBondOrder(bond);
if (order == 2) {
if (this.elemNo > 10 || !JS.CIPChirality.isFirstRow(other)) order = 1;
 else {
this.isAlkene = true;
if (isParentBond) this.setEne();
}}if (nBonds == 1 && order == 1 && isParentBond) return this.isTerminal = true;
switch (order) {
case 3:
if (this.addAtom(pt++, other, isParentBond, false, isParentBond) == null) return !(this.isTerminal = true);
case 2:
if (this.addAtom(pt++, other, order != 2 || isParentBond, order == 2, isParentBond) == null) return !(this.isTerminal = true);
case 1:
if (isParentBond || this.addAtom(pt++, other, order != 1 && this.elemNo <= 10, false, false) != null) break;
default:
return !(this.isTerminal = true);
}
}
this.nAtoms = pt;
switch (pt) {
case 2:
case 3:
if (this.elemNo == 6 && this.b$["JS.CIPChirality"].data.bsNegativeAromatic.get(index) || this.b$["JS.CIPChirality"].data.bsXAromatic.get(index)) {
this.nAtoms++;
this.addAtom(pt++, this.atom, true, false, false);
}break;
}
this.fillAtoms(pt);
try {
java.util.Arrays.sort(this.atoms);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
} else {
throw e;
}
}
return true;
});
Clazz.defineMethod(c$, "fillAtoms", 
function(pt){
if (pt < 4) for (; pt < this.atoms.length; pt++) if (this.atoms[pt] == null) this.atoms[pt] = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(null, this, false, true, false);

}, "~N");
Clazz.defineMethod(c$, "setEne", 
function(){
this.parent.alkeneChild = null;
this.alkeneParent = (this.parent.alkeneParent == null ? this.parent : this.parent.alkeneParent);
this.alkeneParent.alkeneChild = this;
this.nextSP2 = this.parent;
if (this.parent.alkeneParent == null) this.parent.nextSP2 = this;
if (this.atom.getCovalentBondCount() == 2 && this.atom.getValence() == 4) {
this.parent.isAlkeneAtom2 = false;
this.alkeneParent.isEvenEne = !this.alkeneParent.isEvenEne;
} else {
this.isAlkeneAtom2 = true;
}});
Clazz.defineMethod(c$, "addAtom", 
function(i, other, isDuplicate, isAlkene, isParentBond){
if (i >= this.atoms.length) {
if (JU.Logger.debugging) this.b$["JS.CIPChirality"].logInfo(" too many bonds on " + this.atom);
return null;
}if (other.getElementNumber() == 1 && other.getIsotopeNumber() == 0) {
if (++this.h1Count > 1) {
if (this.parent == null) {
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo(" second H atom found on " + this.atom);
return null;
}}}return this.atoms[i] = Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(other, this, isAlkene, isDuplicate, isParentBond);
}, "~N,JU.SimpleNode,~B,~B,~B");
Clazz.defineMethod(c$, "sortSubstituents", 
function(sphere){
if (this.nPriorities == (sphere < 1 ? 4 : 3)) return true;
var ignoreTies = (sphere == -2147483648);
if (ignoreTies) {
if (this.isTerminal) return false;
switch (this.b$["JS.CIPChirality"].currentRule) {
case 5:
case 7:
for (var i = 0; i < 4; i++) if (this.atoms[i] != null && (this.atoms[i].isChiralPath || this.atoms[i].nextChiralBranch != null)) this.atoms[i].sortSubstituents(-2147483648);

if (this.isAlkene) return false;
break;
case 9:
for (var i = 0; i < 4; i++) if (this.atoms[i] != null && !this.atoms[i].isDuplicate && this.atoms[i].atom != null && this.atoms[i].setNode()) this.atoms[i].sortSubstituents(-2147483648);

break;
}
}ignoreTies = new Boolean (ignoreTies | (this.b$["JS.CIPChirality"].currentRule == 6 || this.b$["JS.CIPChirality"].currentRule == 8)).valueOf();
var indices =  Clazz.newIntArray (4, 0);
var newPriorities =  Clazz.newIntArray (4, 0);
if (JU.Logger.debuggingHigh && this.h1Count < 2) {
this.b$["JS.CIPChirality"].logInfo(this.b$["JS.CIPChirality"].root + "---sortSubstituents---" + this);
for (var i = 0; i < 4; i++) {
this.b$["JS.CIPChirality"].logInfo(this.b$["JS.CIPChirality"].getRuleName(this.b$["JS.CIPChirality"].currentRule) + ": " + this + "[" + i + "]=" + this.atoms[i].myPath + " " + Integer.toHexString(this.priorities[i]));
}
this.b$["JS.CIPChirality"].logInfo("---" + this.nPriorities);
}var loser;
for (var i = 0; i < 3; i++) {
var a = this.atoms[i];
var aLoses = a.isDuplicate && this.b$["JS.CIPChirality"].currentRule > 2;
for (var j = i + 1; j < 4; j++) {
var b = this.atoms[loser = j];
var score = 0;
switch (b.atom == null || this.priorities[i] < this.priorities[j] ? -1 : aLoses || a.atom == null || this.priorities[j] < this.priorities[i] ? 1 : (score = a.checkCurrentRule(b)) != 0 && score != -2147483648 || ignoreTies ? score : this.sign(a.breakTie(b, sphere + 1))) {
case 1:
loser = i;
case -1:
newPriorities[loser]++;
if (this.b$["JS.CIPChirality"].doTrack && score != 0 && (sphere == 0 || ignoreTies)) this.b$["JS.CIPChirality"].data.track(this.b$["JS.CIPChirality"], a, b, 1, score, false);
case -2147483648:
case 0:
indices[loser]++;
continue;
}
}
}
this.bsTemp.clearAll();
var newAtoms =  new Array(4);
for (var i = 0; i < 4; i++) {
var pt = indices[i];
var a = newAtoms[pt] = this.atoms[i];
var p = newPriorities[i];
if (a.atom != null) this.bsTemp.set(p);
a.priority = this.priorities[pt] = p;
}
this.atoms = newAtoms;
this.nPriorities = this.bsTemp.cardinality();
if (JU.Logger.debuggingHigh && this.atoms[2].atom != null && this.atoms[2].elemNo != 1) {
this.b$["JS.CIPChirality"].logInfo(this.dots() + this.atom + " nPriorities = " + this.nPriorities);
for (var i = 0; i < 4; i++) {
this.b$["JS.CIPChirality"].logInfo(this.dots() + this.myPath + "[" + i + "]=" + this.atoms[i] + " " + this.priorities[i] + " " + Integer.toHexString(this.priorities[i]));
}
this.b$["JS.CIPChirality"].logInfo(this.dots() + "-------" + this.nPriorities);
}return (this.nPriorities == this.bondCount);
}, "~N");
Clazz.defineMethod(c$, "dots", 
function(){
return ".....................".substring(0, Math.min(20, this.sphere));
});
Clazz.defineMethod(c$, "breakTie", 
function(b, sphere){
var finalScore = 0;
while (true) {
if (this.isDuplicate && (this.b$["JS.CIPChirality"].currentRule > 2 || b.isDuplicate && this.atom === b.atom && this.rootDistance == b.rootDistance) || !this.setNode() || !b.setNode() || this.isTerminal && b.isTerminal || this.isDuplicate && b.isDuplicate) break;
if (this.isTerminal != b.isTerminal) {
finalScore = (this.isTerminal ? 1 : -1) * (sphere + (b.isDuplicate || this.isDuplicate ? 0 : 1));
if (this.b$["JS.CIPChirality"].doTrack) this.b$["JS.CIPChirality"].data.track(this.b$["JS.CIPChirality"], this, b, sphere, finalScore, true);
break;
}var score = (this.b$["JS.CIPChirality"].currentRule > 2 ? 0 : this.unlikeDuplicates(b));
if (score != 0) {
finalScore = score * (sphere + 1);
if (this.b$["JS.CIPChirality"].doTrack) this.b$["JS.CIPChirality"].data.track(this.b$["JS.CIPChirality"], this, b, sphere, finalScore, false);
break;
}for (var i = 0; i < this.nAtoms; i++) if ((score = this.atoms[i].checkCurrentRule(b.atoms[i])) != 0) {
finalScore = score * (sphere + 1);
if (this.b$["JS.CIPChirality"].doTrack) this.b$["JS.CIPChirality"].data.track(this.b$["JS.CIPChirality"], this.atoms[i], b.atoms[i], sphere, finalScore, false);
break;
}
if (finalScore != 0) {
break;
}this.sortSubstituents(sphere);
b.sortSubstituents(sphere);
for (var i = 0, abs, absScore = 2147483647; i < this.nAtoms; i++) {
if ((score = this.atoms[i].breakTie(b.atoms[i], sphere + 1)) != 0 && (abs = Math.abs(score)) < absScore) {
absScore = abs;
finalScore = score;
}}
break;
}
return finalScore;
}, "JS.CIPChirality.CIPAtom,~N");
Clazz.overrideMethod(c$, "compareTo", 
function(b){
var score;
return (this.b$["JS.CIPChirality"].root.rule4Ref == 0 ? (b == null ? -1 : (this.atom == null) != (b.atom == null) ? (this.atom == null ? 1 : -1) : (score = this.compareRule1a(b)) != 0 ? score : (score = this.unlikeDuplicates(b)) != 0 ? score : this.isDuplicate ? this.compareRule1b(b) : this.compareRule2(b)) : this.sphere < b.sphere ? -1 : this.sphere > b.sphere ? 1 : this.chiralPath.compareTo(b.chiralPath));
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "checkCurrentRule", 
function(b){
switch (this.b$["JS.CIPChirality"].currentRule) {
default:
case 1:
return this.compareRule1a(b);
case 2:
return this.compareRule1b(b);
case 3:
return this.compareRule2(b);
case 4:
return this.compareRule3(b);
case 5:
return this.compareRules4ac(b, " sr SR PM");
case 6:
case 8:
return (this.isTerminal || b.isTerminal ? 0 : this.compareRule4b5(b));
case 7:
return this.compareRules4ac(b, " s r p m");
case 9:
return this.compareRule6(b);
}
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "unlikeDuplicates", 
function(b){
return b.isDuplicate == this.isDuplicate ? 0 : this.isDuplicate ? 1 : -1;
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRule1a", 
function(b){
return b.atom == null ? -1 : this.atom == null ? 1 : b.elemNo < this.elemNo ? -1 : b.elemNo > this.elemNo ? 1 : 0;
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRule1b", 
function(b){
return Integer.compare(this.rootDistance, b.rootDistance);
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRule2", 
function(b){
return (this.atomIndex == b.atomIndex ? 0 : this.getMass() > b.getMass() ? -1 : this.mass < b.mass ? 1 : this.b$["JS.CIPChirality"].root.rule6refIndex < 0 ? 0 : !this.b$["JS.CIPChirality"].root.bsRule6Subs.get(this.atomIndex) || !this.b$["JS.CIPChirality"].root.bsRule6Subs.get(b.atomIndex) ? 0 : this.b$["JS.CIPChirality"].root.rule6refIndex == this.atomIndex ? -1 : this.b$["JS.CIPChirality"].root.rule6refIndex == b.atomIndex ? 1 : 0);
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRule3", 
function(b){
return (this.isDuplicate || b.isDuplicate || !this.parent.isAlkeneAtom2 || !b.parent.isAlkeneAtom2 || !this.parent.alkeneParent.isEvenEne || !b.parent.alkeneParent.isEvenEne || this.parent === b.parent ? 0 : this.parent.auxEZ < b.parent.auxEZ ? -1 : 1);
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRules4ac", 
function(b, test){
if (this.isTerminal || this.isDuplicate) return 0;
var isRa = test.indexOf(this.auxChirality);
var isRb = test.indexOf(b.auxChirality);
return (isRa > isRb + 1 ? -1 : isRb > isRa + 1 ? 1 : 0);
}, "JS.CIPChirality.CIPAtom,~S");
Clazz.defineMethod(c$, "compareRule4b5", 
function(b){
var bsA = this.getBetter4bList();
var bsB = b.getBetter4bList();
var best = this.compareLikeUnlike(bsA, bsB);
var score = (best == null ? -2147483648 : best === bsA ? -1 : 1);
if (best != null) {
if (this.b$["JS.CIPChirality"].currentRule == 8) {
if ((this.compareLikeUnlike(this.listRS[2], b.listRS[2]) === this.listRS[2]) == (best === bsA)) this.parent.isRule5Pseudo = !this.parent.isRule5Pseudo;
}if (this.b$["JS.CIPChirality"].doTrack) this.b$["JS.CIPChirality"].data.track(this.b$["JS.CIPChirality"], this, b, 1, score, false);
}return score;
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "compareRule6", 
function(b){
return ((this.atomIndex == this.b$["JS.CIPChirality"].root.rule6refIndex) == (b.atomIndex == this.b$["JS.CIPChirality"].root.rule6refIndex) ? 0 : this.atomIndex == this.b$["JS.CIPChirality"].root.rule6refIndex ? -1 : 1);
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "clearRule4Lists", 
function(){
this.listRS = null;
for (var i = 0; i < 4 && this.atoms[i] != null; i++) this.atoms[i].clearRule4Lists();

});
Clazz.defineMethod(c$, "getBetter4bList", 
function(){
if (this.listRS != null) return this.listRS[this.b$["JS.CIPChirality"].currentRule == 8 ? 1 : 0];
var bs;
this.listRS =  Clazz.newArray(-1, [null, bs = this.rank4bAndRead(null), this.rank4bAndRead(bs)]);
this.b$["JS.CIPChirality"].logInfo("getBest " + this.b$["JS.CIPChirality"].currentRule + " " + this + " " + this.listRS[1] + this.listRS[2] + " " + this.myPath);
bs = this.compareLikeUnlike(this.listRS[1], this.listRS[2]);
return this.listRS[0] = (this.b$["JS.CIPChirality"].currentRule == 8 || bs == null ? this.listRS[1] : bs);
});
Clazz.defineMethod(c$, "rank4bAndRead", 
function(bsR){
var isS = (bsR != null);
var ref = (isS ? 2 : 1);
var list =  new JU.BS();
var chiralAtoms =  new JU.Lst();
this.b$["JS.CIPChirality"].root.rule4Ref = ref;
this.addChiralAtoms(chiralAtoms, ref);
java.util.Collections.sort(chiralAtoms);
this.b$["JS.CIPChirality"].root.rule4Ref = 0;
for (var i = 0, n = chiralAtoms.size(); i < n; i++) {
if (JU.Logger.debugging) this.b$["JS.CIPChirality"].logInfo("" + ref + " " + this + " " + chiralAtoms.get(i).chiralPath);
if (chiralAtoms.get(i).rule4Type == ref) list.set(i);
}
return list;
}, "JU.BS");
Clazz.defineMethod(c$, "addChiralAtoms", 
function(chiralAtoms, ref){
if (this.atom == null || this.isTerminal || this.isDuplicate) return;
if (this.rule4Type != 0) {
var s = "";
var a = this;
while (a != null) {
s = String.fromCharCode(64 + (a.priority << 2) + (a.rule4Type == 0 ? 0 : a.rule4Type == ref ? 1 : 2)) + s;
if ((a = a.parent) != null && a.chiralPath != null) {
s = a.chiralPath + s;
break;
}}
this.chiralPath = s;
chiralAtoms.addLast(this);
}for (var i = 0; i < 4; i++) if (this.atoms[i] != null) this.atoms[i].addChiralAtoms(chiralAtoms, ref);

}, "JU.Lst,~N");
Clazz.defineMethod(c$, "compareLikeUnlike", 
function(bsA, bsB){
var bsXOR = bsB.clone();
bsXOR.xor(bsA);
var l = bsXOR.nextSetBit(0);
return (l < 0 ? null : bsA.get(l) ? bsA : bsB);
}, "JU.BS,JU.BS");
Clazz.defineMethod(c$, "createAuxiliaryDescriptors", 
function(node1, ret){
var isChiralPath = false;
var c = '~';
if (this.atom == null) return false;
this.setNode();
var rs = -1;
var nRS = 0;
var ret1 =  new Array(1);
var skipRules4And5 = false;
var prevIsChiral = true;
var allowTwoSame = (!this.isAlkene && this.nPriorities <= (node1 == null ? 2 : 1));
for (var i = 0; i < 4; i++) {
var a = this.atoms[i];
if (a != null && !a.isDuplicate && !a.isTerminal) {
ret1[0] = null;
var aIsChiralPath = a.createAuxiliaryDescriptors(node1 == null ? a : node1, ret1);
if (ret1[0] != null && ret != null) ret[0] = this.nextChiralBranch = a.nextChiralBranch;
if (a.nextChiralBranch != null || aIsChiralPath) {
nRS++;
isChiralPath = aIsChiralPath;
prevIsChiral = true;
} else {
if (!allowTwoSame && !prevIsChiral && this.priorities[i] == this.priorities[i - 1]) {
return false;
}prevIsChiral = false;
}}}
var isBranch = (nRS >= 2);
switch (nRS) {
case 0:
isChiralPath = false;
case 1:
skipRules4And5 = true;
break;
case 2:
case 3:
case 4:
isChiralPath = false;
if (ret != null) ret[0] = this.nextChiralBranch = this;
break;
}
if (this.isAlkene) {
if (this.alkeneChild != null) {
if (!this.isEvenEne || (this.auxEZ == 15 || this.auxEZ == -1) && !this.isKekuleAmbiguous && this.alkeneChild.bondCount >= 2) {
var rule2 = (this.isEvenEne ?  Clazz.newIntArray (1, 0) : null);
rs = this.getAuxEneWinnerChirality(this, this.alkeneChild, !this.isEvenEne, rule2);
if (rs == 0) {
this.auxEZ = this.alkeneChild.auxEZ = 15;
} else {
isChiralPath = true;
if (rule2 != null && rule2[0] != 8) {
this.auxEZ = this.alkeneChild.auxEZ = rs;
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo("alkene type " + this + " " + (this.auxEZ == 14 ? "E" : "Z"));
} else if (!isBranch) {
switch (rs) {
case 17:
case 13:
rs = 1;
c = 'R';
isChiralPath = true;
break;
case 18:
case 14:
rs = 2;
c = 'S';
isChiralPath = true;
break;
}
this.auxChirality = c;
this.rule4Type = rs;
}}}}} else if (this.isSP3 && ret != null) {
var atom1 = this.clone();
if (atom1.setNode()) {
atom1.addReturnPath(null, this);
var rule = 1;
for (; rule <= 9; rule++) if ((!skipRules4And5 || rule < 5 || rule > 8) && atom1.auxSort(rule)) break;

if (rule > 9) {
c = '~';
} else {
rs = this.b$["JS.CIPChirality"].data.checkHandedness(atom1);
isChiralPath = new Boolean (isChiralPath | (rs != 0)).valueOf();
c = (rs == 1 ? 'R' : rs == 2 ? 'S' : '~');
if (rule == 8) {
c = (c == 'R' ? 'r' : c == 'S' ? 's' : '~');
if (rs != 0) this.b$["JS.CIPChirality"].havePseudoAuxiliary = true;
} else {
this.rule4Type = rs;
}}}this.auxChirality = c;
}if (node1 == null) this.b$["JS.CIPChirality"].bsNeedRule.setBitTo(5, nRS > 0);
if (c != '~') {
this.b$["JS.CIPChirality"].logInfo("creating aux " + c + " for " + this + (this.myPath.length == 0 ? "" : " = " + this.myPath));
}return (this.isChiralPath = isChiralPath);
}, "JS.CIPChirality.CIPAtom,~A");
Clazz.defineMethod(c$, "auxSort", 
function(rule){
var current = this.b$["JS.CIPChirality"].currentRule;
this.b$["JS.CIPChirality"].currentRule = rule;
var rule6ref = this.b$["JS.CIPChirality"].root.rule6refIndex;
var nDup = this.b$["JS.CIPChirality"].root.nRootDuplicates;
var isChiral = (rule == 9 ? this.getRule6Descriptor(true) != 0 : this.sortSubstituents(0));
this.b$["JS.CIPChirality"].root.nRootDuplicates = nDup;
this.b$["JS.CIPChirality"].root.rule6refIndex = rule6ref;
this.b$["JS.CIPChirality"].currentRule = current;
return isChiral;
}, "~N");
Clazz.defineMethod(c$, "getAuxEneWinnerChirality", 
function(end1, end2, isAxial, retRule2){
if (isAxial && end1.nextSP2 === end2) return 0;
var winner1 = this.getAuxEneEndWinner(end1, end1.nextSP2, null);
var winner2 = (winner1 == null || winner1.atom == null ? null : this.getAuxEneEndWinner(end2, end2.nextSP2, retRule2));
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo(this + " alkene end winners " + winner1 + winner2);
return this.b$["JS.CIPChirality"].getEneChirality(winner1, end1, end2, winner2, isAxial, false);
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,~B,~A");
Clazz.defineMethod(c$, "getAuxEneEndWinner", 
function(end, prevSP2, retRule){
var atom1 = end.clone();
if (atom1.parent !== prevSP2) {
atom1.addReturnPath(prevSP2, end);
}var a;
for (var rule = 1; rule <= 9; rule++) {
if (atom1.auxSort(rule)) {
for (var i = 0; i < 4; i++) {
a = atom1.atoms[i];
if (!a.multipleBondDuplicate) {
if (atom1.priorities[i] != atom1.priorities[i + 1]) {
if (retRule != null) retRule[0] = rule;
return (a.atom == null ? null : a);
}}}
}}
return null;
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,~A");
Clazz.defineMethod(c$, "addReturnPath", 
function(newParent, fromAtom){
var path =  new JU.Lst();
var thisAtom = this;
var newSub;
var oldParent = fromAtom;
var oldSub = newParent;
while (oldParent.parent != null && oldParent.parent.atoms[0] != null) {
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo("path:" + oldParent.parent + "->" + oldParent);
path.addLast(oldParent = oldParent.parent);
}
if (oldParent.parent != null && newParent != null) path.addLast(oldParent.parent);
path.addLast(null);
for (var i = 0, n = path.size(); i < n; i++) {
oldParent = path.get(i);
newSub = (oldParent == null ? Clazz.innerTypeInstance(JS.CIPChirality.CIPAtom, this, null).create(null, this, thisAtom.isAlkene, true, false) : oldParent.clone());
newSub.nPriorities = 0;
newSub.sphere = thisAtom.sphere + 1;
if (thisAtom.atoms[0] == null) thisAtom.atoms[0] = oldSub;
thisAtom.replaceParentSubstituent(oldSub, newParent, newSub);
if (i > 0 && thisAtom.isAlkene && !thisAtom.isAlkeneAtom2) {
if (newParent.isAlkeneAtom2) {
if (newParent.alkeneChild == null || newParent.alkeneChild.atom === thisAtom.atom) {
newParent.isAlkeneAtom2 = false;
thisAtom.alkeneParent = newParent;
thisAtom.setEne();
}}}newParent = thisAtom;
thisAtom = newSub;
oldSub = fromAtom;
fromAtom = oldParent;
}
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "replaceParentSubstituent", 
function(oldSub, newParent, newSub){
for (var i = 0; i < 4; i++) if (this.atoms[i] === oldSub || newParent == null && this.atoms[i].atom == null) {
if (JU.Logger.debuggingHigh) this.b$["JS.CIPChirality"].logInfo("reversed: " + newParent + "->" + this + "->" + newSub);
this.parent = newParent;
this.atoms[i] = newSub;
this.fillAtoms(++i);
java.util.Arrays.sort(this.atoms);
break;
}
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "sign", 
function(score){
return (score < 0 ? -1 : score > 0 ? 1 : 0);
}, "~N");
Clazz.defineMethod(c$, "clone", 
function(){
var a = null;
try {
a = Clazz.superCall(this, JS.CIPChirality.CIPAtom, "clone", []);
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
} else {
throw e;
}
}
a.id = this.b$["JS.CIPChirality"].ptIDLogger++;
a.atoms =  new Array(4);
for (var i = 0; i < 4; i++) a.atoms[i] = this.atoms[i];

a.priorities =  Clazz.newIntArray (4, 0);
a.htPathPoints = this.htPathPoints;
a.alkeneParent = null;
a.auxEZ = -1;
a.rule4Type = 0;
a.listRS = null;
if (JU.Logger.debuggingHigh) a.myPath = a.toString();
return a;
});
Clazz.overrideMethod(c$, "toString", 
function(){
if (this.atom == null) return "<null>";
if (JU.Logger.debuggingHigh) return ("[" + this.b$["JS.CIPChirality"].currentRule + "." + this.sphere + "," + this.id + "." + (this.isDuplicate ? this.parent.atom : this.atom).getAtomName() + (this.isDuplicate ? "*(" + this.rootDistance + ")" : "") + (this.auxChirality == '~' ? "" : "" + this.auxChirality) + " " + this.elemNo + "]");
return (this.isDuplicate ? "(" + this.atom.getAtomName() + "." + this.rootDistance + ")" : this.atom.getAtomName());
});
/*eoif4*/})();
};
c$.ruleNames =  Clazz.newArray(-1, ["", "1a", "1b", "2", "3", "4a", "4b", "4c", "5", "6"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
