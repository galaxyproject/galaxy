Clazz.load(["java.util.AbstractMap", "$.AbstractSet", "$.Iterator", "$.Map", "$.MapEntry"], "java.util.IdentityHashMap", ["java.util.AbstractCollection", "java.util.MapEntry.Type"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.elementData = null;
this.$size = 0;
this.threshold = 0;
this.modCount = 0;
Clazz.instantialize(this, arguments);}, java.util, "IdentityHashMap", java.util.AbstractMap, [java.util.Map, java.io.Serializable, Cloneable]);
Clazz.makeConstructor(c$, 
function(){
this.construct (21);
});
Clazz.makeConstructor(c$, 
function(maxSize){
Clazz.superConstructor (this, java.util.IdentityHashMap, []);
if (maxSize >= 0) {
this.$size = 0;
this.threshold = this.getThreshold(maxSize);
this.elementData = this.newElementArray(this.computeElementArraySize());
} else {
throw  new IllegalArgumentException();
}}, "~N");
Clazz.makeConstructor(c$, 
function(map){
this.construct (map.size() < 6 ? 11 : map.size() * 2);
this.putAllImpl(map);
}, "java.util.Map");
Clazz.defineMethod(c$, "getThreshold", 
function(maxSize){
return maxSize > 3 ? maxSize : 3;
}, "~N");
Clazz.defineMethod(c$, "computeElementArraySize", 
function(){
return (Clazz.doubleToInt((this.threshold * 10000) / 7500)) * 2;
});
Clazz.defineMethod(c$, "newElementArray", 
function(s){
return  new Array(s);
}, "~N");
Clazz.defineMethod(c$, "massageValue", 
function(value){
return ((value === java.util.IdentityHashMap.NULL_OBJECT) ? null : value);
}, "~O");
Clazz.overrideMethod(c$, "clear", 
function(){
this.$size = 0;
for (var i = 0; i < this.elementData.length; i++) {
this.elementData[i] = null;
}
this.modCount++;
});
Clazz.overrideMethod(c$, "containsKey", 
function(key){
if (key == null) {
key = java.util.IdentityHashMap.NULL_OBJECT;
}var index = this.findIndex(key, this.elementData);
return this.elementData[index] === key;
}, "~O");
Clazz.overrideMethod(c$, "containsValue", 
function(value){
if (value == null) {
value = java.util.IdentityHashMap.NULL_OBJECT;
}for (var i = 1; i < this.elementData.length; i = i + 2) {
if (this.elementData[i] === value) {
return true;
}}
return false;
}, "~O");
Clazz.overrideMethod(c$, "get", 
function(key){
if (key == null) {
key = java.util.IdentityHashMap.NULL_OBJECT;
}var index = this.findIndex(key, this.elementData);
if (this.elementData[index] === key) {
var result = this.elementData[index + 1];
return this.massageValue(result);
}return null;
}, "~O");
Clazz.defineMethod(c$, "getEntry", 
function(key){
if (key == null) {
key = java.util.IdentityHashMap.NULL_OBJECT;
}var index = this.findIndex(key, this.elementData);
if (this.elementData[index] === key) {
return this.getEntry(index);
}return null;
}, "~O");
Clazz.defineMethod(c$, "getEntry", 
function(index){
var key = this.elementData[index];
var value = this.elementData[index + 1];
if (key === java.util.IdentityHashMap.NULL_OBJECT) {
key = null;
}if (value === java.util.IdentityHashMap.NULL_OBJECT) {
value = null;
}return  new java.util.IdentityHashMap.IdentityHashMapEntry(key, value);
}, "~N");
Clazz.defineMethod(c$, "findIndex", 
function(key, array){
var length = array.length;
var index = this.getModuloHash(key, length);
var last = (index + length - 2) % length;
while (index != last) {
if (array[index] === key || (array[index] == null)) {
break;
}index = (index + 2) % length;
}
return index;
}, "~O,~A");
Clazz.defineMethod(c$, "getModuloHash", 
function(key, length){
return ((System.identityHashCode(key) & 0x7FFFFFFF) % (Clazz.doubleToInt(length / 2))) * 2;
}, "~O,~N");
Clazz.overrideMethod(c$, "put", 
function(key, value){
var _key = key;
var _value = value;
if (_key == null) {
_key = java.util.IdentityHashMap.NULL_OBJECT;
}if (_value == null) {
_value = java.util.IdentityHashMap.NULL_OBJECT;
}var index = this.findIndex(_key, this.elementData);
if (this.elementData[index] !== _key) {
this.modCount++;
if (++this.$size > this.threshold) {
this.rehash();
index = this.findIndex(_key, this.elementData);
}this.elementData[index] = _key;
this.elementData[index + 1] = null;
}var result = this.elementData[index + 1];
this.elementData[index + 1] = _value;
return this.massageValue(result);
}, "~O,~O");
Clazz.overrideMethod(c$, "putAll", 
function(map){
this.putAllImpl(map);
}, "java.util.Map");
Clazz.defineMethod(c$, "rehash", 
function(){
var newlength = this.elementData.length << 1;
if (newlength == 0) {
newlength = 1;
}var newData = this.newElementArray(newlength);
for (var i = 0; i < this.elementData.length; i = i + 2) {
var key = this.elementData[i];
if (key != null) {
var index = this.findIndex(key, newData);
newData[index] = key;
newData[index + 1] = this.elementData[i + 1];
}}
this.elementData = newData;
this.computeMaxSize();
});
Clazz.defineMethod(c$, "computeMaxSize", 
function(){
this.threshold = (Clazz.doubleToInt((Clazz.doubleToInt(this.elementData.length / 2)) * 7500 / 10000));
});
Clazz.overrideMethod(c$, "remove", 
function(key){
if (key == null) {
key = java.util.IdentityHashMap.NULL_OBJECT;
}var hashedOk;
var index;
var next;
var hash;
var result;
var object;
index = next = this.findIndex(key, this.elementData);
if (this.elementData[index] !== key) {
return null;
}result = this.elementData[index + 1];
var length = this.elementData.length;
while (true) {
next = (next + 2) % length;
object = this.elementData[next];
if (object == null) {
break;
}hash = this.getModuloHash(object, length);
hashedOk = hash > index;
if (next < index) {
hashedOk = hashedOk || (hash <= next);
} else {
hashedOk = hashedOk && (hash <= next);
}if (!hashedOk) {
this.elementData[index] = object;
this.elementData[index + 1] = this.elementData[next + 1];
index = next;
}}
this.$size--;
this.modCount++;
this.elementData[index] = null;
this.elementData[index + 1] = null;
return this.massageValue(result);
}, "~O");
Clazz.overrideMethod(c$, "entrySet", 
function(){
return  new java.util.IdentityHashMap.IdentityHashMapEntrySet(this);
});
Clazz.overrideMethod(c$, "keySet", 
function(){
if (this.$keySet == null) {
this.$keySet = ((Clazz.isClassDefined("java.util.IdentityHashMap$1") ? 0 : java.util.IdentityHashMap.$IdentityHashMap$1$ ()), Clazz.innerTypeInstance(java.util.IdentityHashMap$1, this, null));
}return this.$keySet;
});
Clazz.overrideMethod(c$, "values", 
function(){
if (this.$values == null) {
this.$values = ((Clazz.isClassDefined("java.util.IdentityHashMap$2") ? 0 : java.util.IdentityHashMap.$IdentityHashMap$2$ ()), Clazz.innerTypeInstance(java.util.IdentityHashMap$2, this, null));
}return this.$values;
});
Clazz.overrideMethod(c$, "equals", 
function(object){
if (this === object) {
return true;
}if (Clazz.instanceOf(object,"java.util.Map")) {
var map = object;
if (this.size() != map.size()) {
return false;
}var set = this.entrySet();
return set.equals(map.entrySet());
}return false;
}, "~O");
Clazz.defineMethod(c$, "clone", 
function(){
try {
return Clazz.superCall(this, java.util.IdentityHashMap, "clone", []);
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
});
Clazz.overrideMethod(c$, "isEmpty", 
function(){
return this.$size == 0;
});
Clazz.overrideMethod(c$, "size", 
function(){
return this.$size;
});
Clazz.defineMethod(c$, "putAllImpl", 
function(map){
if (map.entrySet() != null) {
Clazz.superCall(this, java.util.IdentityHashMap, "putAll", [map]);
}}, "java.util.Map");
c$.$IdentityHashMap$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "IdentityHashMap$1", java.util.AbstractSet);
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.IdentityHashMap"].containsKey(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.IdentityHashMap"].size();
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.b$["java.util.IdentityHashMap"].clear();
});
Clazz.overrideMethod(c$, "remove", 
function(key){
if (this.b$["java.util.IdentityHashMap"].containsKey(key)) {
this.b$["java.util.IdentityHashMap"].remove(key);
return true;
}return false;
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.IdentityHashMap.IdentityHashMapIterator(((Clazz.isClassDefined("java.util.IdentityHashMap$1$1") ? 0 : java.util.IdentityHashMap.$IdentityHashMap$1$1$ ()), Clazz.innerTypeInstance(java.util.IdentityHashMap$1$1, this, null)), this.b$["java.util.IdentityHashMap"]);
});
/*eoif5*/})();
};
c$.$IdentityHashMap$1$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "IdentityHashMap$1$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
return entry.key;
}, "java.util.MapEntry");
/*eoif5*/})();
};
c$.$IdentityHashMap$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "IdentityHashMap$2", java.util.AbstractCollection);
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.IdentityHashMap"].containsValue(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.IdentityHashMap"].size();
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.b$["java.util.IdentityHashMap"].clear();
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.IdentityHashMap.IdentityHashMapIterator(((Clazz.isClassDefined("java.util.IdentityHashMap$2$1") ? 0 : java.util.IdentityHashMap.$IdentityHashMap$2$1$ ()), Clazz.innerTypeInstance(java.util.IdentityHashMap$2$1, this, null)), this.b$["java.util.IdentityHashMap"]);
});
Clazz.overrideMethod(c$, "remove", 
function(object){
var it = this.iterator();
while (it.hasNext()) {
if (object === it.next()) {
it.remove();
return true;
}}
return false;
}, "~O");
/*eoif5*/})();
};
c$.$IdentityHashMap$2$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "IdentityHashMap$2$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
return entry.value;
}, "java.util.MapEntry");
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.IdentityHashMap, "IdentityHashMapEntry", java.util.MapEntry);
Clazz.overrideMethod(c$, "equals", 
function(object){
if (this === object) {
return true;
}if (Clazz.instanceOf(object,"java.util.Map.Entry")) {
var entry = object;
return (this.key === entry.getKey()) && (this.value === entry.getValue());
}return false;
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
return System.identityHashCode(this.key) ^ System.identityHashCode(this.value);
});
Clazz.overrideMethod(c$, "toString", 
function(){
return this.key + "=" + this.value;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.position = 0;
this.lastPosition = 0;
this.associatedMap = null;
this.expectedModCount = 0;
this.type = null;
this.canRemove = false;
Clazz.instantialize(this, arguments);}, java.util.IdentityHashMap, "IdentityHashMapIterator", null, java.util.Iterator);
Clazz.makeConstructor(c$, 
function(value, hm){
this.associatedMap = hm;
this.type = value;
this.expectedModCount = hm.modCount;
}, "java.util.MapEntry.Type,java.util.IdentityHashMap");
Clazz.overrideMethod(c$, "hasNext", 
function(){
while (this.position < this.associatedMap.elementData.length) {
if (this.associatedMap.elementData[this.position] == null) {
this.position += 2;
} else {
return true;
}}
return false;
});
Clazz.defineMethod(c$, "checkConcurrentMod", 
function(){
if (this.expectedModCount != this.associatedMap.modCount) {
throw  new java.util.ConcurrentModificationException();
}});
Clazz.overrideMethod(c$, "next", 
function(){
this.checkConcurrentMod();
if (!this.hasNext()) {
throw  new java.util.NoSuchElementException();
}var result = this.associatedMap.getEntry(this.position);
this.lastPosition = this.position;
this.position += 2;
this.canRemove = true;
return this.type.get(result);
});
Clazz.overrideMethod(c$, "remove", 
function(){
this.checkConcurrentMod();
if (!this.canRemove) {
throw  new IllegalStateException();
}this.canRemove = false;
this.associatedMap.remove(this.associatedMap.elementData[this.lastPosition]);
this.position = this.lastPosition;
this.expectedModCount++;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.associatedMap = null;
Clazz.instantialize(this, arguments);}, java.util.IdentityHashMap, "IdentityHashMapEntrySet", java.util.AbstractSet);
Clazz.makeConstructor(c$, 
function(hm){
Clazz.superConstructor (this, java.util.IdentityHashMap.IdentityHashMapEntrySet, []);
this.associatedMap = hm;
}, "java.util.IdentityHashMap");
Clazz.defineMethod(c$, "hashMap", 
function(){
return this.associatedMap;
});
Clazz.overrideMethod(c$, "size", 
function(){
return this.associatedMap.$size;
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.associatedMap.clear();
});
Clazz.overrideMethod(c$, "remove", 
function(object){
if (this.contains(object)) {
this.associatedMap.remove((object).getKey());
return true;
}return false;
}, "~O");
Clazz.overrideMethod(c$, "contains", 
function(object){
if (Clazz.instanceOf(object,"java.util.Map.Entry")) {
var entry = this.associatedMap.getEntry((object).getKey());
return entry != null && entry.equals(object);
}return false;
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.IdentityHashMap.IdentityHashMapIterator(((Clazz.isClassDefined("java.util.IdentityHashMap$IdentityHashMapEntrySet$1") ? 0 : java.util.IdentityHashMap.IdentityHashMapEntrySet.$IdentityHashMap$IdentityHashMapEntrySet$1$ ()), Clazz.innerTypeInstance(java.util.IdentityHashMap$IdentityHashMapEntrySet$1, this, null)), this.associatedMap);
});
c$.$IdentityHashMap$IdentityHashMapEntrySet$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "IdentityHashMap$IdentityHashMapEntrySet$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
return entry;
}, "java.util.MapEntry");
/*eoif5*/})();
};
/*eoif3*/})();
c$.NULL_OBJECT =  new Clazz._O();
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
