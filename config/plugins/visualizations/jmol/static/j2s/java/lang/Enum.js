(function(){
var c$ = Clazz.decorateAsClass(function(){
this.$name = null;
this.$ordinal = 0;
Clazz.instantialize(this, arguments);}, java.lang, "Enum", null, [Comparable, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(name, ordinal){
this.$name = name;
this.$ordinal = ordinal;
}, "~S,~N");
Clazz.defineMethod(c$, "name", 
function(){
return this.$name;
});
Clazz.defineMethod(c$, "ordinal", 
function(){
return this.$ordinal;
});
Clazz.overrideMethod(c$, "toString", 
function(){
return this.$name;
});
Clazz.overrideMethod(c$, "equals", 
function(other){
return this === other;
}, "~O");
Clazz.overrideMethod(c$, "clone", 
function(){
throw  new CloneNotSupportedException();
});
Clazz.overrideMethod(c$, "compareTo", 
function(o){
var other = o;
var self = this;
if (self.getClass() !== other.getClass() && self.getDeclaringClass() !== other.getDeclaringClass()) throw  new ClassCastException();
return self.$ordinal - other.$ordinal;
}, "~O");
Clazz.defineMethod(c$, "getDeclaringClass", 
function(){
var clazz = this.getClass();
var zuper = clazz.getSuperclass();
return ((zuper === Enum) ? clazz : zuper);
});
c$.$valueOf = Clazz.defineMethod(c$, "$valueOf", 
function(enumType, name){
var result = null;
{
result = enumType.$clazz$[name];
}if (result != null) return result;
if (name == null) throw  new NullPointerException("Name is null");
throw  new IllegalArgumentException("No enum const " + enumType + "." + name);
}, "Class,~S");
Clazz.overrideMethod(c$, "finalize", 
function(){
});
})();
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
