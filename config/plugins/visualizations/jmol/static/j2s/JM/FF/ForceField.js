Clazz.declarePackage("JM.FF");
Clazz.load(null, "JM.FF.ForceField", ["JU.PT", "JM.Util", "JU.Logger", "JV.FileManager", "$.Viewer"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.name = null;
this.calc = null;
this.criterion = 0;
this.e0 = 0;
this.dE = 0;
this.currentStep = 0;
this.stepMax = 0;
this.coordSaved = null;
this.minAtomCount = 0;
this.minBondCount = 0;
this.minAtoms = null;
this.minBonds = null;
this.minAngles = null;
this.minTorsions = null;
this.bsMinFixed = null;
this.trustRadius = 0.3;
this.minimizer = null;
this.nth = 10;
Clazz.instantialize(this, arguments);}, JM.FF, "ForceField", null);
Clazz.defineMethod(c$, "setModelFields", 
function(){
this.minAtoms = this.minimizer.minAtoms;
this.minBonds = this.minimizer.minBonds;
this.minAngles = this.minimizer.minAngles;
this.minTorsions = this.minimizer.minTorsions;
this.bsMinFixed = this.minimizer.bsMinFixed;
this.minAtomCount = this.minAtoms.length;
this.minBondCount = this.minBonds.length;
});
Clazz.defineMethod(c$, "setConstraints", 
function(m){
this.bsMinFixed = m.bsMinFixed;
this.calc.setConstraints(m.constraints);
this.coordSaved = null;
}, "JM.Minimizer");
Clazz.defineMethod(c$, "steepestDescentInitialize", 
function(stepMax, criterion, trustRadius){
this.stepMax = stepMax;
this.criterion = criterion / this.toUserUnits(1);
this.trustRadius = trustRadius;
this.currentStep = 0;
this.clearForces();
this.calc.setLoggingEnabled(true);
this.calc.setLoggingEnabled(stepMax == 0 || JU.Logger.isActiveLevel(6));
var s = this.name + " " + this.calc.getDebugHeader(-1) + "Jmol Minimization Version " + JV.Viewer.getJmolVersion() + "\n";
this.calc.appendLogData(s);
JU.Logger.info(s);
this.calc.getConstraintList();
if (this.calc.loggingEnabled) this.calc.appendLogData(this.calc.getAtomList("S T E E P E S T   D E S C E N T"));
this.dE = 0;
this.calc.setPreliminary(stepMax > 0);
this.recalculateEnergy();
s = JU.PT.sprintf(" Initial " + this.name + " E = %10.3f " + this.minimizer.units + "/mol criterion = %8.6f max steps = " + stepMax, "ff",  Clazz.newArray(-1, [Float.$valueOf(this.toUserUnits(this.e0)), Float.$valueOf(this.toUserUnits(criterion))]));
this.minimizer.report(s, false);
this.calc.appendLogData(s);
}, "~N,~N,~N");
Clazz.defineMethod(c$, "clearForces", 
function(){
for (var i = 0; i < this.minAtomCount; i++) this.minAtoms[i].force[0] = this.minAtoms[i].force[1] = this.minAtoms[i].force[2] = 0;

});
Clazz.defineMethod(c$, "steepestDescentTakeNSteps", 
function(n, doUpdateAtoms){
if (this.stepMax == 0) return false;
var isPreliminary = true;
for (var iStep = 1; iStep <= n; iStep++) {
this.currentStep++;
this.calc.setSilent(true);
for (var i = 0; i < this.minAtomCount; i++) if (this.bsMinFixed == null || !this.bsMinFixed.get(i)) this.setForcesUsingNumericalDerivative(this.minAtoms[i], 1);

this.linearSearch(doUpdateAtoms);
this.calc.setSilent(false);
if (this.calc.loggingEnabled) this.calc.appendLogData(this.calc.getAtomList("S T E P    " + this.currentStep));
var e1 = this.energyFull(false, false);
this.dE = e1 - this.e0;
var done = JM.Util.isNear3(e1, this.e0, this.criterion);
if (done || this.currentStep % this.nth == 0 || this.stepMax <= this.currentStep) {
var s = JU.PT.sprintf(this.name + " Step %-4d E = %10.6f    dE = %8.6f ", "Fi",  Clazz.newArray(-1, [ Clazz.newFloatArray(-1, [this.toUserUnits(e1), this.toUserUnits(this.dE)]), Integer.$valueOf(this.currentStep)]));
this.minimizer.report(s, false);
this.calc.appendLogData(s);
}this.e0 = e1;
if (done || this.stepMax <= this.currentStep) {
if (this.calc.loggingEnabled) this.calc.appendLogData(this.calc.getAtomList("F I N A L  G E O M E T R Y"));
if (done) {
var s = JU.PT.formatStringF("\n    " + this.name + " STEEPEST DESCENT HAS CONVERGED: E = %8.5f " + this.minimizer.units + "/mol after " + this.currentStep + " steps", "f", this.toUserUnits(e1));
this.calc.appendLogData(s);
this.minimizer.report(s, true);
JU.Logger.info(s);
}return false;
}if (isPreliminary && this.getNormalizedDE() >= 2) {
this.calc.setPreliminary(isPreliminary = false);
this.e0 = this.energyFull(false, false);
}}
return true;
}, "~N,~B");
Clazz.defineMethod(c$, "getEnergies", 
function(terms, gradients){
if ((terms & 1) != 0) return this.energyFull(gradients, true);
var e = 0.0;
if ((terms & 2) != 0) e += this.energyBond(gradients);
if ((terms & 4) != 0) e += this.energyAngle(gradients);
if ((terms & 8) != 0) e += this.energyStretchBend(gradients);
if ((terms & 32) != 0) e += this.energyOOP(gradients);
if ((terms & 16) != 0) e += this.energyTorsion(gradients);
if ((terms & 64) != 0) e += this.energyVDW(gradients);
if ((terms & 128) != 0) e += this.energyES(gradients);
return e;
}, "~N,~B");
Clazz.defineMethod(c$, "setForcesUsingNumericalDerivative", 
function(atom, terms){
var delta = 1.0e-5;
atom.force[0] = -this.getDE(atom, terms, 0, delta);
atom.force[1] = -this.getDE(atom, terms, 1, delta);
atom.force[2] = -this.getDE(atom, terms, 2, delta);
return;
}, "JM.MinAtom,~N");
Clazz.defineMethod(c$, "getDE", 
function(atom, terms, i, delta){
atom.coord[i] += delta;
var e = this.getEnergies(terms, false);
atom.coord[i] -= delta;
return (e - this.e0) / delta;
}, "JM.MinAtom,~N,~N,~N");
Clazz.defineMethod(c$, "energyFull", 
function(gradients, isSilent){
var energy;
if (gradients) this.clearForces();
energy = this.energyBond(gradients) + this.energyAngle(gradients) + this.energyTorsion(gradients) + this.energyStretchBend(gradients) + this.energyOOP(gradients) + this.energyVDW(gradients) + this.energyES(gradients);
if (!isSilent && this.calc.loggingEnabled) this.calc.appendLogData(JU.PT.sprintf("\nTOTAL %s ENERGY = %8.3f %s/mol\n", "sfs",  Clazz.newArray(-1, [this.name, Float.$valueOf(this.toUserUnits(energy)), this.minimizer.units])));
return energy;
}, "~B,~B");
Clazz.defineMethod(c$, "energyStretchBend", 
function(gradients){
return this.calc.energyStretchBend(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyBond", 
function(gradients){
return this.calc.energyBond(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyAngle", 
function(gradients){
return this.calc.energyAngle(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyTorsion", 
function(gradients){
return this.calc.energyTorsion(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyOOP", 
function(gradients){
return this.calc.energyOOP(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyVDW", 
function(gradients){
return this.calc.energyVDW(gradients);
}, "~B");
Clazz.defineMethod(c$, "energyES", 
function(gradients){
return this.calc.energyES(gradients);
}, "~B");
Clazz.defineMethod(c$, "linearSearch", 
function(doUpdateAtoms){
var step = 0.75 * this.trustRadius;
var trustRadius2 = this.trustRadius * this.trustRadius;
var e1 = this.energyFull(false, true);
var nSteps = 10;
var isDone = false;
for (var iStep = 0; iStep < nSteps && !isDone; iStep++) {
this.saveCoordinates();
for (var i = 0; i < this.minAtomCount; ++i) {
if (this.bsMinFixed == null || !this.bsMinFixed.get(i)) {
var force = this.minAtoms[i].force;
var coord = this.minAtoms[i].coord;
var f2 = (force[0] * force[0] + force[1] * force[1] + force[2] * force[2]);
var f = trustRadius2 / step / step / f2;
if (1 > f) {
f2 = Math.sqrt(f);
force[0] *= f2;
force[1] *= f2;
force[2] *= f2;
}for (var j = 0; j < 3; ++j) {
if (JM.Util.isFinite(force[j])) {
var tempStep = force[j] * step;
if (tempStep > this.trustRadius) coord[j] += this.trustRadius;
 else if (tempStep < -this.trustRadius) coord[j] -= this.trustRadius;
 else coord[j] += tempStep;
}}
}}
if (doUpdateAtoms) {
this.minimizer.updateAtomXYZ(false);
}var e2 = this.energyFull(false, true);
isDone = JM.Util.isNear3(e2, e1, 1.0e-3);
if (e2 > e1) {
step *= 0.1;
this.restoreCoordinates();
} else if (e2 < e1) {
e1 = e2;
step *= 2.15;
if (step > 1.0) step = 1.0;
}}
}, "~B");
Clazz.defineMethod(c$, "saveCoordinates", 
function(){
if (this.coordSaved == null) this.coordSaved =  Clazz.newDoubleArray (this.minAtomCount, 3, 0);
for (var i = 0; i < this.minAtomCount; i++) for (var j = 0; j < 3; j++) this.coordSaved[i][j] = this.minAtoms[i].coord[j];


});
Clazz.defineMethod(c$, "restoreCoordinates", 
function(){
for (var i = 0; i < this.minAtomCount; i++) for (var j = 0; j < 3; j++) this.minAtoms[i].coord[j] = this.coordSaved[i][j];


});
Clazz.defineMethod(c$, "detectExplosion", 
function(){
for (var i = 0; i < this.minAtomCount; i++) {
var atom = this.minAtoms[i];
for (var j = 0; j < 3; j++) if (!JM.Util.isFinite(atom.coord[j])) return true;

}
for (var i = 0; i < this.minBondCount; i++) {
var bond = this.minBonds[i];
if (JM.Util.distance2(this.minAtoms[bond.data[0]].coord, this.minAtoms[bond.data[1]].coord) > 900.0) return true;
}
return false;
});
Clazz.defineMethod(c$, "getCurrentStep", 
function(){
return this.currentStep;
});
Clazz.defineMethod(c$, "getEnergy", 
function(){
return this.e0;
});
Clazz.defineMethod(c$, "getAtomList", 
function(title){
return this.calc.getAtomList(title);
}, "~S");
Clazz.defineMethod(c$, "getEnergyDiff", 
function(){
return this.dE;
});
Clazz.defineMethod(c$, "getLogData", 
function(){
return this.calc.getLogData();
});
Clazz.defineMethod(c$, "getNormalizedDE", 
function(){
return Math.abs(this.dE / this.criterion);
});
Clazz.defineMethod(c$, "toUserUnits", 
function(energy){
return this.toUnits(energy, this.calc.getUnits());
}, "~N");
Clazz.defineMethod(c$, "toUnits", 
function(energy, units){
return (units.equalsIgnoreCase(this.minimizer.units) ? energy : energy * (this.minimizer.units.equals("kJ") ? 4.1868 : 0.23884589662749595));
}, "~N,~S");
Clazz.defineMethod(c$, "log", 
function(s){
this.calc.appendLogData(s);
}, "~S");
Clazz.defineMethod(c$, "getBufferedReader", 
function(resourceName){
return JV.FileManager.getBufferedReaderForResource(this.minimizer.vwr, this, "JM/FF/", "data/" + resourceName);
}, "~S");
Clazz.defineMethod(c$, "recalculateEnergy", 
function(){
this.e0 = this.energyFull(false, false);
});
Clazz.defineMethod(c$, "setNth", 
function(n){
this.nth = n;
}, "~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
