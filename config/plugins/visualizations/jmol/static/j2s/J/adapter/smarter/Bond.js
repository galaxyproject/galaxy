Clazz.declarePackage("J.adapter.smarter");
Clazz.load(["J.adapter.smarter.AtomSetObject"], "J.adapter.smarter.Bond", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.atomIndex1 = 0;
this.atomIndex2 = 0;
this.order = 0;
this.radius = -1;
this.colix = -1;
this.uniqueID = -1;
this.distance = 0;
Clazz.instantialize(this, arguments);}, J.adapter.smarter, "Bond", J.adapter.smarter.AtomSetObject);
Clazz.makeConstructor(c$, 
function(atomIndex1, atomIndex2, order){
Clazz.superConstructor (this, J.adapter.smarter.Bond, []);
this.atomIndex1 = atomIndex1;
this.atomIndex2 = atomIndex2;
this.order = order;
}, "~N,~N,~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return "[Bond " + this.atomIndex1 + " " + this.atomIndex2 + " " + this.order + "]";
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
