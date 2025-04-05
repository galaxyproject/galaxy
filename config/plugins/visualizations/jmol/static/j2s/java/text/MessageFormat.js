Clazz.declarePackage("java.text");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.pattern = null;
Clazz.instantialize(this, arguments);}, java.text, "MessageFormat", null);
Clazz.makeConstructor(c$, 
function(pattern){
this.pattern = pattern;
}, "~S");
Clazz.makeConstructor(c$, 
function(pattern, locale){
this.pattern = pattern;
}, "~S,java.util.Locale");
c$.format = Clazz.defineMethod(c$, "format", 
function(pattern, args){
return pattern.replace (/\{(\d+)\}/g, function ($0, $1) {
var i = parseInt ($1);
if (args == null) return null;
return args[i];
});
}, "~S,~A");
Clazz.defineMethod(c$, "format", 
function(obj){
return java.text.MessageFormat.format(this.pattern,  Clazz.newArray(-1, [obj]));
}, "~O");
})();
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
