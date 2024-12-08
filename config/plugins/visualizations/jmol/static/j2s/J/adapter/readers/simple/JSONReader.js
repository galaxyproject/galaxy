Clazz.declarePackage("J.adapter.readers.simple");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.simple.JSONReader", ["JU.P3", "$.PT", "J.adapter.smarter.Bond", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.scale = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.simple, "JSONReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.asc.setCollectionName("JSON");
this.asc.newAtomSet();
var s = "";
while (this.rd() != null) s += this.line;

s = JU.PT.replaceAllCharacters(s, "\" \t", "").$replace(',', ':');
if (s.contains("_is2D:true")) this.set2D();
if (s.contains("_scale:")) this.getScaling(this.getSection(s, "_scale", false));
s = JU.PT.replaceAllCharacters(s, "}", "").$replace(',', ':');
if (s.indexOf("atomArray:[") >= 0) {
this.readAtomArray(this.getSection(s, "atomArray", true));
this.readBondArray(this.getSection(s, "bondArray", true));
} else {
this.readAtoms(this.getSection(s, "a", true));
this.readBonds(this.getSection(s, "b", true));
}this.continuing = false;
});
Clazz.defineMethod(c$, "getScaling", 
function(s){
var xyz = JU.PT.split(s[0], ":");
this.scale = JU.P3.new3(1, 1, 1);
for (var j = 0; j < xyz.length; j += 2) if (xyz[j].length == 1) switch ((xyz[j].charAt(0)).charCodeAt(0)) {
case 120:
this.scale.x = this.parseFloatStr(xyz[j + 1]);
break;
case 121:
this.scale.y = this.parseFloatStr(xyz[j + 1]);
break;
case 122:
this.scale.z = this.parseFloatStr(xyz[j + 1]);
break;
}

JU.Logger.info("scale set to " + this.scale);
}, "~A");
Clazz.defineMethod(c$, "getSection", 
function(json, key, isArray){
var a = JU.PT.split(json, key + ":" + (isArray ? "[" : "") + "{");
if (a.length < 2) return a;
var data = a[1];
data = data.substring(0, data.indexOf((isArray ? "]" : "}"))) + ":";
return JU.PT.split(data, "{");
}, "~S,~S,~B");
Clazz.defineMethod(c$, "readAtoms", 
function(atoms){
for (var i = 0; i < atoms.length; ++i) {
var lxyz = JU.PT.split(atoms[i], ":");
var atom = this.asc.addNewAtom();
var x = 0;
var y = 0;
var z = 0;
var l = "C";
for (var j = 0; j < lxyz.length; j += 2) if (lxyz[j].length == 1) switch ((lxyz[j].charAt(0)).charCodeAt(0)) {
case 120:
x = this.parseFloatStr(lxyz[j + 1]);
break;
case 121:
y = this.parseFloatStr(lxyz[j + 1]);
break;
case 122:
z = this.parseFloatStr(lxyz[j + 1]);
break;
case 108:
l = lxyz[j + 1];
break;
}

if (this.scale != null) {
x /= this.scale.x;
y /= this.scale.y;
z /= this.scale.z;
}this.setAtomCoordXYZ(atom, x, y, z);
atom.elementSymbol = l;
}
}, "~A");
Clazz.defineMethod(c$, "readBonds", 
function(bonds){
for (var i = 0; i < bonds.length; ++i) {
var beo = JU.PT.split(bonds[i], ":");
var b = 0;
var e = 0;
var order = 1;
for (var j = 0; j < beo.length; j += 2) if (beo[j].length == 1) switch ((beo[j].charAt(0)).charCodeAt(0)) {
case 98:
b = this.parseIntStr(beo[j + 1]);
break;
case 101:
e = this.parseIntStr(beo[j + 1]);
break;
case 111:
var o = Clazz.floatToInt(this.parseFloatStr(beo[j + 1]) * 2);
switch (o) {
case 0:
continue;
case 2:
case 4:
case 6:
case 8:
order = Clazz.doubleToInt(o / 2);
break;
case 1:
order = 33;
break;
case 3:
order = 66;
break;
case 5:
order = 97;
break;
default:
order = 1;
break;
}
break;
}

this.asc.addBond( new J.adapter.smarter.Bond(b, e, order));
}
}, "~A");
Clazz.defineMethod(c$, "readAtomArray", 
function(atoms){
for (var i = 0; i < atoms.length; ++i) {
var lxyz = JU.PT.split(atoms[i], ":");
var atom = this.asc.addNewAtom();
var x = 0;
var y = 0;
var z = 0;
var l = "C";
for (var j = 0; j < lxyz.length; j += 2) {
switch ((lxyz[j].charAt(0)).charCodeAt(0)) {
case 120:
x = this.parseFloatStr(lxyz[j + 1]);
break;
case 121:
y = this.parseFloatStr(lxyz[j + 1]);
break;
case 122:
z = this.parseFloatStr(lxyz[j + 1]);
break;
case 101:
l = lxyz[j + 1];
break;
}
}
if (this.scale != null) {
x /= this.scale.x;
y /= this.scale.y;
z /= this.scale.z;
}this.setAtomCoordXYZ(atom, x, y, z);
atom.elementSymbol = l;
}
}, "~A");
Clazz.defineMethod(c$, "readBondArray", 
function(bonds){
for (var i = 0; i < bonds.length; ++i) {
var beo = JU.PT.split(bonds[i], ":");
var b = 0;
var e = 0;
var order = 1;
for (var j = 0; j < beo.length; j += 2) {
if (beo[j].length > 1) {
switch ((beo[j].charAt(1)).charCodeAt(0)) {
case 49:
b = this.parseIntStr(beo[j + 1]) - 1;
break;
case 50:
e = this.parseIntStr(beo[j + 1]) - 1;
break;
case 121:
var type = beo[j + 1];
switch ((type.charAt(0)).charCodeAt(0)) {
case 68:
order = 2;
break;
case 65:
order = 1;
break;
case 83:
default:
order = 1;
break;
}
break;
}
} else {
System.err.println("JSONReader error bond tag " + beo[j]);
}}
if (b >= this.asc.ac || e >= this.asc.ac) System.err.println("JSONReader error bond referencing atoms " + b + " " + e + " atomCount=" + this.asc.ac + " for " + this.fileName);
 else this.asc.addBond( new J.adapter.smarter.Bond(b, e, order));
}
}, "~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
