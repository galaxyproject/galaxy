Clazz.declarePackage("J.adapter.readers.cif");
Clazz.load(["J.adapter.readers.cif.CifReader", "J.adapter.smarter.Atom", "$.Bond", "JU.Lst", "$.P3"], "J.adapter.readers.cif.TopoCifParser", ["java.util.Hashtable", "JU.BS", "J.adapter.readers.cif.Cif2DataParser", "J.api.JmolAdapter", "JS.SymmetryOperation", "JU.JmolMolecule"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.reader = null;
this.atoms = null;
this.nodes = null;
this.links = null;
this.nets = null;
this.singleNet = null;
this.netCount = 0;
this.linkCount = 0;
this.atomCount = 0;
this.temp1 = null;
this.temp2 = null;
this.ac0 = -1;
this.bc0 = 0;
this.cifParser = null;
this.failed = null;
this.ops = null;
this.i0 = 0;
this.b0 = 0;
this.allowedTypes = null;
this.netNotes = "";
this.sym = null;
this.selectedNet = null;
if (!Clazz.isClassDefined("J.adapter.readers.cif.TopoCifParser.TNet")) {
J.adapter.readers.cif.TopoCifParser.$TopoCifParser$TNet$ ();
}
if (!Clazz.isClassDefined("J.adapter.readers.cif.TopoCifParser.TAtom")) {
J.adapter.readers.cif.TopoCifParser.$TopoCifParser$TAtom$ ();
}
if (!Clazz.isClassDefined("J.adapter.readers.cif.TopoCifParser.TNode")) {
J.adapter.readers.cif.TopoCifParser.$TopoCifParser$TNode$ ();
}
if (!Clazz.isClassDefined("J.adapter.readers.cif.TopoCifParser.TLink")) {
J.adapter.readers.cif.TopoCifParser.$TopoCifParser$TLink$ ();
}
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif, "TopoCifParser", null, J.adapter.readers.cif.CifReader.Parser);
Clazz.prepareFields (c$, function(){
this.atoms =  new JU.Lst();
this.nodes =  new JU.Lst();
this.links =  new JU.Lst();
this.nets =  new JU.Lst();
this.temp1 =  new JU.P3();
this.temp2 =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(){
});
c$.getBondType = Clazz.defineMethod(c$, "getBondType", 
function(type, order){
if (type == null) return 0;
type = type.toUpperCase();
if (type.equals("V")) return (order == 0 ? 1 : order);
if (type.equals("sb")) type = "?";
switch ((type.charAt(0)).charCodeAt(0)) {
case 86:
return 14;
}
if (type.length > 3) type = type.substring(0, 3);
return Math.max(1, Clazz.doubleToInt(J.adapter.readers.cif.TopoCifParser.linkTypes.indexOf(type) / 3));
}, "~S,~N");
Clazz.overrideMethod(c$, "setReader", 
function(reader){
if (!reader.checkFilterKey("TOPOL")) {
reader.appendLoadNote("This file has Topology analysis records.\nUse LOAD \"\" {1 1 1} FILTER \"TOPOL\"  to load the topology.");
return this;
}this.reader = reader;
var net = reader.getFilter("TOPOLNET=");
this.selectedNet = net;
var types = reader.getFilter("TOPOS_TYPES=");
if (types == null) types = reader.getFilter("TOPOS_TYPE=");
if (types != null && types.length > 0) {
types = "+" + types.toLowerCase() + "+";
this.allowedTypes = types;
}this.i0 = reader.baseAtomIndex;
this.b0 = reader.baseBondIndex;
return this;
}, "J.adapter.readers.cif.CifReader");
Clazz.overrideMethod(c$, "ProcessRecord", 
function(key, data){
if (this.reader == null || this.failed != null) {
return;
}var pt = key.indexOf(".");
if (pt < 0) {
pt = key.indexOf('_', key.indexOf('_', 1) + 1);
if (pt < 0) return;
key = key.substring(0, pt) + '.' + key.substring(pt + 1);
}this.processBlock(key);
}, "~S,~S");
Clazz.overrideMethod(c$, "processBlock", 
function(key){
if (this.reader == null || this.failed != null) {
return false;
}if (this.ac0 < 0) {
this.reader.asc.firstAtomToBond = this.reader.asc.getAtomSetAtomIndex(this.reader.asc.iSet);
this.ac0 = this.reader.asc.ac;
this.bc0 = this.reader.asc.bondCount;
}if (this.reader.ucItems != null) {
this.reader.allow_a_len_1 = true;
for (var i = 0; i < 6; i++) this.reader.setUnitCellItem(i, this.reader.ucItems[i]);

}this.reader.parseLoopParameters(J.adapter.readers.cif.TopoCifParser.topolFields);
this.cifParser = this.reader.cifParser;
if (key.startsWith("_topol_net")) {
this.processNets();
} else if (key.startsWith("_topol_link")) {
this.processLinks();
} else if (key.startsWith("_topol_node")) {
this.processNodes();
} else if (key.startsWith("_topol_atom")) {
this.processAtoms();
} else {
return false;
}return true;
}, "~S");
Clazz.defineMethod(c$, "processNets", 
function(){
while (this.cifParser.getData()) {
var id = this.getDataValue(0);
var netLabel = this.getDataValue(1);
if (id == null) id = "" + (this.netCount + 1);
var net = this.getNetFor(id, netLabel, true);
net.specialDetails = this.getDataValue(2);
net.line = this.reader.line;
}
});
Clazz.defineMethod(c$, "processLinks", 
function(){
while (this.cifParser.getData()) {
var t = this.getDataValue(18);
var type = (t == null ? null : t.toLowerCase());
if (this.allowedTypes != null && (type == null || this.allowedTypes.indexOf("+" + type + "+") < 0)) continue;
var link = Clazz.innerTypeInstance(J.adapter.readers.cif.TopoCifParser.TLink, this, null);
link.type = type;
var t1 =  Clazz.newIntArray (3, 0);
var t2 =  Clazz.newIntArray (3, 0);
var n = this.cifParser.getColumnCount();
for (var i = 0; i < n; ++i) {
var p = this.reader.fieldProperty(i);
var field = this.reader.field;
switch (p) {
case 3:
link.id = field;
break;
case 4:
link.netID = field;
break;
case 5:
link.nodeIds[0] = field;
break;
case 6:
link.nodeIds[1] = field;
break;
case 56:
link.nodeLabels[0] = field;
break;
case 57:
link.nodeLabels[1] = field;
break;
case 46:
case 7:
link.symops[0] = this.getInt(field) - 1;
break;
case 50:
case 12:
link.symops[1] = this.getInt(field) - 1;
break;
case 21:
link.topoOrder = this.getInt(field);
break;
case 54:
case 47:
case 48:
case 49:
case 8:
case 9:
case 10:
case 11:
t1 = this.processTranslation(p, t1, field);
break;
case 55:
case 51:
case 52:
case 53:
case 13:
case 14:
case 15:
case 16:
t2 = this.processTranslation(p, t2, field);
break;
case 17:
link.cartesianDistance = this.getFloat(field);
break;
case 19:
link.multiplicity = this.getInt(field);
break;
case 20:
link.voronoiAngle = this.getFloat(field);
}
}
if (!link.setLink(t1, t2, this.reader.line)) {
this.failed = "invalid link! " + link;
return;
}this.links.addLast(link);
}
});
Clazz.defineMethod(c$, "processNodes", 
function(){
while (this.cifParser.getData()) {
var node = Clazz.innerTypeInstance(J.adapter.readers.cif.TopoCifParser.TNode, this, null);
var t =  Clazz.newIntArray (3, 0);
var n = this.cifParser.getColumnCount();
for (var i = 0; i < n; ++i) {
var p = this.reader.fieldProperty(i);
var field = this.reader.field;
switch (p) {
case 22:
node.id = field;
break;
case 24:
node.label = field;
break;
case 23:
node.netID = field;
break;
case 25:
node.symop = this.getInt(field) - 1;
break;
case 26:
case 27:
case 28:
case 29:
t = this.processTranslation(p, t, field);
break;
case 30:
node.x = this.getFloat(field);
break;
case 31:
node.y = this.getFloat(field);
break;
case 32:
node.z = this.getFloat(field);
break;
}
}
if (node.setNode(t, this.reader.line)) this.nodes.addLast(node);
}
});
Clazz.defineMethod(c$, "processAtoms", 
function(){
while (this.cifParser.getData()) {
var atom = Clazz.innerTypeInstance(J.adapter.readers.cif.TopoCifParser.TAtom, this, null);
var t =  Clazz.newIntArray (3, 0);
var n = this.cifParser.getColumnCount();
for (var i = 0; i < n; ++i) {
var p = this.reader.fieldProperty(i);
var field = this.reader.field;
switch (p) {
case 33:
atom.id = field;
break;
case 34:
atom.atomLabel = field;
break;
case 35:
atom.nodeID = field;
break;
case 36:
atom.linkID = field;
break;
case 37:
atom.symop = this.getInt(field) - 1;
break;
case 38:
case 39:
case 40:
case 41:
t = this.processTranslation(p, t, field);
break;
case 42:
atom.x = this.getFloat(field);
break;
case 43:
atom.y = this.getFloat(field);
break;
case 44:
atom.z = this.getFloat(field);
break;
case 45:
atom.elementSymbol = field;
break;
}
}
if (atom.setAtom(t, this.reader.line)) this.atoms.addLast(atom);
}
});
Clazz.defineMethod(c$, "processTranslation", 
function(p, t, field){
switch (p) {
case 54:
case 55:
case 8:
case 13:
case 26:
case 38:
t = J.adapter.readers.cif.Cif2DataParser.getIntArrayFromStringList(field, 3);
break;
case 47:
case 51:
case 9:
case 14:
case 27:
case 39:
t[0] = this.getInt(field);
break;
case 48:
case 52:
case 10:
case 15:
case 28:
case 40:
t[1] = this.getInt(field);
break;
case 49:
case 53:
case 11:
case 16:
case 29:
case 41:
t[2] = this.getInt(field);
break;
}
return t;
}, "~N,~A,~S");
Clazz.overrideMethod(c$, "finalizeReader", 
function(){
if (this.reader == null || this.reader.symops == null) return false;
this.cifParser = null;
this.reader.applySymmetryToBonds = true;
var symops = this.reader.symops;
var nOps = symops.size();
this.ops =  new Array(nOps);
var v =  Clazz.newFloatArray (16, 0);
for (var i = 0; i < nOps; i++) {
this.ops[i] = JS.SymmetryOperation.getMatrixFromXYZ("!" + symops.get(i), v, true);
}
for (var i = 0; i < this.atoms.size(); i++) {
this.atoms.get(i).finalizeAtom();
}
this.sym = this.reader.getSymmetry();
for (var i = 0; i < this.links.size(); i++) {
this.links.get(i).finalizeLink();
}
for (var i = this.links.size(); --i >= 0; ) {
if (!this.links.get(i).finalized) this.links.removeItemAt(i);
}
if (this.reader.doApplySymmetry) {
this.reader.applySymmetryAndSetTrajectory();
}if (this.selectedNet != null) this.selectNet();
return true;
});
Clazz.defineMethod(c$, "selectNet", 
function(){
var net = this.getNetFor(null, this.selectedNet, false);
if (net == null) {
net = this.getNetFor(this.selectedNet, null, false);
}if (net == null) return;
var bsAtoms = this.reader.asc.getBSAtoms(-1);
var atoms = this.reader.asc.atoms;
for (var i = this.reader.asc.ac; --i >= 0; ) {
var a = atoms[i];
if (!(Clazz.instanceOf(a,"J.adapter.readers.cif.TopoCifParser.TPoint")) || (a).getNet() !== net) {
bsAtoms.clear(i);
}}
});
Clazz.overrideMethod(c$, "finalizeSymmetry", 
function(haveSymmetry){
if (this.reader == null || !haveSymmetry || this.links.size() == 0) return;
var bsConnected =  new JU.BS();
var bsAtoms =  new JU.BS();
var nLinks = this.processAssociations(bsConnected, bsAtoms);
var bsExclude = J.adapter.readers.cif.TopoCifParser.shiftBits(bsAtoms, bsConnected);
if (!bsConnected.isEmpty()) {
this.reader.asc.bsAtoms = bsAtoms;
this.reader.asc.atomSetInfo.put("bsExcludeBonding", bsExclude);
}this.reader.appendLoadNote("TopoCifParser created " + bsConnected.cardinality() + " nodes and " + nLinks + " links");
var info =  new JU.Lst();
for (var i = 0, n = this.links.size(); i < n; i++) {
info.addLast(this.links.get(i).getLinkInfo());
}
this.reader.asc.setCurrentModelInfo("topology", info);
var script = "if (autobond) {delete !connected && !(atomName LIKE \'*_Link*\' or atomName LIKE \'*_Node*\')}; display displayed or " + this.nets.get(0).label + "__*";
this.reader.addJmolScript(script);
for (var i = 0; i < this.nets.size(); i++) {
this.nets.get(i).finalizeNet();
}
}, "~B");
c$.shiftBits = Clazz.defineMethod(c$, "shiftBits", 
function(bsAtoms, bs){
var bsNew =  new JU.BS();
for (var pt = 0, i = bsAtoms.nextSetBit(0); i >= 0; i = bsAtoms.nextSetBit(i + 1)) {
while (bsAtoms.get(i)) {
bsNew.setBitTo(pt++, bs.get(i++));
}
}
return bsNew;
}, "JU.BS,JU.BS");
Clazz.defineMethod(c$, "processAssociations", 
function(bsConnected, bsAtoms){
var nlinks = 0;
var bsAtoms0 = this.reader.asc.bsAtoms;
var atoms = this.reader.asc.atoms;
for (var i = this.reader.asc.ac; --i >= this.ac0; ) {
var a = atoms[i];
if (bsAtoms0 != null && !bsAtoms0.get(i)) continue;
var idx = (Clazz.instanceOf(a,"J.adapter.readers.cif.TopoCifParser.TAtom") ? (a).idx1 : 0);
if (idx == -2147483648 || idx == 0) continue;
if (idx > 0) {
var node = this.getAssociatedNodeByIdx(idx - 1);
if (node.bsAtoms == null) node.bsAtoms =  new JU.BS();
node.bsAtoms.set(this.i0 + a.index);
} else {
var link = this.getAssoiatedLinkByIdx(-idx - 1);
if (link != null) {
if (link.bsAtoms == null) link.bsAtoms =  new JU.BS();
link.bsAtoms.set(this.i0 + a.index);
}}bsAtoms.set(a.index);
}
var checkDistance = this.reader.doPackUnitCell;
var distance;
var bonds = this.reader.asc.bonds;
for (var i = this.reader.asc.bondCount; --i >= this.bc0; ) {
var b = bonds[i];
if (b.order >= 33554432) {
bonds[i] = null;
} else if (b.order >= 16777216) {
if (bsAtoms0 != null && (!bsAtoms0.get(b.atomIndex1) || !bsAtoms0.get(b.atomIndex2))) {
bonds[i] = null;
continue;
}b.order -= 16777216;
var link = this.getAssoiatedLinkByIdx(b.order >> 4);
if (checkDistance && Math.abs((distance = this.calculateDistance(atoms[b.atomIndex1], atoms[b.atomIndex2])) - link.distance) >= J.adapter.readers.cif.TopoCifParser.ERROR_TOLERANCE) {
System.err.println("Distance error! removed! distance=" + distance + " for " + link + link.linkNodes[0] + link.linkNodes[1]);
bonds[i] = null;
continue;
}if (link.bsBonds == null) link.bsBonds =  new JU.BS();
link.bsBonds.set(this.b0 + i);
switch (b.order & 0xF) {
default:
b.order = 1;
break;
case 2:
b.order = 2;
break;
case 3:
b.order = 3;
break;
case 4:
b.order = 4;
break;
case 5:
b.order = 5;
break;
case 6:
b.order = 6;
break;
case 10:
b.order = 1;
break;
case 11:
case 12:
b.order = 515;
break;
case 13:
b.order = 2048;
break;
case 14:
b.order = 33;
break;
}
bsConnected.set(b.atomIndex1);
bsConnected.set(b.atomIndex2);
nlinks++;
}}
bsAtoms.or(bsConnected);
if (bsAtoms0 != null) bsAtoms.and(bsAtoms0);
for (var i = this.nodes.size(); --i >= 0; ) {
var node = this.nodes.get(i);
if (node.bsAtoms != null) {
node.bsAtoms = J.adapter.readers.cif.TopoCifParser.shiftBits(bsAtoms, node.bsAtoms);
}}
for (var i = this.links.size(); --i >= 0; ) {
var link = this.links.get(i);
if (link.bsAtoms != null) {
link.bsAtoms = J.adapter.readers.cif.TopoCifParser.shiftBits(bsAtoms, link.bsAtoms);
}}
return nlinks;
}, "JU.BS,JU.BS");
c$.isEqualD = Clazz.defineMethod(c$, "isEqualD", 
function(p1, p2, d){
return (Double.isNaN(d) || Math.abs(p1.distance(p2) - d) < J.adapter.readers.cif.TopoCifParser.ERROR_TOLERANCE);
}, "JU.T3,JU.T3,~N");
Clazz.defineMethod(c$, "getDataValue", 
function(key){
var f = this.reader.getFieldString(key);
return ("\0".equals(f) ? null : f);
}, "~N");
Clazz.defineMethod(c$, "getInt", 
function(f){
return (f == null ? -2147483648 : this.reader.parseIntStr(f));
}, "~S");
Clazz.defineMethod(c$, "getFloat", 
function(f){
return (f == null ? NaN : this.reader.parseFloatStr(f));
}, "~S");
c$.getMF = Clazz.defineMethod(c$, "getMF", 
function(tatoms){
var n = tatoms.size();
if (n < 2) return (n == 0 ? "" : tatoms.get(0).elementSymbol);
var atNos =  Clazz.newIntArray (n, 0);
for (var i = 0; i < n; i++) {
atNos[i] = J.api.JmolAdapter.getElementNumber(tatoms.get(i).getElementSymbol());
}
var m =  new JU.JmolMolecule();
m.atNos = atNos;
return m.getMolecularFormula(false, null, false);
}, "JU.Lst");
c$.setTAtom = Clazz.defineMethod(c$, "setTAtom", 
function(a, b){
b.setT(a);
b.formalCharge = a.formalCharge;
b.bondingRadius = a.bondingRadius;
}, "J.adapter.smarter.Atom,J.adapter.smarter.Atom");
c$.setElementSymbol = Clazz.defineMethod(c$, "setElementSymbol", 
function(a, sym){
var name = a.atomName;
if (sym == null) {
a.atomName = (a.atomName == null ? "X" : a.atomName.substring(a.atomName.indexOf('_') + 1));
} else {
a.atomName = sym;
}a.getElementSymbol();
a.atomName = name;
}, "J.adapter.smarter.Atom,~S");
c$.applySymmetry = Clazz.defineMethod(c$, "applySymmetry", 
function(a, ops, op, t){
if (op >= 0) {
if (op >= 1 || t.x != 0 || t.y != 0 || t.z != 0) {
if (op >= 1) ops[op].rotTrans(a);
a.add(t);
}}}, "J.adapter.smarter.Atom,~A,~N,JU.T3");
Clazz.defineMethod(c$, "getNetByID", 
function(id){
for (var i = this.nets.size(); --i >= 0; ) {
var n = this.nets.get(i);
if (n.id.equalsIgnoreCase(id)) return n;
}
var n = Clazz.innerTypeInstance(J.adapter.readers.cif.TopoCifParser.TNet, this, null, this.netCount++, id, "Net" + id, null);
this.nets.addLast(n);
return n;
}, "~S");
Clazz.defineMethod(c$, "getAtomFromName", 
function(atomLabel){
return (atomLabel == null ? null : this.reader.asc.getAtomFromName(atomLabel));
}, "~S");
Clazz.defineMethod(c$, "calculateDistance", 
function(p1, p2){
this.temp1.setT(p1);
this.temp2.setT(p2);
this.sym.toCartesian(this.temp1, true);
this.sym.toCartesian(this.temp2, true);
return this.temp1.distance(this.temp2);
}, "JU.P3,JU.P3");
Clazz.defineMethod(c$, "getNetFor", 
function(id, label, forceNew){
var net = null;
if (id != null) {
net = this.getNetByID(id);
if (net != null && label != null && forceNew) net.label = label;
} else if (label != null) {
for (var i = this.nets.size(); --i >= 0; ) {
var n = this.nets.get(i);
if (n.label.equalsIgnoreCase(label)) {
net = n;
break;
}}
}if (net == null) {
if (!forceNew) return null;
net = this.getNetByID(id == null ? "1" : id);
}if (net != null && label != null && forceNew) net.label = label;
return net;
}, "~S,~S,~B");
Clazz.defineMethod(c$, "getAssociatedNodeByIdx", 
function(idx){
for (var i = this.nodes.size(); --i >= 0; ) {
var n = this.nodes.get(i);
if (n.idx == idx) return n;
}
return null;
}, "~N");
Clazz.defineMethod(c$, "getAssoiatedLinkByIdx", 
function(idx){
for (var i = this.links.size(); --i >= 0; ) {
var l = this.links.get(i);
if (l.idx == idx) return l;
}
return null;
}, "~N");
Clazz.defineMethod(c$, "findNode", 
function(nodeID, op, trans){
for (var i = this.nodes.size(); --i >= 0; ) {
var n = this.nodes.get(i);
if (n.id.equals(nodeID) && (op < 0 && n.linkSymop == 0 && n.linkTrans.equals(J.adapter.readers.cif.TopoCifParser.ZERO) || n.linkSymop == op && n.linkTrans.equals(trans))) return n;
}
return null;
}, "~S,~N,JU.P3");
c$.$TopoCifParser$TNet$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.line = null;
this.id = null;
this.nLinks = 0;
this.nNodes = 0;
this.label = null;
this.specialDetails = null;
this.idx = 0;
this.hasAtoms = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif.TopoCifParser, "TNet", null);
Clazz.makeConstructor(c$, 
function(index, id, label, specialDetails){
this.idx = index;
this.id = id;
this.label = label;
this.specialDetails = specialDetails;
}, "~N,~S,~S,~S");
Clazz.defineMethod(c$, "finalizeNet", 
function(){
if (this.id == null) this.id = "" + (this.idx + 1);
if (this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet != null && !this.label.equalsIgnoreCase(this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet) && !this.id.equalsIgnoreCase(this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet)) return;
var netKey = "," + this.id + ",";
if (this.b$["J.adapter.readers.cif.TopoCifParser"].netNotes.indexOf(netKey) < 0) {
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.appendLoadNote("Net " + this.label + (this.specialDetails == null ? "" : " '" + this.specialDetails + "'") + " created from " + this.nLinks + " links and " + this.nNodes + " nodes.\n" + "Use DISPLAY " + (this.hasAtoms ? this.label + "__* to display it without associated atoms\nUse DISPLAY " + this.label + "_* to display it with its associated atoms" : this.label + "* to display it" + ""));
}});
/*eoif4*/})();
};
c$.$TopoCifParser$TAtom$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.id = null;
this.atomLabel = null;
this.nodeID = null;
this.linkID = null;
this.symop = 0;
this.trans = null;
this.line = null;
this.isFinalized = false;
this.idx = 0;
this.net = null;
this.idx1 = 0;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif.TopoCifParser, "TAtom", J.adapter.smarter.Atom, J.adapter.readers.cif.TopoCifParser.TPoint);
Clazz.prepareFields (c$, function(){
this.trans =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, J.adapter.readers.cif.TopoCifParser.TAtom);
var i = 0;
});
Clazz.defineMethod(c$, "getTClone", 
function(){
try {
var ta = this.clone();
ta.idx = this.b$["J.adapter.readers.cif.TopoCifParser"].atomCount++;
return ta;
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
});
Clazz.overrideMethod(c$, "getNet", 
function(){
return this.net;
});
Clazz.defineMethod(c$, "setAtom", 
function(a, line){
this.line = line;
if (Float.isNaN(this.x) != Float.isNaN(this.y) || Float.isNaN(this.y) != Float.isNaN(this.z)) return false;
this.idx = this.b$["J.adapter.readers.cif.TopoCifParser"].atomCount++;
if (Float.isNaN(this.x)) {
this.trans = JU.P3.new3(a[0], a[1], a[2]);
} else {
this.symop = 0;
}this.atomName = this.atomLabel;
return true;
}, "~A,~S");
Clazz.defineMethod(c$, "finalizeAtom", 
function(){
if (this.isFinalized) return;
this.isFinalized = true;
var a = this.b$["J.adapter.readers.cif.TopoCifParser"].getAtomFromName(this.atomLabel);
J.adapter.readers.cif.TopoCifParser.setElementSymbol(this, this.elementSymbol);
if (a == null && Float.isNaN(this.x)) {
throw  new Exception("_topol_atom: no atom " + this.atomLabel + " line=" + this.line);
}var node = null;
if (this.nodeID != null) {
node = this.b$["J.adapter.readers.cif.TopoCifParser"].findNode(this.nodeID, -1, null);
}var link = null;
if (this.linkID != null) {
link = this.getLinkById(this.linkID);
}if (node == null && link == null) {
System.out.println("TAtom " + this + " ignored");
return;
}if (a != null && Float.isNaN(this.x)) {
J.adapter.readers.cif.TopoCifParser.setTAtom(a, this);
J.adapter.readers.cif.TopoCifParser.applySymmetry(this, this.b$["J.adapter.readers.cif.TopoCifParser"].ops, this.symop, this.trans);
}this.atomName = this.atomLabel;
if (node != null) {
node.addAtom(this);
}var ta = this;
if (link != null) ta = link.addAtom(this);
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.addCifAtom(this, this.atomName, null, null);
if (ta !== this) this.b$["J.adapter.readers.cif.TopoCifParser"].reader.addCifAtom(ta, this.atomName, null, null);
});
Clazz.defineMethod(c$, "getLinkById", 
function(linkID){
for (var i = this.b$["J.adapter.readers.cif.TopoCifParser"].links.size(); --i >= 0; ) {
var l = this.b$["J.adapter.readers.cif.TopoCifParser"].links.get(i);
if (l.id.equalsIgnoreCase(linkID)) return l;
}
return null;
}, "~S");
Clazz.defineMethod(c$, "toString", 
function(){
return this.line + " " + Clazz.superCall(this, J.adapter.readers.cif.TopoCifParser.TAtom, "toString", []);
});
/*eoif4*/})();
};
c$.$TopoCifParser$TNode$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.id = null;
this.atomLabel = null;
this.netID = null;
this.label = null;
this.symop = 0;
this.trans = null;
this.tatoms = null;
this.bsAtoms = null;
this.linkSymop = 0;
this.linkTrans = null;
this.net = null;
this.isFinalized = false;
this.idx = 0;
this.atom = null;
this.line = null;
this.mf = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif.TopoCifParser, "TNode", J.adapter.smarter.Atom, J.adapter.readers.cif.TopoCifParser.TPoint);
Clazz.prepareFields (c$, function(){
this.trans =  new JU.P3();
this.linkTrans =  new JU.P3();
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, J.adapter.readers.cif.TopoCifParser.TNode);
var i = 0;
});
Clazz.makeConstructor(c$, 
function(idx, atom, net, op, trans){
Clazz.superConstructor(this, J.adapter.readers.cif.TopoCifParser.TNode);
this.idx = idx;
this.atom = atom;
this.net = net;
this.linkSymop = op;
this.linkTrans = trans;
this.label = this.atomName = this.atomLabel = atom.atomName;
this.elementSymbol = atom.elementSymbol;
J.adapter.readers.cif.TopoCifParser.setTAtom(atom, this);
}, "~N,J.adapter.smarter.Atom,J.adapter.readers.cif.TopoCifParser.TNet,~N,JU.P3");
Clazz.defineMethod(c$, "getMolecularFormula", 
function(){
return (this.mf == null ? (this.mf = J.adapter.readers.cif.TopoCifParser.getMF(this.tatoms)) : this.mf);
});
Clazz.overrideMethod(c$, "getNet", 
function(){
return this.net;
});
Clazz.defineMethod(c$, "setNode", 
function(a, line){
this.line = line;
if (this.tatoms == null) {
if (Float.isNaN(this.x) != Float.isNaN(this.y) || Float.isNaN(this.y) != Float.isNaN(this.z)) return false;
this.idx = this.b$["J.adapter.readers.cif.TopoCifParser"].atomCount++;
if (Float.isNaN(this.x)) {
this.trans = JU.P3.new3(a[0], a[1], a[2]);
} else {
this.symop = 0;
}}return true;
}, "~A,~S");
Clazz.defineMethod(c$, "addAtom", 
function(atom){
if (this.tatoms == null) this.tatoms =  new JU.Lst();
atom.atomName = "Node_" + atom.nodeID + "_" + atom.atomLabel;
this.tatoms.addLast(atom);
}, "J.adapter.readers.cif.TopoCifParser.TAtom");
Clazz.defineMethod(c$, "finalizeNode", 
function(ops){
if (this.isFinalized) return;
this.isFinalized = true;
if (this.net == null) this.net = this.b$["J.adapter.readers.cif.TopoCifParser"].getNetFor(this.netID, null, true);
var haveXYZ = !Float.isNaN(this.x);
var a;
if (this.tatoms == null) {
a = null;
if (!haveXYZ) {
throw  new Exception("_topol_node no atom " + this.atomLabel + " line=" + this.line);
}} else {
if (Float.isNaN(this.x)) this.setCentroid();
if (this.tatoms.size() == 1) {
var ta = this.tatoms.get(0);
this.elementSymbol = ta.elementSymbol;
this.atomLabel = ta.atomLabel;
this.formalCharge = ta.formalCharge;
this.tatoms = null;
} else {
this.net.hasAtoms = true;
this.elementSymbol = "Xx";
for (var i = this.tatoms.size(); --i >= 0; ) {
var ta = this.tatoms.get(i);
ta.idx1 = this.idx + 1;
if (ta.atomName == null || !ta.atomName.startsWith(this.net.label + "_")) ta.atomName = this.net.label + "_" + ta.atomName;
ta.net = this.net;
}
}a = this;
}if ((a != null && a === this.atom) || !haveXYZ) {
if (a !== this) {
J.adapter.readers.cif.TopoCifParser.setTAtom(a, this);
}J.adapter.readers.cif.TopoCifParser.applySymmetry(this, ops, this.symop, this.trans);
}this.atomName = this.net.label.$replace(' ', '_') + "__";
if (this.label != null && this.label.startsWith(this.atomName)) {
this.atomName = "";
}this.atomName += (this.label != null ? this.label : this.atomLabel != null ? this.atomLabel : "Node_" + this.id);
this.addNode();
}, "~A");
Clazz.defineMethod(c$, "addNode", 
function(){
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.addCifAtom(this, this.atomName, null, null);
this.net.nNodes++;
if (this.tatoms != null && this.tatoms.size() > 1) this.b$["J.adapter.readers.cif.TopoCifParser"].reader.appendLoadNote("_topos_node " + this.id + " " + this.atomName + " has formula " + this.getMolecularFormula());
});
Clazz.defineMethod(c$, "setCentroid", 
function(){
this.x = this.y = this.z = 0;
var n = this.tatoms.size();
for (var i = n; --i >= 0; ) this.add(this.tatoms.get(i));

this.x /= n;
this.y /= n;
this.z /= n;
});
Clazz.defineMethod(c$, "info", 
function(){
return "[node idx=" + this.idx + " id=" + this.id + " " + this.label + "/" + this.atomName + " " + Clazz.superCall(this, J.adapter.readers.cif.TopoCifParser.TNode, "toString", []) + "]";
});
Clazz.defineMethod(c$, "toString", 
function(){
return this.info();
});
Clazz.defineMethod(c$, "copy", 
function(){
var node = this.clone();
node.idx = this.b$["J.adapter.readers.cif.TopoCifParser"].atomCount++;
if (node.isFinalized) node.addNode();
if (this.tatoms != null) {
node.tatoms =  new JU.Lst();
for (var i = 0, n = this.tatoms.size(); i < n; i++) {
var ta = this.tatoms.get(i).getTClone();
node.tatoms.addLast(ta);
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.addCifAtom(ta, ta.atomName, null, null);
}
}return node;
});
Clazz.defineMethod(c$, "clone", 
function(){
try {
return Clazz.superCall(this, J.adapter.readers.cif.TopoCifParser.TNode, "clone", []);
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
});
/*eoif4*/})();
};
c$.$TopoCifParser$TLink$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.id = null;
this.nodeIds = null;
this.nodeLabels = null;
this.symops = null;
this.translations = null;
this.netID = null;
this.netLabel = null;
this.type = "";
this.multiplicity = 0;
this.topoOrder = 0;
this.voronoiAngle = 0;
this.cartesianDistance = 0;
this.idx = 0;
this.net = null;
this.linkNodes = null;
this.typeBondOrder = 0;
this.tatoms = null;
this.bsAtoms = null;
this.bsBonds = null;
this.line = null;
this.finalized = false;
this.mf = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif.TopoCifParser, "TLink", J.adapter.smarter.Bond);
Clazz.prepareFields (c$, function(){
this.nodeIds =  new Array(2);
this.nodeLabels =  new Array(2);
this.symops =  Clazz.newIntArray (2, 0);
this.translations =  new Array(2);
this.linkNodes =  new Array(2);
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, J.adapter.readers.cif.TopoCifParser.TLink, [0, 0, 0]);
var i = 0;
});
Clazz.defineMethod(c$, "setLink", 
function(t1, t2, line){
this.line = line;
this.idx = this.b$["J.adapter.readers.cif.TopoCifParser"].linkCount++;
if (this.nodeIds[1] == null) this.nodeIds[1] = this.nodeIds[0];
this.typeBondOrder = J.adapter.readers.cif.TopoCifParser.getBondType(this.type, this.topoOrder);
this.translations[0] = JU.P3.new3(t1[0], t1[1], t1[2]);
this.translations[1] = JU.P3.new3(t2[0], t2[1], t2[2]);
System.out.println("TopoCifParser.setLink " + this);
return true;
}, "~A,~A,~S");
Clazz.defineMethod(c$, "addAtom", 
function(atom){
if (this.tatoms == null) this.tatoms =  new JU.Lst();
if (atom.nodeID != null) {
atom = atom.getTClone();
atom.nodeID = null;
}atom.atomName = "Link_" + atom.linkID + "_" + atom.atomLabel;
this.tatoms.addLast(atom);
return atom;
}, "J.adapter.readers.cif.TopoCifParser.TAtom");
Clazz.defineMethod(c$, "finalizeLink", 
function(){
this.netID = (this.nodeIds[0] == null ? null : this.b$["J.adapter.readers.cif.TopoCifParser"].findNode(this.nodeIds[0], -1, null).netID);
if (this.netID == null && this.netLabel == null) {
if (this.b$["J.adapter.readers.cif.TopoCifParser"].nets.size() > 0) this.net = this.b$["J.adapter.readers.cif.TopoCifParser"].nets.get(0);
 else this.net = this.b$["J.adapter.readers.cif.TopoCifParser"].getNetFor(null, null, true);
} else {
this.net = this.b$["J.adapter.readers.cif.TopoCifParser"].getNetFor(this.netID, this.netLabel, true);
}this.netLabel = this.net.label;
this.net.nLinks++;
if (this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet != null) {
if (!this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet.equalsIgnoreCase(this.net.label) && !this.b$["J.adapter.readers.cif.TopoCifParser"].selectedNet.equalsIgnoreCase(this.net.id)) {
return;
}}this.finalizeLinkNode(0);
this.finalizeLinkNode(1);
if (this.tatoms != null) {
var n = this.tatoms.size();
this.net.hasAtoms = true;
for (var i = n; --i >= 0; ) {
var a = this.tatoms.get(i);
a.idx1 = -this.idx - 1;
a.atomName = this.netLabel + "_" + a.atomName;
a.net = this.net;
}
if (n >= 0) {
this.mf = J.adapter.readers.cif.TopoCifParser.getMF(this.tatoms);
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.appendLoadNote("_topos_link " + this.id + " for net " + this.netLabel + " has formula " + this.mf);
}}this.order = 16777216 + (this.idx << 4) + this.typeBondOrder;
this.distance = this.b$["J.adapter.readers.cif.TopoCifParser"].calculateDistance(this.linkNodes[0], this.linkNodes[1]);
if (this.cartesianDistance != 0 && Math.abs(this.distance - this.cartesianDistance) >= J.adapter.readers.cif.TopoCifParser.ERROR_TOLERANCE) System.err.println("Distance error! distance=" + this.distance + " for " + this.line);
System.out.println("link d=" + this.distance + " " + this + this.linkNodes[0] + this.linkNodes[1]);
this.b$["J.adapter.readers.cif.TopoCifParser"].reader.asc.addBond(this);
this.finalized = true;
});
Clazz.defineMethod(c$, "finalizeLinkNode", 
function(index){
var id = this.nodeIds[index];
var atomLabel = this.nodeLabels[index];
var op = this.symops[index];
var trans = this.translations[index];
var node = this.getNodeWithSym(id, atomLabel, op, trans);
var node0 = node;
if (node == null && id != null) {
node = this.getNodeWithSym(id, null, -1, null);
}var atom = (node == null && atomLabel != null ? this.b$["J.adapter.readers.cif.TopoCifParser"].getAtomFromName(atomLabel) : null);
if (atom != null) {
node = Clazz.innerTypeInstance(J.adapter.readers.cif.TopoCifParser.TNode, this, null, this.b$["J.adapter.readers.cif.TopoCifParser"].atomCount++, atom, this.net, op, trans);
} else if (node != null) {
if (node0 == null) node = node.copy();
node.linkSymop = op;
node.linkTrans = trans;
this.nodeLabels[index] = node.atomName;
} else {
throw  new Exception("_topol_link: no atom or node " + atomLabel + " line=" + this.line);
}this.b$["J.adapter.readers.cif.TopoCifParser"].nodes.addLast(node);
this.linkNodes[index] = node;
if (index == 1 && node === this.linkNodes[0]) {
this.linkNodes[1] = node.copy();
}node.finalizeNode(this.b$["J.adapter.readers.cif.TopoCifParser"].ops);
if (node0 == null) J.adapter.readers.cif.TopoCifParser.applySymmetry(node, this.b$["J.adapter.readers.cif.TopoCifParser"].ops, op, trans);
if (index == 0) {
this.atomIndex1 = node.index;
} else {
this.atomIndex2 = node.index;
}}, "~N");
Clazz.defineMethod(c$, "getNodeWithSym", 
function(nodeID, nodeLabel, op, trans){
if (nodeID != null) return this.b$["J.adapter.readers.cif.TopoCifParser"].findNode(nodeID, op, trans);
for (var i = this.b$["J.adapter.readers.cif.TopoCifParser"].nodes.size(); --i >= 0; ) {
var n = this.b$["J.adapter.readers.cif.TopoCifParser"].nodes.get(i);
if (n.label.equals(nodeLabel) && (op == -1 && n.linkSymop == 0 && n.linkTrans.equals(J.adapter.readers.cif.TopoCifParser.ZERO) || op == n.linkSymop && trans.equals(n.linkTrans))) return n;
}
return null;
}, "~S,~S,~N,JU.P3");
Clazz.defineMethod(c$, "getLinkInfo", 
function(){
var info =  new java.util.Hashtable();
info.put("index", Integer.$valueOf(this.idx + 1));
if (this.id != null) info.put("id", this.id);
info.put("netID", this.net.id);
info.put("netLabel", this.net.label);
if (this.nodeLabels[0] != null) info.put("nodeLabel1", this.nodeLabels[0]);
if (this.nodeLabels[1] != null) info.put("nodeLabel2", this.nodeLabels[1]);
if (this.nodeIds[0] != null) info.put("nodeId1", this.nodeIds[0]);
if (this.nodeIds[1] != null) info.put("nodeId2", this.nodeIds[1]);
info.put("distance", Float.$valueOf(this.cartesianDistance));
if (!Float.isNaN(this.distance)) info.put("distance", Float.$valueOf(this.distance));
info.put("symops1", Integer.$valueOf(this.symops[0] + 1));
info.put("symops2", Integer.$valueOf(this.symops[1] + 1));
info.put("translation1", this.translations[0]);
info.put("translation2", this.translations[1]);
info.put("multiplicity", Integer.$valueOf(this.multiplicity));
if (this.type != null) info.put("type", this.type);
info.put("voronoiSolidAngle", Float.$valueOf(this.voronoiAngle));
info.put("atomIndex1", Integer.$valueOf(this.b$["J.adapter.readers.cif.TopoCifParser"].i0 + this.linkNodes[0].index));
info.put("atomIndex2", Integer.$valueOf(this.b$["J.adapter.readers.cif.TopoCifParser"].i0 + this.linkNodes[1].index));
if (this.bsAtoms != null && !this.bsAtoms.isEmpty()) info.put("representedAtoms", this.bsAtoms);
info.put("topoOrder", Integer.$valueOf(this.topoOrder));
info.put("order", Integer.$valueOf(this.typeBondOrder));
return info;
});
Clazz.defineMethod(c$, "info", 
function(){
return "[link " + this.line + " : " + this.distance + "]";
});
Clazz.overrideMethod(c$, "toString", 
function(){
return this.info();
});
/*eoif4*/})();
};
Clazz.declareInterface(J.adapter.readers.cif.TopoCifParser, "TPoint");
c$.linkTypes = "?  SINDOUTRIQUAQUISEXSEPOCTAROPOLDELPI HBOVDW";
c$.ERROR_TOLERANCE = 0.001;
c$.topolFields =  Clazz.newArray(-1, ["_topol_net_id", "_topol_net_label", "_topol_net_special_details", "_topol_link_id", "_topol_link_net_id", "_topol_link_node_id_1", "_topol_link_node_id_2", "_topol_link_symop_id_1", "_topol_link_translation_1", "_topol_link_translation_1_x", "_topol_link_translation_1_y", "_topol_link_translation_1_z", "_topol_link_symop_id_2", "_topol_link_translation_2", "_topol_link_translation_2_x", "_topol_link_translation_2_y", "_topol_link_translation_2_z", "_topol_link_distance", "_topol_link_type", "_topol_link_multiplicity", "_topol_link_voronoi_solidangle", "_topol_link_order", "_topol_node_id", "_topol_node_net_id", "_topol_node_label", "_topol_node_symop_id", "_topol_node_translation", "_topol_node_translation_x", "_topol_node_translation_y", "_topol_node_translation_z", "_topol_node_fract_x", "_topol_node_fract_y", "_topol_node_fract_z", "_topol_atom_id", "_topol_atom_atom_label", "_topol_atom_node_id", "_topol_atom_link_id", "_topol_atom_symop_id", "_topol_atom_translation", "_topol_atom_translation_x", "_topol_atom_translation_y", "_topol_atom_translation_z", "_topol_atom_fract_x", "_topol_atom_fract_y", "_topol_atom_fract_z", "_topol_atom_element_symbol", "_topol_link_site_symmetry_symop_1", "_topol_link_site_symmetry_translation_1_x", "_topol_link_site_symmetry_translation_1_y", "_topol_link_site_symmetry_translation_1_z", "_topol_link_site_symmetry_symop_2", "_topol_link_site_symmetry_translation_2_x", "_topol_link_site_symmetry_translation_2_y", "_topol_link_site_symmetry_translation_2_z", "_topol_link_site_symmetry_translation_1", "_topol_link_site_symmetry_translation_2", "_topol_link_node_label_1", "_topol_link_node_label_2", "_topol_link_atom_label_1", "_topol_link_atom_label_2"]);
c$.ZERO =  new JU.P3();
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
