Clazz.load(["java.util.AbstractMap", "$.AbstractSet", "$.Iterator", "$.Map", "$.MapEntry"], "java.util.HashMap", ["java.util.AbstractCollection", "$.Arrays", "java.util.MapEntry.Type"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.elementCount = 0;
this.elementData = null;
this.loadFactor = 0;
this.threshold = 0;
this.modCount = 0;
this.$entrySet = null;
this.__m = null;
this.__allowJS = false;
Clazz.instantialize(this, arguments);}, java.util, "HashMap", java.util.AbstractMap, [java.util.Map, Cloneable, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(){
var size = 16;
var loadFactor = 0.75;
{
size = (arguments[0] || size); loadFactor = (arguments[1] ||
0.75);
}this.initHM(size, loadFactor);
});
Clazz.defineMethod(c$, "newElementArray", 
function(s){
return  new Array(s);
}, "~N");
Clazz.defineMethod(c$, "initHM", 
function(capacity, loadFactor){
var map = null;
{
if (typeof capacity == "object") { map = capacity; this.__allowJS =
map.__allowJS; capacity = (map.size() < 6 ? 11 : map.size() * 2); }
else { this.__allowJS = true; } !capacity && (capacity = 0);
!loadFactor && (loadFactor = 0.75);
}if (capacity == 0) capacity = 16;
if (capacity >= 0) {
this.elementCount = 0;
this.elementData = this.newElementArray(capacity == 0 ? 1 : capacity);
this.loadFactor = loadFactor;
this.computeMaxSize();
} else {
throw  new IllegalArgumentException();
}this.__setJS();
if (map != null) {
this.putAll(map);
}}, "~N,~N");
Clazz.defineMethod(c$, "putMapEntries", 
function(mOriginal, evict){
var n = mOriginal.size();
if (n == 0) return;
var key = null;
var value = null;
if (java.util.HashMap.__isSimple(this) && java.util.HashMap.__isSimple(mOriginal)) {
var me = this;
var hash = 0;
var mode = java.util.HashMap.__hasKey(me, key);
{
mOriginal.__m.forEach(function(value, key) {
me.putJSVal(hash, key, value, false, evict, mode);
});
}return;
}if (java.util.HashMap.__isSimple(mOriginal)) {
var me = this;
{
mOriginal.__m.forEach(function(value, key) {
me.putJavaValue(key, value);
});
}return;
}this.__m = null;
for (var e, $e = mOriginal.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
key = e.getKey();
value = e.getValue();
this.putJavaValue(key, value);
}
}, "java.util.Map,~B");
Clazz.defineMethod(c$, "reinitialize", 
function(){
this.elementData = null;
this.$entrySet = null;
this.$keySet = null;
this.$values = null;
this.modCount = 0;
this.threshold = 0;
this.elementCount = 0;
this.__setJS();
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.modCount++;
if (java.util.HashMap.__isSimple(this)) {
{
this.__m.clear();
}}this.__setJS();
if (this.elementCount > 0) {
this.elementCount = 0;
java.util.Arrays.fill(this.elementData, null);
this.modCount++;
}});
Clazz.defineMethod(c$, "clone", 
function(){
var result;
try {
result = Clazz.superCall(this, java.util.HashMap, "clone", []);
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
result.reinitialize();
result.putMapEntries(this, false);
return result;
});
Clazz.defineMethod(c$, "computeMaxSize", 
function(){
this.threshold = Clazz.floatToInt(this.elementData.length * this.loadFactor);
});
Clazz.overrideMethod(c$, "containsKey", 
function(key){
switch (java.util.HashMap.__hasKey(this, key)) {
case 0:
break;
case 1:
java.util.HashMap.__ensureJavaMap(this);
break;
case 2:
return false;
case 3:
return true;
}
return (this.getJavaEntry(key) != null);
}, "~O");
Clazz.defineMethod(c$, "keysEqual", 
function(k1, entry){
var k1Hash = k1 == null ? 0 : k1.hashCode();
if (k1Hash != entry.origKeyHash) {
return false;
}if (k1 == null && entry.key == null) {
return true;
}return k1.equals(entry.key);
}, "~O,java.util.HashMap.Entry");
Clazz.overrideMethod(c$, "containsValue", 
function(value){
if (java.util.HashMap.__isSimple(this)) {
var m = this.__m;
{
var iter = m.values();
for (var n = iter.next(); !n.done; n = iter.next()) {
if (n.value == value || n.value.equals$O(value)) {
return true;
}
}
}} else if (value != null) {
for (var i = this.elementData.length; --i >= 0; ) {
var entry = this.elementData[i];
while (entry != null) {
if (value.equals(entry.value)) {
return true;
}entry = entry.next;
}
}
} else {
for (var i = this.elementData.length; --i >= 0; ) {
var entry = this.elementData[i];
while (entry != null) {
if (entry.value == null) {
return true;
}entry = entry.next;
}
}
}return false;
}, "~O");
Clazz.overrideMethod(c$, "entrySet", 
function(){
var es;
return (es = this.$entrySet) == null ? (this.$entrySet =  new java.util.HashMap.HashMapEntrySet(this)) : es;
});
Clazz.overrideMethod(c$, "get", 
function(key){
switch (java.util.HashMap.__hasKey(this, key)) {
case 0:
break;
case 1:
java.util.HashMap.__ensureJavaMap(this);
break;
case 2:
return null;
case 3:
var v = null;
{
v = this.__m.get(key);
}return v;
}
var m = this.getJavaEntry(key);
return (m == null ? null : m.value);
}, "~O");
Clazz.defineMethod(c$, "getJavaEntry", 
function(key){
var index = this.getModuloHash(key);
return this.findJavaEntry(key, index);
}, "~O");
Clazz.defineMethod(c$, "getModuloHash", 
function(key){
if (key == null) {
return 0;
}return (key.hashCode() & 0x7FFFFFFF) % this.elementData.length;
}, "~O");
Clazz.defineMethod(c$, "findJavaEntry", 
function(key, index){
var m;
m = this.elementData[index];
if (key != null) {
while (m != null && !this.keysEqual(key, m)) {
m = m.next;
}
} else {
while (m != null && m.key != null) {
m = m.next;
}
}return m;
}, "~O,~N");
Clazz.overrideMethod(c$, "isEmpty", 
function(){
return this.size() == 0;
});
Clazz.overrideMethod(c$, "keySet", 
function(){
if (this.$keySet == null) {
this.$keySet = ((Clazz.isClassDefined("java.util.HashMap$1") ? 0 : java.util.HashMap.$HashMap$1$ ()), Clazz.innerTypeInstance(java.util.HashMap$1, this, null));
}return this.$keySet;
});
Clazz.overrideMethod(c$, "put", 
function(key, value){
var type = java.util.HashMap.__hasKey(this, key);
switch (type) {
case 0:
break;
case 1:
java.util.HashMap.__ensureJavaMap(this);
break;
case 2:
case 3:
return this.putJSVal(1, key, value, false, true, type);
}
return this.putJavaValue(key, value);
}, "~O,~O");
Clazz.defineMethod(c$, "putJavaValue", 
function(key, value){
var index = this.getModuloHash(key);
var entry = this.findJavaEntry(key, index);
if (entry == null) {
this.modCount++;
if (++this.elementCount > this.threshold) {
this.rehash();
index = key == null ? 0 : (key.hashCode() & 0x7FFFFFFF) % this.elementData.length;
}entry = this.createEntry(key, index, value);
return null;
}var result = entry.value;
entry.value = value;
return result;
}, "~O,~O");
Clazz.defineMethod(c$, "createEntry", 
function(key, index, value){
var entry =  new java.util.HashMap.Entry(key, value);
entry.next = this.elementData[index];
this.elementData[index] = entry;
return entry;
}, "~O,~N,~O");
Clazz.overrideMethod(c$, "putAll", 
function(map){
if (!map.isEmpty()) for (var entry, $entry = map.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
this.put(entry.getKey(), entry.getValue());
}
}, "java.util.Map");
Clazz.defineMethod(c$, "putJSVal", 
function(hash, key, value, onlyIfAbsent, evict, mode){
var v0 = null;
switch (mode) {
case 2:
{
this.__m.set(key, value);
}++this.modCount;
break;
case 3:
if (hash != 0) {
{
v0 = this.__m.get(key) || null;
}}if (!onlyIfAbsent || v0 == null) {
{
this.__m.set(key, value);
}}break;
}
return v0;
}, "~N,~O,~O,~B,~B,~N");
Clazz.defineMethod(c$, "rehashImpl", 
function(capacity){
var length = (capacity == 0 ? 1 : capacity << 1);
var newData = this.newElementArray(length);
for (var i = 0; i < this.elementData.length; i++) {
var entry = this.elementData[i];
while (entry != null) {
var key = entry.key;
var index = key == null ? 0 : (key.hashCode() & 0x7FFFFFFF) % length;
var next = entry.next;
entry.next = newData[index];
newData[index] = entry;
entry = next;
}
}
this.elementData = newData;
this.computeMaxSize();
}, "~N");
Clazz.defineMethod(c$, "rehash", 
function(){
this.rehashImpl(this.elementData.length);
});
Clazz.overrideMethod(c$, "remove", 
function(key){
switch (java.util.HashMap.__hasKey(this, key)) {
case 0:
break;
case 1:
java.util.HashMap.__ensureJavaMap(this);
break;
case 2:
return null;
case 3:
return this.removeJSNode(1, key, null, false, true);
}
var entry = this.removeJavaEntry(key);
return (entry == null ? null : entry.value);
}, "~O");
Clazz.defineMethod(c$, "removeJSNode", 
function(hash, key, value, matchValue, movable){
var v = null;
if (hash == 1 || matchValue) {
{
v = this.__m.get(key) || null;
}}if (!matchValue || v === value || (value != null && value.equals(v))) {
{
this.__m["delete"](key);
}++this.modCount;
switch (hash) {
case 1:
return v;
case 3:
return "true";
}
}return null;
}, "~N,~O,~O,~B,~B");
Clazz.defineMethod(c$, "removeJavaEntry", 
function(key){
var index = 0;
var entry;
var last = null;
if (key != null) {
index = (key.hashCode() & 0x7FFFFFFF) % this.elementData.length;
entry = this.elementData[index];
while (entry != null && !this.keysEqual(key, entry)) {
last = entry;
entry = entry.next;
}
} else {
entry = this.elementData[0];
while (entry != null && entry.key != null) {
last = entry;
entry = entry.next;
}
}if (entry == null) {
return null;
}if (last == null) {
this.elementData[index] = entry.next;
} else {
last.next = entry.next;
}this.modCount++;
this.elementCount--;
return entry;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
{
if (this.__m)
return this.__m.size;
}return this.elementCount;
});
Clazz.overrideMethod(c$, "values", 
function(){
if (this.$values == null) {
this.$values = ((Clazz.isClassDefined("java.util.HashMap$2") ? 0 : java.util.HashMap.$HashMap$2$ ()), Clazz.innerTypeInstance(java.util.HashMap$2, this, null));
}return this.$values;
});
Clazz.defineMethod(c$, "__setJS", 
function(){
if (this.__allowJS && java.util.HashMap.USE_SIMPLE) {
var m = null;
{
m = new Map();
}this.__m = m;
} else {
this.__m = null;
}});
c$.__get = Clazz.defineMethod(c$, "__get", 
function(map, key){
{
return map.__m.get(key == null ? null : key + "");
}}, "~O,~O");
c$.__set = Clazz.defineMethod(c$, "__set", 
function(map, key, value){
{
map.__m.set(key == null ? null : key + "", value);
}}, "java.util.Map,~O,~O");
c$.__hasKey = Clazz.defineMethod(c$, "__hasKey", 
function(map, key){
{
return (!map.__m ? 0 : key != null && typeof key != "string" ? 1 :
map.__m.has(key) ? 3 : 2);
}}, "java.util.Map,~O");
c$.__isSimple = Clazz.defineMethod(c$, "__isSimple", 
function(map){
{
return !!map.__m;
}}, "java.util.Map");
c$.__ensureJavaMap = Clazz.defineMethod(c$, "__ensureJavaMap", 
function(map){
{
if (map.__m) { var m = map.__m; map.__m = null;
m.forEach(function(value, key){map.put(key, value);}); m.clear();
}
}}, "java.util.Map");
c$.$HashMap$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "HashMap$1", java.util.AbstractSet);
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.HashMap"].containsKey(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.HashMap"].size();
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.b$["java.util.HashMap"].clear();
});
Clazz.overrideMethod(c$, "remove", 
function(key){
if (!this.b$["java.util.HashMap"].containsKey(key)) return false;
this.b$["java.util.HashMap"].remove(key);
return true;
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.HashMap.HashMapIterator(((Clazz.isClassDefined("java.util.HashMap$1$1") ? 0 : java.util.HashMap.$HashMap$1$1$ ()), Clazz.innerTypeInstance(java.util.HashMap$1$1, this, null)), this.b$["java.util.HashMap"]);
});
/*eoif5*/})();
};
c$.$HashMap$1$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "HashMap$1$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
if (java.util.HashMap.__isSimple(this.b$["java.util.HashMap"])) {
{
return (entry == null ? null : entry.value[0]);
}}return entry.key;
}, "java.util.MapEntry");
/*eoif5*/})();
};
c$.$HashMap$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "HashMap$2", java.util.AbstractCollection);
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.HashMap"].containsValue(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.HashMap"].size();
});
Clazz.overrideMethod(c$, "clear", 
function(){
this.b$["java.util.HashMap"].clear();
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.HashMap.HashMapIterator(((Clazz.isClassDefined("java.util.HashMap$2$1") ? 0 : java.util.HashMap.$HashMap$2$1$ ()), Clazz.innerTypeInstance(java.util.HashMap$2$1, this, null)), this.b$["java.util.HashMap"]);
});
/*eoif5*/})();
};
c$.$HashMap$2$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "HashMap$2$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
if (java.util.HashMap.__isSimple(this.b$["java.util.HashMap"])) {
{
return (entry == null ? null : entry.value[1]);
}}return entry.value;
}, "java.util.MapEntry");
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.origKeyHash = 0;
this.next = null;
Clazz.instantialize(this, arguments);}, java.util.HashMap, "Entry", java.util.MapEntry);
Clazz.makeConstructor(c$, 
function(theKey, theValue){
Clazz.superConstructor(this, java.util.HashMap.Entry, [theKey, theValue]);
this.origKeyHash = (theKey == null ? 0 : theKey.hashCode());
}, "~O,~O");
Clazz.defineMethod(c$, "clone", 
function(){
var entry = Clazz.superCall(this, java.util.HashMap.Entry, "clone", []);
if (this.next != null) {
entry.next = this.next.clone();
}return entry;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.jsMapIterator = null;
this.isSimple = false;
this.index = 0;
this.expectedModCount = 0;
this.type = null;
this.canRemove = false;
this.entry = null;
this.lastEntry = null;
this.associatedMap = null;
Clazz.instantialize(this, arguments);}, java.util.HashMap, "HashMapIterator", null, java.util.Iterator);
Clazz.makeConstructor(c$, 
function(value, hm){
this.associatedMap = hm;
this.type = value;
this.expectedModCount = hm.modCount;
this.lastEntry = this.entry = null;
this.isSimple = java.util.HashMap.__isSimple(this.associatedMap);
if (this.isSimple) {
var m = this.associatedMap.__m;
{
this.jsMapIterator = m.entries();
this.entry = this.jsMapIterator.next();
}}}, "java.util.MapEntry.Type,java.util.HashMap");
Clazz.overrideMethod(c$, "hasNext", 
function(){
if (this.isSimple) {
if (this.entry == null) {
return false;
}var isDone = false;
{
isDone = this.entry.done;
}return !isDone;
}if (this.entry != null) {
return true;
}while (this.index < this.associatedMap.elementData.length) {
if (this.associatedMap.elementData[this.index] == null) {
this.index++;
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
}var result = null;
if (this.isSimple) {
{
result = this.entry;
this.entry = this.jsMapIterator.next() || null;
}} else if (this.entry == null) {
result = this.lastEntry = this.associatedMap.elementData[this.index++];
this.entry = this.lastEntry.next;
} else {
if (this.lastEntry.next !== this.entry) {
this.lastEntry = this.lastEntry.next;
}result = this.entry;
this.entry = this.entry.next;
}this.canRemove = true;
return this.type.get(result);
});
Clazz.overrideMethod(c$, "remove", 
function(){
this.checkConcurrentMod();
if (!this.canRemove) {
throw  new IllegalStateException();
}this.canRemove = false;
this.associatedMap.modCount++;
if (this.lastEntry.next === this.entry) {
while (this.associatedMap.elementData[--this.index] == null) {
;}
this.associatedMap.elementData[this.index] = this.associatedMap.elementData[this.index].next;
this.entry = null;
} else {
this.lastEntry.next = this.entry;
}this.associatedMap.elementCount--;
this.expectedModCount++;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.associatedMap = null;
Clazz.instantialize(this, arguments);}, java.util.HashMap, "HashMapEntrySet", java.util.AbstractSet);
Clazz.makeConstructor(c$, 
function(hm){
Clazz.superConstructor (this, java.util.HashMap.HashMapEntrySet, []);
this.associatedMap = hm;
}, "java.util.HashMap");
Clazz.defineMethod(c$, "hashMap", 
function(){
return this.associatedMap;
});
Clazz.overrideMethod(c$, "size", 
function(){
return this.associatedMap.elementCount;
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
if (!(Clazz.instanceOf(object,"java.util.Map.Entry"))) return false;
var key = (object).getKey();
if (!this.associatedMap.containsKey(key)) return false;
if (java.util.HashMap.__isSimple(this.associatedMap)) {
var value = (object).getValue();
var v = this.associatedMap.get(key);
return (value === v || value != null && value.equals(v));
}var entry = this.associatedMap.getJavaEntry((object).getKey());
return object.equals(entry);
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.HashMap.HashMapIterator(((Clazz.isClassDefined("java.util.HashMap$HashMapEntrySet$1") ? 0 : java.util.HashMap.HashMapEntrySet.$HashMap$HashMapEntrySet$1$ ()), Clazz.innerTypeInstance(java.util.HashMap$HashMapEntrySet$1, this, null)), this.associatedMap);
});
c$.$HashMap$HashMapEntrySet$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "HashMap$HashMapEntrySet$1", null, java.util.MapEntry.Type);
Clazz.overrideMethod(c$, "get", 
function(entry){
if (java.util.HashMap.__isSimple(this.b$["java.util.HashMap.HashMapEntrySet"].associatedMap)) {
var key = null;
var value = null;
{
key = entry.value[0];
value = entry.value[1];
}return  new java.util.HashMap.Entry(key, value);
}return entry;
}, "java.util.MapEntry");
/*eoif5*/})();
};
/*eoif3*/})();
c$.USE_SIMPLE = true;
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
