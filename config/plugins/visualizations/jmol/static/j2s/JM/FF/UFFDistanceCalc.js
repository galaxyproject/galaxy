Clazz.declarePackage("JM.FF");
Clazz.load(["JM.FF.Calculation"], "JM.FF.UFFDistanceCalc", ["JM.FF.CalculationsUFF"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.r0 = 0;
this.kb = 0;
Clazz.instantialize(this, arguments);}, JM.FF, "UFFDistanceCalc", JM.FF.Calculation);
Clazz.overrideMethod(c$, "setData", 
function(calc, ia, ib, bondOrder){
this.calcs.parA = this.calcs.getParameter(this.calcs.minAtoms[ia].sType);
this.calcs.parB = this.calcs.getParameter(this.calcs.minAtoms[ib].sType);
this.r0 = JM.FF.CalculationsUFF.calculateR0(this.calcs.parA.dVal[0], this.calcs.parB.dVal[0], this.calcs.parA.dVal[8], this.calcs.parB.dVal[8], bondOrder);
this.kb = 1390.2842991599998 * this.calcs.parA.dVal[5] * this.calcs.parB.dVal[5] / (this.r0 * this.r0 * this.r0);
calc.addLast( Clazz.newArray(-1, [this.iData =  Clazz.newIntArray(-1, [ia, ib]),  Clazz.newDoubleArray(-1, [this.kb, this.r0, bondOrder]), this.isLoggable(2)]));
}, "JU.Lst,~N,~N,~N");
Clazz.overrideMethod(c$, "compute", 
function(dataIn){
this.getPointers(dataIn);
this.kb = this.dData[0];
this.r0 = this.dData[1];
this.calcs.setPairVariables(this);
this.delta = this.rab - this.r0;
this.energy = this.kb * this.delta * this.delta;
if (this.calcs.gradients) {
this.dE = 2.0 * this.kb * this.delta;
this.calcs.addForces(this, 2);
}if (this.calcs.logging && dataIn[2] === Boolean.TRUE) this.calcs.appendLogData(this.calcs.getDebugLine(0, this));
return this.energy;
}, "~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
