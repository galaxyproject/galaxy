Clazz.declarePackage("J.adapter.writers");
Clazz.load(["J.adapter.writers.CMLWriter", "java.util.Stack", "JU.SB"], "J.adapter.writers.CDXMLWriter", ["java.util.Hashtable", "JU.PT", "$.Rdr", "J.adapter.smarter.SmarterJmolAdapter"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.doc = null;
this.objects = null;
this.sb = null;
this.sbpt = 0;
this.id = 0;
Clazz.instantialize(this, arguments);}, J.adapter.writers, "CDXMLWriter", J.adapter.writers.CMLWriter);
Clazz.prepareFields (c$, function(){
this.objects =  new java.util.Stack();
this.sb =  new JU.SB();
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.writers.CDXMLWriter, []);
});
Clazz.overrideMethod(c$, "set", 
function(viewer, out, data){
throw  new NullPointerException("CDXMLWriter is not implemented for writing");
}, "JV.Viewer,JU.OC,~A");
Clazz.overrideMethod(c$, "write", 
function(bs){
throw  new NullPointerException("CDXMLWriter is not implemented for writing");
}, "JU.BS");
c$.fromCDX = Clazz.defineMethod(c$, "fromCDX", 
function(binaryDoc){
return  new J.adapter.writers.CDXMLWriter().cdxToCdxml(binaryDoc);
}, "javajs.api.GenericBinaryDocument");
c$.fromASC = Clazz.defineMethod(c$, "fromASC", 
function(asc){
return  new J.adapter.writers.CDXMLWriter().ascToCdxml(asc);
}, "J.adapter.smarter.AtomSetCollection");
Clazz.defineMethod(c$, "ascToCdxml", 
function(asc){
var a =  new J.adapter.smarter.SmarterJmolAdapter();
var atomIterator = a.getAtomIterator(asc);
var bondIterator = a.getBondIterator(asc);
J.adapter.writers.CMLWriter.openDocument(this.sb);
J.adapter.writers.CDXMLWriter.appendHeader(this.sb);
J.adapter.writers.CMLWriter.openTag(this.sb, "page");
this.id = 0;
this.openID(this.sb, "fragment");
J.adapter.writers.CMLWriter.terminateTag(this.sb);
var indexToID =  new java.util.Hashtable();
while (atomIterator.hasNext()) {
this.openID(this.sb, "n");
indexToID.put(atomIterator.getUniqueID(), Integer.$valueOf(this.id));
var xyz = atomIterator.getXYZ();
var ele = atomIterator.getElement();
var iso = atomIterator.getIsotope();
var charge = atomIterator.getFormalCharge();
J.adapter.writers.CMLWriter.addAttribute(this.sb, "p", J.adapter.writers.CDXMLWriter.cdxCoord(xyz.x, 200) + " " + J.adapter.writers.CDXMLWriter.cdxCoord(-xyz.y, 400));
if (ele != 6) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Element", "" + ele);
if (iso != 0) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Isotope", "" + iso);
if (charge != 0) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Charge", "" + charge);
J.adapter.writers.CMLWriter.terminateEmptyTag(this.sb);
}
while (bondIterator.hasNext()) {
this.openID(this.sb, "b");
var id1 = bondIterator.getAtomUniqueID1();
var id2 = bondIterator.getAtomUniqueID2();
var order = "1";
var display = null;
var display2 = null;
var bo = bondIterator.getEncodedOrder();
switch (bo) {
case 515:
order = "1.5";
display2 = "Dash";
break;
case 514:
order = "2";
break;
default:
if ((bo & 0x07) != 0) order = "" + (bo & 0x07);
break;
}
switch (bo) {
case 1025:
order = "1";
display = "WedgeBegin";
break;
case 1041:
order = "1";
display = "WedgedHashBegin";
break;
case 1057:
order = "1";
display = "Wavy";
break;
}
J.adapter.writers.CMLWriter.addAttribute(this.sb, "B", indexToID.get(id1).toString());
J.adapter.writers.CMLWriter.addAttribute(this.sb, "E", indexToID.get(id2).toString());
if (!order.equals("1")) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Order", order);
if (display != null) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Display", display);
if (display2 != null) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Display2", display2);
J.adapter.writers.CMLWriter.terminateEmptyTag(this.sb);
}
J.adapter.writers.CMLWriter.closeTag(this.sb, "fragment");
J.adapter.writers.CMLWriter.closeTag(this.sb, "page");
J.adapter.writers.CMLWriter.closeTag(this.sb, "CDXML");
return this.sb.toString();
}, "J.adapter.smarter.AtomSetCollection");
c$.cdxCoord = Clazz.defineMethod(c$, "cdxCoord", 
function(x, off){
return "" + (off + Math.round(x / 1.45 * 14.4 * 100) / 100);
}, "~N,~N");
Clazz.defineMethod(c$, "openID", 
function(sb, name){
J.adapter.writers.CMLWriter.startOpenTag(sb, name);
J.adapter.writers.CMLWriter.addAttribute(sb, "id", "" + ++this.id);
}, "JU.SB,~S");
Clazz.defineMethod(c$, "cdxToCdxml", 
function(doc){
this.doc = doc;
try {
J.adapter.writers.CMLWriter.openDocument(this.sb);
J.adapter.writers.CDXMLWriter.appendHeader(this.sb);
doc.setStreamData(null, false);
doc.seek(22);
this.processObject(doc.readShort());
this.sb.append("</CDXML>\n");
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.out.println(this.sb + "\n" + this.objects);
e.printStackTrace();
return null;
} else {
throw e;
}
}
return this.sb.toString();
}, "javajs.api.GenericBinaryDocument");
c$.appendHeader = Clazz.defineMethod(c$, "appendHeader", 
function(sb){
sb.append("<!DOCTYPE CDXML SYSTEM \"http://www.cambridgesoft.com/xml/cdxml.dtd\" >\n");
J.adapter.writers.CMLWriter.startOpenTag(sb, "CDXML");
J.adapter.writers.CMLWriter.addAttributes(sb, J.adapter.writers.CDXMLWriter.cdxAttributes);
J.adapter.writers.CMLWriter.terminateTag(sb);
}, "JU.SB");
Clazz.defineMethod(c$, "processObject", 
function(type){
var id = this.doc.readInt();
type = type & 0xFFFF;
var terminated = false;
var name = null;
switch (type) {
case 32768:
case 32770:
default:
id = -2147483648;
terminated = true;
break;
case 32769:
name = "page";
id = -2147483648;
break;
case 32771:
name = "fragment";
break;
case 32772:
name = "n";
break;
case 32773:
name = "b";
break;
case 32774:
name = "t";
id = -2147483648;
break;
}
this.sbpt = this.sb.length();
this.objects.push(name);
if (name != null) {
J.adapter.writers.CMLWriter.startOpenTag(this.sb, name);
if (id != -2147483648) {
J.adapter.writers.CMLWriter.addAttribute(this.sb, "id", "" + id);
}}var prop;
while ((prop = this.doc.readShort()) != 0) {
if ((prop & 0x8000) != 0) {
if (!terminated) {
J.adapter.writers.CMLWriter.terminateTag(this.sb);
terminated = true;
}this.processObject(prop);
continue;
}var len = this.readLength();
switch (type) {
case 32772:
this.writeNodeProperties(prop, len);
break;
case 32774:
if (!terminated) {
J.adapter.writers.CMLWriter.terminateTag(this.sb);
terminated = true;
}this.writeTextProperty(prop, len);
break;
case 32773:
this.writeBondProperties(prop, len);
break;
default:
this.skip(len);
break;
}
}
if (name != null) {
if (!terminated) {
J.adapter.writers.CMLWriter.terminateEmptyTag(this.sb);
} else {
J.adapter.writers.CMLWriter.closeTag(this.sb, name);
}}}, "~N");
Clazz.defineMethod(c$, "writeNodeProperties", 
function(prop, len){
switch (prop) {
case 512:
var y = J.adapter.writers.CDXMLWriter.toPoint(this.readInt(len >> 1));
var x = J.adapter.writers.CDXMLWriter.toPoint(this.readInt(len >> 1));
J.adapter.writers.CMLWriter.addAttribute(this.sb, "p", x + " " + y);
break;
case 1024:
var nodeType = J.adapter.writers.CDXMLWriter.getNodeType(this.readInt(len));
J.adapter.writers.CMLWriter.addAttribute(this.sb, "NodeType", nodeType);
break;
case 1026:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "Element", "" + this.readInt(len));
break;
case 1056:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "Isotope", "" + this.readInt(len));
break;
case 1057:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "Charge", "" + this.readInt(len));
break;
case 16:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "Warning", this.readString(len));
break;
case 1073:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "BondOrdering", this.readArray());
break;
case 1285:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "ConnectionOrder", this.readArray());
break;
case 1074:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "Attachments", this.readArray());
break;
case 1075:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "GenericNickname", this.readString(len));
break;
default:
this.skip(len);
}
}, "~N,~N");
Clazz.defineMethod(c$, "writeBondProperties", 
function(prop, len){
switch (prop) {
case 1536:
var order = J.adapter.writers.CDXMLWriter.getBondOrder(this.readInt(len));
if (order == null) {
this.removeObject();
return;
}J.adapter.writers.CMLWriter.addAttribute(this.sb, "Order", order);
break;
case 1537:
var d = J.adapter.writers.CDXMLWriter.getBondDisplay(this.readInt(len));
if (d == null) {
this.removeObject();
return;
}J.adapter.writers.CMLWriter.addAttribute(this.sb, "Display", d);
break;
case 1538:
var d2 = J.adapter.writers.CDXMLWriter.getBondDisplay(this.readInt(len));
if (d2 != null) J.adapter.writers.CMLWriter.addAttribute(this.sb, "Display2", d2);
break;
case 1540:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "B", "" + this.readInt(len));
break;
case 1541:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "E", "" + this.readInt(len));
break;
case 1544:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "BeginAttach", "" + this.readInt(len));
break;
case 1545:
J.adapter.writers.CMLWriter.addAttribute(this.sb, "EndAttach", "" + this.readInt(len));
break;
default:
this.skip(len);
}
}, "~N,~N");
Clazz.defineMethod(c$, "writeTextProperty", 
function(prop, len){
switch (prop) {
case 1792:
var text = this.readString(len);
System.out.println("CDXMLW text=" + text);
J.adapter.writers.CMLWriter.openTag(this.sb, "s");
this.sb.setLength(this.sb.length() - 1);
this.sb.append(J.adapter.writers.CDXMLWriter.wrapCData(text));
J.adapter.writers.CMLWriter.closeTag(this.sb, "s");
break;
default:
this.skip(len);
}
}, "~N,~N");
c$.wrapCData = Clazz.defineMethod(c$, "wrapCData", 
function(s){
return (s.indexOf("&") < 0 && s.indexOf("<") < 0 ? s : "<![CDATA[" + JU.PT.rep(s, "]]>", "]]]]><![CDATA[>") + "]]>");
}, "~S");
c$.getNodeType = Clazz.defineMethod(c$, "getNodeType", 
function(n){
var name = null;
switch (n) {
case 0:
return "Unspecified";
case 1:
return "Element";
case 4:
return "Nickname";
case 5:
return "Fragment";
case 7:
return "GenericNickname";
case 10:
return "MultiAttachment";
case 11:
return "VariableAttachment";
case 12:
return "ExternalConnectionPoint";
case 2:
name = "ElementList";
break;
case 3:
name = "ElementListNickname";
break;
case 6:
name = "Formula";
break;
case 8:
name = "AnonymousAlternativeGroup";
break;
case 9:
name = "NamedAnonymousGroup";
break;
case 13:
name = "LinkNode";
break;
}
System.err.println("CDXMLWriter Node type " + name + " not identified");
return "_";
}, "~N");
c$.getBondDisplay = Clazz.defineMethod(c$, "getBondDisplay", 
function(i){
switch (i) {
case 0:
return "Solid";
case 1:
return "Dash";
case 2:
return "Hash";
case 3:
return "WedgedHashBegin";
case 4:
return "WedgedHashEnd";
case 5:
return "Bold";
case 6:
return "WedgeBegin";
case 7:
return "WedgeEnd";
case 8:
return "Wavy";
case 9:
return "HollowWedgeBegin";
case 10:
return "HollowWedgeEnd";
case 11:
return "WavyWedgeBegin";
case 12:
return "WavyWedgeEnd";
case 13:
return "Dot";
case 14:
return "DashDot";
}
return null;
}, "~N");
c$.getBondOrder = Clazz.defineMethod(c$, "getBondOrder", 
function(i){
switch (i) {
case 1:
return "1";
case 2:
return "2";
case 4:
return "3";
case 8:
return "4";
case 16:
return "5";
case 32:
return "6";
case 64:
return "0.5";
case 128:
return "1.5";
case 256:
return "2.5";
case 512:
return "3.5";
case 1024:
return "4.5";
case 2048:
return "5.5";
case 4096:
return "dative";
case 8192:
return "ionic";
case 16384:
return "hydrogen";
case 32768:
return "threecenter";
}
return null;
}, "~N");
Clazz.defineMethod(c$, "removeObject", 
function(){
this.sb.setLength(this.sbpt);
});
Clazz.defineMethod(c$, "skip", 
function(len){
this.doc.seek(this.doc.getPosition() + len);
}, "~N");
Clazz.defineMethod(c$, "readInt", 
function(len){
switch (len) {
case 1:
return (256 + this.doc.readByte()) % 256;
case 2:
return this.doc.readShort();
case 4:
return this.doc.readInt();
case 8:
return this.doc.readLong();
}
System.err.println("CDXMLWriter.readInt len " + len);
return 0;
}, "~N");
Clazz.defineMethod(c$, "readString", 
function(len){
var nStyles = this.doc.readShort();
len -= 2;
switch (nStyles) {
case 0:
break;
default:
this.skip(nStyles * 10);
len -= nStyles * 10;
break;
}
return this.doc.readString(len);
}, "~N");
Clazz.defineMethod(c$, "readArray", 
function(){
var s = "";
for (var i = this.doc.readShort(); --i >= 0; ) {
s += " " + this.doc.readInt();
}
return s.trim();
});
Clazz.defineMethod(c$, "readLength", 
function(){
var len = this.doc.readShort();
if (len == -1) {
len = this.doc.readInt();
}return len;
});
c$.toPoint = Clazz.defineMethod(c$, "toPoint", 
function(i){
return Math.round(i / 655.36) / 100.0;
}, "~N");
c$.main = Clazz.defineMethod(c$, "main", 
function(args){
}, "~A");
c$.fromString = Clazz.defineMethod(c$, "fromString", 
function(vwr, type, mol){
var htParams =  new java.util.Hashtable();
htParams.put("filter", "filetype=" + type);
var o;
try {
o = vwr.getModelAdapter().getAtomSetCollectionFromReader("", JU.Rdr.getBR(mol), htParams);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
return null;
} else {
throw e;
}
}
if ((typeof(o)=='string')) {
return null;
}return J.adapter.writers.CDXMLWriter.fromASC(o);
}, "JV.Viewer,~S,~S");
c$.cdxAttributes =  Clazz.newArray(-1, ["HashSpacing", "2.50", "MarginWidth", "1.60", "LineWidth", "0.60", "BoldWidth", "2", "BondLength", "14.40", "BondSpacing", "18"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
