Clazz.declarePackage("J.adapter.readers.xml");
Clazz.load(["J.adapter.readers.xml.XmlReader", "J.adapter.smarter.Atom", "$.Bond", "java.util.HashMap", "$.Stack", "JU.Lst"], "J.adapter.readers.xml.XmlCdxReader", ["JU.BS", "$.PT", "J.api.JmolAdapter", "JU.Edge", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.minX = 3.4028235E38;
this.minY = 3.4028235E38;
this.minZ = 3.4028235E38;
this.maxZ = -3.4028235E38;
this.maxY = -3.4028235E38;
this.maxX = -3.4028235E38;
this.no3D = false;
if (!Clazz.isClassDefined("J.adapter.readers.xml.XmlCdxReader.CDNode")) {
J.adapter.readers.xml.XmlCdxReader.$XmlCdxReader$CDNode$ ();
}
if (!Clazz.isClassDefined("J.adapter.readers.xml.XmlCdxReader.CDBond")) {
J.adapter.readers.xml.XmlCdxReader.$XmlCdxReader$CDBond$ ();
}
this.fragments = null;
this.thisFragmentID = null;
this.thisNode = null;
this.nodes = null;
this.nostereo = null;
this.objectsByID = null;
this.textBuffer = null;
this.isCDX = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xml, "XmlCdxReader", J.adapter.readers.xml.XmlReader);
Clazz.prepareFields (c$, function(){
this.fragments =  new java.util.Stack();
this.nodes =  new java.util.Stack();
this.nostereo =  new JU.Lst();
this.objectsByID =  new java.util.HashMap();
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.readers.xml.XmlCdxReader, []);
});
Clazz.overrideMethod(c$, "processXml", 
function(parent, saxReader){
this.is2D = true;
if (parent == null) {
this.processXml2(this, saxReader);
parent = this;
} else {
this.no3D = parent.checkFilterKey("NO3D");
this.noHydrogens = parent.noHydrogens;
this.processXml2(parent, saxReader);
this.filter = parent.filter;
}}, "J.adapter.readers.xml.XmlReader,~O");
Clazz.overrideMethod(c$, "processStartElement", 
function(localName, nodeName){
var id = this.atts.get("id");
if ("fragment".equals(localName)) {
this.objectsByID.put(id, this.setFragment(id));
return;
}if ("n".equals(localName)) {
this.objectsByID.put(id, this.setNode(id));
return;
}if ("b".equals(localName)) {
this.objectsByID.put(id, this.setBond(id));
return;
}if ("t".equals(localName)) {
this.textBuffer = "";
}if ("s".equals(localName)) {
this.setKeepChars(true);
}}, "~S,~S");
Clazz.defineMethod(c$, "setFragment", 
function(id){
this.fragments.push(this.thisFragmentID = id);
var fragmentNode = (this.thisNode == null || !this.thisNode.isFragment ? null : this.thisNode);
if (fragmentNode != null) {
fragmentNode.setInnerFragmentID(id);
}var s = this.atts.get("connectionorder");
if (s != null) {
System.out.println(id + " ConnectionOrder is " + s);
this.thisNode.setConnectionOrder(JU.PT.split(s.trim(), " "));
}return fragmentNode;
}, "~S");
Clazz.overrideMethod(c$, "processEndElement", 
function(localName){
if ("fragment".equals(localName)) {
this.thisFragmentID = this.fragments.pop();
return;
}if ("n".equals(localName)) {
this.thisNode = (this.nodes.size() == 0 ? null : this.nodes.pop());
return;
}if ("s".equals(localName)) {
this.textBuffer += this.chars.toString();
}if ("t".equals(localName)) {
if (this.thisNode == null) {
System.out.println("XmlChemDrawReader unassigned text: " + this.textBuffer);
} else {
this.thisNode.text = this.textBuffer;
if (this.atom.elementNumber == 0) {
System.err.println("XmlChemDrawReader: Problem with \"" + this.textBuffer + "\"");
}if (this.thisNode.warning != null) this.parent.appendLoadNote("Warning: " + this.textBuffer + " " + this.thisNode.warning);
}this.textBuffer = "";
}this.setKeepChars(false);
}, "~S");
Clazz.defineMethod(c$, "setNode", 
function(id){
var nodeType = this.atts.get("nodetype");
if (this.asc.bsAtoms == null) this.asc.bsAtoms =  new JU.BS();
if (this.thisNode != null) this.nodes.push(this.thisNode);
if ("_".equals(nodeType)) {
this.atom = this.thisNode = null;
return null;
}this.atom = this.thisNode = Clazz.innerTypeInstance(J.adapter.readers.xml.XmlCdxReader.CDNode, this, null, id, nodeType, this.thisFragmentID, this.thisNode);
this.asc.addAtomWithMappedSerialNumber(this.atom);
this.asc.bsAtoms.set(this.atom.index);
var w = this.atts.get("warning");
if (w != null) {
this.thisNode.warning = JU.PT.rep(w, "&apos;", "'");
this.thisNode.isValid = (w.indexOf("ChemDraw can't interpret") < 0);
}var element = this.atts.get("element");
var s = this.atts.get("genericnickname");
if (s != null) {
element = s;
}this.atom.elementNumber = (!this.checkWarningOK(w) ? 0 : element == null ? 6 : this.parseIntStr(element));
element = J.api.JmolAdapter.getElementSymbol(this.atom.elementNumber);
s = this.atts.get("isotope");
if (s != null) element = s + element;
this.setElementAndIsotope(this.atom, element);
s = this.atts.get("charge");
if (s != null) {
this.atom.formalCharge = this.parseIntStr(s);
}var hasXYZ = (this.atts.containsKey("xyz"));
var hasXY = (this.atts.containsKey("p"));
if (hasXYZ && (!this.no3D || !hasXY)) {
this.is2D = false;
this.setAtom("xyz");
} else if (this.atts.containsKey("p")) {
this.setAtom("p");
}s = this.atts.get("attachments");
if (s != null) {
System.out.println(id + " Attachments is " + s);
this.thisNode.setMultipleAttachments(JU.PT.split(s.trim(), " "));
}s = this.atts.get("bondordering");
if (s != null) {
System.out.println(id + " BondOrdering is " + s);
this.thisNode.setBondOrdering(JU.PT.split(s.trim(), " "));
}if (JU.Logger.debugging) JU.Logger.info("XmlChemDraw id=" + id + " " + element + " " + this.atom);
return this.thisNode;
}, "~S");
Clazz.defineMethod(c$, "checkWarningOK", 
function(warning){
return (warning == null || warning.indexOf("valence") >= 0 || warning.indexOf("very close") >= 0 || warning.indexOf("two identical colinear bonds") >= 0);
}, "~S");
Clazz.defineMethod(c$, "setBond", 
function(id){
var atom1 = this.atts.get("b");
var atom2 = this.atts.get("e");
var a = this.atts.get("beginattach");
var beginAttach = (a == null ? 0 : this.parseIntStr(a));
a = this.atts.get("endattach");
var endAttach = (a == null ? 0 : this.parseIntStr(a));
var s = this.atts.get("order");
var disp = this.atts.get("display");
var disp2 = this.atts.get("display2");
var order = 131071;
var invertEnds = false;
if (disp == null) {
if (s == null) {
order = 1;
} else if (s.equals("1.5")) {
order = 515;
} else {
if (s.indexOf(".") > 0 && !"Dash".equals(disp2)) {
s = s.substring(0, s.indexOf("."));
}order = JU.Edge.getBondOrderFromString(s);
}} else if (disp.equals("WedgeBegin")) {
order = 1025;
} else if (disp.equals("Hash") || disp.equals("WedgedHashBegin")) {
order = 1041;
} else if (disp.equals("WedgeEnd")) {
invertEnds = true;
order = 1025;
} else if (disp.equals("WedgedHashEnd")) {
invertEnds = true;
order = 1041;
} else if (disp.equals("Wavy")) {
order = 1057;
}if (order == 131071) {
System.err.println("XmlChemDrawReader ignoring bond type " + s);
return null;
}var b = (invertEnds ? Clazz.innerTypeInstance(J.adapter.readers.xml.XmlCdxReader.CDBond, this, null, id, atom2, atom1, order) : Clazz.innerTypeInstance(J.adapter.readers.xml.XmlCdxReader.CDBond, this, null, id, atom1, atom2, order));
var node1 = this.asc.atoms[b.atomIndex1];
var node2 = this.asc.atoms[b.atomIndex2];
if (order == 1057) {
if (!this.nostereo.contains(node1)) this.nostereo.addLast(node1);
if (!this.nostereo.contains(node2)) this.nostereo.addLast(node2);
}if (node1.hasMultipleAttachments) {
node1.attachedAtom = node2;
return b;
} else if (node2.hasMultipleAttachments) {
node2.attachedAtom = node1;
return b;
}if (node1.isFragment && beginAttach == 0) beginAttach = 1;
if (node2.isFragment && endAttach == 0) endAttach = 1;
if (beginAttach > 0) {
(invertEnds ? node2 : node1).addAttachedAtom(b, beginAttach);
}if (endAttach > 0) {
(invertEnds ? node1 : node2).addAttachedAtom(b, endAttach);
}if (node1.isExternalPt) {
node1.setInternalAtom(node2);
}if (node2.isExternalPt) {
node2.setInternalAtom(node1);
}this.asc.addBondNoCheck(b);
return b;
}, "~S");
Clazz.defineMethod(c$, "setAtom", 
function(key){
var xyz = this.atts.get(key);
var tokens = JU.PT.getTokens(xyz);
var x = this.parseFloatStr(tokens[0]);
var y = -this.parseFloatStr(tokens[1]);
var z = (key === "xyz" ? this.parseFloatStr(tokens[2]) : 0);
if (x < this.minX) this.minX = x;
if (x > this.maxX) this.maxX = x;
if (y < this.minY) this.minY = y;
if (y > this.maxY) this.maxY = y;
if (z < this.minZ) this.minZ = z;
if (z > this.maxZ) this.maxZ = z;
this.atom.set(x, y, z);
}, "~S");
Clazz.overrideMethod(c$, "finalizeSubclassReader", 
function(){
this.fixConnections();
this.fixInvalidAtoms();
this.centerAndScale();
this.parent.appendLoadNote((this.isCDX ? "CDX: " : "CDXML: ") + (this.is2D ? "2D" : "3D"));
this.asc.setInfo("minimize3D", Boolean.$valueOf(!this.is2D && !this.noHydrogens));
this.asc.setInfo("is2D", Boolean.$valueOf(this.is2D));
if (this.is2D) {
this.optimize2D = !this.noHydrogens && !this.noMinimize;
this.asc.setModelInfoForSet("dimension", "2D", this.asc.iSet);
this.set2D();
}});
Clazz.defineMethod(c$, "fixConnections", 
function(){
for (var i = this.asc.ac; --i >= 0; ) {
var a = this.asc.atoms[i];
if (a.isFragment || a.hasMultipleAttachments) a.fixAttachments();
}
for (var i = 0, n = this.asc.bondCount; i < n; i++) {
var b = this.asc.bonds[i];
if (b == null) {
continue;
}var a1 = this.asc.atoms[b.atomIndex1];
var a2 = this.asc.atoms[b.atomIndex2];
a1.isConnected = true;
a2.isConnected = true;
if (this.nostereo.contains(a1) != this.nostereo.contains(a2)) {
b.order = 1;
}}
});
Clazz.defineMethod(c$, "centerAndScale", 
function(){
if (this.minX > this.maxX) return;
var sum = 0;
var n = 0;
var lenH = 1;
for (var i = this.asc.bondCount; --i >= 0; ) {
var a1 = this.asc.atoms[this.asc.bonds[i].atomIndex1];
var a2 = this.asc.atoms[this.asc.bonds[i].atomIndex2];
var d = a1.distance(a2);
if (a1.elementNumber > 1 && a2.elementNumber > 1) {
sum += d;
n++;
} else {
lenH = d;
}}
var f = (sum > 0 ? 1.45 * n / sum : lenH > 0 ? 1 / lenH : 1);
if (f > 0.5) f = 1;
var cx = (this.maxX + this.minX) / 2;
var cy = (this.maxY + this.minY) / 2;
var cz = (this.maxZ + this.minZ) / 2;
for (var i = this.asc.ac; --i >= 0; ) {
var a = this.asc.atoms[i];
a.x = (a.x - cx) * f;
a.y = (a.y - cy) * f;
a.z = (a.z - cz) * f;
}
});
Clazz.defineMethod(c$, "fixInvalidAtoms", 
function(){
for (var i = this.asc.ac; --i >= 0; ) {
var a = this.asc.atoms[i];
a.atomSerial = -2147483648;
if (a.isFragment || a.isExternalPt || !a.isConnected && (!a.isValid || a.elementNumber == 6 || a.elementNumber == 0)) {
this.asc.bsAtoms.clear(a.index);
}}
});
c$.$XmlCdxReader$CDNode$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.warning = null;
this.id = null;
this.intID = 0;
this.isValid = true;
this.isConnected = false;
this.isExternalPt = false;
this.nodeType = null;
this.isFragment = false;
this.outerFragmentID = null;
this.innerFragmentID = null;
this.text = null;
this.parentNode = null;
this.orderedConnectionBonds = null;
this.internalAtom = null;
this.orderedExternalPoints = null;
this.attachments = null;
this.bondOrdering = null;
this.connectionOrder = null;
this.hasMultipleAttachments = false;
this.attachedAtom = null;
this.isGeneric = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xml.XmlCdxReader, "CDNode", J.adapter.smarter.Atom);
Clazz.makeConstructor(c$, 
function(id, nodeType, fragmentID, parent){
Clazz.superConstructor (this, J.adapter.readers.xml.XmlCdxReader.CDNode, []);
this.id = id;
this.outerFragmentID = fragmentID;
this.atomSerial = this.intID = Integer.parseInt(id);
this.nodeType = nodeType;
this.parentNode = parent;
this.isFragment = "Fragment".equals(nodeType) || "Nickname".equals(nodeType);
this.isExternalPt = "ExternalConnectionPoint".equals(nodeType);
this.isGeneric = "GenericNickname".equals(nodeType);
}, "~S,~S,~S,J.adapter.readers.xml.XmlCdxReader.CDNode");
Clazz.defineMethod(c$, "setInnerFragmentID", 
function(id){
this.innerFragmentID = id;
}, "~S");
Clazz.defineMethod(c$, "setBondOrdering", 
function(bondOrdering){
this.bondOrdering = bondOrdering;
}, "~A");
Clazz.defineMethod(c$, "setConnectionOrder", 
function(connectionOrder){
this.connectionOrder = connectionOrder;
}, "~A");
Clazz.defineMethod(c$, "setMultipleAttachments", 
function(attachments){
this.attachments = attachments;
this.hasMultipleAttachments = true;
}, "~A");
Clazz.defineMethod(c$, "addExternalPoint", 
function(externalPoint){
if (this.orderedExternalPoints == null) this.orderedExternalPoints =  new JU.Lst();
var i = this.orderedExternalPoints.size();
while (--i >= 0 && this.orderedExternalPoints.get(i).intID >= externalPoint.internalAtom.intID) {
}
this.orderedExternalPoints.add(++i, externalPoint);
}, "J.adapter.readers.xml.XmlCdxReader.CDNode");
Clazz.defineMethod(c$, "setInternalAtom", 
function(a){
this.internalAtom = a;
if (this.parentNode == null) {
} else {
this.parentNode.addExternalPoint(this);
}}, "J.adapter.readers.xml.XmlCdxReader.CDNode");
Clazz.defineMethod(c$, "addAttachedAtom", 
function(bond, pt){
if (this.orderedConnectionBonds == null) this.orderedConnectionBonds =  new JU.Lst();
var i = this.orderedConnectionBonds.size();
while (--i >= 0 && (this.orderedConnectionBonds.get(i)[0]).intValue() > pt) {
}
this.orderedConnectionBonds.add(++i,  Clazz.newArray(-1, [Integer.$valueOf(pt), bond]));
}, "J.adapter.readers.xml.XmlCdxReader.CDBond,~N");
Clazz.defineMethod(c$, "fixAttachments", 
function(){
if (this.hasMultipleAttachments && this.attachedAtom != null) {
var order = JU.Edge.getBondOrderFromString("partial");
var a1 = this.attachedAtom.index;
for (var i = this.attachments.length; --i >= 0; ) {
var a = this.b$["J.adapter.readers.xml.XmlCdxReader"].objectsByID.get(this.attachments[i]);
if (a != null) this.b$["J.adapter.readers.xml.XmlCdxReader"].asc.addBondNoCheck( new J.adapter.smarter.Bond(a1, a.index, order));
}
}if (this.orderedExternalPoints == null || this.text == null) return;
var n = this.orderedExternalPoints.size();
if (n != this.orderedConnectionBonds.size()) {
System.err.println("XmlCdxReader cannot fix attachments for fragment " + this.text);
return;
}System.out.println("XmlCdxReader attaching fragment " + this.outerFragmentID + " " + this.text);
if (this.bondOrdering == null) {
this.bondOrdering =  new Array(n);
for (var i = 0; i < n; i++) {
this.bondOrdering[i] = (this.orderedConnectionBonds.get(i)[1]).id;
}
}if (this.connectionOrder == null) {
this.connectionOrder =  new Array(n);
for (var i = 0; i < n; i++) {
this.connectionOrder[i] = this.orderedExternalPoints.get(i).id;
}
}for (var i = 0; i < n; i++) {
var b = this.b$["J.adapter.readers.xml.XmlCdxReader"].objectsByID.get(this.bondOrdering[i]);
var pt = this.b$["J.adapter.readers.xml.XmlCdxReader"].objectsByID.get(this.connectionOrder[i]);
var a = pt.internalAtom;
this.updateExternalBond(b, a);
}
});
Clazz.defineMethod(c$, "updateExternalBond", 
function(bond2f, intAtom){
if (bond2f.atomIndex2 == this.index) {
bond2f.atomIndex2 = intAtom.index;
} else if (bond2f.atomIndex1 == this.index) {
bond2f.atomIndex1 = intAtom.index;
} else {
System.err.println("XmlCdxReader attachment failed! " + intAtom + " " + bond2f);
}}, "J.adapter.readers.xml.XmlCdxReader.CDBond,J.adapter.readers.xml.XmlCdxReader.CDNode");
Clazz.overrideMethod(c$, "toString", 
function(){
return "[CDNode " + this.id + " " + this.elementSymbol + " " + this.elementNumber + " index=" + this.index + " ext=" + this.isExternalPt + " frag=" + this.isFragment + " " + this.elementSymbol + " " + this.x + " " + this.y + "]";
});
/*eoif4*/})();
};
c$.$XmlCdxReader$CDBond$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.id = null;
this.id1 = null;
this.id2 = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xml.XmlCdxReader, "CDBond", J.adapter.smarter.Bond);
Clazz.makeConstructor(c$, 
function(id, id1, id2, order){
Clazz.superConstructor(this, J.adapter.readers.xml.XmlCdxReader.CDBond, [(this.b$["J.adapter.readers.xml.XmlCdxReader"].objectsByID.get(id1)).index, (this.b$["J.adapter.readers.xml.XmlCdxReader"].objectsByID.get(id2)).index, order]);
this.id = id;
this.id1 = id1;
this.id2 = id2;
}, "~S,~S,~S,~N");
Clazz.defineMethod(c$, "getOtherNode", 
function(a){
return this.b$["J.adapter.readers.xml.XmlCdxReader"].asc.atoms[this.atomIndex1 == a.index ? this.atomIndex2 : this.atomIndex1];
}, "J.adapter.readers.xml.XmlCdxReader.CDNode");
Clazz.defineMethod(c$, "toString", 
function(){
return "[CDBond " + this.id + " id1=" + this.id1 + " id2=" + this.id2 + Clazz.superCall(this, J.adapter.readers.xml.XmlCdxReader.CDBond, "toString", []) + "]";
});
/*eoif4*/})();
};
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
