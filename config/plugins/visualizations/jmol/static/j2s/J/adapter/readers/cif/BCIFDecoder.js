Clazz.declarePackage("J.adapter.readers.cif");
Clazz.load(null, "J.adapter.readers.cif.BCIFDecoder", ["JU.BC", "$.SB"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.dataType = 1;
this.type = null;
this.key = null;
this.encodings = null;
this.offsetDecoder = null;
this.dataDecoder = null;
this.maskDecoder = null;
this.data = null;
this.btype = 0;
this.byteLen = 0;
this.srcType = 0;
this.mode = 0;
this.unsigned = false;
this.srcSize = 0;
this.rowCount = 0;
this.catname = null;
this.name = null;
this.byteCount = 0;
this.origin = -2147483648;
this.factor = 0;
this.byteData = null;
this.stringData = null;
this.stringLen = 0;
this.floatDoubleData = null;
this.intData = null;
this.indices = null;
this.mask = null;
this.offsets = null;
this.isDecoded = false;
this.kind = '\0';
this.packingSize = 0;
this.dtype = null;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif, "BCIFDecoder", null);
Clazz.makeConstructor(c$, 
function(sb, key, map, byteData, ekey){
{
switch (arguments.length) {
case 3:
byteData = ekey = null;
break;
case 4:
ekey = key;
break;
}
}this.key = key;
var data = (byteData == null ? map.get("data") : byteData);
if (Clazz.instanceOf(data,"java.util.Map")) {
this.data = data;
data = this.data.get("data");
}if (Clazz.instanceOf(data,Array)) {
this.setByteData(data);
}if (ekey == null) {
if (this.data == null) {
this.encodings = map.get("encoding");
} else {
this.name = map.get("name");
this.encodings = this.data.get("encoding");
var mask = map.get("mask");
if (mask != null) {
this.maskDecoder =  new J.adapter.readers.cif.BCIFDecoder(sb, null, mask, null);
this.maskDecoder.dtype = "m";
}}} else {
this.encodings = map.get(ekey);
this.dtype = ekey.substring(0, 1);
}this.initializeEncodings(this.encodings, sb);
if (sb != null) {
this.type = this.debugGetDecoderType(this.encodings);
if (this.maskDecoder != null) this.type += ".mask." + this.maskDecoder.toString();
sb.append(this + "\n");
}}, "JU.SB,~S,java.util.Map,~O,~S");
Clazz.defineMethod(c$, "setRowCount", 
function(rowCount, catName){
this.rowCount = rowCount;
this.catname = catName;
return this;
}, "~N,~S");
Clazz.defineMethod(c$, "setByteData", 
function(data){
this.byteData = data;
this.byteLen = this.byteData.length;
}, "~O");
Clazz.overrideMethod(c$, "toString", 
function(){
return this.type + (this.dtype == null ? "" : this.dtype) + (this.btype == 0 ? "[" + this.byteLen + "]" : "(srcSize/rowcount=" + this.srcSize + "/" + this.rowCount + " mode=" + this.mode + " bt=" + this.btype + " bl=" + this.byteLen + " sl=" + this.stringLen + ")") + (this.key == null ? "" : ":" + this.key);
});
c$.getMapChar = Clazz.defineMethod(c$, "getMapChar", 
function(ht, key){
var s = ht.get(key);
return (s != null && s.length > 0 ? s.charAt(0) : 0);
}, "java.util.Map,~S");
c$.geMapInt = Clazz.defineMethod(c$, "geMapInt", 
function(o){
return (o == null ? 0 : (o).intValue());
}, "~O");
c$.getMapBool = Clazz.defineMethod(c$, "getMapBool", 
function(o){
return (o === Boolean.TRUE);
}, "~O");
Clazz.defineMethod(c$, "initializeEncodings", 
function(encodings, sb){
var n = encodings.length;
for (var i = 0; i < n; i++) {
var encoding = encodings[i];
var kind = J.adapter.readers.cif.BCIFDecoder.getMapChar(encoding, "kind");
if (encoding.containsKey("min")) {
kind = 'Q';
this.dataType = 0;
}if ((this.kind).charCodeAt(0) == 0) this.kind = kind;
switch ((kind).charCodeAt(0)) {
case 70:
this.factor = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("factor"));
this.dataType = 2;
this.mode |= 8;
break;
case 68:
this.origin = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("origin"));
this.mode |= 1;
break;
case 82:
this.mode |= 2;
this.srcSize = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("srcSize"));
break;
case 73:
this.mode |= 4;
this.packingSize = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("srcSize"));
if (this.srcSize == 0) this.srcSize = this.packingSize;
this.unsigned = J.adapter.readers.cif.BCIFDecoder.getMapBool(encoding.get("isUnsigned"));
continue;
case 66:
this.btype = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("type"));
this.byteCount = (this.btype == 33 ? 8 : this.btype == 32 ? 4 : 1 << (((this.btype - 1) % 3)));
if (this.btype >= 32) {
this.dataType = 2;
}continue;
case 83:
this.dataType = 3;
this.stringData = encoding.get("stringData");
this.stringLen = this.stringData.length;
this.dataDecoder =  new J.adapter.readers.cif.BCIFDecoder(sb, "dataEncoding", encoding, this.byteData);
this.offsetDecoder =  new J.adapter.readers.cif.BCIFDecoder(sb, "offsetEncoding", encoding, encoding.get("offsets"));
continue;
}
if (this.srcType == 0) {
this.srcType = J.adapter.readers.cif.BCIFDecoder.geMapInt(encoding.get("srcType"));
}}
}, "~A,JU.SB");
Clazz.defineMethod(c$, "finalizeDecoding", 
function(sb){
if (this.isDecoded) return this;
if (sb != null) sb.append("finalizing " + this + "\n");
this.isDecoded = true;
this.mask = (this.maskDecoder == null ? null : this.maskDecoder.finalizeDecoding(sb).intData);
if (this.mask != null && !J.adapter.readers.cif.BCIFDecoder.haveCheckMask(this.mask)) {
if (sb != null) sb.append("no valid data (mask completely \'.\' or \'?\'\n");
this.dataType = 0;
return null;
}if (this.mask != null && sb != null) sb.append("mask = " + J.adapter.readers.cif.BCIFDecoder.debugToStr(this.mask) + "\n");
if (this.dataDecoder != null) {
this.indices = this.dataDecoder.finalizeDecoding(sb).intData;
this.offsets = this.offsetDecoder.finalizeDecoding(sb).intData;
if (sb != null) {
sb.append("stringData = " + J.adapter.readers.cif.BCIFDecoder.debugToStr(this.stringData) + "\n");
sb.append("indices = " + J.adapter.readers.cif.BCIFDecoder.debugToStr(this.indices) + "\n");
sb.append("offsets = " + J.adapter.readers.cif.BCIFDecoder.debugToStr(this.offsets) + "\n");
}} else {
if (sb != null) sb.append("bytes->int " + Clazz.doubleToInt(this.byteData.length / this.byteCount) + " rc=" + this.rowCount + " ps=" + this.packingSize + "\n");
var run = null;
var len = this.srcSize;
if ((this.mode & 2) == 2) {
run = J.adapter.readers.cif.BCIFDecoder.getTemp(this.srcSize);
len = this.srcSize;
}if ((this.mode & 4) == 4) {
this.intData = J.adapter.readers.cif.BCIFDecoder.unpackInts(this.byteData, this.byteCount, len, this.unsigned, this.origin, run);
} else if (this.btype == 32 || this.btype == 33) {
this.floatDoubleData = this.bytesToFixedPt(this.byteData, this.btype == 32 ? 4 : 8);
} else {
this.intData = J.adapter.readers.cif.BCIFDecoder.bytesToInt(this.byteData, this.byteCount, len, this.unsigned, this.origin, run);
}}return this;
}, "JU.SB");
c$.haveCheckMask = Clazz.defineMethod(c$, "haveCheckMask", 
function(mask){
for (var i = mask.length; --i >= 0; ) {
if (mask[i] == 0) return true;
}
return false;
}, "~A");
Clazz.defineMethod(c$, "getStringValue", 
function(row){
if (this.dataType != 3 || this.mask != null && this.mask[row] != 0) return "\u0000";
var pt = this.indices[row];
return this.stringData.substring(this.offsets[pt++], (pt == this.rowCount ? this.stringLen : this.offsets[pt]));
}, "~N");
Clazz.defineMethod(c$, "getIntValue", 
function(row){
return (this.dataType != 1 || this.mask != null && this.mask[row] != 0 ? -2147483648 : this.intData[row]);
}, "~N");
Clazz.defineMethod(c$, "getFixedPtValue", 
function(row){
return (this.dataType != 2 || this.mask != null && this.mask[row] != 0 ? NaN : this.floatDoubleData == null ? this.intData[row] / this.factor : this.floatDoubleData[row]);
}, "~N");
Clazz.defineMethod(c$, "bytesToFixedPt", 
function(b, byteLen){
if (b == null) return null;
var n = Clazz.doubleToInt(b.length / byteLen);
var a =  Clazz.newFloatArray (n, 0);
try {
switch (byteLen) {
case 4:
for (var i = 0, j = 0; i < n; i++, j += 4) {
a[i] = JU.BC.bytesToFloat(b, j, false);
}
break;
case 8:
for (var i = 0, j = 0; i < n; i++, j += 8) {
a[i] = JU.BC.bytesToDoubleToFloat(b, j, false);
}
break;
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return a;
}, "~A,~N");
c$.bytesToInt = Clazz.defineMethod(c$, "bytesToInt", 
function(b, byteLen, rowCount, unsigned, origin, run){
if (b == null) return null;
var n = Clazz.doubleToInt(b.length / byteLen);
var ret =  Clazz.newIntArray (rowCount == 0 ? n : rowCount, 0);
var a = (run == null ? ret : run);
var ii;
switch (byteLen) {
case 1:
for (var i = 0, j = 0; i < n; i++, j++) {
ii = b[j] & 0xFF;
a[i] = (unsigned ? ii : ii > 0xEF ? ii - 0x100 : ii);
}
break;
case 2:
for (var i = 0, j = 0; i < n; i++, j += 2) {
ii = JU.BC.bytesToShort(b, j, false);
a[i] = (unsigned ? ii & 0xFFFF : ii);
}
break;
case 4:
for (var i = 0, j = 0; i < n; i++, j += 4) {
a[i] = JU.BC.bytesToInt(b, j, false);
}
break;
}
if (run != null) {
for (var p = 0, i = 0; i < n; ) {
var val = a[i++];
for (var j = a[i++]; --j >= 0; ) ret[p++] = val;

}
}if (origin != -2147483648) {
for (var i = 0; i < rowCount; i++) {
origin = ret[i] = origin + ret[i];
}
}return ret;
}, "~A,~N,~N,~B,~N,~A");
c$.unpackInts = Clazz.defineMethod(c$, "unpackInts", 
function(b, byteLen, srcSize, unsigned, origin, run){
if (b == null) return null;
var ret =  Clazz.newIntArray (srcSize, 0);
var a = (run == null ? ret : run);
var max;
switch (byteLen) {
case 1:
max = (unsigned ? 0xFF : 127);
for (var i = 0, pt = 0, n = b.length, offset = 0; pt < n; ) {
var val = b[pt++];
if (unsigned) val = val & max;
if (val == max || val == -128) {
offset += val;
} else {
a[i++] = val + offset;
offset = 0;
}}
break;
case 2:
max = (unsigned ? 0xFFFF : 32767);
for (var i = 0, pt = 0, n = Clazz.doubleToInt(b.length / 2), offset = 0; pt < n; ) {
var val = JU.BC.bytesToShort(b, (pt++) << 1, false);
if (unsigned) val = val & max;
if (val == max || val == -32768) {
offset += val;
} else {
a[i++] = val + offset;
offset = 0;
}}
break;
}
if (run != null) {
for (var p = 0, i = 0; p < srcSize; i++) {
var val = a[i];
for (var j = a[++i]; --j >= 0; ) ret[p++] = val;

}
}if (origin != -2147483648) {
for (var i = 0; i < srcSize; i++) {
origin = ret[i] = origin + ret[i];
}
}return ret;
}, "~A,~N,~N,~B,~N,~A");
c$.getTemp = Clazz.defineMethod(c$, "getTemp", 
function(n){
if (J.adapter.readers.cif.BCIFDecoder.temp == null || J.adapter.readers.cif.BCIFDecoder.temp.length < n) J.adapter.readers.cif.BCIFDecoder.temp =  Clazz.newIntArray (Math.max(n, 1000), 0);
return J.adapter.readers.cif.BCIFDecoder.temp;
}, "~N");
c$.clearTemp = Clazz.defineMethod(c$, "clearTemp", 
function(){
J.adapter.readers.cif.BCIFDecoder.temp = null;
});
c$.debugToStr = Clazz.defineMethod(c$, "debugToStr", 
function(o){
if (Clazz.instanceOf(o,Array)) return J.adapter.readers.cif.BCIFDecoder.debugToStrI(o);
if (Clazz.instanceOf(o,Array)) return J.adapter.readers.cif.BCIFDecoder.debugToStrB(o);
if (Clazz.instanceOf(o,Array)) return J.adapter.readers.cif.BCIFDecoder.debugToStrD(o);
if ((typeof(o)=='string')) {
var s = o;
return (s.length < 100 ? s : s.substring(0, 100) + "..." + s.length);
}return J.adapter.readers.cif.BCIFDecoder.debugToStrO(o);
}, "~O");
c$.debugToStrO = Clazz.defineMethod(c$, "debugToStrO", 
function(o){
var sb =  new JU.SB();
var sep = '[';
var n = Math.min(o.length, 20);
for (var i = 0; i < n; i++) {
sb.appendC(sep).appendO(o[i]);
sep = ',';
}
if (n < o.length) sb.append("...").appendI(o.length);
sb.appendC(']');
return sb.toString();
}, "~A");
c$.debugToStrI = Clazz.defineMethod(c$, "debugToStrI", 
function(o){
var sb =  new JU.SB();
var sep = '[';
var n = Math.min(o.length, 20);
for (var i = 0; i < n; i++) {
sb.appendC(sep).appendI(o[i]);
sep = ',';
}
if (n < o.length) sb.append("...").appendI(o.length);
sb.appendC(']');
return sb.toString();
}, "~A");
c$.debugToStrB = Clazz.defineMethod(c$, "debugToStrB", 
function(o){
var sb =  new JU.SB();
var sep = '[';
var n = Math.min(o.length, 20);
for (var i = 0; i < n; i++) {
sb.appendC(sep).appendI(o[i]);
sep = ',';
}
if (n < o.length) sb.append("...").appendI(o.length);
sb.appendC(']');
return sb.toString();
}, "~A");
c$.debugToStrD = Clazz.defineMethod(c$, "debugToStrD", 
function(o){
var sb =  new JU.SB();
var sep = '[';
var n = Math.min(o.length, 20);
for (var i = 0; i < n; i++) {
sb.appendC(sep).appendF(o[i]);
sep = ',';
}
if (n < o.length) sb.append("...").appendI(o.length);
sb.appendC(']');
return sb.toString();
}, "~A");
c$.temp = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
