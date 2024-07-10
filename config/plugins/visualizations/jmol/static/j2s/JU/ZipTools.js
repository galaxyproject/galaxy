Clazz.declarePackage("JU");
Clazz.load(["javajs.api.GenericZipTools"], "JU.ZipTools", ["java.io.BufferedInputStream", "java.util.zip.CRC32", "$.GZIPInputStream", "$.ZipEntry", "javajs.api.GenericZipInputStream", "$.Interface", "JU.BArray", "$.Lst", "$.Rdr", "$.SB"], function(){
var c$ = Clazz.declareType(JU, "ZipTools", null, javajs.api.GenericZipTools);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "newZipInputStream", 
function(is){
return JU.ZipTools.newZIS(is);
}, "java.io.InputStream");
c$.newZIS = Clazz.defineMethod(c$, "newZIS", 
function(is){
return (Clazz.instanceOf(is,"java.util.zip.ZipInputStream") ? is : Clazz.instanceOf(is,"java.io.BufferedInputStream") ?  new javajs.api.GenericZipInputStream(is) :  new javajs.api.GenericZipInputStream( new java.io.BufferedInputStream(is)));
}, "java.io.InputStream");
Clazz.overrideMethod(c$, "getAllZipData", 
function(is, subfileList, name0, binaryFileList, exclude, fileData){
}, "java.io.InputStream,~A,~S,~S,~S,java.util.Map");
Clazz.overrideMethod(c$, "getZipFileDirectory", 
function(bis, list, listPtr, asBufferedInputStream){
var ret;
var justDir = (list == null || listPtr >= list.length);
var fileName = (justDir ? "." : list[listPtr]);
if (JU.Rdr.isTar(bis)) return JU.ZipTools.getTarFileDirectory(bis, fileName, asBufferedInputStream);
if (justDir) return this.getZipDirectoryAsStringAndClose(bis);
bis = JU.Rdr.getPngZipStream(bis, true);
var zis = JU.ZipTools.newZIS(bis);
var ze;
try {
var isAll = (fileName.equals("."));
if (isAll || fileName.lastIndexOf("/") == fileName.length - 1) {
ret =  new JU.SB();
while ((ze = zis.getNextEntry()) != null) {
var name = ze.getName();
if (isAll || name.startsWith(fileName)) ret.append(name).appendC('\n');
}
var str = ret.toString();
return (asBufferedInputStream ? JU.Rdr.getBIS(str.getBytes()) : str);
}var pt = fileName.indexOf(":asBinaryString");
var asBinaryString = (pt > 0);
if (asBinaryString) fileName = fileName.substring(0, pt);
fileName = fileName.$replace('\\', '/');
while ((ze = zis.getNextEntry()) != null && !fileName.equals(ze.getName())) {
}
var bytes = (ze == null ? null : JU.Rdr.getLimitedStreamBytes(zis, ze.getSize()));
ze = null;
zis.close();
if (bytes == null) return "";
if (JU.Rdr.isZipB(bytes) || JU.Rdr.isPngZipB(bytes)) return this.getZipFileDirectory(JU.Rdr.getBIS(bytes), list, ++listPtr, asBufferedInputStream);
if (asBufferedInputStream) return JU.Rdr.getBIS(bytes);
if (asBinaryString) {
ret =  new JU.SB();
for (var i = 0; i < bytes.length; i++) ret.append(Integer.toHexString(bytes[i] & 0xFF)).appendC(' ');

return ret.toString();
}if (JU.Rdr.isGzipB(bytes)) bytes = JU.Rdr.getLimitedStreamBytes(this.getUnGzippedInputStream(bytes), -1);
return JU.Rdr.fixUTF(bytes);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return "";
} else {
throw e;
}
}
}, "java.io.BufferedInputStream,~A,~N,~B");
c$.getTarFileDirectory = Clazz.defineMethod(c$, "getTarFileDirectory", 
function(bis, fileName, asBufferedInputStream){
var ret;
try {
var isAll = (fileName.equals("."));
if (isAll || fileName.lastIndexOf("/") == fileName.length - 1) {
ret =  new JU.SB();
JU.ZipTools.getTarContents(bis, fileName, ret);
var str = ret.toString();
return (asBufferedInputStream ? JU.Rdr.getBIS(str.getBytes()) : str);
}fileName = fileName.$replace('\\', '/');
var bytes = JU.ZipTools.getTarContents(bis, fileName, null);
bis.close();
return (bytes == null ? "" : asBufferedInputStream ? JU.Rdr.getBIS(bytes) : JU.Rdr.fixUTF(bytes));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return "";
} else {
throw e;
}
}
}, "java.io.BufferedInputStream,~S,~B");
Clazz.overrideMethod(c$, "getZipFileContentsAsBytes", 
function(bis, list, listPtr){
var ret =  Clazz.newByteArray (0, 0);
var fileName = list[listPtr];
if (fileName.lastIndexOf("/") == fileName.length - 1) return ret;
try {
if (JU.Rdr.isTar(bis)) return JU.ZipTools.getTarContents(bis, fileName, null);
bis = JU.Rdr.getPngZipStream(bis, true);
var zis = JU.ZipTools.newZIS(bis);
var ze;
while ((ze = zis.getNextEntry()) != null) {
if (!fileName.equals(ze.getName())) continue;
var bytes = JU.Rdr.getLimitedStreamBytes(zis, ze.getSize());
return ((JU.Rdr.isZipB(bytes) || JU.Rdr.isPngZipB(bytes)) && ++listPtr < list.length ? this.getZipFileContentsAsBytes(JU.Rdr.getBIS(bytes), list, listPtr) : bytes);
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return ret;
}, "java.io.BufferedInputStream,~A,~N");
c$.getTarContents = Clazz.defineMethod(c$, "getTarContents", 
function(bis, fileName, sb){
if (JU.ZipTools.b512 == null) JU.ZipTools.b512 =  Clazz.newByteArray (512, 0);
var len = fileName.length;
while (bis.read(JU.ZipTools.b512, 0, 512) > 0) {
var bytes = JU.ZipTools.getTarFile(bis, fileName, len, sb, null, false);
if (bytes != null) return bytes;
}
return null;
}, "java.io.BufferedInputStream,~S,JU.SB");
c$.getTarFile = Clazz.defineMethod(c$, "getTarFile", 
function(bis, fileName, len, sb, cache, oneFile){
var j = 124;
while (JU.ZipTools.b512[j] == 48) j++;

var isAll = (sb != null && fileName.equals("."));
var nbytes = 0;
while (j < 135) nbytes = (nbytes << 3) + (JU.ZipTools.b512[j++] - 48);

if (nbytes == 0) return null;
var fname =  String.instantialize(JU.ZipTools.b512, 0, 100).trim();
var prefix =  String.instantialize(JU.ZipTools.b512, 345, 155).trim();
var name = prefix + fname;
var found = false;
if (sb != null) {
if (name.length == 0) return null;
if (isAll || (oneFile ? name.equalsIgnoreCase(fileName) : name.startsWith(fileName))) {
found = (cache != null);
sb.append(name).appendC('\n');
}len = -1;
}var nul = (512 - (nbytes % 512)) % 512;
if (!found && (len != name.length || !fileName.equals(name))) {
var nBlocks = (nbytes + nul) >> 9;
for (var i = nBlocks; --i >= 0; ) bis.read(JU.ZipTools.b512, 0, 512);

return null;
}var bytes = JU.Rdr.getLimitedStreamBytes(bis, nbytes);
if (cache != null) {
cache.put(name,  new JU.BArray(bytes));
bis.read(JU.ZipTools.b512, 0, nul);
}return bytes;
}, "java.io.BufferedInputStream,~S,~N,JU.SB,java.util.Map,~B");
Clazz.overrideMethod(c$, "getZipDirectoryAsStringAndClose", 
function(bis){
var sb =  new JU.SB();
var s =  new Array(0);
try {
s = this.getZipDirectoryOrErrorAndClose(bis, null);
bis.close();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.out.println(e.toString());
} else {
throw e;
}
}
for (var i = 0; i < s.length; i++) sb.append(s[i]).appendC('\n');

return sb.toString();
}, "java.io.BufferedInputStream");
Clazz.overrideMethod(c$, "getZipDirectoryAndClose", 
function(bis, manifestID){
var s =  new Array(0);
try {
s = this.getZipDirectoryOrErrorAndClose(bis, manifestID);
bis.close();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.out.println(e.toString());
} else {
throw e;
}
}
return s;
}, "java.io.BufferedInputStream,~S");
Clazz.defineMethod(c$, "getZipDirectoryOrErrorAndClose", 
function(bis, manifestID){
bis = JU.Rdr.getPngZipStream(bis, true);
var v =  new JU.Lst();
var zis = JU.ZipTools.newZIS(bis);
var ze;
var manifest = null;
while ((ze = zis.getNextEntry()) != null) {
var fileName = ze.getName();
if (manifestID != null && fileName.startsWith(manifestID)) manifest = JU.ZipTools.getStreamAsString(zis);
 else if (!fileName.startsWith("__MACOS")) v.addLast(fileName);
}
zis.close();
if (manifestID != null) v.add(0, manifest == null ? "" : manifest + "\n############\n");
return v.toArray( new Array(v.size()));
}, "java.io.BufferedInputStream,~S");
c$.getStreamAsString = Clazz.defineMethod(c$, "getStreamAsString", 
function(is){
return JU.Rdr.fixUTF(JU.Rdr.getLimitedStreamBytes(is, -1));
}, "java.io.InputStream");
Clazz.overrideMethod(c$, "newGZIPInputStream", 
function(is){
return  new java.io.BufferedInputStream( new java.util.zip.GZIPInputStream(is, 512));
}, "java.io.InputStream");
Clazz.overrideMethod(c$, "newBZip2InputStream", 
function(is){
return  new java.io.BufferedInputStream((javajs.api.Interface.getInterface("org.apache.tools.bzip2.CBZip2InputStreamFactory")).getStream(is));
}, "java.io.InputStream");
Clazz.overrideMethod(c$, "getUnGzippedInputStream", 
function(bytes){
try {
return JU.Rdr.getUnzippedInputStream(this, JU.Rdr.getBIS(bytes));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return null;
} else {
throw e;
}
}
}, "~A");
Clazz.overrideMethod(c$, "addZipEntry", 
function(zos, fileName){
(zos).putNextEntry( new java.util.zip.ZipEntry(fileName));
}, "~O,~S");
Clazz.overrideMethod(c$, "closeZipEntry", 
function(zos){
(zos).closeEntry();
}, "~O");
Clazz.overrideMethod(c$, "getZipOutputStream", 
function(bos){
{
return javajs.api.Interface.getInterface(
"java.util.zip.ZipOutputStream").setZOS(bos);
}}, "~O");
Clazz.overrideMethod(c$, "getCrcValue", 
function(bytes){
var crc =  new java.util.zip.CRC32();
crc.update(bytes, 0, bytes.length);
return crc.getValue();
}, "~A");
Clazz.overrideMethod(c$, "readFileAsMap", 
function(bis, bdata, name){
JU.ZipTools.readFileAsMapStatic(bis, bdata, name);
}, "java.io.BufferedInputStream,java.util.Map,~S");
c$.readFileAsMapStatic = Clazz.defineMethod(c$, "readFileAsMapStatic", 
function(bis, bdata, name){
var pt = (name == null ? -1 : name.indexOf("|"));
name = (pt >= 0 ? name.substring(pt + 1) : null);
try {
var isZip = false;
if (JU.Rdr.isPngZipStream(bis)) {
var isImage = "_IMAGE_".equals(name);
if (name == null || isImage) bdata.put((isImage ? "_DATA_" : "_IMAGE_"),  new JU.BArray(JU.ZipTools.getPngImageBytes(bis)));
isZip = !isImage;
} else if (JU.Rdr.isZipS(bis)) {
isZip = true;
} else if (JU.Rdr.isTar(bis)) {
JU.ZipTools.cacheTarContentsStatic(bis, name, bdata);
} else if (name == null) {
bdata.put("_DATA_",  new JU.BArray(JU.Rdr.getLimitedStreamBytes(bis, -1)));
} else {
throw  new java.io.IOException("ZIP file " + name + " not found");
}if (isZip) JU.ZipTools.cacheZipContentsStatic(bis, name, bdata, true);
bdata.put("$_BINARY_$", Boolean.TRUE);
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
bdata.clear();
bdata.put("_ERROR_", e.getMessage());
} else {
throw e;
}
}
}, "java.io.BufferedInputStream,java.util.Map,~S");
c$.cacheTarContentsStatic = Clazz.defineMethod(c$, "cacheTarContentsStatic", 
function(bis, fileName, cache){
var listing =  new JU.SB();
var n = 0;
if (fileName != null && fileName.endsWith("/.")) fileName = fileName.substring(0, fileName.length - 1);
var isPath = (fileName != null && fileName.endsWith("/"));
var justOne = (fileName != null && !isPath);
try {
if (JU.ZipTools.b512 == null) JU.ZipTools.b512 =  Clazz.newByteArray (512, 0);
while (bis.read(JU.ZipTools.b512, 0, 512) > 0) {
var bytes = JU.ZipTools.getTarFile(bis, fileName == null ? "." : fileName, -1, listing, cache, justOne);
if (bytes != null) {
n += bytes.length;
if (justOne) break;
}}
bis.close();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
try {
bis.close();
} catch (e1) {
if (Clazz.exceptionOf(e1,"java.io.IOException")){
} else {
throw e1;
}
}
return null;
} else {
throw e;
}
}
if (n == 0 || fileName == null) return null;
System.out.println("ZipTools cached " + n + " bytes from " + fileName);
return listing.toString();
}, "java.io.BufferedInputStream,~S,java.util.Map");
Clazz.overrideMethod(c$, "cacheZipContents", 
function(bis, fileName, cache, asByteArray){
return JU.ZipTools.cacheZipContentsStatic(bis, fileName, cache, asByteArray);
}, "java.io.BufferedInputStream,~S,java.util.Map,~B");
c$.cacheZipContentsStatic = Clazz.defineMethod(c$, "cacheZipContentsStatic", 
function(bis, fileName, cache, asByteArray){
var zis = JU.ZipTools.newZIS(bis);
var ze;
var listing =  new JU.SB();
var n = 0;
if (fileName != null && fileName.endsWith("/.")) fileName = fileName.substring(0, fileName.length - 1);
var isPath = (fileName != null && fileName.endsWith("/"));
var oneFile = (fileName != null && !isPath && asByteArray);
var pt = (oneFile ? fileName.indexOf("|") : -1);
var zipEntryRoot = (pt >= 0 ? fileName : null);
if (pt >= 0) fileName = fileName.substring(0, pt);
var prefix = (fileName == null || isPath ? "" : fileName + "|");
try {
while ((ze = zis.getNextEntry()) != null) {
if (ze.isDirectory()) continue;
var name = ze.getName();
if (fileName != null) {
if (oneFile) {
if (!name.equalsIgnoreCase(fileName)) continue;
} else {
if (isPath && !name.startsWith(fileName)) continue;
listing.append(name).appendC('\n');
}}var nBytes = ze.getSize();
var bytes = JU.Rdr.getLimitedStreamBytes(zis, nBytes);
if (zipEntryRoot != null) {
JU.ZipTools.readFileAsMapStatic(JU.Rdr.getBIS(bytes), cache, zipEntryRoot);
return null;
}n += bytes.length;
var o = (asByteArray ?  new JU.BArray(bytes) : bytes);
cache.put((oneFile ? "_DATA_" : prefix + name), o);
if (oneFile) break;
}
zis.close();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
try {
zis.close();
} catch (e1) {
if (Clazz.exceptionOf(e1,"java.io.IOException")){
} else {
throw e1;
}
}
return null;
} else {
throw e;
}
}
if (n == 0 || fileName == null) return null;
System.out.println("ZipTools cached " + n + " bytes from " + fileName);
return listing.toString();
}, "java.io.BufferedInputStream,~S,java.util.Map,~B");
c$.getPngImageBytes = Clazz.defineMethod(c$, "getPngImageBytes", 
function(bis){
try {
if (JU.Rdr.isPngZipStream(bis)) {
var pt_count =  Clazz.newIntArray (2, 0);
JU.Rdr.getPngZipPointAndCount(bis, pt_count);
if (pt_count[1] != 0) return JU.ZipTools.deActivatePngZipB(JU.Rdr.getLimitedStreamBytes(bis, pt_count[0]));
}return JU.Rdr.getLimitedStreamBytes(bis, -1);
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
return null;
} else {
throw e;
}
}
}, "java.io.BufferedInputStream");
c$.deActivatePngZipB = Clazz.defineMethod(c$, "deActivatePngZipB", 
function(bytes){
if (JU.Rdr.isPngZipB(bytes)) bytes[51] = 32;
return bytes;
}, "~A");
Clazz.overrideMethod(c$, "isZipStream", 
function(br){
return Clazz.instanceOf(br,"javajs.api.ZInputStream");
}, "~O");
c$.b512 = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
