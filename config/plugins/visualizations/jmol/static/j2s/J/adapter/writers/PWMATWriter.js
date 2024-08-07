Clazz.declarePackage("J.adapter.writers");
Clazz.load(["J.adapter.writers.XtlWriter", "J.api.JmolWriter"], "J.adapter.writers.PWMATWriter", ["JU.P3", "$.PT", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.oc = null;
this.uc = null;
this.names = null;
this.bs = null;
this.isSlab = false;
this.writeGlobals = false;
Clazz.instantialize(this, arguments);}, J.adapter.writers, "PWMATWriter", J.adapter.writers.XtlWriter, J.api.JmolWriter);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.writers.PWMATWriter, []);
this.isHighPrecision = true;
});
Clazz.overrideMethod(c$, "set", 
function(viewer, oc, data){
this.vwr = viewer;
this.isSlab = (data != null && data[0] != null && data[0].equals("slab"));
this.oc = (oc == null ? this.vwr.getOutputChannel(null, null) : oc);
}, "JV.Viewer,JU.OC,~A");
Clazz.overrideMethod(c$, "write", 
function(bs){
if (bs == null) bs = this.vwr.bsA();
try {
this.uc = this.vwr.ms.getUnitCellForAtom(bs.nextSetBit(0));
this.bs = (this.isSlab ? bs : this.uc.removeDuplicates(this.vwr.ms, bs, false));
this.names = this.vwr.getDataObj("property_pwm_*", null, -1);
this.writeHeader();
this.writeLattice();
this.writePositions();
this.writeDataBlocks();
if (this.writeGlobals) this.writeGlobalBlocks();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.err.println("Error writing PWmat file " + e);
} else {
throw e;
}
}
return this.toString();
}, "JU.BS");
Clazz.defineMethod(c$, "writeHeader", 
function(){
this.oc.append(JU.PT.formatStringI("%12i\n", "i", this.bs.cardinality()));
});
Clazz.defineMethod(c$, "writeLattice", 
function(){
this.oc.append("Lattice vector\n");
if (this.uc == null) {
this.uc = this.vwr.getSymTemp();
var bb = this.vwr.getBoundBoxCornerVector();
var len = Math.round(bb.length() * 2);
this.uc.setUnitCellFromParams( Clazz.newFloatArray(-1, [len, len, len, 90, 90, 90]), false, 1.0E-12);
}var abc = this.uc.getUnitCellVectors();
var f = "%18.10p%18.10p%18.10p\n";
this.oc.append(JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[1]])));
this.oc.append(JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[2]])));
this.oc.append(JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[3]])));
JU.Logger.info("PWMATWriter: LATTICE VECTORS");
});
Clazz.defineMethod(c$, "writePositions", 
function(){
var cx = this.getData("CONSTRAINTS_X");
var cy = (cx == null ? null : this.getData("CONSTRAINTS_Y"));
var cz = (cy == null ? null : this.getData("CONSTRAINTS_Z"));
this.oc.append("Position, move_x, move_y, move_z\n");
var f = "%4i%40s" + (cz == null ? "  1  1  1" : "%4i%4i%4i") + "\n";
var a = this.vwr.ms.at;
var p =  new JU.P3();
for (var ic = 0, i = this.bs.nextSetBit(0); i >= 0; i = this.bs.nextSetBit(i + 1), ic++) {
p.setT(a[i]);
this.uc.toFractional(p, false);
var coord = this.clean(p.x) + this.clean(p.y) + this.clean(p.z);
if (cz == null) {
this.oc.append(JU.PT.sprintf(f, "is",  Clazz.newArray(-1, [Integer.$valueOf(a[i].getElementNumber()), coord])));
} else {
var ix = Clazz.floatToInt(cx[ic]);
var iy = Clazz.floatToInt(cy[ic]);
var iz = Clazz.floatToInt(cz[ic]);
this.oc.append(JU.PT.sprintf(f, "isiii",  Clazz.newArray(-1, [Integer.$valueOf(a[i].getElementNumber()), coord, Integer.$valueOf(ix), Integer.$valueOf(iy), Integer.$valueOf(iz)])));
}}
JU.Logger.info("PWMATWriter: POSITIONS");
});
Clazz.defineMethod(c$, "getData", 
function(name){
name = "property_pwm_" + name.toLowerCase();
for (var i = this.names.size(); --i >= 0; ) {
var n = this.names.get(i);
if (name.equalsIgnoreCase(n)) {
this.names.removeItemAt(i);
return this.vwr.getDataObj(n, this.bs, 1);
}}
return null;
}, "~S");
Clazz.defineMethod(c$, "getVectors", 
function(name){
var vectors =  Clazz.newArray(-1, [this.getData(name + "_x"), this.getData(name + "_y"), this.getData(name + "_z")]);
return (vectors[0] == null || vectors[1] == null || vectors[2] == null ? null : vectors);
}, "~S");
Clazz.defineMethod(c$, "writeDataBlocks", 
function(){
this.writeVectors("FORCE");
this.writeVectors("VELOCITY");
this.writeMagnetic();
this.writeMoreData();
});
Clazz.defineMethod(c$, "writeVectors", 
function(name){
var xyz = this.getVectors(name);
if (xyz == null) return;
var a = this.vwr.ms.at;
var p =  new JU.P3();
this.oc.append(name.toUpperCase()).append("\n");
var f = "%4i%18.12p%18.12p%18.12p\n";
for (var ic = 0, i = this.bs.nextSetBit(0); i >= 0; i = this.bs.nextSetBit(i + 1), ic++) {
p.set(xyz[0][ic], xyz[1][ic], xyz[2][ic]);
this.oc.append(JU.PT.sprintf(f, "ip",  Clazz.newArray(-1, [Integer.$valueOf(a[i].getElementNumber()), p])));
}
JU.Logger.info("PWMATWriter: " + name);
}, "~S");
Clazz.defineMethod(c$, "writeMagnetic", 
function(){
var m = this.writeItems("MAGNETIC");
if (m == null) return;
this.writeItem2(m, "CONSTRAINT_MAG");
});
Clazz.defineMethod(c$, "writeItem2", 
function(m, name){
var v = this.getData(name);
if (v == null) return;
var a = this.vwr.ms.at;
this.oc.append(name.toUpperCase()).append("\n");
var f = "%4i%18.12f%18.12f\n";
for (var ic = 0, i = this.bs.nextSetBit(0); i >= 0; i = this.bs.nextSetBit(i + 1), ic++) {
this.oc.append(JU.PT.sprintf(f, "iff",  Clazz.newArray(-1, [Integer.$valueOf(a[i].getElementNumber()), Float.$valueOf(m[ic]), Float.$valueOf(v[ic])])));
}
}, "~A,~S");
Clazz.defineMethod(c$, "writeItems", 
function(name){
var m = this.getData(name);
if (m == null) return null;
var a = this.vwr.ms.at;
name = name.toUpperCase();
this.oc.append(name).append("\n");
var f = "%4i%18.12f\n";
for (var ic = 0, i = this.bs.nextSetBit(0); i >= 0; i = this.bs.nextSetBit(i + 1), ic++) {
this.oc.append(JU.PT.sprintf(f, "if",  Clazz.newArray(-1, [Integer.$valueOf(a[i].getElementNumber()), Float.$valueOf(m[ic])])));
}
JU.Logger.info("PWMATWriter: " + name);
return m;
}, "~S");
Clazz.defineMethod(c$, "writeMoreData", 
function(){
var n = this.names.size();
var i0 = 0;
while (this.names.size() > i0 && --n >= 0) {
var name = this.names.get(i0).substring(13);
System.out.println(name);
if (name.endsWith("_y") || name.endsWith("_z")) {
i0++;
continue;
}if (name.endsWith("_x")) {
this.writeVectors(name.substring(0, name.length - 2));
i0 = 0;
} else {
this.writeItems(name);
}}
});
Clazz.defineMethod(c$, "writeGlobalBlocks", 
function(){
var globals = this.vwr.getModelForAtomIndex(this.bs.nextSetBit(0)).auxiliaryInfo.get("globalPWmatData");
if (globals != null) for (var e, $e = globals.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
this.oc.append(e.getKey()).append("\n");
var lines = e.getValue();
for (var i = 0; i < lines.length; i++) this.oc.append(lines[i]).append("\n");

}
});
Clazz.overrideMethod(c$, "toString", 
function(){
return (this.oc == null ? "" : this.oc.toString());
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
