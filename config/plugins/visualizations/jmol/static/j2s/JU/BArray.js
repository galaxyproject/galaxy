Clazz.declarePackage("JU");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.data = null;
Clazz.instantialize(this, arguments);}, JU, "BArray", null);
Clazz.makeConstructor(c$, 
function(data){
this.data = data;
}, "~A");
Clazz.overrideMethod(c$, "equals", 
function(o){
if (Clazz.instanceOf(o,"JU.BArray")) {
var d = (o).data;
if (d.length == this.data.length) {
for (var i = 0; i < d.length; i++) if (d[i] != this.data[i]) return false;

return true;
}}return false;
}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.data.hashCode();
});
Clazz.overrideMethod(c$, "toString", 
function(){
return  String.instantialize(this.data);
});
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
