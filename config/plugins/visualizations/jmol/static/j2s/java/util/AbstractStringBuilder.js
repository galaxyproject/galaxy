(function(){
var c$ = Clazz.decorateAsClass(function(){
this.value = null;
this.count = 0;
this.shared = false;
Clazz.instantialize(this, arguments);}, java.util, "AbstractStringBuilder", null);
Clazz.makeConstructor(c$, 
function(){
this.value =  Clazz.newCharArray (16, '\0');
});
Clazz.makeConstructor(c$, 
function(capacity){
if (capacity < 0) throw  new NegativeArraySizeException();
this.value =  Clazz.newCharArray (capacity, '\0');
}, "~N");
Clazz.makeConstructor(c$, 
function(string){
this.count = string.length;
this.shared = false;
this.value =  Clazz.newCharArray (this.count + 16, '\0');
string.getChars(0, this.count, this.value, 0);
}, "~S");
Clazz.defineMethod(c$, "getValue", 
function(){
return this.value;
});
Clazz.defineMethod(c$, "shareValue", 
function(){
this.shared = true;
return this.value;
});
Clazz.defineMethod(c$, "set", 
function(val, len){
if (val == null) val =  Clazz.newCharArray (0, '\0');
if (val.length < len) throw  new java.io.InvalidObjectException(("K0199"));
this.shared = false;
this.value = val;
this.count = len;
}, "~A,~N");
Clazz.defineMethod(c$, "enlargeBuffer", 
function(min){
var twice = (this.value.length << 1) + 2;
var newData =  Clazz.newCharArray (min > twice ? min : twice, '\0');
System.arraycopy(this.value, 0, newData, 0, this.count);
this.value = newData;
this.shared = false;
}, "~N");
Clazz.defineMethod(c$, "appendNull", 
function(){
var newSize = this.count + 4;
if (newSize > this.value.length) {
this.enlargeBuffer(newSize);
} else if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}this.value[this.count++] = 'n';
this.value[this.count++] = 'u';
this.value[this.count++] = 'l';
this.value[this.count++] = 'l';
});
Clazz.defineMethod(c$, "append0", 
function(chars){
var newSize = this.count + chars.length;
if (newSize > this.value.length) {
this.enlargeBuffer(newSize);
} else if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}System.arraycopy(chars, 0, this.value, this.count, chars.length);
this.count = newSize;
}, "~A");
Clazz.defineMethod(c$, "append0", 
function(chars, start, length){
if (chars == null) {
throw  new NullPointerException();
}if (start >= 0 && 0 <= length && length <= chars.length - start) {
var newSize = this.count + length;
if (newSize > this.value.length) {
this.enlargeBuffer(newSize);
} else if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}System.arraycopy(chars, start, this.value, this.count, length);
this.count = newSize;
} else {
throw  new ArrayIndexOutOfBoundsException();
}}, "~A,~N,~N");
Clazz.defineMethod(c$, "append0", 
function(ch){
if (this.count == this.value.length) {
this.enlargeBuffer(this.count + 1);
}if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}this.value[this.count++] = ch;
}, "~S");
Clazz.defineMethod(c$, "append0", 
function(string){
if (string == null) {
this.appendNull();
return;
}var adding = string.length;
var newSize = this.count + adding;
if (newSize > this.value.length) {
this.enlargeBuffer(newSize);
} else if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}string.getChars(0, adding, this.value, this.count);
this.count = newSize;
}, "~S");
Clazz.defineMethod(c$, "append0", 
function(s, start, end){
if (s == null) s = "null";
if (start < 0 || end < 0 || start > end || end > s.length) throw  new IndexOutOfBoundsException();
this.append0(s.subSequence(start, end).toString());
}, "CharSequence,~N,~N");
Clazz.defineMethod(c$, "capacity", 
function(){
return this.value.length;
});
Clazz.defineMethod(c$, "charAt", 
function(index){
if (index < 0 || index >= this.count) throw  new StringIndexOutOfBoundsException(index);
return this.value[index];
}, "~N");
Clazz.defineMethod(c$, "delete0", 
function(start, end){
if (start >= 0) {
if (end > this.count) {
end = this.count;
}if (end == start) {
return;
}if (end > start) {
var length = this.count - end;
if (length > 0) {
if (!this.shared) {
System.arraycopy(this.value, end, this.value, start, length);
} else {
var newData =  Clazz.newCharArray (this.value.length, '\0');
System.arraycopy(this.value, 0, newData, 0, start);
System.arraycopy(this.value, end, newData, start, length);
this.value = newData;
this.shared = false;
}}this.count -= end - start;
return;
}}throw  new StringIndexOutOfBoundsException();
}, "~N,~N");
Clazz.defineMethod(c$, "deleteCharAt0", 
function(location){
if (0 > location || location >= this.count) throw  new StringIndexOutOfBoundsException(location);
var length = this.count - location - 1;
if (length > 0) {
if (!this.shared) {
System.arraycopy(this.value, location + 1, this.value, location, length);
} else {
var newData =  Clazz.newCharArray (this.value.length, '\0');
System.arraycopy(this.value, 0, newData, 0, location);
System.arraycopy(this.value, location + 1, newData, location, length);
this.value = newData;
this.shared = false;
}}this.count--;
}, "~N");
Clazz.defineMethod(c$, "ensureCapacity", 
function(min){
if (min > this.value.length) {
this.enlargeBuffer(min);
}}, "~N");
Clazz.defineMethod(c$, "getChars", 
function(start, end, dest, destStart){
if (start > this.count || end > this.count || start > end) {
throw  new StringIndexOutOfBoundsException();
}System.arraycopy(this.value, start, dest, destStart, end - start);
}, "~N,~N,~A,~N");
Clazz.defineMethod(c$, "insert0", 
function(index, chars){
if (0 > index || index > this.count) {
throw  new StringIndexOutOfBoundsException(index);
}if (chars.length != 0) {
this.move(chars.length, index);
System.arraycopy(chars, 0, this.value, index, chars.length);
this.count += chars.length;
}}, "~N,~A");
Clazz.defineMethod(c$, "insert0", 
function(index, chars, start, length){
if (0 <= index && index <= this.count) {
if (start >= 0 && 0 <= length && length <= chars.length - start) {
if (length != 0) {
this.move(length, index);
System.arraycopy(chars, start, this.value, index, length);
this.count += length;
}return;
}throw  new StringIndexOutOfBoundsException("offset " + start + ", len " + length + ", array.length " + chars.length);
}throw  new StringIndexOutOfBoundsException(index);
}, "~N,~A,~N,~N");
Clazz.defineMethod(c$, "insert0", 
function(index, ch){
if (0 > index || index > this.count) {
throw  new ArrayIndexOutOfBoundsException(index);
}this.move(1, index);
this.value[index] = ch;
this.count++;
}, "~N,~S");
Clazz.defineMethod(c$, "insert0", 
function(index, string){
if (0 <= index && index <= this.count) {
if (string == null) string = "null";
var min = string.length;
if (min != 0) {
this.move(min, index);
string.getChars(0, min, this.value, index);
this.count += min;
}} else {
throw  new StringIndexOutOfBoundsException(index);
}}, "~N,~S");
Clazz.defineMethod(c$, "insert0", 
function(index, s, start, end){
if (s == null) s = "null";
if (index < 0 || index > this.count || start < 0 || end < 0 || start > end || end > s.length) throw  new IndexOutOfBoundsException();
this.insert0(index, s.subSequence(start, end).toString());
}, "~N,CharSequence,~N,~N");
Clazz.defineMethod(c$, "length", 
function(){
return this.count;
});
Clazz.defineMethod(c$, "move", 
function(size, index){
var newSize;
if (this.value.length - this.count >= size) {
if (!this.shared) {
System.arraycopy(this.value, index, this.value, index + size, this.count - index);
return;
}newSize = this.value.length;
} else {
var a = this.count + size;
var b = (this.value.length << 1) + 2;
newSize = a > b ? a : b;
}var newData =  Clazz.newCharArray (newSize, '\0');
System.arraycopy(this.value, 0, newData, 0, index);
System.arraycopy(this.value, index, newData, index + size, this.count - index);
this.value = newData;
this.shared = false;
}, "~N,~N");
Clazz.defineMethod(c$, "replace0", 
function(start, end, string){
if (start >= 0) {
if (end > this.count) end = this.count;
if (end > start) {
var stringLength = string.length;
var diff = end - start - stringLength;
if (diff > 0) {
if (!this.shared) {
System.arraycopy(this.value, end, this.value, start + stringLength, this.count - end);
} else {
var newData =  Clazz.newCharArray (this.value.length, '\0');
System.arraycopy(this.value, 0, newData, 0, start);
System.arraycopy(this.value, end, newData, start + stringLength, this.count - end);
this.value = newData;
this.shared = false;
}} else if (diff < 0) {
this.move(-diff, end);
} else if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}string.getChars(0, stringLength, this.value, start);
this.count -= diff;
return;
}if (start == end) {
if (string == null) throw  new NullPointerException();
this.insert0(start, string);
return;
}}throw  new StringIndexOutOfBoundsException();
}, "~N,~N,~S");
Clazz.defineMethod(c$, "reverse0", 
function(){
if (this.count < 2) {
return;
}if (!this.shared) {
for (var i = 0, end = this.count, mid = Clazz.doubleToInt(this.count / 2); i < mid; i++) {
var temp = this.value[--end];
this.value[end] = this.value[i];
this.value[i] = temp;
}
} else {
var newData =  Clazz.newCharArray (this.value.length, '\0');
for (var i = 0, end = this.count; i < this.count; i++) {
newData[--end] = this.value[i];
}
this.value = newData;
this.shared = false;
}});
Clazz.defineMethod(c$, "setCharAt", 
function(index, ch){
if (0 > index || index >= this.count) {
throw  new StringIndexOutOfBoundsException(index);
}if (this.shared) {
this.value = this.value.clone();
this.shared = false;
}this.value[index] = ch;
}, "~N,~S");
Clazz.defineMethod(c$, "setLength", 
function(length){
if (length < 0) throw  new StringIndexOutOfBoundsException(length);
if (this.count < length) {
if (length > this.value.length) {
this.enlargeBuffer(length);
} else {
if (this.shared) {
var newData =  Clazz.newCharArray (this.value.length, '\0');
System.arraycopy(this.value, 0, newData, 0, this.count);
this.value = newData;
this.shared = false;
} else {
for (var i = this.count; i < length; i++) {
this.value[i] = String.fromCharCode( 0);
}
}}}this.count = length;
}, "~N");
Clazz.defineMethod(c$, "substring", 
function(start){
if (0 <= start && start <= this.count) {
if (start == this.count) return "";
this.shared = true;
return  String.instantialize(this.value, start, this.count - start);
}throw  new StringIndexOutOfBoundsException(start);
}, "~N");
Clazz.defineMethod(c$, "substring", 
function(start, end){
if (0 <= start && start <= end && end <= this.count) {
if (start == end) return "";
this.shared = true;
return  String.instantialize(this.value, start, end - start);
}throw  new StringIndexOutOfBoundsException();
}, "~N,~N");
Clazz.overrideMethod(c$, "toString", 
function(){
if (this.count == 0) return "";
if (this.count >= 256 && this.count <= (this.value.length >> 1)) return  String.instantialize(this.value, 0, this.count);
this.shared = true;
return  String.instantialize(this.value, 0, this.count);
});
Clazz.defineMethod(c$, "subSequence", 
function(start, end){
return this.substring(start, end);
}, "~N,~N");
Clazz.defineMethod(c$, "indexOf", 
function(string){
return this.indexOf(string, 0);
}, "~S");
Clazz.defineMethod(c$, "indexOf", 
function(subString, start){
if (start < 0) start = 0;
var subCount = subString.length;
if (subCount > 0) {
if (subCount + start > this.count) return -1;
var firstChar = subString.charAt(0);
while (true) {
var i = start;
var found = false;
for (; i < this.count; i++) if (this.value[i] == firstChar) {
found = true;
break;
}
if (!found || subCount + i > this.count) return -1;
var o1 = i;
var o2 = 0;
while (++o2 < subCount && this.value[++o1] == subString.charAt(o2)) {
}
if (o2 == subCount) return i;
start = i + 1;
}
}return (start < this.count || start == 0) ? start : this.count;
}, "~S,~N");
Clazz.defineMethod(c$, "lastIndexOf", 
function(string){
return this.lastIndexOf(string, this.count);
}, "~S");
Clazz.defineMethod(c$, "lastIndexOf", 
function(subString, start){
var subCount = subString.length;
if (subCount <= this.count && start >= 0) {
if (subCount > 0) {
if (start > this.count - subCount) start = this.count - subCount;
var firstChar = subString.charAt(0);
while (true) {
var i = start;
var found = false;
for (; i >= 0; --i) if (this.value[i] == firstChar) {
found = true;
break;
}
if (!found) return -1;
var o1 = i;
var o2 = 0;
while (++o2 < subCount && this.value[++o1] == subString.charAt(o2)) {
}
if (o2 == subCount) return i;
start = i - 1;
}
}return start < this.count ? start : this.count;
}return -1;
}, "~S,~N");
Clazz.defineMethod(c$, "trimToSize", 
function(){
if (this.count < this.value.length) {
var newValue =  Clazz.newCharArray (this.count, '\0');
System.arraycopy(this.value, 0, newValue, 0, this.count);
this.value = newValue;
this.shared = false;
}});
})();
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
