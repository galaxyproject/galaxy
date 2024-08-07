Clazz.declarePackage("JSV.source");
Clazz.load(null, "JSV.source.BrukerReader", ["java.io.BufferedInputStream", "$.ByteArrayInputStream", "$.File", "java.util.Hashtable", "java.util.zip.ZipInputStream", "JU.BinaryDocument", "$.Lst", "$.Rdr", "JSV.common.Coordinate", "$.Spectrum", "JSV.source.JDXReader", "$.JDXSource"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.allowPhasing = false;
Clazz.instantialize(this, arguments);}, JSV.source, "BrukerReader", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "readBrukerZip", 
function(bytes, fullPath){
try {
var zis =  new java.util.zip.ZipInputStream(bytes == null ?  new java.io.FileInputStream(fullPath) :  new java.io.ByteArrayInputStream(bytes));
var ze;
var map =  new java.util.Hashtable();
var data1r =  Clazz.newByteArray (0, 0);
var data1i =  Clazz.newByteArray (0, 0);
var data2rr =  Clazz.newByteArray (0, 0);
var root = null;
var title = null;
out : while ((ze = zis.getNextEntry()) != null) {
var zeName = ze.getName();
System.out.println(zeName);
var pt = zeName.lastIndexOf('/');
var zeShortName = zeName.substring(pt + 1);
if (root == null) {
root = zeName.substring(0, pt + 1);
pt = root.indexOf("/pdata/");
if (pt >= 0) root = root.substring(0, pt + 1);
}if (!zeName.startsWith(root)) break out;
var isacq = false;
if (zeShortName.equals("title")) {
title =  String.instantialize(this.getBytes(zis, ze.getSize(), false));
map.put("##title", title);
} else if (zeShortName.equals("1r")) {
data1r = this.getBytes(zis, ze.getSize(), false);
} else if (zeShortName.equals("1i")) {
if (this.allowPhasing) data1i = this.getBytes(zis, ze.getSize(), false);
} else if (zeShortName.equals("2rr")) {
data2rr = this.getBytes(zis, ze.getSize(), false);
} else if (zeShortName.equals("proc2s") || zeShortName.equals("acqu2s")) {
JSV.source.JDXReader.getHeaderMapS( new java.io.ByteArrayInputStream(this.getBytes(zis, ze.getSize(), false)), map, "_2");
} else if (zeShortName.equals("procs") || (isacq = zeShortName.equals("acqus"))) {
if (isacq) {
root = zeName.substring(0, pt + 1);
}JSV.source.JDXReader.getHeaderMap( new java.io.ByteArrayInputStream(this.getBytes(zis, ze.getSize(), false)), map);
}}
zis.close();
map.put("##TITLE", (title == null ? "" : title));
return this.getSource(fullPath, map, data1r, data1i, data2rr);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "~A,~S");
Clazz.defineMethod(c$, "readBrukerDir", 
function(fullPath){
var dir =  new java.io.File(fullPath);
if (!dir.isDirectory()) {
dir = dir.getParentFile();
}var procs =  new java.io.File(dir, "procs");
if (!procs.exists()) procs =  new java.io.File(dir, "pdata/1/procs");
var pdata = procs.getParentFile();
var brukerDir = pdata.getParentFile().getParentFile();
var map =  new java.util.Hashtable();
this.mapParameters(brukerDir, "acqus", map, null);
this.mapParameters(brukerDir, "acqu2s", map, "_2");
this.mapParameters(pdata, "procs", map, null);
this.mapParameters(pdata, "proc2s", map, "_2");
map.put("##TITLE",  String.instantialize(this.getFileContentsAsBytes( new java.io.File(pdata, "title"))));
var data1r = this.getFileContentsAsBytes( new java.io.File(procs.getParent(), "1r"));
var data1i = (this.allowPhasing ? this.getFileContentsAsBytes( new java.io.File(procs.getParent(), "1i")) :  Clazz.newByteArray (0, 0));
var data2rr = this.getFileContentsAsBytes( new java.io.File(procs.getParent(), "2rr"));
return this.getSource(brukerDir.toString(), map, data1r, data1i, data2rr);
}, "~S");
Clazz.defineMethod(c$, "mapParameters", 
function(dir, fname, map, suffix){
var f =  new java.io.File(dir, fname);
if (!f.exists()) return;
var is =  new java.io.FileInputStream(f);
JSV.source.JDXReader.getHeaderMapS(is, map, suffix);
is.close();
}, "java.io.File,~S,java.util.Map,~S");
Clazz.defineMethod(c$, "getSource", 
function(brukerDir, map, data1r, data1i, data2rr){
var dtypp = Integer.parseInt(map.get("##$DTYPP"));
var byteorp = (dtypp == 0 ? Integer.parseInt(map.get("##$BYTORDP")) : 2147483647);
if (dtypp == -2147483648 || byteorp == -2147483648) return null;
var source = null;
if (data1r.length > 0) {
source =  new JSV.source.JDXSource((data1i.length == 0 ? 0 : 2), brukerDir);
this.setSource(this.getData(data1r, dtypp, byteorp), this.getData(data1i, dtypp, byteorp), map, source, false);
} else if (data2rr.length > 0) {
source =  new JSV.source.JDXSource(2, brukerDir);
this.setSource(this.getData(data2rr, dtypp, byteorp), null, map, source, true);
}return source;
}, "~S,java.util.Map,~A,~A,~A");
Clazz.defineMethod(c$, "setSource", 
function(datar, datai, map, source, is2D){
var LDRTable =  new JU.Lst();
var spectrum0 =  new JSV.common.Spectrum();
spectrum0.setTitle(map.get("##TITLE"));
spectrum0.setJcampdx(is2D ? "6.0" : "5.1");
spectrum0.setDataClass("XYDATA");
spectrum0.setDataType(is2D ? "nD NMR SPECTRUM" : "NMR SPECTRUM");
spectrum0.setContinuous(true);
spectrum0.setIncreasing(false);
spectrum0.setLongDate(map.get("##$DATE"));
spectrum0.setOrigin("Bruker BioSpin GmbH/JSpecView");
spectrum0.setOwner(map.get("##OWNER"));
var freq = JSV.source.BrukerReader.parseDouble(map.get("##$SFO1"));
var ref = JSV.source.BrukerReader.parseDouble(map.get("##$ABSF1"));
if (ref == 0) {
ref = JSV.source.BrukerReader.parseDouble(map.get("##$OFFSET"));
}var nuc1 = this.cleanJDXValue(map.get("##$NUC1"));
var nuc2 = this.cleanJDXValue(map.get("##$NUC2"));
if (nuc2.length == 0) nuc2 = nuc1;
var sw_hz = JSV.source.BrukerReader.parseDouble(map.get("##$SWP"));
var sw = sw_hz / freq;
var shift = ref - sw;
var solvent = this.cleanJDXValue(map.get("##$SOLVENT"));
var shiftType = "INTERNAL";
JSV.source.JDXReader.addHeader(LDRTable, "##.SHIFTREFERENCE", shiftType + ", " + solvent + ", 1, " + ref);
JSV.source.JDXReader.addHeader(LDRTable, "##.OBSERVEFREQUENCY", "" + freq);
JSV.source.JDXReader.addHeader(LDRTable, "##.OBSERVENUCLEUS", nuc1);
JSV.source.JDXReader.addHeader(LDRTable, "##SPECTROMETER/DATA SYSTEM", this.cleanJDXValue(map.get("##$INSTRUM")));
spectrum0.setHeaderTable(LDRTable);
spectrum0.setObservedNucleus(nuc1);
spectrum0.setObservedFreq(freq);
spectrum0.setHZtoPPM(true);
if (is2D) {
source.isCompoundSource = true;
spectrum0.setNumDim(2);
spectrum0.setNucleusAndFreq(nuc2, false);
var si0 = Integer.parseInt(map.get("##$SI"));
var si1 = Integer.parseInt(map.get("##$SI_2"));
var ref1 = JSV.source.BrukerReader.parseDouble(map.get("##$ABSF1_2"));
if (ref1 == 0) {
ref1 = JSV.source.BrukerReader.parseDouble(map.get("##$OFFSET"));
}var freq1 = JSV.source.BrukerReader.parseDouble(map.get("##$SFO1_2"));
var sw_hz1 = JSV.source.BrukerReader.parseDouble(map.get("##$SWP_2"));
var npoints = si0;
var xfactor = sw_hz / npoints;
var xfactor1 = sw_hz1 / si1;
var freq2 = freq1;
freq1 = ref1 * freq1 - xfactor1;
spectrum0.fileNPoints = npoints;
spectrum0.fileFirstX = sw_hz - xfactor;
spectrum0.fileLastX = 0;
var f = 1;
for (var j = 0, pt = 0; j < si1; j++) {
var spectrum =  new JSV.common.Spectrum();
spectrum0.copyTo(spectrum);
spectrum.setTitle(spectrum0.getTitle());
spectrum.setY2D(freq1);
spectrum.blockID = Math.random();
spectrum0.fileNPoints = npoints;
spectrum0.fileFirstX = sw_hz - xfactor;
spectrum0.fileLastX = 0;
spectrum.setY2DUnits("HZ");
spectrum.setXFactor(1);
spectrum.setYFactor(1);
spectrum.setObservedNucleus(nuc2);
spectrum.setObservedFreq(freq2);
var xyCoords =  new Array(npoints);
for (var i = 0; i < npoints; i++) {
xyCoords[npoints - i - 1] =  new JSV.common.Coordinate().set((npoints - i) * xfactor / freq + shift, datar[pt++] * f);
}
spectrum.setXYCoords(xyCoords);
source.addJDXSpectrum(null, spectrum, j > 0);
freq1 -= xfactor1;
}
} else {
var npoints = datar.length;
var xfactor = sw_hz / npoints;
spectrum0.fileFirstX = sw_hz - xfactor;
spectrum0.fileLastX = 0;
spectrum0.fileNPoints = npoints;
var xyCoords =  new Array(npoints);
for (var i = 0; i < npoints; i++) {
xyCoords[npoints - i - 1] =  new JSV.common.Coordinate().set((npoints - i - 1) * xfactor / freq + shift, datar[i]);
}
spectrum0.setXYCoords(xyCoords);
spectrum0.fileNPoints = npoints;
spectrum0.setXFactor(xfactor);
spectrum0.setYFactor(1);
spectrum0.setXUnits("ppm");
spectrum0.setYUnits("ARBITRARY UNITS");
spectrum0.setNumDim(1);
if (spectrum0.getMaxY() >= 10000) spectrum0.normalizeSimulation(1000);
source.addJDXSpectrum(null, spectrum0, false);
}}, "~A,~A,java.util.Map,JSV.source.JDXSource,~B");
c$.parseDouble = Clazz.defineMethod(c$, "parseDouble", 
function(val){
return (val == null || val.length == 0 ? NaN : Double.parseDouble(val));
}, "~S");
Clazz.defineMethod(c$, "getData", 
function(bytes, dtypp, byteorp){
var len = Clazz.doubleToInt(bytes.length / (dtypp == 0 ? 4 : 8));
var doc =  new JU.BinaryDocument();
doc.setStream( new java.io.BufferedInputStream( new java.io.ByteArrayInputStream(bytes)), byteorp != 0);
var ad =  Clazz.newDoubleArray (len, 0);
var d = 0;
var dmin = 1.7976931348623157E308;
var dmax = -1.7976931348623157E308;
if (dtypp == 0) {
for (var i = 0; i < len; i++) {
var f = 1;
ad[i] = d = doc.readInt() * f;
if (d < dmin) dmin = d;
if (d > dmax) dmax = d;
}
} else {
for (var i = 0; i < len; i++) {
ad[i] = d = doc.readDouble();
if (d < dmin) dmin = d;
if (d > dmax) dmax = d;
}
}doc.close();
return ad;
}, "~A,~N,~N");
Clazz.defineMethod(c$, "cleanJDXValue", 
function(val){
var s = (val == null ? "" : val.startsWith("<") ? val.substring(1, val.length - 1) : val);
return (s.equals("off") ? "" : s);
}, "~S");
Clazz.defineMethod(c$, "getFileContentsAsBytes", 
function(file){
if (!file.exists()) return  Clazz.newByteArray (0, 0);
var len = file.length();
return this.getBytes( new java.io.FileInputStream(file), len, true);
}, "java.io.File");
Clazz.defineMethod(c$, "getBytes", 
function($in, len, andClose){
try {
return JU.Rdr.getLimitedStreamBytes($in, len);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return  Clazz.newByteArray (0, 0);
}, "java.io.InputStream,~N,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
