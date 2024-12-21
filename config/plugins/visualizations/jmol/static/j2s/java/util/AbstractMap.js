Clazz.load(["java.util.Map"], "java.util.AbstractMap", ["java.util.AbstractCollection", "$.AbstractSet", "$.Iterator"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.$keySet = null;
this.$values = null;
Clazz.instantialize(this, arguments);}, java.util, "AbstractMap", null, java.util.Map);
Clazz.overrideMethod(c$, "clear", 
function(){
this.entrySet().clear();
});
Clazz.overrideMethod(c$, "containsKey", 
function(key){
var it = this.entrySet().iterator();
if (key != null) {
while (it.hasNext()) {
if (key.equals(it.next().getKey())) {
return true;
}}
} else {
while (it.hasNext()) {
if (it.next().getKey() == null) {
return true;
}}
}return false;
}, "~O");
Clazz.overrideMethod(c$, "containsValue", 
function(value){
var it = this.entrySet().iterator();
if (value != null) {
while (it.hasNext()) {
if (value.equals(it.next().getValue())) {
return true;
}}
} else {
while (it.hasNext()) {
if (it.next().getValue() == null) {
return true;
}}
}return false;
}, "~O");
Clazz.overrideMethod(c$, "equals", 
function(object){
if (this === object) {
return true;
}if (Clazz.instanceOf(object,"java.util.Map")) {
var map = object;
if (this.size() != map.size()) {
return false;
}var objectSet = map.entrySet();
var it = this.entrySet().iterator();
while (it.hasNext()) {
if (!objectSet.contains(it.next())) {
return false;
}}
return true;
}return false;
}, "~O");
Clazz.overrideMethod(c$, "get", 
function(key){
var it = this.entrySet().iterator();
if (key != null) {
while (it.hasNext()) {
var entry = it.next();
if (key.equals(entry.getKey())) {
return entry.getValue();
}}
} else {
while (it.hasNext()) {
var entry = it.next();
if (entry.getKey() == null) {
return entry.getValue();
}}
}return null;
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
var result = 0;
var it = this.entrySet().iterator();
while (it.hasNext()) {
result += it.next().hashCode();
}
return result;
});
Clazz.overrideMethod(c$, "isEmpty", 
function(){
return this.size() == 0;
});
Clazz.overrideMethod(c$, "keySet", 
function(){
if (this.$keySet == null) {
this.$keySet = ((Clazz.isClassDefined("java.util.AbstractMap$1") ? 0 : java.util.AbstractMap.$AbstractMap$1$ ()), Clazz.innerTypeInstance(java.util.AbstractMap$1, this, null));
}return this.$keySet;
});
Clazz.overrideMethod(c$, "put", 
function(key, value){
throw  new UnsupportedOperationException();
}, "~O,~O");
Clazz.overrideMethod(c$, "putAll", 
function(map){
this.putAllAM(map);
}, "java.util.Map");
Clazz.defineMethod(c$, "putAllAM", 
function(map){
if (!map.isEmpty()) for (var entry, $entry = map.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
this.put(entry.getKey(), entry.getValue());
}
}, "java.util.Map");
Clazz.overrideMethod(c$, "remove", 
function(key){
var it = this.entrySet().iterator();
if (key != null) {
while (it.hasNext()) {
var entry = it.next();
if (key.equals(entry.getKey())) {
it.remove();
return entry.getValue();
}}
} else {
while (it.hasNext()) {
var entry = it.next();
if (entry.getKey() == null) {
it.remove();
return entry.getValue();
}}
}return null;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.entrySet().size();
});
Clazz.overrideMethod(c$, "toString", 
function(){
if (this.isEmpty()) {
return "{}";
}var buffer = "{";
var it = this.entrySet().iterator();
while (it.hasNext()) {
var entry = it.next();
var key = entry.getKey();
if (key !== this) {
buffer += (key);
} else {
buffer += ("(this Map)");
}buffer += ('=');
var value = entry.getValue();
if (value !== this) {
buffer += (value);
} else {
buffer += ("(this Map)");
}if (it.hasNext()) {
buffer += (", ");
}}
buffer += ('}');
return buffer;
});
Clazz.overrideMethod(c$, "values", 
function(){
if (this.$values == null) {
this.$values = ((Clazz.isClassDefined("java.util.AbstractMap$2") ? 0 : java.util.AbstractMap.$AbstractMap$2$ ()), Clazz.innerTypeInstance(java.util.AbstractMap$2, this, null));
}return this.$values;
});
Clazz.defineMethod(c$, "clone", 
function(){
return this.cloneAM();
});
Clazz.defineMethod(c$, "cloneAM", 
function(){
var result;
{
result = Clazz.clone(this);
}result.$keySet = null;
result.$values = null;
return result;
});
c$.$AbstractMap$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "AbstractMap$1", java.util.AbstractSet);
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.AbstractMap"].containsKey(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.AbstractMap"].size();
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.AbstractMap$1$1") ? 0 : java.util.AbstractMap.$AbstractMap$1$1$ ()), Clazz.innerTypeInstance(java.util.AbstractMap$1$1, this, null));
});
/*eoif5*/})();
};
c$.$AbstractMap$1$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.setIterator = null;
Clazz.instantialize(this, arguments);}, java.util, "AbstractMap$1$1", null, java.util.Iterator);
Clazz.prepareFields (c$, function(){
this.setIterator = this.b$["java.util.AbstractMap"].entrySet().iterator();
});
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.setIterator.hasNext();
});
Clazz.overrideMethod(c$, "next", 
function(){
return this.setIterator.next().getKey();
});
Clazz.overrideMethod(c$, "remove", 
function(){
this.setIterator.remove();
});
/*eoif5*/})();
};
c$.$AbstractMap$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "AbstractMap$2", java.util.AbstractCollection);
Clazz.overrideMethod(c$, "size", 
function(){
return this.b$["java.util.AbstractMap"].size();
});
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.b$["java.util.AbstractMap"].containsValue(object);
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.AbstractMap$2$1") ? 0 : java.util.AbstractMap.$AbstractMap$2$1$ ()), Clazz.innerTypeInstance(java.util.AbstractMap$2$1, this, null));
});
/*eoif5*/})();
};
c$.$AbstractMap$2$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.setIterator = null;
Clazz.instantialize(this, arguments);}, java.util, "AbstractMap$2$1", null, java.util.Iterator);
Clazz.prepareFields (c$, function(){
this.setIterator = this.b$["java.util.AbstractMap"].entrySet().iterator();
});
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.setIterator.hasNext();
});
Clazz.overrideMethod(c$, "next", 
function(){
return this.setIterator.next().getValue();
});
Clazz.overrideMethod(c$, "remove", 
function(){
this.setIterator.remove();
});
/*eoif5*/})();
};
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
