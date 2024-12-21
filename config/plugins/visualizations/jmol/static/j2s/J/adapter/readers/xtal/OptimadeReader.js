Clazz.declarePackage("J.adapter.readers.xtal");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.xtal.OptimadeReader", ["java.util.HashMap", "JU.SB", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.modelNo = 0;
this.iHaveDesiredModel = false;
this.permutation = 0;
this.isPolymer = false;
this.isSlab = false;
this.noSlab = false;
this.xyz = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.xtal, "OptimadeReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.prepareFields (c$, function(){
this.xyz =  Clazz.newFloatArray (3, 0);
});
Clazz.defineMethod(c$, "initializeReader", 
function(){
Clazz.superCall(this, J.adapter.readers.xtal.OptimadeReader, "initializeReader", []);
this.noSlab = this.checkFilterKey("NOSLAB");
try {
var strJSON = this.htParams.get("fileData");
if (strJSON == null) {
var sb =  new JU.SB();
while (this.rd() != null) sb.append(this.line);

strJSON = sb.toString();
this.line = null;
}var aData = null;
if (strJSON.startsWith("[")) {
var data = this.vwr.parseJSONArray(strJSON);
for (var i = 0; i < data.size(); i++) {
if (Clazz.instanceOf(data.get(i),"java.util.Map")) {
aData = (data.get(i)).get("data");
if (aData != null) {
break;
}}}
} else {
aData = this.vwr.parseJSONMap(strJSON).get("data");
}if (aData != null) {
for (var i = 0; !this.iHaveDesiredModel && i < aData.size(); i++) {
var data = aData.get(i);
if ("structures".equals(data.get("type"))) {
this.readModel(data.get("attributes"));
}}
}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
} else {
throw e;
}
}
this.continuing = false;
});
Clazz.defineMethod(c$, "readModel", 
function(map){
if (!this.doGetModel(this.modelNumber = ++this.modelNo, null)) return;
this.iHaveDesiredModel = this.isLastModel(this.modelNumber);
this.applySymmetryAndSetTrajectory();
this.asc.newAtomSet();
this.setFractionalCoordinates(false);
var dimensionType =  Clazz.newFloatArray (3, 0);
if (J.adapter.readers.xtal.OptimadeReader.toFloatArray(map.get("dimension_types"), dimensionType)) {
this.checkDimensionType(dimensionType);
}if (!this.isMolecular) {
this.setSpaceGroupName("P1");
this.asc.setInfo("symmetryType", (this.isSlab ? "2D - SLAB" : this.isPolymer ? "1D - POLYMER" : "3D"));
}this.asc.setAtomSetName(map.get("chemical_formula_descriptive"));
this.doConvertToFractional = (!this.isMolecular && this.readLattice(map.get("lattice_vectors")));
this.readAtoms(map.get("species"), map.get("species_at_sites"), map.get("cartesian_site_positions"));
}, "java.util.Map");
Clazz.defineMethod(c$, "checkDimensionType", 
function(dt){
this.isPolymer = this.isSlab = this.isMolecular = false;
if (this.noSlab) return;
this.permutation = 0;
switch (Clazz.floatToInt(dt[2] + dt[1] * 2 + dt[0] * 4)) {
default:
case 0:
this.isMolecular = true;
break;
case 1:
this.isPolymer = true;
this.permutation = 1;
break;
case 2:
this.isPolymer = true;
this.permutation = 2;
break;
case 3:
this.isSlab = true;
this.permutation = 2;
break;
case 5:
this.isSlab = true;
this.permutation = 1;
break;
case 4:
this.isPolymer = true;
break;
case 6:
this.isSlab = true;
break;
case 7:
break;
}
}, "~A");
Clazz.defineMethod(c$, "readLattice", 
function(lattice){
if (lattice == null) return false;
var abc =  Clazz.newFloatArray (3, 0);
for (var i = 0; i < 3; i++) {
if (!J.adapter.readers.xtal.OptimadeReader.toFloatArray(lattice.get(i), this.xyz)) {
return false;
}this.unitCellParams[0] = NaN;
if (this.isSlab || this.isPolymer) {
abc[i] = Math.sqrt(this.xyz[0] * this.xyz[0] + this.xyz[1] * this.xyz[1] + this.xyz[2] * this.xyz[2]);
if (abc[i] >= 500) {
this.xyz[0] /= abc[i];
this.xyz[1] /= abc[i];
this.xyz[2] /= abc[i];
}}if (this.isSlab || this.isPolymer) this.unitCellParams[0] = 0;
if (i == 2) {
if (this.isSlab || this.isPolymer) {
this.unitCellParams[0] = abc[this.permutation];
if (this.isSlab) this.unitCellParams[1] = abc[(this.permutation + 1) % 3];
}}this.addExplicitLatticeVector((i + this.permutation) % 3, this.xyz, 0);
}
this.doApplySymmetry = true;
return true;
}, "java.util.List");
Clazz.defineMethod(c$, "readAtoms", 
function(species, sites, coords){
var natoms = sites.size();
var speciesByName = null;
if (species == null) {
JU.Logger.error("OptimadeReader - no 'species' key");
} else {
speciesByName =  new java.util.HashMap();
for (var i = species.size(); --i >= 0; ) {
var s = species.get(i);
speciesByName.put(s.get("name"), s);
}
}for (var i = 0; i < natoms; i++) {
var sname = sites.get(i);
J.adapter.readers.xtal.OptimadeReader.toFloatArray(coords.get(i), this.xyz);
if (species == null) {
this.addAtom(this.xyz, sites.get(i), sname);
} else {
var sp = speciesByName.get(sname);
var syms = sp.get("chemical_symbols");
var nOcc = syms.size();
if (nOcc > 1) {
var conc =  Clazz.newFloatArray (nOcc, 0);
if (J.adapter.readers.xtal.OptimadeReader.toFloatArray(sp.get("concentration"), conc)) {
for (var j = 0; j < conc.length; j++) {
var a = this.addAtom(this.xyz, syms.get(j), sname);
a.foccupancy = conc[j];
}
continue;
}}this.addAtom(this.xyz, syms.get(0), sname);
}}
}, "java.util.List,java.util.List,java.util.List");
Clazz.defineMethod(c$, "addAtom", 
function(xyz, sym, name){
var atom = this.asc.addNewAtom();
if (sym != null) atom.elementSymbol = sym;
if (name != null) atom.atomName = name;
this.setAtomCoordXYZ(atom, xyz[0], xyz[1], xyz[2]);
return atom;
}, "~A,~S,~S");
c$.toFloatArray = Clazz.defineMethod(c$, "toFloatArray", 
function(list, a){
if (list == null) return false;
for (var i = a.length; --i >= 0; ) {
var d = list.get(i);
if (d == null) return false;
a[i] = list.get(i).floatValue();
}
return true;
}, "java.util.List,~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
