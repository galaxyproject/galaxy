Clazz.load(null, "java.io.ObjectStreamField", ["java.util.Arrays"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.name = null;
this.type = null;
this.offset = 0;
this.typeString = null;
this.unshared = false;
this.isDeserialized = false;
Clazz.instantialize(this, arguments);}, java.io, "ObjectStreamField", null, Comparable);
Clazz.makeConstructor(c$, 
function(name, cl){
if (name == null || cl == null) {
throw  new NullPointerException();
}this.name = name;
this.type = cl;
}, "~S,Class");
Clazz.makeConstructor(c$, 
function(name, cl, unshared){
if (name == null || cl == null) {
throw  new NullPointerException();
}this.name = name;
this.type = cl;
this.unshared = unshared;
}, "~S,Class,~B");
Clazz.makeConstructor(c$, 
function(signature, name){
if (name == null) {
throw  new NullPointerException();
}this.name = name;
this.typeString = signature.$replace('.', '/');
this.isDeserialized = true;
}, "~S,~S");
Clazz.overrideMethod(c$, "compareTo", 
function(o){
var f = o;
var thisPrimitive = this.isPrimitive();
var fPrimitive = f.isPrimitive();
if (thisPrimitive != fPrimitive) {
return thisPrimitive ? -1 : 1;
}return this.getName().compareTo(f.getName());
}, "~O");
Clazz.overrideMethod(c$, "equals", 
function(arg0){
return this.compareTo(arg0) == 0;
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
return this.getName().hashCode();
});
Clazz.defineMethod(c$, "getName", 
function(){
return this.name;
});
Clazz.defineMethod(c$, "getOffset", 
function(){
return this.offset;
});
Clazz.defineMethod(c$, "getTypeInternal", 
function(){
return this.type;
});
Clazz.defineMethod(c$, "getType", 
function(){
var cl = this.getTypeInternal();
if (this.isDeserialized && !cl.isPrimitive()) {
return Clazz._O;
}return cl;
});
Clazz.defineMethod(c$, "getTypeCode", 
function(){
var t = this.getTypeInternal();
if (t === Integer.TYPE) {
return 'I';
}if (t === Byte.TYPE) {
return 'B';
}if (t === Character.TYPE) {
return 'C';
}if (t === Short.TYPE) {
return 'S';
}if (t === Boolean.TYPE) {
return 'Z';
}if (t === Long.TYPE) {
return 'J';
}if (t === Float.TYPE) {
return 'F';
}if (t === Double.TYPE) {
return 'D';
}if (t.isArray()) {
return '[';
}return 'L';
});
Clazz.defineMethod(c$, "getTypeString", 
function(){
if (this.isPrimitive()) {
return null;
}if (this.typeString == null) {
var t = this.getTypeInternal();
var typeName = t.getName().$replace('.', '/');
var str = (t.isArray()) ? typeName : ("L" + typeName + ';');
this.typeString = str.intern();
}return this.typeString;
});
Clazz.defineMethod(c$, "isPrimitive", 
function(){
var t = this.getTypeInternal();
return t != null && t.isPrimitive();
});
Clazz.defineMethod(c$, "setOffset", 
function(newValue){
this.offset = newValue;
}, "~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return this.getClass().getName() + '(' + this.getName() + ':' + this.getTypeInternal() + ')';
});
c$.sortFields = Clazz.defineMethod(c$, "sortFields", 
function(fields){
if (fields.length > 1) {
var fieldDescComparator = ((Clazz.isClassDefined("java.io.ObjectStreamField$1") ? 0 : java.io.ObjectStreamField.$ObjectStreamField$1$ ()), Clazz.innerTypeInstance(java.io.ObjectStreamField$1, this, null));
java.util.Arrays.sort(fields, fieldDescComparator);
}}, "~A");
Clazz.defineMethod(c$, "resolve", 
function(loader){
if (this.typeString.length == 1) {
switch ((this.typeString.charAt(0)).charCodeAt(0)) {
case 73:
this.type = Integer.TYPE;
return;
case 66:
this.type = Byte.TYPE;
return;
case 67:
this.type = Character.TYPE;
return;
case 83:
this.type = Short.TYPE;
return;
case 90:
this.type = Boolean.TYPE;
return;
case 74:
this.type = Long.TYPE;
return;
case 70:
this.type = Float.TYPE;
return;
case 68:
this.type = Double.TYPE;
return;
}
}var className = this.typeString.$replace('/', '.');
if (className.charAt(0) == 'L') {
className = className.substring(1, className.length - 1);
}try {
var cl = Clazz._4Name(className, false, loader);
this.type = cl;
} catch (e) {
if (Clazz.exceptionOf(e,"ClassNotFoundException")){
} else {
throw e;
}
}
}, "ClassLoader");
Clazz.defineMethod(c$, "isUnshared", 
function(){
return this.unshared;
});
c$.$ObjectStreamField$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.io, "ObjectStreamField$1", null, java.util.Comparator);
Clazz.overrideMethod(c$, "compare", 
function(f1, f2){
return f1.compareTo(f2);
}, "java.io.ObjectStreamField,java.io.ObjectStreamField");
/*eoif5*/})();
};
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
