Clazz.declarePackage("J.adapter.smarter");
Clazz.load(null, "J.adapter.smarter.Resolver", ["java.io.BufferedInputStream", "java.util.StringTokenizer", "JU.LimitedLineReader", "$.PT", "$.Rdr", "J.adapter.smarter.AtomSetCollectionReader", "$.SmarterJmolAdapter", "J.api.Interface", "JU.Logger", "JV.JC"], function(){
var c$ = Clazz.declareType(J.adapter.smarter, "Resolver", null);
c$.getReaderClassBase = Clazz.defineMethod(c$, "getReaderClassBase", 
function(type){
var name = type + "Reader";
if (type.startsWith("Xml")) return "J.adapter.readers." + "xml." + name;
var key = ";" + type + ";";
for (var i = 1; i < J.adapter.smarter.Resolver.readerSets.length; i += 2) if (J.adapter.smarter.Resolver.readerSets[i].indexOf(key) >= 0) return "J.adapter.readers." + J.adapter.smarter.Resolver.readerSets[i - 1] + name;

return "J.adapter.readers." + "???." + name;
}, "~S");
c$.getFileType = Clazz.defineMethod(c$, "getFileType", 
function(br){
try {
return J.adapter.smarter.Resolver.determineAtomSetCollectionReader(br, null);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "java.io.BufferedReader");
c$.getAtomCollectionReader = Clazz.defineMethod(c$, "getAtomCollectionReader", 
function(fullName, type, readerOrDocument, htParams, ptFile){
var readerName;
fullName = J.adapter.smarter.Resolver.fixDOSName(fullName);
var errMsg = null;
if (type == null && htParams != null) {
type = J.adapter.smarter.Resolver.getFileTypefromFilter(htParams.get("filter"));
}if (type != null) {
readerName = J.adapter.smarter.Resolver.getReaderFromType(type);
if (readerName == null) readerName = J.adapter.smarter.Resolver.getReaderFromType("Xml" + type);
if (readerName == null) errMsg = "unrecognized file format type " + type + " file=" + fullName;
 else JU.Logger.info("The Resolver assumes " + readerName + " file=" + fullName);
} else {
readerName = J.adapter.smarter.Resolver.determineAtomSetCollectionReader(readerOrDocument, htParams);
if (readerName.charAt(0) == '\n') {
type = (htParams == null ? null : htParams.get("defaultType"));
if (type != null) {
type = J.adapter.smarter.Resolver.getReaderFromType(type);
if (type != null) readerName = type;
}}if (readerName.charAt(0) == '\n') errMsg = "unrecognized file format for file\n" + fullName + "\n" + J.adapter.smarter.Resolver.split(readerName, 50);
 else if (readerName.equals("spt")) errMsg = "NOTE: file recognized as a script file: " + fullName + "\n";
 else if (!fullName.equals("ligand")) JU.Logger.info("The Resolver thinks " + readerName);
}if (errMsg != null) {
J.adapter.smarter.SmarterJmolAdapter.close(readerOrDocument);
return errMsg;
}htParams.put("ptFile", Integer.$valueOf(ptFile));
if (ptFile <= 0) htParams.put("readerName", readerName);
return J.adapter.smarter.Resolver.getReader(readerName, htParams);
}, "~S,~S,~O,java.util.Map,~N");
c$.getReader = Clazz.defineMethod(c$, "getReader", 
function(readerName, htParams){
var rdr = null;
var className = null;
var err = null;
className = J.adapter.smarter.Resolver.getReaderClassBase(readerName);
if ((rdr = J.api.Interface.getInterface(className, null, "reader")) == null) {
err = JV.JC.READER_NOT_FOUND + className;
JU.Logger.error(err);
return err;
}return rdr;
}, "~S,java.util.Map");
c$.getReaderFromType = Clazz.defineMethod(c$, "getReaderFromType", 
function(type){
if (type.endsWith("(XML)")) {
type = "Xml" + type.substring(0, type.length - 5);
}type = ";" + type.toLowerCase() + ";";
if (";zmatrix;cfi;c;vfi;v;mnd;jag;gms;g;gau;mp;nw;orc;pqs;qc;".indexOf(type) >= 0) return "Input";
var set;
var pt;
for (var i = J.adapter.smarter.Resolver.readerSets.length; --i >= 0; ) {
if ((pt = (set = J.adapter.smarter.Resolver.readerSets[i--]).toLowerCase().indexOf(type)) >= 0) return set.substring(pt + 1, set.indexOf(";", pt + 2));
}
return null;
}, "~S");
c$.split = Clazz.defineMethod(c$, "split", 
function(a, n){
var s = "";
var l = a.length;
for (var i = 0, j = 0; i < l; i = j) s += a.substring(i, (j = Math.min(i + n, l))) + "\n";

return s;
}, "~S,~N");
c$.DOMResolve = Clazz.defineMethod(c$, "DOMResolve", 
function(htParams){
var rdrName = J.adapter.smarter.Resolver.getXmlType(htParams.get("nameSpaceInfo"));
if (JU.Logger.debugging) {
JU.Logger.debug("The Resolver thinks " + rdrName);
}htParams.put("readerName", rdrName);
return J.adapter.smarter.Resolver.getReader("XmlReader", htParams);
}, "java.util.Map");
c$.determineAtomSetCollectionReader = Clazz.defineMethod(c$, "determineAtomSetCollectionReader", 
function(readerOrDocument, htParams){
var readerName;
if (Clazz.instanceOf(readerOrDocument,"javajs.api.GenericBinaryDocument")) {
var doc = readerOrDocument;
readerName = J.adapter.smarter.Resolver.getBinaryType(doc.getInputStream());
return (readerName == null ? "binary file type not recognized" : readerName);
}if (Clazz.instanceOf(readerOrDocument,"java.io.InputStream")) {
readerName = J.adapter.smarter.Resolver.getBinaryType(readerOrDocument);
if (readerName != null) return readerName;
readerOrDocument = JU.Rdr.getBufferedReader( new java.io.BufferedInputStream(readerOrDocument), null);
}var rdr = readerOrDocument;
var llr =  new JU.LimitedLineReader(rdr, 16384);
var leader = llr.getHeader(64).trim();
if (leader.length == 0) throw  new java.io.EOFException("File contains no data.");
if (leader.indexOf("PNG") == 1 && leader.indexOf("PNGJ") >= 0) return "pngj";
if (leader.indexOf("PNG") == 1 || leader.indexOf("JPG") == 1 || leader.indexOf("JFIF") == 6) return "spt";
if (leader.indexOf("\"num_pairs\"") >= 0) return "dssr";
if (leader.indexOf("output.31\n") >= 0) return "GenNBO|output.31";
if ((readerName = J.adapter.smarter.Resolver.checkFileStart(leader)) != null) {
return (readerName.equals("Xml") ? J.adapter.smarter.Resolver.getXmlType(llr.getHeader(0)) : readerName);
}var msg;
var isJSONMap = (leader.charAt(0) == '{');
var lines =  new Array(16);
var nLines = 0;
for (var i = 0; i < lines.length; ++i) {
lines[i] = llr.readLineWithNewline();
if (lines[i].length > 0) nLines++;
}
if ((readerName = J.adapter.smarter.Resolver.checkSpecial1(nLines, lines, leader)) != null) return readerName;
if ((readerName = J.adapter.smarter.Resolver.checkLineStarts(lines)) != null) return readerName;
if ((readerName = J.adapter.smarter.Resolver.checkHeaderContains(llr.getHeader(0))) != null) {
return readerName;
}if ((readerName = J.adapter.smarter.Resolver.checkSpecial2(lines)) != null) return readerName;
if (isJSONMap) {
var json = rdr.readLine();
if ((readerName = J.adapter.smarter.Resolver.checkJSONContains(json)) != null) {
if (htParams != null) htParams.put("fileData", json);
return readerName;
}msg = (htParams == null ? null : json.substring(0, Math.min(100, json.length)));
} else {
msg = (htParams == null ? null : "\n" + lines[0] + "\n" + lines[1] + "\n" + lines[2] + "\n");
}return msg;
}, "~O,java.util.Map");
c$.getBinaryType = Clazz.defineMethod(c$, "getBinaryType", 
function(inputStream){
var magic4 = null;
return (JU.Rdr.isPickleS(inputStream) ? "PyMOL" : (JU.Rdr.getMagic(inputStream, 1)[0] & 0xFF) == 0xDE ? "MMTF" : (JU.Rdr.getMagic(inputStream, 10)[9] & 0xFF) == 0xB6 ? "BCIF" : J.adapter.smarter.Resolver.bytesMatch((magic4 = JU.Rdr.getMagic(inputStream, 4)), J.adapter.smarter.Resolver.cdxMagic) ? "CDX" : J.adapter.smarter.Resolver.bytesMatch(magic4, J.adapter.smarter.Resolver.cmdfMagic) ? "Cmdf" : null);
}, "java.io.InputStream");
c$.bytesMatch = Clazz.defineMethod(c$, "bytesMatch", 
function(a, b){
if (b.length > a.length) return false;
for (var i = b.length; --i >= 0; ) {
if (a[i] != b[i]) return false;
}
return true;
}, "~A,~A");
c$.checkFileStart = Clazz.defineMethod(c$, "checkFileStart", 
function(leader){
for (var i = 0; i < J.adapter.smarter.Resolver.fileStartsWithRecords.length; ++i) {
var recordTags = J.adapter.smarter.Resolver.fileStartsWithRecords[i];
for (var j = 1; j < recordTags.length; ++j) {
var recordTag = recordTags[j];
if (leader.startsWith(recordTag)) return recordTags[0];
}
}
return null;
}, "~S");
c$.checkSpecial1 = Clazz.defineMethod(c$, "checkSpecial1", 
function(nLines, lines, leader){
if (nLines == 1 && lines[0].length > 0 && JU.PT.isDigit(lines[0].charAt(0))) return "Jme";
if (J.adapter.smarter.Resolver.checkMopacGraphf(lines)) return "MopacGraphf";
if (J.adapter.smarter.Resolver.checkOdyssey(lines)) return "Odyssey";
switch (J.adapter.smarter.Resolver.checkMol(lines)) {
case 1:
case 3:
case 2000:
case 3000:
return "Mol";
}
switch (J.adapter.smarter.Resolver.checkXyz(lines)) {
case 1:
return "Xyz";
case 2:
return "Bilbao";
case 3:
return "PWmat";
}
if (J.adapter.smarter.Resolver.checkAlchemy(lines[0])) return "Alchemy";
if (J.adapter.smarter.Resolver.checkFoldingXyz(lines)) return "FoldingXyz";
if (J.adapter.smarter.Resolver.checkXSF(lines)) return "Xcrysden";
if (J.adapter.smarter.Resolver.checkCube(lines)) return "Cube";
if (J.adapter.smarter.Resolver.checkWien2k(lines)) return "Wien2k";
if (J.adapter.smarter.Resolver.checkAims(lines)) return "Aims";
if (J.adapter.smarter.Resolver.checkGenNBO(lines, leader)) return "GenNBO";
return null;
}, "~N,~A,~S");
c$.checkXSF = Clazz.defineMethod(c$, "checkXSF", 
function(lines){
var i = 0;
while (lines[i].length == 0) {
i++;
}
return (lines[i].startsWith("ANIMSTEPS ") || lines[i].equals("ATOMS\n") && JU.PT.parseInt(lines[i + 1]) > 0);
}, "~A");
c$.checkAims = Clazz.defineMethod(c$, "checkAims", 
function(lines){
for (var i = 0; i < lines.length; i++) {
if (lines[i].startsWith("mol 1")) return false;
var tokens = JU.PT.getTokens(lines[i]);
if (tokens.length == 0) continue;
if (tokens[0].startsWith("atom") && tokens.length > 4 && Float.isNaN(JU.PT.parseFloat(tokens[4])) || tokens[0].startsWith("multipole") && tokens.length >= 6 || tokens[0].startsWith("lattice_vector") && tokens.length >= 4) return true;
}
return false;
}, "~A");
c$.checkAlchemy = Clazz.defineMethod(c$, "checkAlchemy", 
function(line){
var pt;
if ((pt = line.indexOf("ATOMS")) > 0 && line.indexOf("BONDS") > pt) {
var n = JU.PT.parseInt(line.substring(0, pt).trim());
return (n > 0);
}return false;
}, "~S");
c$.isInt = Clazz.defineMethod(c$, "isInt", 
function(s){
J.adapter.smarter.Resolver.n[0] = 0;
s = s.trim();
return s.length > 0 && JU.PT.parseIntNext(s, J.adapter.smarter.Resolver.n) != -2147483648 && J.adapter.smarter.Resolver.n[0] == s.length;
}, "~S");
c$.isFloat = Clazz.defineMethod(c$, "isFloat", 
function(s){
return !Float.isNaN(JU.PT.parseFloat(s));
}, "~S");
c$.checkCube = Clazz.defineMethod(c$, "checkCube", 
function(lines){
for (var j = 2; j <= 5; j++) {
var tokens2 =  new java.util.StringTokenizer(lines[j]);
var n = tokens2.countTokens();
if (!(n == 4 || j == 2 && n == 5) || !J.adapter.smarter.Resolver.isInt(tokens2.nextToken())) return false;
for (var i = 3; --i >= 0; ) if (!J.adapter.smarter.Resolver.isFloat(tokens2.nextToken())) return false;

if (n == 5 && !J.adapter.smarter.Resolver.isInt(tokens2.nextToken())) return false;
}
return true;
}, "~A");
c$.checkFoldingXyz = Clazz.defineMethod(c$, "checkFoldingXyz", 
function(lines){
var tokens =  new java.util.StringTokenizer(lines[0].trim(), " \t");
if (tokens.countTokens() < 2 || !J.adapter.smarter.Resolver.isInt(tokens.nextToken().trim())) return false;
var secondLine = lines[1].trim();
if (secondLine.length == 0) secondLine = lines[2].trim();
tokens =  new java.util.StringTokenizer(secondLine, " \t");
return (tokens.countTokens() > 0 && J.adapter.smarter.Resolver.isInt(tokens.nextToken().trim()));
}, "~A");
c$.checkGenNBO = Clazz.defineMethod(c$, "checkGenNBO", 
function(lines, leader){
return (leader.indexOf("$GENNBO") >= 0 || lines[1].startsWith(" Basis set information needed for plotting orbitals") || lines[1].indexOf("s in the AO basis:") >= 0 || lines[1].indexOf("***** NBO ") >= 0 || lines[2].indexOf(" N A T U R A L   A T O M I C   O R B I T A L") >= 0);
}, "~A,~S");
c$.checkMol = Clazz.defineMethod(c$, "checkMol", 
function(lines){
var line4trimmed = ("X" + lines[3]).trim().toUpperCase();
if (line4trimmed.length < 7 || line4trimmed.indexOf(".") >= 0 || lines[0].startsWith("data_")) return 0;
if (line4trimmed.endsWith("V2000")) return 2000;
if (line4trimmed.endsWith("V3000")) return 3000;
var n1 = JU.PT.parseInt(lines[3].substring(0, 3).trim());
var n2 = JU.PT.parseInt(lines[3].substring(3, 6).trim());
return (n1 > 0 && n2 >= 0 && lines[0].indexOf("@<TRIPOS>") != 0 && lines[1].indexOf("@<TRIPOS>") != 0 && lines[2].indexOf("@<TRIPOS>") != 0 ? 3 : 0);
}, "~A");
c$.checkMopacGraphf = Clazz.defineMethod(c$, "checkMopacGraphf", 
function(lines){
return (lines[0].indexOf("MOPAC-Graphical data") > 2);
}, "~A");
c$.checkOdyssey = Clazz.defineMethod(c$, "checkOdyssey", 
function(lines){
var i;
for (i = 0; i < lines.length; i++) if (!lines[i].startsWith("C ") && lines[i].length != 0) break;

if (i >= lines.length || lines[i].charAt(0) != ' ' || (i = i + 2) + 1 >= lines.length) return false;
var l = lines[i];
if (l.length < 3) return false;
var spin = JU.PT.parseInt(l.substring(2).trim());
var charge = JU.PT.parseInt(l.substring(0, 2).trim());
if ((l = lines[i + 1]).length < 2) return false;
var atom1 = JU.PT.parseInt(l.substring(0, 2).trim());
if (spin < 0 || spin > 5 || atom1 <= 0 || charge == -2147483648 || charge > 5) return false;
var atomline = J.adapter.smarter.AtomSetCollectionReader.getTokensFloat(l, null, 5);
return !Float.isNaN(atomline[1]) && !Float.isNaN(atomline[2]) && !Float.isNaN(atomline[3]) && Float.isNaN(atomline[4]);
}, "~A");
c$.checkWien2k = Clazz.defineMethod(c$, "checkWien2k", 
function(lines){
return (lines[2].startsWith("MODE OF CALC=") || lines[2].startsWith("             RELA") || lines[2].startsWith("             NREL"));
}, "~A");
c$.checkXyz = Clazz.defineMethod(c$, "checkXyz", 
function(lines){
var checkPWM = false;
var i = JU.PT.parseInt(lines[0]);
if (i >= 0 && lines[0].trim().equals("" + i)) {
if (J.adapter.smarter.Resolver.isInt(lines[2])) return 2;
checkPWM = true;
}if (lines[0].indexOf("Bilbao Crys") >= 0) return 2;
var s;
if ((checkPWM || lines.length > 5 && i > 0) && ((s = lines[1].trim().toUpperCase()).startsWith("LATTICE VECTOR") || s.equals("LATTICE"))) return 3;
return (checkPWM ? 1 : 0);
}, "~A");
c$.checkLineStarts = Clazz.defineMethod(c$, "checkLineStarts", 
function(lines){
for (var i = 0; i < J.adapter.smarter.Resolver.lineStartsWithRecords.length; ++i) {
var recordTags = J.adapter.smarter.Resolver.lineStartsWithRecords[i];
for (var j = 1; j < recordTags.length; ++j) {
var recordTag = recordTags[j];
for (var k = 0; k < lines.length; k++) {
if (lines[k].startsWith(recordTag)) return recordTags[0];
}
}
}
return null;
}, "~A");
c$.checkHeaderContains = Clazz.defineMethod(c$, "checkHeaderContains", 
function(header){
for (var i = 0; i < J.adapter.smarter.Resolver.headerContainsRecords.length; ++i) {
var fileType = J.adapter.smarter.Resolver.checkHeaderRecords(header, J.adapter.smarter.Resolver.headerContainsRecords[i]);
if (fileType != null) return fileType;
}
return null;
}, "~S");
c$.checkJSONContains = Clazz.defineMethod(c$, "checkJSONContains", 
function(header){
for (var i = 0; i < J.adapter.smarter.Resolver.jsonContainsRecords.length; ++i) {
var fileType = J.adapter.smarter.Resolver.checkHeaderRecords(header, J.adapter.smarter.Resolver.jsonContainsRecords[i]);
if (fileType != null) return fileType;
}
return null;
}, "~S");
c$.checkHeaderRecords = Clazz.defineMethod(c$, "checkHeaderRecords", 
function(header, recordTags){
for (var j = 1; j < recordTags.length; ++j) {
var recordTag = recordTags[j];
if (header.indexOf(recordTag) < 0) continue;
var type = recordTags[0];
if (!type.equals("Xml")) return type;
if (header.indexOf("/AFLOWDATA/") >= 0 || header.indexOf("-- Structure PRE --") >= 0) return "AFLOW";
return (header.indexOf("<!DOCTYPE HTML PUBLIC") < 0 && header.indexOf("XHTML") < 0 && (header.indexOf("xhtml") < 0 || header.indexOf("<cml") >= 0) ? J.adapter.smarter.Resolver.getXmlType(header) : null);
}
return null;
}, "~S,~A");
c$.getXmlType = Clazz.defineMethod(c$, "getXmlType", 
function(header){
if (header.indexOf("http://www.molpro.net/") >= 0) {
return "XmlMolpro";
}if (header.indexOf("odyssey") >= 0) {
return "XmlOdyssey";
}if (header.indexOf("C3XML") >= 0) {
return "XmlChem3d";
}if (header.indexOf("CDXML") >= 0) {
return "XmlCdx";
}if (header.indexOf("arguslab") >= 0) {
return "XmlArgus";
}if (header.indexOf("jvxl") >= 0 || header.indexOf("http://www.xml-cml.org/schema") >= 0 || header.indexOf("cml:") >= 0 || header.indexOf("<cml>") >= 0) {
return "XmlCml";
}if (header.indexOf("XSD") >= 0) {
return "XmlXsd";
}if (header.indexOf(">vasp") >= 0) {
return "XmlVasp";
}if (header.indexOf("<GEOMETRY_INFO>") >= 0) {
return "XmlQE";
}return "XmlCml(unidentified)";
}, "~S");
c$.checkSpecial2 = Clazz.defineMethod(c$, "checkSpecial2", 
function(lines){
if (J.adapter.smarter.Resolver.checkGromacs(lines)) return "Gromacs";
if (J.adapter.smarter.Resolver.checkCrystal(lines)) return "Crystal";
if (J.adapter.smarter.Resolver.checkFAH(lines)) return "FAH";
var s = J.adapter.smarter.Resolver.checkCastepVaspSiesta(lines);
if (s != null) return s;
return null;
}, "~A");
c$.checkFAH = Clazz.defineMethod(c$, "checkFAH", 
function(lines){
var s = lines[0].trim() + lines[2].trim();
return s.equals("{\"atoms\": [");
}, "~A");
c$.checkCrystal = Clazz.defineMethod(c$, "checkCrystal", 
function(lines){
var s = lines[1].trim();
if (s.equals("SLAB") || s.equals("MOLECULE") || s.equals("CRYSTAL") || s.equals("POLYMER") || (s = lines[3]).equals("SLAB") || s.equals("MOLECULE") || s.equals("POLYMER")) return true;
for (var i = 0; i < lines.length; i++) {
if (lines[i].trim().equals("OPTGEOM") || lines[i].trim().equals("FREQCALC") || lines[i].contains("DOVESI") || lines[i].contains("TORINO") || lines[i].contains("http://www.crystal.unito.it") || lines[i].contains("Pcrystal") || lines[i].contains("MPPcrystal") || lines[i].contains("crystal executable")) return true;
}
return false;
}, "~A");
c$.checkGromacs = Clazz.defineMethod(c$, "checkGromacs", 
function(lines){
if (JU.PT.parseInt(lines[1]) == -2147483648) return false;
var len = -1;
for (var i = 2; i < 16 && len != 0; i++) if ((len = lines[i].length) != 69 && len != 45 && len != 0) return false;

return true;
}, "~A");
c$.checkCastepVaspSiesta = Clazz.defineMethod(c$, "checkCastepVaspSiesta", 
function(lines){
for (var i = 0; i < lines.length; i++) {
var line = lines[i].toUpperCase();
if (line.indexOf("FREQUENCIES IN         CM-1") == 1 || line.contains("CASTEP") || line.startsWith("%BLOCK LATTICE_ABC") || line.startsWith("%BLOCK LATTICE_CART") || line.startsWith("%BLOCK POSITIONS_FRAC") || line.startsWith("%BLOCK POSITIONS_ABS") || line.contains("<-- E")) return "Castep";
if (line.contains("%BLOCK")) return "Siesta";
if (i >= 6 && i < 10 && (line.startsWith("DIRECT") || line.startsWith("CARTESIAN"))) return "VaspPoscar";
}
return null;
}, "~A");
c$.getFileTypefromFilter = Clazz.defineMethod(c$, "getFileTypefromFilter", 
function(filter){
var pt = (filter == null ? -1 : filter.toLowerCase().indexOf("filetype"));
return (pt < 0 ? null : filter.substring(pt + 8, (filter + ";").indexOf(";", pt)).$replace('=', ' ').trim());
}, "~S");
c$.fixDOSName = Clazz.defineMethod(c$, "fixDOSName", 
function(fileName){
return (fileName.indexOf(":\\") >= 0 ? fileName.$replace('\\', '/') : fileName);
}, "~S");
c$.readerSets =  Clazz.newArray(-1, ["cif.", ";Cif;Cif2;MMCif;MMTF;MagCif;BCIF;", "molxyz.", ";Mol3D;Mol;Xyz;", "more.", ";AFLOW;BinaryDcd;CDX;Gromacs;Jcampdx;MdCrd;MdTop;Mol2;TlsDataOnly;", "quantum.", ";Adf;Csf;Dgrid;GamessUK;GamessUS;Gaussian;GaussianFchk;GaussianWfn;Jaguar;Molden;MopacGraphf;GenNBO;NWChem;Psi;Qchem;QCJSON;WebMO;Orca;MO;Ams;", "pdb.", ";Pdb;Pqr;P2n;JmolData;", "pymol.", ";PyMOL;", "simple.", ";Alchemy;Ampac;Cube;FoldingXyz;GhemicalMM;HyperChem;Jme;JSON;Mopac;MopacArchive;Tinker;Input;FAH;", "spartan.", ";Spartan;SpartanSmol;Odyssey;", "xtal.", ";Abinit;Aims;Bilbao;Castep;Cgd;Crystal;Dmol;Espresso;Gulp;Jana;Magres;Shelx;Siesta;VaspOutcar;VaspPoscar;Wien2k;Xcrysden;PWmat;Optimade;Cmdf;", "xml.", ";XmlCdx;XmlArgus;XmlCml;XmlChem3d;XmlMolpro;XmlOdyssey;XmlXsd;XmlVasp;XmlQE;"]);
c$.cdxMagic =  Clazz.newByteArray(-1, ['V', 'j', 'C', 'D']);
c$.cmdfMagic =  Clazz.newByteArray(-1, ['C', 'M', 'D', 'F']);
c$.sptRecords =  Clazz.newArray(-1, ["spt", "# Jmol state", "# Jmol script", "JmolManifest"]);
c$.m3dStartRecords =  Clazz.newArray(-1, ["Alchemy", "STRUCTURE  1.00     1"]);
c$.cubeFileStartRecords =  Clazz.newArray(-1, ["Cube", "JVXL", "#JVXL"]);
c$.mol2Records =  Clazz.newArray(-1, ["Mol2", "mol2", "@<TRIPOS>"]);
c$.webmoFileStartRecords =  Clazz.newArray(-1, ["WebMO", "[HEADER]"]);
c$.moldenFileStartRecords =  Clazz.newArray(-1, ["Molden", "[Molden", "MOLDEN", "[MOLDEN"]);
c$.dcdFileStartRecords =  Clazz.newArray(-1, ["BinaryDcd", "T\0\0\0CORD", "\0\0\0TCORD"]);
c$.tlsDataOnlyFileStartRecords =  Clazz.newArray(-1, ["TlsDataOnly", "REFMAC\n\nTL", "REFMAC\r\n\r\n", "REFMAC\r\rTL"]);
c$.inputFileStartRecords =  Clazz.newArray(-1, ["Input", "#ZMATRIX", "%mem=", "AM1", "$rungauss"]);
c$.magresFileStartRecords =  Clazz.newArray(-1, ["Magres", "#$magres", "# magres"]);
c$.pymolStartRecords =  Clazz.newArray(-1, ["PyMOL", "}q"]);
c$.janaStartRecords =  Clazz.newArray(-1, ["Jana", "Version Jana"]);
c$.jsonStartRecords =  Clazz.newArray(-1, ["JSON", "{\"mol\":"]);
c$.jcampdxStartRecords =  Clazz.newArray(-1, ["Jcampdx", "##TITLE"]);
c$.jmoldataStartRecords =  Clazz.newArray(-1, ["JmolData", "REMARK   6 Jmol"]);
c$.pqrStartRecords =  Clazz.newArray(-1, ["Pqr", "REMARK   1 PQR", "REMARK    The B-factors"]);
c$.p2nStartRecords =  Clazz.newArray(-1, ["P2n", "REMARK   1 P2N"]);
c$.cif2StartRecords =  Clazz.newArray(-1, ["Cif2", "#\\#CIF_2", "\u00EF\u00BB\u00BF#\\#CIF_2"]);
c$.xmlStartRecords =  Clazz.newArray(-1, ["Xml", "<?xml"]);
c$.cfiStartRecords =  Clazz.newArray(-1, ["Input", "$CFI"]);
c$.fileStartsWithRecords =  Clazz.newArray(-1, [J.adapter.smarter.Resolver.xmlStartRecords, J.adapter.smarter.Resolver.sptRecords, J.adapter.smarter.Resolver.m3dStartRecords, J.adapter.smarter.Resolver.cubeFileStartRecords, J.adapter.smarter.Resolver.mol2Records, J.adapter.smarter.Resolver.webmoFileStartRecords, J.adapter.smarter.Resolver.moldenFileStartRecords, J.adapter.smarter.Resolver.dcdFileStartRecords, J.adapter.smarter.Resolver.tlsDataOnlyFileStartRecords, J.adapter.smarter.Resolver.inputFileStartRecords, J.adapter.smarter.Resolver.magresFileStartRecords, J.adapter.smarter.Resolver.pymolStartRecords, J.adapter.smarter.Resolver.janaStartRecords, J.adapter.smarter.Resolver.jsonStartRecords, J.adapter.smarter.Resolver.jcampdxStartRecords, J.adapter.smarter.Resolver.jmoldataStartRecords, J.adapter.smarter.Resolver.pqrStartRecords, J.adapter.smarter.Resolver.p2nStartRecords, J.adapter.smarter.Resolver.cif2StartRecords, J.adapter.smarter.Resolver.cfiStartRecords]);
c$.n =  Clazz.newIntArray (1, 0);
c$.mmcifLineStartRecords =  Clazz.newArray(-1, ["MMCif", "_entry.id", "_database_PDB_", "_pdbx_", "_chem_comp.pdbx_type", "_audit_author.name", "_atom_site."]);
c$.cifLineStartRecords =  Clazz.newArray(-1, ["Cif", "data_", "_publ"]);
c$.pdbLineStartRecords =  Clazz.newArray(-1, ["Pdb", "HEADER", "OBSLTE", "TITLE ", "CAVEAT", "COMPND", "SOURCE", "KEYWDS", "EXPDTA", "AUTHOR", "REVDAT", "SPRSDE", "JRNL  ", "REMARK ", "DBREF ", "SEQADV", "SEQRES", "MODRES", "HELIX ", "SHEET ", "TURN  ", "CRYST1", "ORIGX1", "ORIGX2", "ORIGX3", "SCALE1", "SCALE2", "SCALE3", "ATOM  ", "HETATM", "MODEL ", "LINK  ", "USER  MOD "]);
c$.cgdLineStartRecords =  Clazz.newArray(-1, ["Cgd", "EDGE ", "edge "]);
c$.shelxLineStartRecords =  Clazz.newArray(-1, ["Shelx", "TITL ", "ZERR ", "LATT ", "SYMM ", "CELL ", "TITL\t"]);
c$.ghemicalMMLineStartRecords =  Clazz.newArray(-1, ["GhemicalMM", "!Header mm1gp", "!Header gpr"]);
c$.jaguarLineStartRecords =  Clazz.newArray(-1, ["Jaguar", "  |  Jaguar version"]);
c$.mdlLineStartRecords =  Clazz.newArray(-1, ["Mol", "$MDL "]);
c$.spartanSmolLineStartRecords =  Clazz.newArray(-1, ["SpartanSmol", "INPUT="]);
c$.csfLineStartRecords =  Clazz.newArray(-1, ["Csf", "local_transform"]);
c$.mdTopLineStartRecords =  Clazz.newArray(-1, ["MdTop", "%FLAG TITLE"]);
c$.hyperChemLineStartRecords =  Clazz.newArray(-1, ["HyperChem", "mol 1"]);
c$.vaspOutcarLineStartRecords =  Clazz.newArray(-1, ["VaspOutcar", " vasp.", " INCAR:"]);
c$.orcaInputLineStartRecords =  Clazz.newArray(-1, ["Orca", "* xyz", "*xyz"]);
c$.lineStartsWithRecords =  Clazz.newArray(-1, [J.adapter.smarter.Resolver.mmcifLineStartRecords, J.adapter.smarter.Resolver.cifLineStartRecords, J.adapter.smarter.Resolver.pdbLineStartRecords, J.adapter.smarter.Resolver.cgdLineStartRecords, J.adapter.smarter.Resolver.shelxLineStartRecords, J.adapter.smarter.Resolver.ghemicalMMLineStartRecords, J.adapter.smarter.Resolver.jaguarLineStartRecords, J.adapter.smarter.Resolver.mdlLineStartRecords, J.adapter.smarter.Resolver.spartanSmolLineStartRecords, J.adapter.smarter.Resolver.csfLineStartRecords, J.adapter.smarter.Resolver.mol2Records, J.adapter.smarter.Resolver.mdTopLineStartRecords, J.adapter.smarter.Resolver.hyperChemLineStartRecords, J.adapter.smarter.Resolver.vaspOutcarLineStartRecords, J.adapter.smarter.Resolver.orcaInputLineStartRecords]);
c$.bilbaoContainsRecords =  Clazz.newArray(-1, ["Bilbao", ">Bilbao Crystallographic Server<"]);
c$.xmlContainsRecords =  Clazz.newArray(-1, ["Xml", "<?xml", "<atom", "<molecule", "<reaction", "<cml", "<bond", ".dtd\"", "<list>", "<entry", "<identifier", "http://www.xml-cml.org/schema/cml2/core"]);
c$.gaussianContainsRecords =  Clazz.newArray(-1, ["Gaussian", "Entering Gaussian System", "Entering Link 1", "1998 Gaussian, Inc."]);
c$.ampacContainsRecords =  Clazz.newArray(-1, ["Ampac", "AMPAC Version"]);
c$.mopacContainsRecords =  Clazz.newArray(-1, ["Mopac", "MOPAC 93 (c) Fujitsu", "MOPAC FOR LINUX (PUBLIC DOMAIN VERSION)", "MOPAC:  VERSION  6", "MOPAC   7", "MOPAC2", "MOPAC (PUBLIC"]);
c$.qchemContainsRecords =  Clazz.newArray(-1, ["Qchem", "Welcome to Q-Chem", "A Quantum Leap Into The Future Of Chemistry"]);
c$.gamessUKContainsRecords =  Clazz.newArray(-1, ["GamessUK", "GAMESS-UK", "G A M E S S - U K"]);
c$.gamessUSContainsRecords =  Clazz.newArray(-1, ["GamessUS", "GAMESS", "$CONTRL"]);
c$.spartanBinaryContainsRecords =  Clazz.newArray(-1, ["SpartanSmol", "|PropertyArchive", "_spartan", "spardir", "BEGIN Directory Entry Molecule"]);
c$.spartanContainsRecords =  Clazz.newArray(-1, ["Spartan", "Spartan", "converted archive file"]);
c$.adfContainsRecords =  Clazz.newArray(-1, ["Adf", "Amsterdam Density Functional"]);
c$.amsContainsRecords =  Clazz.newArray(-1, ["Ams", "Amsterdam Modeling Suite"]);
c$.psiContainsRecords =  Clazz.newArray(-1, ["Psi", "    PSI  3", "PSI3:"]);
c$.nwchemContainsRecords =  Clazz.newArray(-1, ["NWChem", " argument  1 = "]);
c$.uicrcifContainsRecords =  Clazz.newArray(-1, ["Cif", "Crystallographic Information File"]);
c$.dgridContainsRecords =  Clazz.newArray(-1, ["Dgrid", "BASISFILE   created by DGrid"]);
c$.crystalContainsRecords =  Clazz.newArray(-1, ["Crystal", "*                                CRYSTAL", "TORINO", "DOVESI"]);
c$.dmolContainsRecords =  Clazz.newArray(-1, ["Dmol", "DMol^3"]);
c$.gulpContainsRecords =  Clazz.newArray(-1, ["Gulp", "GENERAL UTILITY LATTICE PROGRAM"]);
c$.espressoContainsRecords =  Clazz.newArray(-1, ["Espresso", "Program PWSCF", "Program PHONON"]);
c$.siestaContainsRecords =  Clazz.newArray(-1, ["Siesta", "MD.TypeOfRun", "SolutionMethod", "MeshCutoff", "WELCOME TO SIESTA"]);
c$.xcrysDenContainsRecords =  Clazz.newArray(-1, ["Xcrysden", "PRIMVEC", "CONVVEC", "PRIMCOORD", "ANIMSTEP"]);
c$.mopacArchiveContainsRecords =  Clazz.newArray(-1, ["MopacArchive", "SUMMARY OF PM"]);
c$.abinitContainsRecords =  Clazz.newArray(-1, ["Abinit", "http://www.abinit.org", "Catholique", "Louvain"]);
c$.qcJsonContainsRecords =  Clazz.newArray(-1, ["QCJSON", "\"QCJSON"]);
c$.optimadeContainsRecords =  Clazz.newArray(-1, ["Optimade", "\"cartesian_site_positions\":", "\"api_version\":", "optimade"]);
c$.jsonArrayContainsRecords =  Clazz.newArray(-1, ["JSON", "\"atomArray\":[", "\"atomArray\" : ["]);
c$.orcaContainsRecords =  Clazz.newArray(-1, ["Orca", "* O   R   C   A *"]);
c$.gaussianFchkContainsRecords =  Clazz.newArray(-1, ["GaussianFchk", "Number of point charges in /Mol/"]);
c$.inputContainsRecords =  Clazz.newArray(-1, ["Input", " ATOMS cartesian", "$molecule", "&zmat", "geometry={", "$DATA", "%coords", "GEOM=PQS", "geometry units angstroms"]);
c$.aflowContainsRecords =  Clazz.newArray(-1, ["AFLOW", "/AFLOWDATA/"]);
c$.magCifContainsRecords =  Clazz.newArray(-1, ["MagCif", "_space_group_magn"]);
c$.headerContainsRecords =  Clazz.newArray(-1, [J.adapter.smarter.Resolver.sptRecords, J.adapter.smarter.Resolver.bilbaoContainsRecords, J.adapter.smarter.Resolver.xmlContainsRecords, J.adapter.smarter.Resolver.gaussianContainsRecords, J.adapter.smarter.Resolver.ampacContainsRecords, J.adapter.smarter.Resolver.mopacContainsRecords, J.adapter.smarter.Resolver.gamessUKContainsRecords, J.adapter.smarter.Resolver.gamessUSContainsRecords, J.adapter.smarter.Resolver.qchemContainsRecords, J.adapter.smarter.Resolver.spartanBinaryContainsRecords, J.adapter.smarter.Resolver.spartanContainsRecords, J.adapter.smarter.Resolver.mol2Records, J.adapter.smarter.Resolver.adfContainsRecords, J.adapter.smarter.Resolver.psiContainsRecords, J.adapter.smarter.Resolver.nwchemContainsRecords, J.adapter.smarter.Resolver.uicrcifContainsRecords, J.adapter.smarter.Resolver.dgridContainsRecords, J.adapter.smarter.Resolver.crystalContainsRecords, J.adapter.smarter.Resolver.dmolContainsRecords, J.adapter.smarter.Resolver.gulpContainsRecords, J.adapter.smarter.Resolver.espressoContainsRecords, J.adapter.smarter.Resolver.siestaContainsRecords, J.adapter.smarter.Resolver.xcrysDenContainsRecords, J.adapter.smarter.Resolver.mopacArchiveContainsRecords, J.adapter.smarter.Resolver.abinitContainsRecords, J.adapter.smarter.Resolver.gaussianFchkContainsRecords, J.adapter.smarter.Resolver.inputContainsRecords, J.adapter.smarter.Resolver.aflowContainsRecords, J.adapter.smarter.Resolver.magCifContainsRecords, J.adapter.smarter.Resolver.qcJsonContainsRecords, J.adapter.smarter.Resolver.optimadeContainsRecords, J.adapter.smarter.Resolver.orcaContainsRecords, J.adapter.smarter.Resolver.jsonArrayContainsRecords, J.adapter.smarter.Resolver.amsContainsRecords]);
c$.jsonContainsRecords =  Clazz.newArray(-1, [J.adapter.smarter.Resolver.optimadeContainsRecords]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
