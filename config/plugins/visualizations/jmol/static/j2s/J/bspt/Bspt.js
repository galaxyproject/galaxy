Clazz.declarePackage("J.bspt");
Clazz.load(null, "J.bspt.Bspt", ["J.bspt.CubeIterator", "$.Leaf"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.treeDepth = 0;
this.dimMax = 0;
this.index = 0;
this.eleRoot = null;
Clazz.instantialize(this, arguments);}, J.bspt, "Bspt", null);
Clazz.makeConstructor(c$, 
function(dimMax, index){
this.dimMax = dimMax;
this.index = index;
this.reset();
}, "~N,~N");
Clazz.defineMethod(c$, "reset", 
function(){
this.eleRoot =  new J.bspt.Leaf(this, null, 0);
this.treeDepth = 1;
});
Clazz.defineMethod(c$, "addTuple", 
function(tuple){
this.eleRoot = this.eleRoot.addTuple(0, tuple);
}, "JU.T3");
Clazz.defineMethod(c$, "stats", 
function(){
});
Clazz.defineMethod(c$, "allocateCubeIterator", 
function(){
return  new J.bspt.CubeIterator(this);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
