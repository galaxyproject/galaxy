Clazz.declarePackage("JV");
Clazz.load(["java.util.Hashtable", "JU.SB", "$.V3", "JU.Elements"], "JV.JC", ["JU.PT", "J.i18n.GT", "JU.Logger"], function(){
var c$ = Clazz.declareType(JV, "JC", null);
c$.getNBOTypeFromName = Clazz.defineMethod(c$, "getNBOTypeFromName", 
function(nboType){
var pt = ";AO;;;;PNAO;;NAO;;;PNHO;;NHO;;;PNBO;;NBO;;;PNLMO;NLMO;;MO;;;;NO;;;;;;;;;;PRNBO;RNBO;;;;;;;;".indexOf(";" + nboType + ";");
return (pt < 0 ? pt : Clazz.doubleToInt(pt / 6) + 31);
}, "~S");
c$.getCIPChiralityName = Clazz.defineMethod(c$, "getCIPChiralityName", 
function(flags){
switch (flags) {
case 13:
return "Z";
case 5:
return "z";
case 14:
return "E";
case 6:
return "e";
case 17:
return "M";
case 18:
return "P";
case 1:
return "R";
case 2:
return "S";
case 9:
return "r";
case 10:
return "s";
case 25:
return "m";
case 26:
return "p";
case 7:
return "?";
case 3:
case 0:
default:
return "";
}
}, "~N");
c$.getCIPRuleName = Clazz.defineMethod(c$, "getCIPRuleName", 
function(i){
return JV.JC.ruleNames[i];
}, "~N");
c$.getCIPChiralityCode = Clazz.defineMethod(c$, "getCIPChiralityCode", 
function(c){
switch ((c).charCodeAt(0)) {
case 90:
return 13;
case 122:
return 5;
case 69:
return 14;
case 101:
return 6;
case 82:
return 1;
case 83:
return 2;
case 114:
return 9;
case 115:
return 10;
case 63:
return 7;
default:
return 0;
}
}, "~S");
c$.fixOptimadeCall = Clazz.defineMethod(c$, "fixOptimadeCall", 
function(url){
var pt = url.indexOf("response_fields=") + 16;
var a = ",chemical_formula_descriptive,dimension_types,lattice_vectors,cartesian_site_positions,species_at_sites,species,";
if (pt < 16) {
var ptQ = url.indexOf("?");
url += (ptQ < 0 ? "?" : "&") + "response_fields=" + a.substring(1, a.length - 1);
} else {
var fields = "," + url.substring(pt, (url + "&").indexOf('&', pt)) + ",";
var flen = fields.length;
for (var i = 0, b = 0; i >= 0; i = b) {
b = a.indexOf(',', i + 1);
if (b < 0) break;
var k = a.substring(i, b + 1);
if (fields.indexOf(k) < 0) {
fields += k.substring(1);
}}
url = url.substring(0, pt) + fields.substring(1, fields.length - 1) + url.substring(pt + flen - 2);
}return url;
}, "~S");
c$.resolveDataBase = Clazz.defineMethod(c$, "resolveDataBase", 
function(database, id, format){
if (format == null) {
if ((format = JV.JC.databases.get(database.toLowerCase())) == null) return null;
var pt = id.indexOf("/");
if (pt < 0) {
if (database.equals("pubchem")) id = "name/" + id;
 else if (database.equals("nci")) id += "/file?format=sdf&get3d=true";
}if (format.startsWith("'")) {
pt = id.indexOf(".");
var n = (pt > 0 ? JU.PT.parseInt(id.substring(pt + 1)) : 0);
if (pt > 0) id = id.substring(0, pt);
format = JU.PT.rep(format, "%n", "" + n);
}} else if (id.indexOf(".") >= 0 && format.indexOf("%FILE.") >= 0) {
format = format.substring(0, format.indexOf("%FILE"));
}if (format.indexOf("%c") >= 0) for (var i = 1, n = id.length; i <= n; i++) if (format.indexOf("%c" + i) >= 0) format = JU.PT.rep(format, "%c" + i, id.substring(i - 1, i).toLowerCase());

return (format.indexOf("%FILE") >= 0 ? JU.PT.rep(format, "%FILE", id) : format.indexOf("%file") >= 0 ? JU.PT.rep(format, "%file", id.toLowerCase()) : format + id);
}, "~S,~S,~S");
c$.fixProtocol = Clazz.defineMethod(c$, "fixProtocol", 
function(name){
var isHttp = (name != null && name.indexOf("http") >= 0);
var newname = (name == null || !isHttp ? name : name.indexOf("http://www.rcsb.org/pdb/files/") == 0 ? JV.JC.resolveDataBase(name.indexOf("/ligand/") >= 0 ? "ligand" : "pdb", name.substring(name.lastIndexOf("/") + 1), null) : name.indexOf("http://www.ebi") == 0 || name.indexOf("http://rruff") == 0 || name.indexOf("http://pubchem") == 0 || name.indexOf("http://cactus") == 0 || name.indexOf("http://www.materialsproject") == 0 ? "https://" + name.substring(7) : name.indexOf("optimade") > 0 ? JV.JC.fixOptimadeCall(name) : name);
if (newname !== name) JU.Logger.info("JC.fixProtocol " + name + " --> " + newname);
return newname;
}, "~S");
c$.embedScript = Clazz.defineMethod(c$, "embedScript", 
function(s){
return "\n/**" + "**** Jmol Embedded Script ****" + " \n" + s + "\n**/";
}, "~S");
c$.getShapeVisibilityFlag = Clazz.defineMethod(c$, "getShapeVisibilityFlag", 
function(shapeID){
return 16 << Math.min(shapeID, 26);
}, "~N");
c$.shapeTokenIndex = Clazz.defineMethod(c$, "shapeTokenIndex", 
function(tok){
switch (tok) {
case 1153433601:
case 1073741859:
return 0;
case 1677721602:
case 659488:
return 1;
case 1613238294:
return 2;
case 1611141176:
return 3;
case 659482:
return 4;
case 1825200146:
return 5;
case 1745489939:
case 537006096:
return 6;
case 1112152076:
return 7;
case 1112152070:
return 8;
case 1114249217:
return 9;
case 1112152078:
return 10;
case 1112152066:
return 11;
case 1649022989:
return 12;
case 1112152071:
return 13;
case 1112152073:
return 14;
case 1112152074:
return 15;
case 1112150019:
return 16;
case 135175:
return 17;
case 135198:
return 18;
case 1112150021:
return 19;
case 1112150020:
return 20;
case 1275203608:
return 21;
case 135174:
return 23;
case 135176:
return 22;
case 135180:
return 24;
case 134353926:
return 25;
case 135182:
return 26;
case 1073877010:
return 27;
case 1073877011:
return 28;
case 135188:
return 29;
case 135190:
return 30;
case 537022465:
return 31;
case 1611272194:
return 34;
case 1812599299:
return 32;
case 1814695966:
return 33;
case 544771:
return 35;
case 1611272202:
return 36;
}
return -1;
}, "~N");
c$.getShapeClassName = Clazz.defineMethod(c$, "getShapeClassName", 
function(shapeID, isRenderer){
if (shapeID < 0) return JV.JC.shapeClassBases[~shapeID];
return "J." + (isRenderer ? "render" : "shape") + (shapeID >= 9 && shapeID < 16 ? "bio." : shapeID >= 16 && shapeID < 23 ? "special." : shapeID >= 24 && shapeID < 30 ? "surface." : shapeID == 23 ? "cgo." : ".") + JV.JC.shapeClassBases[shapeID];
}, "~N,~B");
c$.getEchoName = Clazz.defineMethod(c$, "getEchoName", 
function(type){
return JV.JC.echoNames[type];
}, "~N");
c$.setZPosition = Clazz.defineMethod(c$, "setZPosition", 
function(offset, pos){
return (offset & -49) | pos;
}, "~N,~N");
c$.setPointer = Clazz.defineMethod(c$, "setPointer", 
function(offset, pointer){
return (offset & -4) | pointer;
}, "~N,~N");
c$.getPointer = Clazz.defineMethod(c$, "getPointer", 
function(offset){
return offset & 3;
}, "~N");
c$.getPointerName = Clazz.defineMethod(c$, "getPointerName", 
function(pointer){
return ((pointer & 1) == 0 ? "" : (pointer & 2) > 0 ? "background" : "on");
}, "~N");
c$.isOffsetAbsolute = Clazz.defineMethod(c$, "isOffsetAbsolute", 
function(offset){
return ((offset & 64) != 0);
}, "~N");
c$.getOffset = Clazz.defineMethod(c$, "getOffset", 
function(xOffset, yOffset, isAbsolute){
xOffset = Math.min(Math.max(xOffset, -500), 500);
yOffset = (Math.min(Math.max(yOffset, -500), 500));
var offset = ((xOffset & 1023) << 21) | ((yOffset & 1023) << 11) | (isAbsolute ? 64 : 0);
if (offset == JV.JC.LABEL_DEFAULT_OFFSET) offset = 0;
 else if (!isAbsolute && (xOffset == 0 || yOffset == 0)) offset |= 256;
return offset;
}, "~N,~N,~B");
c$.getXOffset = Clazz.defineMethod(c$, "getXOffset", 
function(offset){
if (offset == 0) return 4;
var x = (offset >> 21) & 1023;
x = (x > 500 ? x - 1023 - 1 : x);
return x;
}, "~N");
c$.getYOffset = Clazz.defineMethod(c$, "getYOffset", 
function(offset){
if (offset == 0) return 4;
var y = (offset >> 11) & 1023;
return (y > 500 ? y - 1023 - 1 : y);
}, "~N");
c$.getAlignment = Clazz.defineMethod(c$, "getAlignment", 
function(offset){
return (offset & 12);
}, "~N");
c$.setHorizAlignment = Clazz.defineMethod(c$, "setHorizAlignment", 
function(offset, hAlign){
return (offset & -13) | hAlign;
}, "~N,~N");
c$.getHorizAlignmentName = Clazz.defineMethod(c$, "getHorizAlignmentName", 
function(align){
return JV.JC.hAlignNames[(align >> 2) & 3];
}, "~N");
c$.isSmilesCanonical = Clazz.defineMethod(c$, "isSmilesCanonical", 
function(options){
return (options != null && JU.PT.isOneOf(options.toLowerCase(), ";/cactvs///;/cactus///;/nci///;/canonical///;"));
}, "~S");
c$.getServiceCommand = Clazz.defineMethod(c$, "getServiceCommand", 
function(script){
return (script.length < 7 ? -1 : ("JSPECVIPEAKS: SELECT:JSVSTR:H1SIMULC13SIMUNBO:MODNBO:RUNNBO:VIENBO:SEANBO:CONNONESIM").indexOf(script.substring(0, 7).toUpperCase()));
}, "~S");
c$.getUnitIDFlags = Clazz.defineMethod(c$, "getUnitIDFlags", 
function(type){
var i = 14;
if (type.indexOf("-") == 0) {
if (type.indexOf("m") > 0) i |= 1;
if (type.indexOf("a") < 0) i ^= 4;
if (type.indexOf("t") > 0) i |= 16;
}return i;
}, "~S");
c$.getBoolName = Clazz.defineMethod(c$, "getBoolName", 
function(g){
return JV.JC.globalBooleans[g];
}, "~N");
c$.isSpaceGroupInfoKey = Clazz.defineMethod(c$, "isSpaceGroupInfoKey", 
function(key){
return (key.indexOf("nitCell") >= 0 || key.equals("coordinatesAreFractional") || key.startsWith("spaceGroup") || key.indexOf("ymmet") >= 0 || key.startsWith("lattice") || key.startsWith("intlTable"));
}, "~S");
c$.getMenuScript = Clazz.defineMethod(c$, "getMenuScript", 
function(type){
if (type === "openPDB") {
return "var x__id__ = _modelTitle; if (x__id__.length != 4) { x__id__ = '1crn'};x__id__ = prompt('" + J.i18n.GT.$("Enter a four-digit PDB model ID or \"=\" and a three-digit ligand ID") + "',x__id__);if (!x__id__) { quit }; load @{'=' + x__id__}";
}if (type === "openMOL") {
return "var x__id__ = _smilesString; if (!x__id__) { x__id__ = 'tylenol'};x__id__ = prompt('" + J.i18n.GT.$("Enter the name or identifier (SMILES, InChI, CAS) of a compound. Preface with \":\" to load from PubChem; otherwise Jmol will use the NCI/NIH Resolver.") + "',x__id__);if (!x__id__) { quit }; load @{(x__id__[1]==':' ? x__id__ : '$' + x__id__)}";
}return null;
}, "~S");
c$.axisLabels =  Clazz.newArray(-1, ["+X", "+Y", "+Z", null, null, null, "a", "b", "c", "X", "Y", "Z", null, null, null, "X", null, "Z", null, "(Y)", null]);
c$.axesTypes =  Clazz.newArray(-1, ["a", "b", "c", "x", "y", "z"]);
c$.ruleNames =  Clazz.newArray(-1, ["", "1a", "1b", "2", "3", "4a", "4b", "4c", "5", "6"]);
c$.databaseArray =  Clazz.newArray(-1, ["itatable", "https://www.cryst.ehu.es/cgi-bin/cryst/programs/nph-getgen?gnum=$FILE&what=gp&list=Standard%2FDefault+Setting", "itadiagram", "https://onlinelibrary.wiley.com/iucr/itc/Ac/ch2o3v0001/sgtable2o3o%FILE", "aflowbin", "http://aflowlib.mems.duke.edu/users/jmolers/binary_new/%FILE.aflow_binary", "aflowlib", "https://aflow.org/p/%FILE.cif", "aflowpro", "$aflowlib", "ams", "'https://rruff.geo.arizona.edu/AMS/viewJmol.php?'+(0+'%file'==0? 'mineral':('%file'.length==7? 'amcsd':'id'))+'=%file&action=showcif#_DOCACHE_'", "dssr", "http://dssr-jmol.x3dna.org/report.php?id=%FILE&opts=--json=ebi", "dssrModel", "http://dssr-jmol.x3dna.org/report.php?POST?opts=--json=ebi&model=", "iucr", "http://scripts.iucr.org/cgi-bin/sendcif_yard?%FILE", "cod", "http://www.crystallography.net/cod/cif/%c1/%c2%c3/%c4%c5/%FILE.cif", "nmr", "https://www.nmrdb.org/new_predictor?POST?molfile=", "nmrdb", "https://www.nmrdb.org/service/predictor?POST?molfile=", "nmrdb13", "https://www.nmrdb.org/service/jsmol13c?POST?molfile=", "magndata", "http://webbdcrista1.ehu.es/magndata/mcif/%FILE.mcif", "rna3d", "http://rna.bgsu.edu/rna3dhub/%TYPE/download/%FILE", "mmtf", "https://mmtf.rcsb.org/v1.0/full/%FILE", "bcif", "https://models.rcsb.org/%file.bcif", "chebi", "https://www.ebi.ac.uk/chebi/saveStructure.do?defaultImage=true&chebiId=%file%2D%", "ligand", "https://files.rcsb.org/ligands/download/%FILE.cif", "mp", "https://www.materialsproject.org/materials/mp-%FILE/cif#_DOCACHE_", "nci", "https://cactus.nci.nih.gov/chemical/structure/", "pdb", "https://files.rcsb.org/download/%FILE.pdb", "pdb0", "https://files.rcsb.org/download/%FILE.pdb", "pdbe", "https://www.ebi.ac.uk/pdbe/entry-files/download/%FILE.cif", "pdbe2", "https://www.ebi.ac.uk/pdbe/static/entry/%FILE_updated.cif", "pubchem", "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/%FILE/SDF?record_type=3d", "map", "https://www.ebi.ac.uk/pdbe/api/%TYPE/%FILE?pretty=false&metadata=true", "pdbemap", "https://www.ebi.ac.uk/pdbe/coordinates/files/%file.ccp4", "pdbemapdiff", "https://www.ebi.ac.uk/pdbe/coordinates/files/%file_diff.ccp4", "pdbemapserver", "https://www.ebi.ac.uk/pdbe/densities/x-ray/%file/box/0,0,0/0,0,0?detail=6&space=cartesian&encoding=bcif", "pdbemapdiffserver", "https://www.ebi.ac.uk/pdbe/densities/x-ray/%file/box/0,0,0/0,0,0?detail=6&space=cartesian&encoding=bcif&diff=1", "emdbmap", "https://www.ebi.ac.uk/pdbe/densities/emd/emd-%file/cell?detail=6&space=cartesian&encoding=bcif", "emdbquery", "https://www.ebi.ac.uk/emdb/api/search/fitted_pdbs:%file?fl=emdb_id,map_contour_level_value&wt=csv", "emdbmapserver", "https://www.ebi.ac.uk/pdbe/densities/emd/emd-%file/box/0,0,0/0,0,0?detail=6&space=cartesian&encoding=bcif", "xxxresolverResolver", "https://chemapps.stolaf.edu/resolver", "smiles2d", "https://cirx.chemicalcreatures.com/chemical/structure/%FILE/file?format=sdf&get3d=false", "smiles3d", "https://cirx.chemicalcreatures.com/chemical/structure/%FILE/file?format=sdf&get3d=true"]);
c$.databases =  new java.util.Hashtable();
{
for (var i = 0; i < JV.JC.databaseArray.length; i += 2) {
var target = JV.JC.databaseArray[i + 1];
if (target.charAt(0) == '$') {
target = JV.JC.databases.get(target.substring(1));
}JV.JC.databases.put(JV.JC.databaseArray[i].toLowerCase(), target);
}
}c$.majorVersion = null;
{
var tmpVersion = null;
var tmpDate = null;
{
tmpVersion = Jmol.___JmolVersion; tmpDate = Jmol.___JmolDate;
}if (tmpDate != null) {
tmpDate = tmpDate.substring(7, 23);
}JV.JC.version = (tmpVersion != null ? tmpVersion : "(Unknown_version)");
JV.JC.majorVersion = (tmpVersion != null ? tmpVersion : "(Unknown_version)");
JV.JC.date = (tmpDate != null ? tmpDate : "(Unknown_date)");
var v = -1;
try {
var s = JV.JC.version;
var major = "";
var i = s.indexOf(".");
if (i < 0) {
v = 100000 * Integer.parseInt(s);
s = null;
}if (s != null) {
v = 100000 * Integer.parseInt(major = s.substring(0, i));
s = s.substring(i + 1);
i = s.indexOf(".");
if (i < 0) {
v += 1000 * Integer.parseInt(s);
s = null;
}if (s != null) {
var m = s.substring(0, i);
major += "." + m;
JV.JC.majorVersion = major;
v += 1000 * Integer.parseInt(m);
s = s.substring(i + 1);
i = s.indexOf("_");
if (i >= 0) s = s.substring(0, i);
i = s.indexOf(" ");
if (i >= 0) s = s.substring(0, i);
v += Integer.parseInt(s);
}}} catch (e) {
if (Clazz.exceptionOf(e,"NumberFormatException")){
} else {
throw e;
}
}
JV.JC.versionInt = v;
}c$.center = JU.V3.new3(0, 0, 0);
c$.axisX = JU.V3.new3(1, 0, 0);
c$.axisY = JU.V3.new3(0, 1, 0);
c$.axisZ = JU.V3.new3(0, 0, 1);
c$.axisNX = JU.V3.new3(-1, 0, 0);
c$.axisNY = JU.V3.new3(0, -1, 0);
c$.axisNZ = JU.V3.new3(0, 0, -1);
c$.unitAxisVectors =  Clazz.newArray(-1, [JV.JC.axisX, JV.JC.axisY, JV.JC.axisZ, JV.JC.axisNX, JV.JC.axisNY, JV.JC.axisNZ]);
c$.altArgbsCpk =  Clazz.newIntArray(-1, [0xFFFF1493, 0xFFBFA6A6, 0xFFFFFF30, 0xFF57178F, 0xFFFFFFC0, 0xFFFFFFA0, 0xFFD8D8D8, 0xFF505050, 0xFF404040, 0xFF105050]);
c$.FORMAL_CHARGE_COLIX_RED = JU.Elements.elementSymbols.length + JV.JC.altArgbsCpk.length;
c$.argbsFormalCharge =  Clazz.newIntArray(-1, [0xFFFF0000, 0xFFFF4040, 0xFFFF8080, 0xFFFFC0C0, 0xFFFFFFFF, 0xFFD8D8FF, 0xFFB4B4FF, 0xFF9090FF, 0xFF6C6CFF, 0xFF4848FF, 0xFF2424FF, 0xFF0000FF]);
c$.PARTIAL_CHARGE_COLIX_RED = JV.JC.FORMAL_CHARGE_COLIX_RED + JV.JC.argbsFormalCharge.length;
c$.argbsRwbScale =  Clazz.newIntArray(-1, [0xFFFF0000, 0xFFFF1010, 0xFFFF2020, 0xFFFF3030, 0xFFFF4040, 0xFFFF5050, 0xFFFF6060, 0xFFFF7070, 0xFFFF8080, 0xFFFF9090, 0xFFFFA0A0, 0xFFFFB0B0, 0xFFFFC0C0, 0xFFFFD0D0, 0xFFFFE0E0, 0xFFFFFFFF, 0xFFE0E0FF, 0xFFD0D0FF, 0xFFC0C0FF, 0xFFB0B0FF, 0xFFA0A0FF, 0xFF9090FF, 0xFF8080FF, 0xFF7070FF, 0xFF6060FF, 0xFF5050FF, 0xFF4040FF, 0xFF3030FF, 0xFF2020FF, 0xFF1010FF, 0xFF0000FF]);
c$.PARTIAL_CHARGE_RANGE_SIZE = JV.JC.argbsRwbScale.length;
c$.argbsRoygbScale =  Clazz.newIntArray(-1, [0xFFFF0000, 0xFFFF2000, 0xFFFF4000, 0xFFFF6000, 0xFFFF8000, 0xFFFFA000, 0xFFFFC000, 0xFFFFE000, 0xFFFFF000, 0xFFFFFF00, 0xFFF0F000, 0xFFE0FF00, 0xFFC0FF00, 0xFFA0FF00, 0xFF80FF00, 0xFF60FF00, 0xFF40FF00, 0xFF20FF00, 0xFF00FF00, 0xFF00FF20, 0xFF00FF40, 0xFF00FF60, 0xFF00FF80, 0xFF00FFA0, 0xFF00FFC0, 0xFF00FFE0, 0xFF00FFFF, 0xFF00E0FF, 0xFF00C0FF, 0xFF00A0FF, 0xFF0080FF, 0xFF0060FF, 0xFF0040FF, 0xFF0020FF, 0xFF0000FF]);
c$.predefinedVariable =  Clazz.newArray(-1, ["@_1H _H & !(_2H,_3H)", "@_12C _C & !(_13C,_14C)", "@_14N _N & !(_15N)", "@solvent water, (_g>=45 & _g<48)", "@ligand _g=0|!(_g<46,protein,nucleic,water)", "@turn structure=1", "@sheet structure=2", "@helix structure=3", "@helix310 substructure=7", "@helixalpha substructure=8", "@helixpi substructure=9", "@bulges within(dssr,'bulges')", "@coaxStacks within(dssr,'coaxStacks')", "@hairpins within(dssr,'hairpins')", "@hbonds within(dssr,'hbonds')", "@helices within(dssr,'helices')", "@iloops within(dssr,'iloops')", "@isoCanonPairs within(dssr,'isoCanonPairs')", "@junctions within(dssr,'junctions')", "@kissingLoops within(dssr,'kissingLoops')", "@multiplets within(dssr,'multiplets')", "@nonStack within(dssr,'nonStack')", "@nts within(dssr,'nts')", "@pairs within(dssr,'pairs')", "@ssSegments within(dssr,'ssSegments')", "@stacks within(dssr,'stacks')", "@stems within(dssr,'stems')"]);
c$.predefinedStatic =  Clazz.newArray(-1, ["@amino _g>0 & _g<=23", "@acidic asp,glu", "@basic arg,his,lys", "@charged acidic,basic", "@negative acidic", "@positive basic", "@neutral amino&!(acidic,basic)", "@polar amino&!hydrophobic", "@peptide protein&within(chain,monomer>1)&!within(chain,monomer>12)", "@cyclic his,phe,pro,trp,tyr", "@acyclic amino&!cyclic", "@aliphatic ala,gly,ile,leu,val", "@aromatic his,phe,trp,tyr", "@cystine within(group,(cys,cyx)&atomname=sg&connected((cys,cyx)&atomname=sg))", "@buried ala,cys,ile,leu,met,phe,trp,val", "@surface amino&!buried", "@hydrophobic ala,gly,ile,leu,met,phe,pro,trp,tyr,val", "@mainchain backbone", "@small ala,gly,ser", "@medium asn,asp,cys,pro,thr,val", "@large arg,glu,gln,his,ile,leu,lys,met,phe,trp,tyr", "@c nucleic & ([C] or [DC] or within(group,_a=42))", "@g nucleic & ([G] or [DG] or within(group,_a=43))", "@cg c,g", "@a nucleic & ([A] or [DA] or within(group,_a=44))", "@t nucleic & ([T] or [DT] or within(group,_a=45 | _a=49))", "@at a,t", "@i nucleic & ([I] or [DI] or within(group,_a=46) & !g)", "@u nucleic & ([U] or [DU] or within(group,_a=47) & !t)", "@tu nucleic & within(group,_a=48)", "@ions _g>=46&_g<48", "@alpha _a=2", "@_bb protein&(_a>=1&_a<6|_a=64) | nucleic&(_a>=6&_a<14|_a>=73&&_a<=79||_a==99||_a=100)", "@backbone _bb | _H && connected(single, _bb)", "@spine protein&_a>=1&_a<4|nucleic&(_a>=6&_a<11|_a=13)", "@sidechain (protein,nucleic) & !backbone", "@base nucleic & !backbone", "@dynamic_flatring search('[a]')", "@nonmetal _H,_He,_B,_C,_N,_O,_F,_Ne,_Si,_P,_S,_Cl,_Ar,_As,_Se,_Br,_Kr,_Te,_I,_Xe,_At,_Rn", "@metal !nonmetal && !_Xx", "@alkaliMetal _Li,_Na,_K,_Rb,_Cs,_Fr", "@alkalineEarth _Be,_Mg,_Ca,_Sr,_Ba,_Ra", "@nobleGas _He,_Ne,_Ar,_Kr,_Xe,_Rn", "@metalloid _B,_Si,_Ge,_As,_Sb,_Te", "@transitionMetal elemno>=21&elemno<=30|elemno=57|elemno=89|elemno>=39&elemno<=48|elemno>=72&elemno<=80|elemno>=104&elemno<=112", "@lanthanide elemno>57&elemno<=71", "@actinide elemno>89&elemno<=103"]);
c$.shapeClassBases =  Clazz.newArray(-1, ["Balls", "Sticks", "Hsticks", "Sssticks", "Struts", "Labels", "Measures", "Stars", "Halos", "Backbone", "Trace", "Cartoon", "Strands", "MeshRibbon", "Ribbons", "Rockets", "Dots", "Dipoles", "Vectors", "GeoSurface", "Ellipsoids", "Polyhedra", "Draw", "CGO", "Isosurface", "Contact", "LcaoCartoon", "MolecularOrbital", "NBO", "Pmesh", "Plot3D", "Echo", "Bbcage", "Uccage", "Axes", "Hover", "Frank"]);
{
{
}}c$.LABEL_DEFAULT_OFFSET = 8396800;
c$.echoNames =  Clazz.newArray(-1, ["top", "bottom", "middle", "xy", "xyz"]);
c$.hAlignNames =  Clazz.newArray(-1, ["", "left", "center", "right"]);
c$.READER_NOT_FOUND = "File reader was not found:";
c$.globalBooleans =  Clazz.newArray(-1, ["someModelsHaveFractionalCoordinates", "someModelsHaveSymmetry", "someModelsHaveUnitcells", "someModelsHaveCONECT", "isPDB", "someModelsHaveDomains", "someModelsHaveValidations", "isSupercell", "someModelsHaveAromaticBonds", "someModelsAreModulated"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
