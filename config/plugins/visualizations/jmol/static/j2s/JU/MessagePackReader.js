Clazz.declarePackage("JU");
Clazz.load(null, "JU.MessagePackReader", ["java.util.Hashtable", "JU.BC", "$.BinaryDocument", "$.SB"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.doc = null;
this.isHomo = false;
Clazz.instantialize(this, arguments);}, JU, "MessagePackReader", null);
Clazz.makeConstructor(c$, 
function(binaryDoc, isHomogeneousArrays){
this.isHomo = isHomogeneousArrays;
this.doc = binaryDoc;
}, "javajs.api.GenericBinaryDocumentReader,~B");
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "getMapForStream", 
function(is){
this.doc =  new JU.BinaryDocument().setStream(is, true);
var map = this.readMap();
is.close();
return map;
}, "java.io.BufferedInputStream");
Clazz.defineMethod(c$, "readMap", 
function(){
return this.getNext(null, 0);
});
Clazz.defineMethod(c$, "getNext", 
function(array, pt){
var b = this.doc.readByte() & 0xFF;
var be0 = b & 0xE0;
if ((b & 128) == 0) {
if (array != null) {
(array)[pt] = b;
return null;
}return Integer.$valueOf(b);
}switch (be0) {
case 224:
b = JU.BC.intToSignedInt(b | 0xFFFFFF00);
if (array != null) {
(array)[pt] = b;
return null;
}return Integer.$valueOf(b);
case 160:
{
var s = this.doc.readString(b & 0x1F);
if (array != null) {
(array)[pt] = s;
return null;
}return s;
}case 128:
return ((b & 0xF0) == 128 ? this.getMap(b & 0x0F) : this.getArray(b & 0x0F));
case 192:
switch (b) {
case 192:
return null;
case 194:
return Boolean.FALSE;
case 195:
return Boolean.TRUE;
case 199:
return this.getObject(this.doc.readUInt8());
case 200:
return this.getObject(this.doc.readUnsignedShort());
case 201:
return this.getObject(this.doc.readInt());
case 212:
return this.getObject(1);
case 213:
return this.getObject(2);
case 214:
return this.getObject(4);
case 215:
return this.getObject(8);
case 216:
return this.getObject(16);
case 220:
return this.getArray(this.doc.readUnsignedShort());
case 221:
return this.getArray(this.doc.readInt());
case 222:
return this.getMap(this.doc.readUnsignedShort());
case 223:
return this.getMap(this.doc.readInt());
case 196:
return this.doc.readBytes(this.doc.readUInt8());
case 197:
return this.doc.readBytes(this.doc.readUnsignedShort());
case 198:
return this.doc.readBytes(this.doc.readInt());
}
if (array == null) {
switch (b) {
case 202:
return Float.$valueOf(this.doc.readFloat());
case 203:
return Float.$valueOf(this.doc.readDouble());
case 204:
return Integer.$valueOf(this.doc.readUInt8());
case 205:
return Integer.$valueOf(this.doc.readUnsignedShort());
case 206:
return Integer.$valueOf(this.doc.readInt());
case 207:
return Long.$valueOf(this.doc.readLong());
case 208:
return Integer.$valueOf(this.doc.readByte());
case 209:
return Integer.$valueOf(this.doc.readShort());
case 210:
return Integer.$valueOf(this.doc.readInt());
case 211:
return Long.$valueOf(this.doc.readLong());
case 217:
return this.doc.readString(this.doc.readUInt8());
case 218:
return this.doc.readString(this.doc.readUnsignedShort());
case 219:
return this.doc.readString(this.doc.readInt());
}
} else {
switch (b) {
case 202:
(array)[pt] = this.doc.readFloat();
break;
case 203:
(array)[pt] = this.doc.readDouble();
break;
case 204:
(array)[pt] = this.doc.readUInt8();
break;
case 205:
(array)[pt] = this.doc.readUnsignedShort();
break;
case 206:
(array)[pt] = this.doc.readInt();
break;
case 207:
(array)[pt] = this.doc.readLong();
break;
case 208:
(array)[pt] = this.doc.readByte();
break;
case 209:
(array)[pt] = this.doc.readShort();
break;
case 210:
(array)[pt] = this.doc.readInt();
break;
case 211:
(array)[pt] = this.doc.readLong();
break;
case 217:
(array)[pt] = this.doc.readString(this.doc.readUInt8());
break;
case 218:
(array)[pt] = this.doc.readString(this.doc.readUnsignedShort());
break;
case 219:
(array)[pt] = this.doc.readString(this.doc.readInt());
break;
}
}}
return null;
}, "~O,~N");
Clazz.defineMethod(c$, "getObject", 
function(n){
return  Clazz.newArray(-1, [Integer.$valueOf(this.doc.readUInt8()), this.doc.readBytes(n)]);
}, "~N");
Clazz.defineMethod(c$, "getArray", 
function(n){
if (this.isHomo) {
if (n == 0) return null;
var v = this.getNext(null, 0);
if (Clazz.instanceOf(v, Integer)) {
var a =  Clazz.newIntArray (n, 0);
a[0] = (v).intValue();
v = a;
} else if (Clazz.instanceOf(v, Float)) {
var a =  Clazz.newFloatArray (n, 0);
a[0] = (v).floatValue();
v = a;
} else if ((typeof(v)=='string')) {
var a =  new Array(n);
a[0] = v;
v = a;
} else {
var o =  new Array(n);
o[0] = v;
for (var i = 1; i < n; i++) o[i] = this.getNext(null, 0);

return o;
}for (var i = 1; i < n; i++) this.getNext(v, i);

return v;
}var o =  new Array(n);
for (var i = 0; i < n; i++) o[i] = this.getNext(null, 0);

return o;
}, "~N");
Clazz.defineMethod(c$, "getMap", 
function(n){
var map =  new java.util.Hashtable();
for (var i = 0; i < n; i++) {
var key = this.getNext(null, 0).toString();
var value = this.getNext(null, 0);
if (value == null) {
} else {
map.put(key, value);
}}
return map;
}, "~N");
c$.decode = Clazz.defineMethod(c$, "decode", 
function(b){
var type = JU.BC.bytesToInt(b, 0, true);
var n = JU.BC.bytesToInt(b, 4, true);
var param = JU.BC.bytesToInt(b, 8, true);
switch (type) {
case 1:
return JU.MessagePackReader.getFloats(b, n, 1);
case 2:
case 3:
case 4:
return JU.MessagePackReader.getInts(b, n);
case 5:
return JU.MessagePackReader.rldecode32ToStr(b);
case 6:
return JU.MessagePackReader.rldecode32ToChar(b, n);
case 7:
return JU.MessagePackReader.rldecode32(b, n);
case 8:
return JU.MessagePackReader.rldecode32Delta(b, n);
case 9:
return JU.MessagePackReader.rldecodef(b, n, param);
case 10:
return JU.MessagePackReader.unpack16Deltaf(b, n, param);
case 11:
return JU.MessagePackReader.getFloats(b, n, param);
case 12:
case 13:
return JU.MessagePackReader.unpackf(b, 14 - type, n, param);
case 14:
case 15:
return JU.MessagePackReader.unpack(b, 16 - type, n);
default:
System.out.println("MMTF type " + type + " not found!");
return null;
}
}, "~A");
c$.getFloats = Clazz.defineMethod(c$, "getFloats", 
function(b, n, divisor){
if (b == null) return null;
var a =  Clazz.newFloatArray (n, 0);
try {
switch (Clazz.doubleToInt((b.length - 12) / n)) {
case 2:
for (var i = 0, j = 12; i < n; i++, j += 2) a[i] = JU.BC.bytesToShort(b, j, false) / divisor;

break;
case 4:
for (var i = 0, j = 12; i < n; i++, j += 4) a[i] = JU.BC.bytesToFloat(b, j, false);

break;
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return a;
}, "~A,~N,~N");
c$.getInts = Clazz.defineMethod(c$, "getInts", 
function(b, n){
if (b == null) return null;
var a =  Clazz.newIntArray (n, 0);
switch (Clazz.doubleToInt((b.length - 12) / n)) {
case 1:
for (var i = 0, j = 12; i < n; i++, j++) a[i] = b[j];

break;
case 2:
for (var i = 0, j = 12; i < n; i++, j += 2) a[i] = JU.BC.bytesToShort(b, j, true);

break;
case 4:
for (var i = 0, j = 12; i < n; i++, j += 4) a[i] = JU.BC.bytesToInt(b, j, true);

break;
}
return a;
}, "~A,~N");
c$.rldecode32ToStr = Clazz.defineMethod(c$, "rldecode32ToStr", 
function(b){
var id =  new Array(Clazz.doubleToInt((b.length - 12) / 4));
out : for (var i = 0, len = id.length, pt = 12; i < len; i++) {
var sb =  new JU.SB();
for (var j = 0; j < 4; j++) {
switch (b[pt]) {
case 0:
id[i] = sb.toString();
pt += 4 - j;
continue out;
default:
sb.appendC(String.fromCharCode(b[pt++]));
if (j == 3) id[i] = sb.toString();
continue;
}
}
}
return id;
}, "~A");
c$.rldecode32ToChar = Clazz.defineMethod(c$, "rldecode32ToChar", 
function(b, n){
if (b == null) return null;
var ret =  Clazz.newCharArray (n, '\0');
for (var i = 0, pt = 3; i < n; ) {
var val = String.fromCharCode(b[((pt++) << 2) + 3]);
for (var j = JU.BC.bytesToInt(b, (pt++) << 2, true); --j >= 0; ) ret[i++] = val;

}
return ret;
}, "~A,~N");
c$.rldecode32 = Clazz.defineMethod(c$, "rldecode32", 
function(b, n){
if (b == null) return null;
var ret =  Clazz.newIntArray (n, 0);
for (var i = 0, pt = 3; i < n; ) {
var val = JU.BC.bytesToInt(b, (pt++) << 2, true);
for (var j = JU.BC.bytesToInt(b, (pt++) << 2, true); --j >= 0; ) ret[i++] = val;

}
return ret;
}, "~A,~N");
c$.rldecode32Delta = Clazz.defineMethod(c$, "rldecode32Delta", 
function(b, n){
if (b == null) return null;
var ret =  Clazz.newIntArray (n, 0);
for (var i = 0, pt = 3, val = 0; i < n; ) {
var diff = JU.BC.bytesToInt(b, (pt++) << 2, true);
for (var j = JU.BC.bytesToInt(b, (pt++) << 2, true); --j >= 0; ) ret[i++] = (val = val + diff);

}
return ret;
}, "~A,~N");
c$.rldecodef = Clazz.defineMethod(c$, "rldecodef", 
function(b, n, divisor){
if (b == null) return null;
var ret =  Clazz.newFloatArray (n, 0);
for (var i = 0, pt = 3; i < n; ) {
var val = JU.BC.bytesToInt(b, (pt++) << 2, true);
for (var j = JU.BC.bytesToInt(b, (pt++) << 2, true); --j >= 0; ) ret[i++] = val / divisor;

}
return ret;
}, "~A,~N,~N");
c$.unpack16Deltaf = Clazz.defineMethod(c$, "unpack16Deltaf", 
function(b, n, divisor){
if (b == null) return null;
var ret =  Clazz.newFloatArray (n, 0);
for (var i = 0, pt = 6, val = 0, buf = 0; i < n; ) {
var diff = JU.BC.bytesToShort(b, (pt++) << 1, true);
if (diff == 32767 || diff == -32768) {
buf += diff;
} else {
ret[i++] = (val = val + diff + buf) / divisor;
buf = 0;
}}
return ret;
}, "~A,~N,~N");
c$.unpackf = Clazz.defineMethod(c$, "unpackf", 
function(b, nBytes, n, divisor){
if (b == null) return null;
var ret =  Clazz.newFloatArray (n, 0);
switch (nBytes) {
case 1:
for (var i = 0, pt = 12, offset = 0; i < n; ) {
var val = b[pt++];
if (val == 127 || val == -128) {
offset += val;
} else {
ret[i++] = (val + offset) / divisor;
offset = 0;
}}
break;
case 2:
for (var i = 0, pt = 6, offset = 0; i < n; ) {
var val = JU.BC.bytesToShort(b, (pt++) << 1, true);
if (val == 32767 || val == -32768) {
offset += val;
} else {
ret[i++] = (val + offset) / divisor;
offset = 0;
}}
break;
}
return ret;
}, "~A,~N,~N,~N");
c$.unpack = Clazz.defineMethod(c$, "unpack", 
function(b, nBytes, n){
if (b == null) return null;
var ret =  Clazz.newIntArray (n, 0);
switch (nBytes) {
case 1:
for (var i = 0, pt = 12, offset = 0; i < n; ) {
var val = b[pt++];
if (val == 127 || val == -128) {
offset += val;
} else {
ret[i++] = val + offset;
offset = 0;
}}
break;
case 2:
for (var i = 0, pt = 6, offset = 0; i < n; ) {
var val = JU.BC.bytesToShort(b, (pt++) << 1, true);
if (val == 32767 || val == -32768) {
offset += val;
} else {
ret[i++] = val + offset;
offset = 0;
}}
break;
}
return ret;
}, "~A,~N,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
