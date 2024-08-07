Clazz.load(["java.util.AbstractList", "$.List", "$.RandomAccess"], "java.util.ArrayList", ["java.util.Arrays"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.firstIndex = 0;
this.lastIndex = 0;
this.array = null;
Clazz.instantialize(this, arguments);}, java.util, "ArrayList", java.util.AbstractList, [java.util.List, Cloneable, java.io.Serializable, java.util.RandomAccess]);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, java.util.ArrayList, []);
this.setCapacity(0);
});
Clazz.makeConstructor(c$, 
function(capacity){
Clazz.superConstructor (this, java.util.ArrayList, []);
this.setCapacity(capacity);
}, "~N");
Clazz.makeConstructor(c$, 
function(collection){
this.firstIndex = this.lastIndex = 0;
var n = -1;
{
if (!collection) {
n = 0;
} else if (typeof collection == "number") {
n = collection;
}
}if (n >= 0) {
this.setCapacity(n);
return;
}var size = collection.size();
this.array = this.newElementArray(size + (Clazz.doubleToInt(size / 10)));
this.addAll(collection);
}, "java.util.Collection");
Clazz.defineMethod(c$, "setCapacity", 
function(capacity){
try {
this.array = this.newElementArray(capacity);
} catch (e) {
if (Clazz.exceptionOf(e,"NegativeArraySizeException")){
throw  new IllegalArgumentException();
} else {
throw e;
}
}
}, "~N");
Clazz.defineMethod(c$, "newElementArray", 
function(size){
return  new Array(size);
}, "~N");
Clazz.defineMethod(c$, "add", 
function(location, object){
this.add2(location, object);
}, "~N,~O");
Clazz.defineMethod(c$, "add2", 
function(location, object){
var size = this.size();
if (0 < location && location < size) {
if (this.firstIndex == 0 && this.lastIndex == this.array.length) {
this.growForInsert(location, 1);
} else if ((location < Clazz.doubleToInt(size / 2) && this.firstIndex > 0) || this.lastIndex == this.array.length) {
System.arraycopy(this.array, this.firstIndex, this.array, --this.firstIndex, location);
} else {
var index = location + this.firstIndex;
System.arraycopy(this.array, index, this.array, index + 1, size - location);
this.lastIndex++;
}this.array[location + this.firstIndex] = object;
} else if (location == 0) {
if (this.firstIndex == 0) {
this.growAtFront(1);
}this.array[--this.firstIndex] = object;
} else if (location == size) {
if (this.lastIndex == this.array.length) {
this.growAtEnd(1);
}this.array[this.lastIndex++] = object;
} else {
throw  new IndexOutOfBoundsException();
}this.modCount++;
}, "~N,~O");
Clazz.defineMethod(c$, "add", 
function(object){
return this.add1(object);
}, "~O");
Clazz.defineMethod(c$, "add1", 
function(object){
if (this.lastIndex == this.array.length) {
this.growAtEnd(1);
}this.array[this.lastIndex++] = object;
this.modCount++;
return true;
}, "~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
var size = this.size();
if (location < 0 || location > size) {
throw  new IndexOutOfBoundsException();
}var growSize = collection.size();
if (0 < location && location < size) {
if (this.array.length - size < growSize) {
this.growForInsert(location, growSize);
} else if ((location < Clazz.doubleToInt(size / 2) && this.firstIndex > 0) || this.lastIndex > this.array.length - growSize) {
var newFirst = this.firstIndex - growSize;
if (newFirst < 0) {
var index = location + this.firstIndex;
System.arraycopy(this.array, index, this.array, index - newFirst, size - location);
this.lastIndex -= newFirst;
newFirst = 0;
}System.arraycopy(this.array, this.firstIndex, this.array, newFirst, location);
this.firstIndex = newFirst;
} else {
var index = location + this.firstIndex;
System.arraycopy(this.array, index, this.array, index + growSize, size - location);
this.lastIndex += growSize;
}} else if (location == 0) {
this.growAtFront(growSize);
this.firstIndex -= growSize;
} else if (location == size) {
if (this.lastIndex > this.array.length - growSize) {
this.growAtEnd(growSize);
}this.lastIndex += growSize;
}if (growSize > 0) {
var it = collection.iterator();
var index = location + this.firstIndex;
var end = index + growSize;
while (index < end) {
this.array[index++] = it.next();
}
this.modCount++;
return true;
}return false;
}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "addAll", 
function(collection){
var growSize = collection.size();
if (growSize > 0) {
if (this.lastIndex > this.array.length - growSize) {
this.growAtEnd(growSize);
}var it = collection.iterator();
var end = this.lastIndex + growSize;
while (this.lastIndex < end) {
this.array[this.lastIndex++] = it.next();
}
this.modCount++;
return true;
}return false;
}, "java.util.Collection");
Clazz.overrideMethod(c$, "clear", 
function(){
if (this.firstIndex != this.lastIndex) {
java.util.Arrays.fill(this.array, this.firstIndex, this.lastIndex, null);
this.firstIndex = this.lastIndex = 0;
this.modCount++;
}});
Clazz.defineMethod(c$, "clone", 
function(){
try {
var newList = Clazz.superCall(this, java.util.ArrayList, "clone", []);
newList.array = this.array.clone();
return newList;
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
});
Clazz.overrideMethod(c$, "contains", 
function(object){
if (object != null) {
for (var i = this.firstIndex; i < this.lastIndex; i++) {
if (object.equals(this.array[i])) {
return true;
}}
} else {
for (var i = this.firstIndex; i < this.lastIndex; i++) {
if (this.array[i] == null) {
return true;
}}
}return false;
}, "~O");
Clazz.defineMethod(c$, "ensureCapacity", 
function(minimumCapacity){
if (this.array.length < minimumCapacity) {
if (this.firstIndex > 0) {
this.growAtFront(minimumCapacity - this.array.length);
} else {
this.growAtEnd(minimumCapacity - this.array.length);
}}}, "~N");
Clazz.overrideMethod(c$, "get", 
function(location){
if (0 <= location && location < this.size()) {
return this.array[this.firstIndex + location];
}throw  new IndexOutOfBoundsException();
}, "~N");
Clazz.defineMethod(c$, "growAtEnd", 
function(required){
var size = this.size();
if (this.firstIndex >= required - (this.array.length - this.lastIndex)) {
var newLast = this.lastIndex - this.firstIndex;
if (size > 0) {
System.arraycopy(this.array, this.firstIndex, this.array, 0, size);
var start = newLast < this.firstIndex ? this.firstIndex : newLast;
java.util.Arrays.fill(this.array, start, this.array.length, null);
}this.firstIndex = 0;
this.lastIndex = newLast;
} else {
var increment = Clazz.doubleToInt(size / 2);
if (required > increment) {
increment = required;
}if (increment < 12) {
increment = 12;
}var newArray = this.newElementArray(size + increment);
if (size > 0) {
System.arraycopy(this.array, this.firstIndex, newArray, this.firstIndex, size);
}this.array = newArray;
}}, "~N");
Clazz.defineMethod(c$, "growAtFront", 
function(required){
var size = this.size();
if (this.array.length - this.lastIndex >= required) {
var newFirst = this.array.length - size;
if (size > 0) {
System.arraycopy(this.array, this.firstIndex, this.array, newFirst, size);
var length = this.firstIndex + size > newFirst ? newFirst : this.firstIndex + size;
java.util.Arrays.fill(this.array, this.firstIndex, length, null);
}this.firstIndex = newFirst;
this.lastIndex = this.array.length;
} else {
var increment = Clazz.doubleToInt(size / 2);
if (required > increment) {
increment = required;
}if (increment < 12) {
increment = 12;
}var newArray = this.newElementArray(size + increment);
if (size > 0) {
System.arraycopy(this.array, this.firstIndex, newArray, newArray.length - size, size);
}this.firstIndex = newArray.length - size;
this.lastIndex = newArray.length;
this.array = newArray;
}}, "~N");
Clazz.defineMethod(c$, "growForInsert", 
function(location, required){
var size = this.size();
var increment = Clazz.doubleToInt(size / 2);
if (required > increment) {
increment = required;
}if (increment < 12) {
increment = 12;
}var newArray = this.newElementArray(size + increment);
if (location < Clazz.doubleToInt(size / 2)) {
var newFirst = newArray.length - (size + required);
System.arraycopy(this.array, location, newArray, location + increment, size - location);
System.arraycopy(this.array, this.firstIndex, newArray, newFirst, location);
this.firstIndex = newFirst;
this.lastIndex = newArray.length;
} else {
System.arraycopy(this.array, this.firstIndex, newArray, 0, location);
System.arraycopy(this.array, location, newArray, location + required, size - location);
this.firstIndex = 0;
this.lastIndex += required;
}this.array = newArray;
}, "~N,~N");
Clazz.overrideMethod(c$, "indexOf", 
function(object){
if (object != null) {
for (var i = this.firstIndex; i < this.lastIndex; i++) {
if (object.equals(this.array[i])) {
return i - this.firstIndex;
}}
} else {
for (var i = this.firstIndex; i < this.lastIndex; i++) {
if (this.array[i] == null) {
return i - this.firstIndex;
}}
}return -1;
}, "~O");
Clazz.overrideMethod(c$, "isEmpty", 
function(){
return this.lastIndex == this.firstIndex;
});
Clazz.overrideMethod(c$, "lastIndexOf", 
function(object){
if (object != null) {
for (var i = this.lastIndex - 1; i >= this.firstIndex; i--) {
if (object.equals(this.array[i])) {
return i - this.firstIndex;
}}
} else {
for (var i = this.lastIndex - 1; i >= this.firstIndex; i--) {
if (this.array[i] == null) {
return i - this.firstIndex;
}}
}return -1;
}, "~O");
Clazz.defineMethod(c$, "remove", 
function(location){
{
}return this._removeItemAt(location);
}, "~N");
Clazz.defineMethod(c$, "_removeObject", 
function(o){
var i = this.indexOf(o);
if (i < 0) return false;
this._removeItemAt(i);
return true;
}, "~O");
Clazz.defineMethod(c$, "_removeItemAt", 
function(location){
var result;
var size = this.size();
if (0 <= location && location < size) {
if (location == size - 1) {
result = this.array[--this.lastIndex];
this.array[this.lastIndex] = null;
} else if (location == 0) {
result = this.array[this.firstIndex];
this.array[this.firstIndex++] = null;
} else {
var elementIndex = this.firstIndex + location;
result = this.array[elementIndex];
if (location < Clazz.doubleToInt(size / 2)) {
System.arraycopy(this.array, this.firstIndex, this.array, this.firstIndex + 1, location);
this.array[this.firstIndex++] = null;
} else {
System.arraycopy(this.array, elementIndex + 1, this.array, elementIndex, size - location - 1);
this.array[--this.lastIndex] = null;
}}} else {
throw  new IndexOutOfBoundsException();
}this.modCount++;
return result;
}, "~N");
Clazz.overrideMethod(c$, "removeRange", 
function(start, end){
if (start >= 0 && start <= end && end <= this.size()) {
if (start == end) {
return;
}var size = this.size();
if (end == size) {
java.util.Arrays.fill(this.array, this.firstIndex + start, this.lastIndex, null);
this.lastIndex = this.firstIndex + start;
} else if (start == 0) {
java.util.Arrays.fill(this.array, this.firstIndex, this.firstIndex + end, null);
this.firstIndex += end;
} else {
System.arraycopy(this.array, this.firstIndex + end, this.array, this.firstIndex + start, size - end);
var newLast = this.lastIndex + start - end;
java.util.Arrays.fill(this.array, newLast, this.lastIndex, null);
this.lastIndex = newLast;
}this.modCount++;
} else {
throw  new IndexOutOfBoundsException();
}}, "~N,~N");
Clazz.overrideMethod(c$, "set", 
function(location, object){
if (0 <= location && location < this.size()) {
var result = this.array[this.firstIndex + location];
this.array[this.firstIndex + location] = object;
return result;
}throw  new IndexOutOfBoundsException();
}, "~N,~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.lastIndex - this.firstIndex;
});
Clazz.overrideMethod(c$, "toArray", 
function(contents){
var size = this.size();
if (contents == null || size > contents.length) {
{
return this.array.slice(this.firstIndex, this.firstIndex + size);
}}System.arraycopy(this.array, this.firstIndex, contents, 0, size);
if (size < contents.length) {
contents[size] = null;
}return contents;
}, "~A");
Clazz.defineMethod(c$, "trimToSize", 
function(){
var size = this.size();
var newArray = this.newElementArray(size);
System.arraycopy(this.array, this.firstIndex, newArray, 0, size);
this.array = newArray;
this.firstIndex = 0;
this.lastIndex = this.array.length;
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
