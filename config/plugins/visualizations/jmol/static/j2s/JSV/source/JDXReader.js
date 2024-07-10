Clazz.declarePackage("JSV.source");
Clazz.load(["J.api.JmolJDXMOLReader"], "JSV.source.JDXReader", ["java.io.BufferedReader", "$.StringReader", "java.util.Hashtable", "$.LinkedHashMap", "$.StringTokenizer", "javajs.api.Interface", "JU.AU", "$.Lst", "$.PT", "$.Rdr", "$.SB", "JSV.common.Coordinate", "$.JSVFileManager", "$.JSViewer", "$.PeakInfo", "$.Spectrum", "JSV.exception.JSVException", "JSV.source.JDXDecompressor", "$.JDXSource", "$.JDXSourceStreamTokenizer", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.nmrMaxY = NaN;
this.source = null;
this.t = null;
this.errorLog = null;
this.obscure = false;
this.done = false;
this.isZipFile = false;
this.filePath = null;
this.loadImaginary = true;
this.isSimulation = false;
this.ignoreShiftReference = false;
this.ignorePeakTables = false;
this.lastErrPath = null;
this.isTabularData = false;
this.firstSpec = 0;
this.lastSpec = 0;
this.nSpec = 0;
this.blockID = 0;
this.mpr = null;
this.reader = null;
this.modelSpectrum = null;
this.acdAssignments = null;
this.acdMolFile = null;
this.peakData = null;
Clazz.instantialize(this, arguments);}, JSV.source, "JDXReader", null, J.api.JmolJDXMOLReader);
Clazz.makeConstructor(c$, 
function(filePath, obscure, loadImaginary, iSpecFirst, iSpecLast, nmrNormalization){
filePath = JU.PT.trimQuotes(filePath);
this.isSimulation = (filePath != null && filePath.startsWith("http://SIMULATION/"));
if (this.isSimulation) {
this.nmrMaxY = (Float.isNaN(nmrNormalization) ? 10000 : nmrNormalization);
}this.filePath = filePath;
this.obscure = obscure;
this.firstSpec = iSpecFirst;
this.lastSpec = iSpecLast;
this.loadImaginary = loadImaginary;
}, "~S,~B,~B,~N,~N,~N");
c$.getVarList = Clazz.defineMethod(c$, "getVarList", 
function(dataClass){
var index = JSV.source.JDXReader.VAR_LIST_TABLE[0].indexOf(dataClass);
return JSV.source.JDXReader.VAR_LIST_TABLE[1].substring(index + 1, index + 12).trim();
}, "~S");
c$.createJDXSourceFromStream = Clazz.defineMethod(c$, "createJDXSourceFromStream", 
function($in, obscure, loadImaginary, nmrMaxY){
return JSV.source.JDXReader.createJDXSource(null, $in, "stream", obscure, loadImaginary, -1, -1, nmrMaxY);
}, "java.io.InputStream,~B,~B,~N");
c$.getHeaderMap = Clazz.defineMethod(c$, "getHeaderMap", 
function($in, map){
return JSV.source.JDXReader.getHeaderMapS($in, map, null);
}, "java.io.InputStream,java.util.Map");
c$.getHeaderMapS = Clazz.defineMethod(c$, "getHeaderMapS", 
function($in, map, suffix){
if (map == null) map =  new java.util.LinkedHashMap();
var hlist = JSV.source.JDXReader.createJDXSource(null, $in, null, false, false, 0, -1, 0).getJDXSpectrum(0).headerTable;
for (var i = 0, n = hlist.size(); i < n; i++) {
var h = hlist.get(i);
map.put((suffix == null ? h[2] : h[2] + suffix), h[1]);
}
return map;
}, "java.io.InputStream,java.util.Map,~S");
c$.createJDXSource = Clazz.defineMethod(c$, "createJDXSource", 
function(file, $in, filePath, obscure, loadImaginary, iSpecFirst, iSpecLast, nmrMaxY){
var isHeaderOnly = (iSpecLast < iSpecFirst);
var data = null;
var br;
var bytes = null;
if (JU.AU.isAB($in)) {
bytes = $in;
if (JU.Rdr.isZipB(bytes)) {
return JSV.source.JDXReader.readBrukerFileZip(bytes, file == null ? filePath : file.getFullPath());
}}if ((typeof($in)=='string') || bytes != null) {
if ((typeof($in)=='string')) data = $in;
br = JSV.common.JSVFileManager.getBufferedReaderForStringOrBytes($in);
} else if (Clazz.instanceOf($in,"java.io.InputStream")) {
br = JSV.common.JSVFileManager.getBufferedReaderForInputStream($in);
} else {
br = $in;
}var header = null;
var source = null;
try {
if (br == null) {
if (file != null && file.isDirectory()) return JSV.source.JDXReader.readBrukerFileDir(file.getFullPath());
br = JSV.common.JSVFileManager.getBufferedReaderFromName(filePath, "##TITLE");
}if (!isHeaderOnly) {
br.mark(400);
var chs =  Clazz.newCharArray (400, '\0');
br.read(chs, 0, 400);
br.reset();
header =  String.instantialize(chs);
if (header.startsWith("PK")) {
br.close();
return JSV.source.JDXReader.readBrukerFileZip(null, file.getFullPath());
}if (header.indexOf('\0') >= 0 || header.indexOf("##TITLE= Parameter file") == 0 || header.indexOf("##TITLE= Audit trail") == 0) {
br.close();
return JSV.source.JDXReader.readBrukerFileDir(file.getParentAsFile().getFullPath());
}var pt1 = header.indexOf('#');
var pt2 = header.indexOf('<');
if (pt1 < 0 || pt2 >= 0 && pt2 < pt1) {
var xmlType = header.toLowerCase();
xmlType = (xmlType.contains("<animl") || xmlType.contains("<!doctype technique") ? "AnIML" : xmlType.contains("xml-cml") ? "CML" : null);
if (xmlType == null) return JSV.source.JDXReader.readBrukerFileDir(file.getFullPath());
source = (JSV.common.JSViewer.getInterface("JSV.source." + xmlType + "Reader")).getSource(filePath, br);
br.close();
if (source == null) {
JU.Logger.error(header + "...");
throw  new JSV.exception.JSVException("File type not recognized");
}}}if (source == null) {
source = ( new JSV.source.JDXReader(filePath, obscure, loadImaginary, iSpecFirst, iSpecLast, nmrMaxY)).getJDXSource(br, isHeaderOnly);
}if (data != null) source.setInlineData(data);
return source;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (!JSV.common.JSViewer.isJS) e.printStackTrace();
if (br != null) br.close();
if (header != null) JU.Logger.error(header + "...");
var s = e.getMessage();
{
}throw  new JSV.exception.JSVException("Error reading data: " + s);
} else {
throw e;
}
}
}, "J.api.GenericFileInterface,~O,~S,~B,~B,~N,~N,~N");
c$.readBrukerFileDir = Clazz.defineMethod(c$, "readBrukerFileDir", 
function(filePath){
return (javajs.api.Interface.getInterface("JSV.source.BrukerReader")).readBrukerDir(filePath);
}, "~S");
c$.readBrukerFileZip = Clazz.defineMethod(c$, "readBrukerFileZip", 
function(bytes, filePath){
return (javajs.api.Interface.getInterface("JSV.source.BrukerReader")).readBrukerZip(bytes, filePath);
}, "~A,~S");
Clazz.defineMethod(c$, "getJDXSource", 
function(reader, isHeaderOnly){
this.source =  new JSV.source.JDXSource(0, this.filePath);
this.isZipFile = (Clazz.instanceOf(reader,"JSV.api.JSVZipReader"));
this.t =  new JSV.source.JDXSourceStreamTokenizer(reader);
this.errorLog =  new JU.SB();
var label = null;
var value = null;
var isOK = false;
while (!this.done && "##TITLE".equals(this.t.peakLabel())) {
isOK = true;
if (label != null && !this.isZipFile) this.logError("Warning - file is a concatenation without LINK record -- does not conform to JCAMP-DX standard 6.1.3!");
var spectrum =  new JSV.common.Spectrum();
var dataLDRTable =  new JU.Lst();
if (isHeaderOnly) spectrum.setHeaderTable(dataLDRTable);
while (!this.done && (label = this.t.getLabel()) != null && (value = this.getValue(label)) != null) {
if (this.isTabularData) {
this.processTabularData(spectrum, dataLDRTable, label, isHeaderOnly);
this.addSpectrum(spectrum, false);
if (this.isSimulation && spectrum.getXUnits().equals("PPM")) spectrum.setHZtoPPM(true);
spectrum = null;
if (isHeaderOnly) {
JSV.source.JDXReader.addHeader(dataLDRTable, this.t.rawLabel, "<data>");
break;
}continue;
}if (!isHeaderOnly) {
if (label.equals("##DATATYPE") && value.toUpperCase().equals("LINK")) {
this.getBlockSpectra(dataLDRTable);
spectrum = null;
continue;
}if (label.equals("##NTUPLES") || label.equals("##VARNAME")) {
this.getNTupleSpectra(dataLDRTable, spectrum, label);
spectrum = null;
continue;
}}if (label.equals("##JCAMPDX")) {
this.setVenderSpecificValues(this.t.rawLine);
}if (spectrum == null) spectrum =  new JSV.common.Spectrum();
this.processLabel(spectrum, dataLDRTable, label, value, isHeaderOnly);
}
if (isHeaderOnly && spectrum != null) this.addSpectrum(spectrum, false);
}
if (!isOK) throw  new JSV.exception.JSVException("##TITLE record not found");
this.source.setErrorLog(this.errorLog.toString());
return this.source;
}, "~O,~B");
Clazz.defineMethod(c$, "processLabel", 
function(spectrum, dataLDRTable, label, value, isHeaderOnly){
if (!this.readDataLabel(spectrum, label, value, this.errorLog, this.obscure, isHeaderOnly) && !isHeaderOnly) return;
JSV.source.JDXReader.addHeader(dataLDRTable, this.t.rawLabel, value);
if (!isHeaderOnly) this.checkCustomTags(spectrum, label, value);
}, "JSV.common.Spectrum,JU.Lst,~S,~S,~B");
Clazz.defineMethod(c$, "logError", 
function(err){
this.errorLog.append(this.filePath == null || this.filePath.equals(this.lastErrPath) ? "" : this.filePath).append("\n").append(err).append("\n");
this.lastErrPath = this.filePath;
}, "~S");
Clazz.defineMethod(c$, "setVenderSpecificValues", 
function(rawLine){
if (rawLine.indexOf("JEOL") >= 0) {
System.out.println("Skipping ##SHIFTREFERENCE for JEOL " + rawLine);
this.ignoreShiftReference = true;
}if (rawLine.indexOf("MestReNova") >= 0) {
this.ignorePeakTables = true;
}}, "~S");
Clazz.defineMethod(c$, "getValue", 
function(label){
var value = (this.isTabularDataLabel(label) ? "" : this.t.getValue());
return ("##END".equals(label) ? null : value);
}, "~S");
Clazz.defineMethod(c$, "isTabularDataLabel", 
function(label){
return (this.isTabularData = ("##DATATABLE##PEAKTABLE##XYDATA##XYPOINTS#".indexOf(label + "#") >= 0));
}, "~S");
Clazz.defineMethod(c$, "addSpectrum", 
function(spectrum, forceSub){
if (!this.loadImaginary && spectrum.isImaginary()) {
JU.Logger.info("FileReader skipping imaginary spectrum -- use LOADIMAGINARY TRUE to load this spectrum.");
return true;
}if (this.acdAssignments != null) {
if (!spectrum.dataType.equals("MASS SPECTRUM") && !spectrum.isContinuous()) {
JU.Logger.info("Skipping ACD Labs line spectrum for " + spectrum);
return true;
}if (this.acdAssignments.size() > 0) {
try {
this.mpr.setACDAssignments(spectrum.title, spectrum.getTypeLabel(), this.source.peakCount, this.acdAssignments, this.acdMolFile);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.info("Failed to create peak data: " + e);
} else {
throw e;
}
}
}if (this.acdMolFile != null) JSV.common.JSVFileManager.cachePut("mol", this.acdMolFile);
}if (!Float.isNaN(this.nmrMaxY)) spectrum.normalizeSimulation(this.nmrMaxY);
 else if (spectrum.getMaxY() >= 10000) spectrum.normalizeSimulation(1000);
if (this.isSimulation) spectrum.setSimulated(this.filePath);
this.nSpec++;
if (this.firstSpec > 0 && this.nSpec < this.firstSpec) return true;
if (this.lastSpec > 0 && this.nSpec > this.lastSpec) return !(this.done = true);
spectrum.setBlockID(this.blockID);
this.source.addJDXSpectrum(null, spectrum, forceSub);
return true;
}, "JSV.common.Spectrum,~B");
Clazz.defineMethod(c$, "getBlockSpectra", 
function(sourceLDRTable){
JU.Logger.debug("--JDX block start--");
var label = "";
var value = null;
var isNew = (this.source.type == 0);
var forceSub = false;
while ((label = this.t.getLabel()) != null && !label.equals("##TITLE")) {
value = this.getValue(label);
if (isNew && !JSV.source.JDXReader.readHeaderLabel(this.source, label, value, this.errorLog, this.obscure)) JSV.source.JDXReader.addHeader(sourceLDRTable, this.t.rawLabel, value);
if (label.equals("##BLOCKS")) {
var nBlocks = JU.PT.parseInt(value);
if (nBlocks > 100 && this.firstSpec <= 0) forceSub = true;
}}
value = this.getValue(label);
if (!"##TITLE".equals(label)) throw  new JSV.exception.JSVException("Unable to read block source");
if (isNew) this.source.setHeaderTable(sourceLDRTable);
this.source.type = 1;
this.source.isCompoundSource = true;
var dataLDRTable;
var spectrum =  new JSV.common.Spectrum();
dataLDRTable =  new JU.Lst();
this.readDataLabel(spectrum, label, value, this.errorLog, this.obscure, false);
try {
var tmp;
while ((tmp = this.t.getLabel()) != null) {
if ((value = this.getValue(tmp)) == null && "##END".equals(label)) {
JU.Logger.debug("##END= " + this.t.getValue());
break;
}label = tmp;
if (this.isTabularData) {
this.processTabularData(spectrum, dataLDRTable, label, false);
continue;
}if (label.equals("##DATATYPE")) {
if (value.toUpperCase().equals("LINK")) {
this.getBlockSpectra(dataLDRTable);
spectrum = null;
label = null;
} else if (value.toUpperCase().startsWith("NMR PEAK")) {
if (this.ignorePeakTables) {
this.done = true;
return this.source;
}}} else if (label.equals("##NTUPLES") || label.equals("##VARNAME")) {
this.getNTupleSpectra(dataLDRTable, spectrum, label);
spectrum = null;
label = "";
}if (this.done) break;
if (spectrum == null) {
spectrum =  new JSV.common.Spectrum();
dataLDRTable =  new JU.Lst();
if (label === "") continue;
if (label == null) {
label = "##END";
continue;
}}if (value == null) {
if (spectrum.getXYCoords().length > 0 && !this.addSpectrum(spectrum, forceSub)) return this.source;
spectrum =  new JSV.common.Spectrum();
dataLDRTable =  new JU.Lst();
continue;
}this.processLabel(spectrum, dataLDRTable, label, value, false);
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (!JSV.common.JSViewer.isJS) e.printStackTrace();
throw  new JSV.exception.JSVException(e.getMessage());
} else {
throw e;
}
}
this.addErrorLogSeparator();
this.source.setErrorLog(this.errorLog.toString());
JU.Logger.debug("--JDX block end--");
return this.source;
}, "JU.Lst");
Clazz.defineMethod(c$, "addErrorLogSeparator", 
function(){
if (this.errorLog.length() > 0 && this.errorLog.lastIndexOf("=====================\n") != this.errorLog.length() - "=====================\n".length) this.logError("=====================\n");
});
Clazz.defineMethod(c$, "getNTupleSpectra", 
function(sourceLDRTable, spectrum0, label){
var minMaxY =  Clazz.newDoubleArray(-1, [1.7976931348623157E308, 4.9E-324]);
this.blockID = Math.random();
var isOK = true;
if (this.firstSpec > 0) spectrum0.setNumDim(1);
var isVARNAME = label.equals("##VARNAME");
if (!isVARNAME) {
label = "";
}var nTupleTable =  new java.util.Hashtable();
var plotSymbols =  new Array(2);
var isNew = (this.source.type == 0);
if (isNew) {
this.source.type = 2;
this.source.isCompoundSource = true;
this.source.setHeaderTable(sourceLDRTable);
}while (!(label = (isVARNAME ? label : this.t.getLabel())).equals("##PAGE")) {
isVARNAME = false;
var st =  new java.util.StringTokenizer(this.t.getValue(), ",");
var attrList =  new JU.Lst();
while (st.hasMoreTokens()) attrList.addLast(st.nextToken().trim());

nTupleTable.put(label, attrList);
}
var symbols = nTupleTable.get("##SYMBOL");
if (!label.equals("##PAGE")) throw  new JSV.exception.JSVException("Error Reading NTuple Source");
var page = this.t.getValue();
var spectrum = null;
var isFirst = true;
while (!this.done) {
if ((label = this.t.getLabel()).equals("##ENDNTUPLES")) {
this.t.getValue();
break;
}if (label.equals("##PAGE")) {
page = this.t.getValue();
continue;
}if (spectrum == null) {
spectrum =  new JSV.common.Spectrum();
spectrum0.copyTo(spectrum);
spectrum.setTitle(spectrum0.getTitle());
if (!spectrum.is1D()) {
var pt = page.indexOf('=');
if (pt >= 0) try {
spectrum.setY2D(this.parseAFFN(page.substring(0, pt), page.substring(pt + 1).trim()));
var y2dUnits = page.substring(0, pt).trim();
var i = symbols.indexOf(y2dUnits);
if (i >= 0) spectrum.setY2DUnits(nTupleTable.get("##UNITS").get(i));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
}}var dataLDRTable =  new JU.Lst();
spectrum.setHeaderTable(dataLDRTable);
while (!label.equals("##DATATABLE")) {
JSV.source.JDXReader.addHeader(dataLDRTable, this.t.rawLabel, this.t.getValue());
label = this.t.getLabel();
}
var continuous = true;
var line = this.t.flushLine();
if (line.trim().indexOf("PEAKS") > 0) continuous = false;
var index1 = line.indexOf('(');
var index2 = line.lastIndexOf(')');
if (index1 == -1 || index2 == -1) throw  new JSV.exception.JSVException("Variable List not Found");
var varList = line.substring(index1, index2 + 1);
var countSyms = 0;
for (var i = 0; i < symbols.size(); i++) {
var sym = symbols.get(i).trim();
if (varList.indexOf(sym) != -1) {
plotSymbols[countSyms++] = sym;
}if (countSyms == 2) break;
}
this.setTabularDataType(spectrum, "##" + (continuous ? "XYDATA" : "PEAKTABLE"));
if (!this.readNTUPLECoords(spectrum, nTupleTable, plotSymbols, minMaxY)) throw  new JSV.exception.JSVException("Unable to read Ntuple Source");
if (!spectrum.nucleusX.equals("?")) spectrum0.nucleusX = spectrum.nucleusX;
spectrum0.nucleusY = spectrum.nucleusY;
spectrum0.freq2dX = spectrum.freq2dX;
spectrum0.freq2dY = spectrum.freq2dY;
spectrum0.y2DUnits = spectrum.y2DUnits;
for (var i = 0; i < sourceLDRTable.size(); i++) {
var entry = sourceLDRTable.get(i);
var key = JSV.source.JDXSourceStreamTokenizer.cleanLabel(entry[0]);
if (!key.equals("##TITLE") && !key.equals("##DATACLASS") && !key.equals("##NTUPLES")) dataLDRTable.addLast(entry);
}
if (isOK) this.addSpectrum(spectrum, !isFirst);
isFirst = false;
spectrum = null;
}
this.addErrorLogSeparator();
this.source.setErrorLog(this.errorLog.toString());
JU.Logger.info("NTUPLE MIN/MAX Y = " + minMaxY[0] + " " + minMaxY[1]);
return this.source;
}, "JU.Lst,JSV.source.JDXDataObject,~S");
Clazz.defineMethod(c$, "readDataLabel", 
function(spectrum, label, value, errorLog, obscure, isHeaderOnly){
if (!JSV.source.JDXReader.readHeaderLabel(spectrum, label, value, errorLog, obscure)) return false;
label += " ";
if (("##MINX ##MINY ##MAXX ##MAXY ##FIRSTY ##DELTAX ##DATACLASS ").indexOf(label) >= 0) return false;
switch (("##FIRSTX  ##LASTX   ##NPOINTS ##XFACTOR ##YFACTOR ##XUNITS  ##YUNITS  ##XLABEL  ##YLABEL  ##NUMDIM  ##OFFSET  ").indexOf(label)) {
case 0:
spectrum.fileFirstX = this.parseAFFN(label, value);
return false;
case 10:
spectrum.fileLastX = this.parseAFFN(label, value);
return false;
case 20:
spectrum.fileNPoints = Integer.parseInt(value);
return false;
case 30:
spectrum.setXFactor(this.parseAFFN(label, value));
return false;
case 40:
spectrum.yFactor = this.parseAFFN(label, value);
return false;
case 50:
spectrum.setXUnits(value);
return false;
case 60:
spectrum.setYUnits(value);
return false;
case 70:
spectrum.setXLabel(value);
return true;
case 80:
spectrum.setYLabel(value);
return true;
case 90:
spectrum.setNumDim(Integer.parseInt(value));
return false;
case 100:
if (!spectrum.isShiftTypeSpecified()) {
spectrum.setShiftReference(this.parseAFFN(label, value), 1, 1);
}return false;
default:
if (label.length < 17) return true;
if (label.equals("##.OBSERVEFREQUENCY ")) {
spectrum.setObservedFreq(this.parseAFFN(label, value));
return false;
}if (label.equals("##.OBSERVENUCLEUS ")) {
spectrum.setObservedNucleus(value);
return false;
}if (label.equals("##$REFERENCEPOINT ") && !spectrum.isShiftTypeSpecified()) {
var pt = value.indexOf(" ");
if (pt > 0) value = value.substring(0, pt);
spectrum.setShiftReference(this.parseAFFN(label, value), 1, 2);
return false;
}if (label.equals("##.SHIFTREFERENCE ")) {
if (this.ignoreShiftReference || !(spectrum.dataType.toUpperCase().contains("SPECTRUM"))) return false;
value = JU.PT.replaceAllCharacters(value, ")(", "");
var srt =  new java.util.StringTokenizer(value, ",");
if (srt.countTokens() != 4) return false;
try {
srt.nextToken();
srt.nextToken();
var pt = Integer.parseInt(srt.nextToken().trim());
var shift = this.parseAFFN(label, srt.nextToken().trim());
spectrum.setShiftReference(shift, pt, 0);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return false;
}return true;
}
}, "JSV.source.JDXDataObject,~S,~S,JU.SB,~B,~B");
c$.readHeaderLabel = Clazz.defineMethod(c$, "readHeaderLabel", 
function(jdxHeader, label, value, errorLog, obscure){
switch (("##TITLE#####JCAMPDX###ORIGIN####OWNER#####DATATYPE##LONGDATE##DATE######TIME####").indexOf(label + "#")) {
case 0:
jdxHeader.setTitle(obscure || value == null || value.equals("") ? "Unknown" : value);
return false;
case 10:
jdxHeader.jcampdx = value;
var version = JU.PT.parseFloat(value);
if (version >= 6.0 || Float.isNaN(version)) {
if (errorLog != null) errorLog.append("Warning: JCAMP-DX version may not be fully supported: " + value);
}return false;
case 20:
jdxHeader.origin = (value != null && !value.equals("") ? value : "Unknown");
return false;
case 30:
jdxHeader.owner = (value != null && !value.equals("") ? value : "Unknown");
return false;
case 40:
jdxHeader.dataType = value;
return false;
case 50:
jdxHeader.longDate = value;
return false;
case 60:
jdxHeader.date = value;
return false;
case 70:
jdxHeader.time = value;
return false;
}
return true;
}, "JSV.source.JDXHeader,~S,~S,JU.SB,~B");
Clazz.defineMethod(c$, "setTabularDataType", 
function(spectrum, label){
if (label.equals("##PEAKASSIGNMENTS")) spectrum.setDataClass("PEAKASSIGNMENTS");
 else if (label.equals("##PEAKTABLE")) spectrum.setDataClass("PEAKTABLE");
 else if (label.equals("##XYDATA")) spectrum.setDataClass("XYDATA");
 else if (label.equals("##XYPOINTS")) spectrum.setDataClass("XYPOINTS");
}, "JSV.source.JDXDataObject,~S");
Clazz.defineMethod(c$, "processTabularData", 
function(spec, table, label, isHeaderOnly){
this.setTabularDataType(spec, label);
spec.setHeaderTable(table);
if (spec.dataClass.equals("XYDATA")) {
spec.checkJDXRequiredTokens();
if (!isHeaderOnly) this.decompressData(spec, null);
return;
}if (spec.dataClass.equals("PEAKTABLE") || spec.dataClass.equals("XYPOINTS")) {
spec.setContinuous(spec.dataClass.equals("XYPOINTS"));
try {
this.t.readLineTrimmed();
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
} else {
throw e;
}
}
var xyCoords;
if (spec.xFactor != 1.7976931348623157E308 && spec.yFactor != 1.7976931348623157E308) {
var data = this.t.getValue();
xyCoords = JSV.common.Coordinate.parseDSV(data, spec.xFactor, spec.yFactor);
} else {
xyCoords = JSV.common.Coordinate.parseDSV(this.t.getValue(), 1, 1);
}spec.setXYCoords(xyCoords);
var fileDeltaX = JSV.common.Coordinate.deltaX(xyCoords[xyCoords.length - 1].getXVal(), xyCoords[0].getXVal(), xyCoords.length);
spec.setIncreasing(fileDeltaX > 0);
return;
}throw  new JSV.exception.JSVException("Unable to read JDX file tabular data for line " + this.t.labelLineNo);
}, "JSV.source.JDXDataObject,JU.Lst,~S,~B");
Clazz.defineMethod(c$, "readNTUPLECoords", 
function(spec, nTupleTable, plotSymbols, minMaxY){
var list;
var label;
if (spec.dataClass.equals("XYDATA")) {
list = nTupleTable.get("##SYMBOL");
var index1 = list.indexOf(plotSymbols[0]);
var index2 = list.indexOf(plotSymbols[1]);
list = nTupleTable.get("##VARNAME");
spec.setVarName(list.get(index2).toUpperCase());
list = nTupleTable.get(label = "##FACTOR");
spec.setXFactor(this.parseAFFN(label, list.get(index1)));
spec.setYFactor(this.parseAFFN(label, list.get(index2)));
list = nTupleTable.get(label = "##LAST");
spec.fileLastX = this.parseAFFN(label, list.get(index1));
list = nTupleTable.get(label = "##FIRST");
spec.fileFirstX = this.parseAFFN(label, list.get(index1));
list = nTupleTable.get("##VARDIM");
spec.fileNPoints = Integer.parseInt(list.get(index1));
list = nTupleTable.get("##UNITS");
spec.setXUnits(list.get(index1));
spec.setYUnits(list.get(index2));
if (spec.nucleusX == null && (list = nTupleTable.get("##.NUCLEUS")) != null) {
spec.setNucleusAndFreq(list.get(0), false);
spec.setNucleusAndFreq(list.get(index1), true);
} else {
if (spec.nucleusX == null) spec.nucleusX = "?";
}this.decompressData(spec, minMaxY);
return true;
}if (spec.dataClass.equals("PEAKTABLE") || spec.dataClass.equals("XYPOINTS")) {
spec.setContinuous(spec.dataClass.equals("XYPOINTS"));
list = nTupleTable.get("##SYMBOL");
var index1 = list.indexOf(plotSymbols[0]);
var index2 = list.indexOf(plotSymbols[1]);
list = nTupleTable.get("##UNITS");
spec.setXUnits(list.get(index1));
spec.setYUnits(list.get(index2));
spec.setXYCoords(JSV.common.Coordinate.parseDSV(this.t.getValue(), spec.xFactor, spec.yFactor));
return true;
}return false;
}, "JSV.source.JDXDataObject,java.util.Map,~A,~A");
Clazz.defineMethod(c$, "parseAFFN", 
function(label, val){
var pt = val.indexOf("E");
if (pt > 0) {
var len = val.length;
var ch;
switch (len - pt) {
case 2:
case 3:
this.logError("Warning - " + label + " value " + val + " is not of the format xxxE[+/-]nn or xxxE[+/-]nnn (spec. 4.5.3) -- warning only; accepted");
break;
case 4:
case 5:
if ((ch = val.charAt(pt + 1)) == '+' || ch == '-') break;
default:
this.logError("Error - " + label + " value " + val + " is not of the format xxxE[+/-]nn or xxxE[+/-]nnn (spec. 4.5.3) -- " + val.substring(pt) + " ignored!");
val = val.substring(0, pt);
}
}return Double.parseDouble(val);
}, "~S,~S");
Clazz.defineMethod(c$, "decompressData", 
function(spec, minMaxY){
var errPt = this.errorLog.length();
spec.setIncreasing(spec.fileLastX > spec.fileFirstX);
spec.setContinuous(true);
var decompressor =  new JSV.source.JDXDecompressor(this.t, spec.fileFirstX, spec.fileLastX, spec.xFactor, spec.yFactor, spec.fileNPoints);
var t = System.currentTimeMillis();
var xyCoords = decompressor.decompressData(this.errorLog);
if (JU.Logger.debugging) JU.Logger.debug("decompression time = " + (System.currentTimeMillis() - t) + " ms");
spec.setXYCoords(xyCoords);
var d = decompressor.getMinY();
if (minMaxY != null) {
if (d < minMaxY[0]) minMaxY[0] = d;
d = decompressor.getMaxY();
if (d > minMaxY[1]) minMaxY[1] = d;
}spec.finalizeCoordinates();
if (this.errorLog.length() != errPt) {
var fileDeltaX = JSV.common.Coordinate.deltaX(spec.fileLastX, spec.fileFirstX, spec.fileNPoints);
this.logError(spec.getTitle());
this.logError("firstX from Header " + spec.fileFirstX);
this.logError("lastX from Header " + spec.fileLastX + " Found " + decompressor.lastX);
this.logError("deltaX from Header " + fileDeltaX);
this.logError("Number of points in Header " + spec.fileNPoints + " Found " + decompressor.getNPointsFound());
} else {
}if (JU.Logger.debugging) {
System.err.println(this.errorLog.toString());
}}, "JSV.source.JDXDataObject,~A");
c$.addHeader = Clazz.defineMethod(c$, "addHeader", 
function(table, label, value){
var entry = null;
for (var i = 0; i < table.size(); i++) if ((entry = table.get(i))[0].equals(label)) {
entry[1] = value;
return;
}
table.addLast( Clazz.newArray(-1, [label, value, JSV.source.JDXSourceStreamTokenizer.cleanLabel(label)]));
}, "JU.Lst,~S,~S");
Clazz.defineMethod(c$, "checkCustomTags", 
function(spectrum, label, value){
if (label.length > 10) label = label.substring(0, 10);
if (spectrum == null) System.out.println(label);
 else this.modelSpectrum = spectrum;
var pt = "##$MODELS ##$PEAKS  ##$SIGNALS##$MOLFILE##PEAKASSI##$UVIRASS##$MSFRAGM".indexOf(label);
if (pt < 0) return false;
this.getMpr().set(this, this.filePath, null);
try {
this.reader =  new java.io.BufferedReader( new java.io.StringReader(value));
switch (pt) {
case 0:
this.mpr.readModels();
break;
case 10:
case 20:
this.peakData =  new JU.Lst();
this.source.peakCount += this.mpr.readPeaks(pt == 20, this.source.peakCount);
break;
case 30:
this.acdAssignments =  new JU.Lst();
this.acdMolFile = JU.PT.rep(value, "$$ Empty String", "");
break;
case 40:
case 50:
case 60:
this.acdAssignments = this.mpr.readACDAssignments((spectrum).fileNPoints, pt == 40);
break;
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
throw  new JSV.exception.JSVException(e.getMessage());
} else {
throw e;
}
} finally {
this.reader = null;
}
return true;
}, "JSV.common.Spectrum,~S,~S");
Clazz.defineMethod(c$, "getMpr", 
function(){
return (this.mpr == null ? this.mpr = JSV.common.JSViewer.getInterface("J.jsv.JDXMOLParser") : this.mpr);
});
Clazz.overrideMethod(c$, "rd", 
function(){
return this.reader.readLine();
});
Clazz.overrideMethod(c$, "setSpectrumPeaks", 
function(nH, peakXLabel, peakYlabel){
this.modelSpectrum.setPeakList(this.peakData, peakXLabel, peakYlabel);
if (this.modelSpectrum.isNMR()) this.modelSpectrum.setHydrogenCount(nH);
}, "~N,~S,~S");
Clazz.overrideMethod(c$, "addPeakData", 
function(info){
if (this.peakData == null) this.peakData =  new JU.Lst();
this.peakData.addLast( new JSV.common.PeakInfo(info));
}, "~S");
Clazz.overrideMethod(c$, "processModelData", 
function(id, data, type, base, last, modelScale, vibScale, isFirst){
}, "~S,~S,~S,~S,~S,~N,~N,~B");
Clazz.overrideMethod(c$, "discardLinesUntilContains", 
function(containsMatch){
var line;
while ((line = this.rd()) != null && line.indexOf(containsMatch) < 0) {
}
return line;
}, "~S");
Clazz.overrideMethod(c$, "discardLinesUntilContains2", 
function(s1, s2){
var line;
while ((line = this.rd()) != null && line.indexOf(s1) < 0 && line.indexOf(s2) < 0) {
}
return line;
}, "~S,~S");
Clazz.overrideMethod(c$, "discardLinesUntilNonBlank", 
function(){
var line;
while ((line = this.rd()) != null && line.trim().length == 0) {
}
return line;
});
c$.VAR_LIST_TABLE =  Clazz.newArray(-1, ["PEAKTABLE   XYDATA      XYPOINTS", " (XY..XY)    (X++(Y..Y)) (XY..XY)    "]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
