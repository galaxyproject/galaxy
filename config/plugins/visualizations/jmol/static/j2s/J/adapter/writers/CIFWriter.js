Clazz.declarePackage("J.adapter.writers");
Clazz.load(["J.adapter.writers.XtlWriter", "J.api.JmolWriter", "JU.P3"], "J.adapter.writers.CIFWriter", ["JU.BS", "$.PT", "$.SB", "JV.Viewer"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.oc = null;
this.isP1 = false;
Clazz.instantialize(this, arguments);}, J.adapter.writers, "CIFWriter", J.adapter.writers.XtlWriter, J.api.JmolWriter);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.writers.CIFWriter, []);
});
Clazz.overrideMethod(c$, "set", 
function(viewer, oc, data){
this.vwr = viewer;
this.oc = (oc == null ? this.vwr.getOutputChannel(null, null) : oc);
this.isP1 = (data != null && data.length > 0 && "P1".equals(data[0]));
}, "JV.Viewer,JU.OC,~A");
Clazz.overrideMethod(c$, "write", 
function(bs){
if (bs == null) bs = this.vwr.bsA();
try {
var mi = this.vwr.ms.at[bs.nextSetBit(0)].mi;
var uc = this.vwr.getCurrentUnitCell();
this.haveUnitCell = (uc != null);
if (!this.haveUnitCell) uc = this.vwr.getSymTemp().setUnitCellFromParams(null, false, 0.00001);
this.slop = uc.getPrecision();
this.isHighPrecision = (this.slop == 1.0E-12);
this.precision = Clazz.doubleToInt(-Math.log10(this.slop));
var offset = uc.getFractionalOffset();
var fractionalOffset = offset != null && (offset.x != Clazz.floatToInt(offset.x) || offset.y != Clazz.floatToInt(offset.y) || offset.z != Clazz.floatToInt(offset.z));
var fset;
var haveCustom = (fractionalOffset || (fset = uc.getUnitCellMultiplier()) != null && (fset.z == 1 ? !fset.equals(J.adapter.writers.CIFWriter.fset0) : fset.z != 0));
var ucm = uc.getUnitCellMultiplied();
this.isP1 = (this.isP1 || ucm !== uc || fractionalOffset || uc.getSpaceGroupOperationCount() < 2);
uc = ucm;
var modelAU = (!this.haveUnitCell ? bs : this.isP1 ? uc.removeDuplicates(this.vwr.ms, bs, false) : this.vwr.ms.am[mi].bsAsymmetricUnit);
var bsOut;
if (modelAU == null) {
bsOut = bs;
} else {
bsOut =  new JU.BS();
bsOut.or(modelAU);
bsOut.and(bs);
}this.vwr.setErrorMessage(null, " (" + bsOut.cardinality() + " atoms)");
if (bsOut.isEmpty()) return "";
var sb =  new JU.SB();
sb.append("## CIF file created by Jmol " + JV.Viewer.getJmolVersion());
if (haveCustom) {
sb.append(JU.PT.rep("\n" + uc.getUnitCellInfo(false), "\n", "\n##Jmol_orig "));
}sb.append("\ndata_global");
var params = uc.getUnitCellAsArray(false);
this.appendKey(sb, "_cell_length_a").append(this.cleanT(params[0]));
this.appendKey(sb, "_cell_length_b").append(this.cleanT(params[1]));
this.appendKey(sb, "_cell_length_c").append(this.cleanT(params[2]));
this.appendKey(sb, "_cell_angle_alpha").append(this.cleanT(params[3]));
this.appendKey(sb, "_cell_angle_beta").append(this.cleanT(params[4]));
this.appendKey(sb, "_cell_angle_gamma").append(this.cleanT(params[5]));
sb.append("\n");
var n;
var hallName;
var hmName;
var ita;
if (this.isP1) {
ita = "1";
hallName = "P 1";
hmName = "P1";
n = 0;
} else {
uc.getSpaceGroupInfo(this.vwr.ms, null, mi, true, null);
ita = uc.getSpaceGroupNameType("ITA");
hallName = uc.getSpaceGroupNameType("Hall");
hmName = uc.getSpaceGroupNameType("HM");
n = uc.getSpaceGroupOperationCount();
}this.appendKey(sb, "_space_group_IT_number").append(ita == null ? "?" : ita.toString());
this.appendKey(sb, "_space_group_name_Hall").append(hallName == null || hallName.equals("?") ? "?" : "'" + hallName + "'");
this.appendKey(sb, "_space_group_name_H-M_alt").append(hmName == null ? "?" : "'" + hmName + "'");
sb.append("\n\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz");
if (n == 0) {
sb.append("\n1 x,y,z");
} else {
for (var i = 0; i < n; i++) {
sb.append("\n").appendI(i + 1).append("\t").append(uc.getSpaceGroupXyz(i, false).replaceAll(" ", ""));
}
}var atoms = this.vwr.ms.at;
var elements = "";
var haveOccupancy = false;
var occ = (this.haveUnitCell ? this.vwr.ms.occupancies : null);
if (occ != null) {
for (var i = bsOut.nextSetBit(0); i >= 0; i = bsOut.nextSetBit(i + 1)) {
if (occ[i] != 1) {
haveOccupancy = true;
break;
}}
}var haveAltLoc = false;
for (var i = bsOut.nextSetBit(0); i >= 0; i = bsOut.nextSetBit(i + 1)) {
if (atoms[i].altloc != '\0') {
haveAltLoc = true;
break;
}}
var sbLength = sb.length();
sb.append("\n\nloop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z");
if (haveAltLoc) {
sb.append("\n_atom_site_disorder_group");
}if (haveOccupancy) {
sb.append("\n_atom_site_occupancy");
} else if (!this.haveUnitCell) {
sb.append("\n_atom_site_Cartn_x\n_atom_site_Cartn_y\n_atom_site_Cartn_z");
}sb.append("\n");
var jmol_atom =  new JU.SB();
jmol_atom.append("\n\nloop_\n_jmol_atom_index\n_jmol_atom_name\n_jmol_atom_site_label\n");
var nAtoms = 0;
var p =  new JU.P3();
var elemNums =  Clazz.newIntArray (130, 0);
for (var i = bsOut.nextSetBit(0); i >= 0; i = bsOut.nextSetBit(i + 1)) {
var a = atoms[i];
p.setT(a);
if (this.haveUnitCell) {
uc.toFractional(p, !this.isP1);
}nAtoms++;
var name = a.getAtomName();
var sym = a.getElementSymbol();
var elemno = a.getElementNumber();
var key = sym + "\n";
if (elements.indexOf(key) < 0) elements += key;
var label = sym + ++elemNums[elemno];
sb.append(JU.PT.formatS(label, 5, 0, true, false)).append(" ").append(JU.PT.formatS(sym, 3, 0, true, false)).append(this.clean(p.x)).append(this.clean(p.y)).append(this.clean(p.z));
if (haveAltLoc) {
sb.append(" ").appendC(a.altloc == '\0' ? '.' : a.altloc);
}if (haveOccupancy) sb.append(" ").append(this.clean(occ[i] / 100));
 else if (!this.haveUnitCell) sb.append(this.clean(a.x)).append(this.clean(a.y)).append(this.clean(a.z));
sb.append("\n");
jmol_atom.append(JU.PT.formatS("" + a.getIndex(), 3, 0, false, false)).append(" ");
this.writeChecked(jmol_atom, name);
jmol_atom.append(" ").append(JU.PT.formatS(label, 5, 0, false, false)).append("\n");
}
if (nAtoms > 0) {
sb.append("\nloop_\n_atom_type_symbol\n").append(elements).append("\n");
sb.appendSB(jmol_atom);
} else {
sb.setLength(sbLength);
}sb.append("\n_jmol_atom_count   " + nAtoms);
sb.append("\n_jmol_precision    " + this.precision + "\n");
this.oc.append(sb.toString());
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (!JV.Viewer.isJS) e.printStackTrace();
} else {
throw e;
}
}
return this.toString();
}, "JU.BS");
Clazz.defineMethod(c$, "writeChecked", 
function(output, val){
if (val == null || val.length == 0) {
output.append(". ");
return false;
}var escape = val.charAt(0) == '_';
var escapeCharStart = "'";
var escapeCharEnd = "' ";
var hasWhitespace = false;
var hasSingle = false;
var hasDouble = false;
for (var i = 0; i < val.length; i++) {
var c = val.charAt(i);
switch ((c).charCodeAt(0)) {
case 9:
case 32:
hasWhitespace = true;
break;
case 10:
this.writeMultiline(output, val);
return true;
case 34:
if (hasSingle) {
this.writeMultiline(output, val);
return true;
}hasDouble = true;
escape = true;
escapeCharStart = "'";
escapeCharEnd = "' ";
break;
case 39:
if (hasDouble) {
this.writeMultiline(output, val);
return true;
}escape = true;
hasSingle = true;
escapeCharStart = "\"";
escapeCharEnd = "\" ";
break;
}
}
var fst = val.charAt(0);
if (!escape && (fst == '#' || fst == '$' || fst == ';' || fst == '[' || fst == ']' || hasWhitespace)) {
escapeCharStart = "'";
escapeCharEnd = "' ";
escape = true;
}if (escape) {
output.append(escapeCharStart).append(val).append(escapeCharEnd);
} else {
output.append(val).append(" ");
}return false;
}, "JU.SB,~S");
Clazz.defineMethod(c$, "writeMultiline", 
function(output, val){
output.append("\n;").append(val).append("\n;\n");
}, "JU.SB,~S");
Clazz.defineMethod(c$, "appendKey", 
function(sb, key){
return sb.append("\n").append(JU.PT.formatS(key, 27, 0, true, false));
}, "JU.SB,~S");
Clazz.defineMethod(c$, "toString", 
function(){
return (this.oc == null ? "" : this.oc.toString());
});
c$.fset0 = JU.P3.new3(555, 555, 1);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
