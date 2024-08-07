Clazz.declarePackage("J.adapter.readers.xtal");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.xtal.CmdfReader", ["J.adapter.smarter.Atom", "J.api.JmolAdapter"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.buf = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xtal, "CmdfReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.prepareFields (c$, function(){
this.buf =  Clazz.newByteArray (100, 0);
});
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.setFractionalCoordinates(true);
});
Clazz.overrideMethod(c$, "processBinaryDocument", 
function(){
this.binaryDoc.setStream(null, false);
this.binaryDoc.seek(28);
var len = this.binaryDoc.readInt();
System.out.println("file length: " + len + " " + Integer.toHexString(len));
this.seek("CELL", 32);
var uc =  Clazz.newFloatArray (6, 0);
for (var i = 0; i < 6; i++) {
uc[i] = this.binaryDoc.readFloat();
}
this.setUnitCell(uc[0], uc[1], uc[2], uc[3], uc[4], uc[5]);
this.seek("SYMM", -1);
var sg = J.adapter.readers.xtal.CmdfReader.fixSpaceGroup(this.binaryDoc.readString(20));
this.setSpaceGroupName(sg);
System.out.println("Space group is " + sg);
this.readAtoms();
System.out.println("done");
});
c$.fixSpaceGroup = Clazz.defineMethod(c$, "fixSpaceGroup", 
function(sg){
var pt = sg.indexOf('\0');
if (pt == 0) System.out.println("SYMM: empty;NO space group??");
return (pt < 0 ? sg : sg.substring(0, pt)).trim();
}, "~S");
Clazz.defineMethod(c$, "readAtoms", 
function(){
this.seek("AUN7", 32);
var nSites = this.binaryDoc.readInt();
System.out.println(nSites + " sites");
for (var i = 0; i < nSites; i++) this.readSite();

});
Clazz.defineMethod(c$, "readSite", 
function(){
var nOccupants = this.binaryDoc.readByte();
var atoms =  new Array(nOccupants);
for (var i = 0; i < nOccupants; i++) {
var a = atoms[i] =  new J.adapter.smarter.Atom();
var ch2 = String.fromCharCode(this.binaryDoc.readByte());
var ch1 = String.fromCharCode(this.binaryDoc.readByte());
a.elementSymbol = J.adapter.readers.xtal.CmdfReader.getSymbol("" + ch1 + ch2);
if (J.api.JmolAdapter.getElementNumber(a.elementSymbol) == 0) {
System.out.println("ELEMENT error " + a.elementSymbol + " " + this.fileName);
}a.foccupancy = this.binaryDoc.readFloat();
this.asc.addAtom(a);
}
this.binaryDoc.readInt();
var sym0 = atoms[0].elementSymbol;
var name = this.readString();
var valence = this.binaryDoc.readInt();
for (var i = 0; i < nOccupants; i++) {
atoms[i].atomName = (i == 0 || sym0.length > name.length ? name : atoms[i].elementSymbol + name.substring(sym0.length));
}
var unk3s = this.binaryDoc.readShort() & 0xFFFF;
var x = this.binaryDoc.readFloat();
var y = this.binaryDoc.readFloat();
var z = this.binaryDoc.readFloat();
for (var i = 0; i < nOccupants; i++) {
this.setAtomCoordXYZ(atoms[i], x, y, z);
}
var index2 = this.binaryDoc.readInt() / 32;
var unk4b = this.binaryDoc.readByte() & 0xFF;
var siteNumber = this.binaryDoc.readShort();
var unk5b = this.binaryDoc.readByte() & 0xFF;
var wyn = this.binaryDoc.readInt();
var wyabc = this.binaryDoc.readByte();
var wyckoff = "" + wyn + String.fromCharCode(0x60 + wyabc);
System.out.println("SITE " + siteNumber + " occ=" + nOccupants + " " + atoms[0].elementSymbol + " " + atoms[0].atomName + " " + wyckoff + " " + atoms[0] + (nOccupants > 1 ? atoms[1].atomName : "") + " valence=" + valence + " " + index2 + " " + Integer.toHexString(unk3s) + " " + Integer.toHexString(unk4b) + " " + Integer.toHexString(unk5b));
return;
});
Clazz.defineMethod(c$, "readString", 
function(){
var n = this.binaryDoc.readByte();
this.binaryDoc.readByteArray(this.buf, 0, n);
return  String.instantialize(this.buf, 0, n);
});
Clazz.defineMethod(c$, "seek", 
function(label, where){
var bytes = label.getBytes();
if (where > 0) this.binaryDoc.seek(where);
var p = (where >= 0 ? where : this.binaryDoc.getPosition());
System.out.println("looking for " + label + " @" + p);
var off = 0;
var n = bytes.length;
var p0 = p;
while (off < n) {
var b = this.binaryDoc.readByte();
p++;
if (b == bytes[off]) {
off++;
} else if (off > 0) {
this.binaryDoc.seek(p = p0 = p0 + 1);
off = 0;
}}
System.out.println(label + " found at " + (p - n));
return p;
}, "~S,~N");
c$.getSymbol = Clazz.defineMethod(c$, "getSymbol", 
function(sym){
if (sym == null) return "Xx";
var len = sym.length;
if (len < 2) return sym;
var ch1 = sym.charAt(1);
if (ch1 >= 'a' && ch1 <= 'z') return sym.substring(0, 2);
return "" + sym.charAt(0);
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
