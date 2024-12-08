Clazz.declarePackage("J.adapter.readers.cif");
Clazz.load(["J.adapter.readers.cif.MSRdr"], "J.adapter.readers.cif.MSCifParser", ["JU.M3", "$.Matrix", "$.PT", "J.adapter.readers.cif.Cif2DataParser"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.field = null;
this.comSSMat = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif, "MSCifParser", J.adapter.readers.cif.MSRdr);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.adapter.readers.cif.MSCifParser, []);
});
Clazz.defineMethod(c$, "processEntry", 
function(){
var cr = this.cr;
if (cr.key.equals("_cell_commen_t_section_1")) {
this.isCommensurate = true;
this.commensurateSection1 = cr.parseIntField();
}if (cr.key.startsWith("_cell_commen_supercell_matrix")) {
this.isCommensurate = true;
if (this.comSSMat == null) this.comSSMat = JU.M3.newM3(null);
var tokens = JU.PT.split(cr.key, "_");
var r = cr.parseIntStr(tokens[tokens.length - 2]);
var c = cr.parseIntStr(tokens[tokens.length - 1]);
if (r > 0 && c > 0) this.comSSMat.setElement(r - 1, c - 1, cr.parseFloatField());
}});
Clazz.defineMethod(c$, "processLoopBlock", 
function(){
var cr = this.cr;
var key = cr.key;
if (key.equals("_cell_subsystem_code")) return this.processSubsystemLoopBlock();
if (!key.startsWith("_cell_wave") && !key.contains("fourier") && !key.contains("legendre") && !key.contains("_special_func")) {
if (key.contains("crenel_ortho")) cr.appendLoadNote("WARNING: Orthogonalized non-Legendre functions not supported.\nThe following block has been ignored. Use Legendre functions instead.\n\n" + cr.cifParser.skipLoop(true) + "=================================\n");
return 0;
}if (cr.asc.iSet < 0) cr.asc.newAtomSet();
cr.parseLoopParametersFor("_atom_site", J.adapter.readers.cif.MSCifParser.modulationFields);
var tok;
while (cr.cifParser.getData()) {
var ignore = false;
var type_id = null;
var atomLabel = null;
var axis = null;
var pt =  Clazz.newDoubleArray(-1, [NaN, NaN, NaN]);
var q = null;
var c = NaN;
var w = NaN;
var fid = null;
var n = cr.cifParser.getColumnCount();
var sep = "_";
for (var i = 0; i < n; ++i) {
switch (tok = this.fieldProperty(cr, i)) {
case 0:
pt[0] = pt[1] = pt[2] = 0;
type_id = "F_";
fid = this.field;
sep = "";
break;
case 1:
cr.haveCellWaveVector = true;
type_id = "W_" + this.field;
sep = "";
break;
case 41:
case 42:
case 43:
pt[0] = pt[1] = pt[2] = 0;
sep = "";
case 14:
case 26:
case 51:
case 36:
case 44:
case 45:
case 46:
switch (tok) {
case 41:
case 42:
case 43:
fid = "?id" + this.field;
pt[2] = 1;
sep = "_";
continue;
case 44:
case 45:
case 46:
atomLabel = axis = "*";
sep = "_id";
type_id = J.adapter.readers.cif.MSCifParser.modulationFields[tok].substring(11, 12).toUpperCase();
break;
case 14:
case 26:
case 51:
case 36:
type_id = J.adapter.readers.cif.MSCifParser.modulationFields[tok].substring(11, 12).toUpperCase();
break;
}
type_id += sep + this.field;
break;
case 47:
type_id = "J_O";
pt[0] = pt[2] = 1;
axis = "0";
atomLabel = this.field;
break;
case 31:
type_id = "O_0";
axis = "0";
atomLabel = this.field;
break;
case 19:
type_id = "D_S";
axis = "0";
atomLabel = this.field;
break;
case 56:
type_id = "M_T";
axis = "0";
atomLabel = this.field;
break;
case 62:
type_id = "D_L";
atomLabel = this.field;
break;
case 66:
type_id = "U_L";
atomLabel = this.field;
break;
case 70:
type_id = "O_L";
atomLabel = this.field;
break;
case 12:
case 25:
case 49:
case 34:
atomLabel = this.field;
break;
case 13:
case 50:
case 63:
axis = this.field;
if (this.modAxes != null && this.modAxes.indexOf(axis.toUpperCase()) < 0) ignore = true;
break;
case 67:
case 35:
axis = this.field.toUpperCase();
break;
case 8:
q = J.adapter.readers.cif.Cif2DataParser.getArrayFromStringList(this.field, this.modDim);
break;
default:
var f = this.parseDouble(this.field);
switch (tok) {
case 65:
case 72:
case 69:
pt[0] = f;
if (f != 0) pt[2] = 0;
break;
case 32:
case 28:
case 16:
case 53:
case 38:
case 78:
case 74:
case 76:
pt[2] = 0;
case 2:
case 5:
case 20:
case 57:
pt[0] = f;
break;
case 9:
if (q == null) q =  Clazz.newDoubleArray (this.modDim, 0);
q[0] = f;
break;
case 10:
if (q == null) q =  Clazz.newDoubleArray (this.modDim, 0);
q[1] = f;
break;
case 11:
if (q == null) q =  Clazz.newDoubleArray (this.modDim, 0);
q[2] = f;
break;
case 17:
case 29:
case 54:
case 39:
pt[0] = f;
pt[2] = 1;
break;
case 71:
case 75:
axis = "0";
case 64:
case 68:
case 3:
case 6:
case 27:
case 18:
case 30:
case 55:
case 40:
case 33:
case 21:
case 58:
case 48:
case 15:
case 52:
case 37:
case 73:
case 77:
pt[1] = f;
break;
case 4:
case 7:
case 22:
case 59:
pt[2] = f;
break;
case 23:
case 60:
c = f;
break;
case 24:
case 61:
w = f;
break;
}
break;
}
}
if (ignore || type_id == null && q == null || atomLabel != null && !atomLabel.equals("*") && cr.rejectAtomName(atomLabel)) continue;
var ok = true;
if (q != null) {
for (var j = 0, nzero = q.length; j < q.length; j++) if (Double.isNaN(q[j]) || q[j] > 1e100 || q[j] == 0 && --nzero == 0) {
ok = false;
}
if (!ok) continue;
this.addMod(key, "F_coefs_", fid, q);
pt[0] = NaN;
}for (var j = 0, nzero = pt.length; j < pt.length; j++) if (Double.isNaN(pt[j]) || pt[j] > 1e100 || pt[j] == 0 && --nzero == 0) {
ok = false;
break;
}
if (!ok) continue;
var tchar = type_id.charAt(0);
switch ((tchar).charCodeAt(0)) {
case 67:
case 68:
case 79:
case 77:
case 85:
case 74:
if (atomLabel == null || axis == null && tchar != 'O') continue;
if (type_id.equals("D_S") || type_id.equals("M_T")) {
if (Double.isNaN(c) || Double.isNaN(w)) continue;
if (pt[0] != 0) this.addMod(key, type_id + "#x;" + atomLabel, fid,  Clazz.newDoubleArray(-1, [c, w, pt[0]]));
if (pt[1] != 0) this.addMod(key, type_id + "#y;" + atomLabel, fid,  Clazz.newDoubleArray(-1, [c, w, pt[1]]));
if (pt[2] != 0) this.addMod(key, type_id + "#z;" + atomLabel, fid,  Clazz.newDoubleArray(-1, [c, w, pt[2]]));
continue;
}if (type_id.indexOf("_L") == 1) {
if (type_id.startsWith("U")) type_id += Clazz.doubleToInt(pt[1]);
 else axis += Clazz.doubleToInt(pt[1]);
}type_id += "#" + (axis == null ? "*" : axis) + ";" + atomLabel;
break;
}
this.addMod(key, type_id, fid, pt);
}
return 1;
});
Clazz.defineMethod(c$, "addMod", 
function(key, id, fid, params){
var k = (fid == null ? id : id + fid);
this.addModulation(null, k, params, -1);
}, "~S,~S,~S,~A");
Clazz.defineMethod(c$, "processSubsystemLoopBlock", 
function(){
var cr = this.cr;
cr.parseLoopParameters(null);
while (cr.cifParser.getData()) {
this.fieldProperty(cr, 0);
var id = this.field;
this.addSubsystem(id, this.getSparseMatrix(cr, "_w_", 1, 3 + this.modDim));
}
return 1;
});
Clazz.defineMethod(c$, "getSparseMatrix", 
function(cr, term, i, dim){
var m =  new JU.Matrix(null, dim, dim);
var a = m.getArray();
var key;
var p;
var n = cr.cifParser.getColumnCount();
for (; i < n; ++i) {
if ((p = this.fieldProperty(cr, i)) < 0 || !(key = cr.cifParser.getColumnName(p)).contains(term)) continue;
var tokens = JU.PT.split(key, "_");
var r = cr.parseIntStr(tokens[tokens.length - 2]);
var c = cr.parseIntStr(tokens[tokens.length - 1]);
if (r > 0 && c > 0) a[r - 1][c - 1] = this.parseDouble(this.field);
}
return m;
}, "J.adapter.readers.cif.CifReader,~S,~N,~N");
Clazz.defineMethod(c$, "parseDouble", 
function(field){
var d = this.cr.parseFloatStr(field);
return this.fixDouble(d);
}, "~S");
Clazz.defineMethod(c$, "fixDouble", 
function(d){
return d;
}, "~N");
Clazz.defineMethod(c$, "fieldProperty", 
function(cr, i){
return ((this.field = cr.cifParser.getColumnData(i)).length > 0 && this.field.charAt(0) != '\0' ? cr.col2key[i] : -1);
}, "J.adapter.readers.cif.CifReader,~N");
c$.modulationFields =  Clazz.newArray(-1, ["*_fourier_wave_vector_seq_id", "_cell_wave_vector_seq_id", "_cell_wave_vector_x", "_cell_wave_vector_y", "_cell_wave_vector_z", "*_fourier_wave_vector_x", "*_fourier_wave_vector_y", "*_fourier_wave_vector_z", "*_fourier_wave_vector_q_coeff", "*_fourier_wave_vector_q1_coeff", "*_fourier_wave_vector_q2_coeff", "*_fourier_wave_vector_q3_coeff", "*_displace_fourier_atom_site_label", "*_displace_fourier_axis", "*_displace_fourier_wave_vector_seq_id", "*_displace_fourier_param_cos", "*_displace_fourier_param_sin", "*_displace_fourier_param_modulus", "*_displace_fourier_param_phase", "*_displace_special_func_atom_site_label", "*_displace_special_func_sawtooth_ax", "*_displace_special_func_sawtooth_ay", "*_displace_special_func_sawtooth_az", "*_displace_special_func_sawtooth_c", "*_displace_special_func_sawtooth_w", "*_occ_fourier_atom_site_label", "*_occ_fourier_wave_vector_seq_id", "*_occ_fourier_param_cos", "*_occ_fourier_param_sin", "*_occ_fourier_param_modulus", "*_occ_fourier_param_phase", "*_occ_special_func_atom_site_label", "*_occ_special_func_crenel_c", "*_occ_special_func_crenel_w", "*_u_fourier_atom_site_label", "*_u_fourier_tens_elem", "*_u_fourier_wave_vector_seq_id", "*_u_fourier_param_cos", "*_u_fourier_param_sin", "*_u_fourier_param_modulus", "*_u_fourier_param_phase", "*_displace_fourier_id", "*_occ_fourier_id", "*_u_fourier_id", "*_displace_fourier_param_id", "*_occ_fourier_param_id", "*_u_fourier_param_id", "*_occ_fourier_absolute_site_label", "*_occ_fourier_absolute", "*_moment_fourier_atom_site_label", "*_moment_fourier_axis", "*_moment_fourier_wave_vector_seq_id", "*_moment_fourier_param_cos", "*_moment_fourier_param_sin", "*_moment_fourier_param_modulus", "*_moment_fourier_param_phase", "*_moment_special_func_atom_site_label", "*_moment_special_func_sawtooth_ax", "*_moment_special_func_sawtooth_ay", "*_moment_special_func_sawtooth_az", "*_moment_special_func_sawtooth_c", "*_moment_special_func_sawtooth_w", "*_displace_legendre_atom_site_label", "*_displace_legendre_axis", "*_displace_legendre_param_order", "*_displace_legendre_param_coeff", "*_u_legendre_atom_site_label", "*_u_legendre_tens_elem", "*_u_legendre_param_order", "*_u_legendre_param_coeff", "*_occ_legendre_atom_site_label", "*_occ_legendre_param_order", "*_occ_legendre_param_coeff", "*_displace_fourier_cos", "*_displace_fourier_sin", "*_occ_fourier_cos", "*_occ_fourier_sin", "*_u_fourier_cos", "*_u_fourier_sin"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
