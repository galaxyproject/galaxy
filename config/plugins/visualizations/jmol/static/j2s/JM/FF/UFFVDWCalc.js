Clazz.declarePackage("JM.FF");
Clazz.load(["JM.FF.Calculation"], "JM.FF.UFFVDWCalc", null, function(){
var c$ = Clazz.declareType(JM.FF, "UFFVDWCalc", JM.FF.Calculation);
Clazz.overrideMethod(c$, "setData", 
function(calc, ia, ib, dd){
this.a = this.calcs.minAtoms[ia];
this.b = this.calcs.minAtoms[ib];
if (this.a.atom.distanceSquared(this.b.atom) > 50.0) return;
var parA = this.calcs.getParameter(this.a.sType);
var parB = this.calcs.getParameter(this.b.sType);
var Xa;
var Da;
var Xb;
var Db;
if (parA == null || parA.dVal == null) {
System.out.println("OHOH");
Xa = Da = 0;
} else {
Xa = parA.dVal[2];
Da = parA.dVal[3];
}if (parB == null || parB.dVal == null) {
System.out.println("OHOH");
Xb = Db = 0;
} else {
Xb = parB.dVal[2];
Db = parB.dVal[3];
}var Dab = 4.1868 * Math.sqrt(Da * Db);
var Xab = Math.sqrt(Xa * Xb);
calc.addLast( Clazz.newArray(-1, [this.iData =  Clazz.newIntArray(-1, [ia, ib]),  Clazz.newDoubleArray(-1, [Xab, Dab]), this.isLoggable(2)]));
}, "JU.Lst,~N,~N,~N");
Clazz.overrideMethod(c$, "compute", 
function(dataIn){
this.getPointers(dataIn);
var Xab = this.dData[0];
var Dab = this.dData[1];
this.calcs.setPairVariables(this);
var term = Xab / this.rab;
var term6 = term * term * term;
term6 *= term6;
this.energy = Dab * term6 * (term6 - 2.0);
if (this.calcs.gradients) {
this.dE = Dab * 12.0 * (1.0 - term6) * term6 * term / Xab;
this.calcs.addForces(this, 2);
}if (this.calcs.logging && dataIn[2] === Boolean.TRUE) this.calcs.appendLogData(this.calcs.getDebugLine(5, this));
return this.energy;
}, "~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
