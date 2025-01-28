Clazz.declarePackage("JM.FF");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.key = null;
this.dE = 0;
this.a = null;
this.b = null;
this.c = null;
this.d = null;
this.ia = 0;
this.ib = 0;
this.ic = 0;
this.id = 0;
this.iData = null;
this.dData = null;
this.delta = 0;
this.rab = 0;
this.theta = 0;
this.energy = 0;
this.calcs = null;
Clazz.instantialize(this, arguments);}, JM.FF, "Calculation", null);
Clazz.defineMethod(c$, "set", 
function(calcs){
this.calcs = calcs;
return this;
}, "JM.FF.Calculations");
Clazz.defineMethod(c$, "setData", 
function(calc, ia, ib, d){
}, "JU.Lst,~N,~N,~N");
Clazz.defineMethod(c$, "getEnergy", 
function(){
return this.energy;
});
Clazz.defineMethod(c$, "getPointers", 
function(dataIn){
this.dData = dataIn[1];
this.iData = dataIn[0];
switch (this.iData.length) {
default:
this.id = this.iData[3];
case 3:
this.ic = this.iData[2];
case 2:
this.ib = this.iData[1];
case 1:
this.ia = this.iData[0];
case 0:
break;
}
}, "~A");
Clazz.defineMethod(c$, "isLoggable", 
function(n){
return this.calcs.ff.minimizer.isLoggable(this.iData, n);
}, "~N");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
