Clazz.declarePackage("J.adapter.readers.quantum");
Clazz.load(["J.adapter.readers.quantum.MOReader"], "J.adapter.readers.quantum.SlaterReader", ["java.util.Arrays", "JU.Lst", "J.quantum.SlaterData", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.scaleSlaters = true;
if (!Clazz.isClassDefined("J.adapter.readers.quantum.SlaterReader.SlaterSorter")) {
J.adapter.readers.quantum.SlaterReader.$SlaterReader$SlaterSorter$ ();
}
if (!Clazz.isClassDefined("J.adapter.readers.quantum.SlaterReader.OrbitalSorter")) {
J.adapter.readers.quantum.SlaterReader.$SlaterReader$OrbitalSorter$ ();
}
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum, "SlaterReader", J.adapter.readers.quantum.MOReader);
Clazz.defineMethod(c$, "addSlater", 
function(iAtom, a, b, c, d, zeta, coef){
var sd =  new J.quantum.SlaterData(iAtom, a, b, c, d, zeta, coef);
this.getSlaters().addLast(sd);
return sd;
}, "~N,~N,~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "getSlaters", 
function(){
return (this.slaters == null ? this.slaters =  new JU.Lst() : this.slaters);
});
Clazz.defineMethod(c$, "addSlater", 
function(sd, n){
sd.index = n;
this.getSlaters().addLast(sd);
}, "J.quantum.SlaterData,~N");
Clazz.defineMethod(c$, "setSlaters", 
function(doSort){
if (this.slaters == null || this.slaters.size() == 0) return;
if (this.slaterArray == null) {
var nSlaters = this.slaters.size();
this.slaterArray =  new Array(nSlaters);
for (var i = 0; i < this.slaterArray.length; i++) this.slaterArray[i] = this.slaters.get(i);

}if (this.scaleSlaters) for (var i = 0; i < this.slaterArray.length; i++) {
var sd = this.slaterArray[i];
sd.coef *= this.scaleSlater(sd.x, sd.y, sd.z, sd.r, sd.zeta);
if (this.debugging) {
JU.Logger.debug("SlaterReader " + i + ": " + sd.atomNo + " " + sd.x + " " + sd.y + " " + sd.z + " " + sd.r + " " + sd.zeta + " " + sd.coef);
}}
if (doSort) {
java.util.Arrays.sort(this.slaterArray, Clazz.innerTypeInstance(J.adapter.readers.quantum.SlaterReader.SlaterSorter, this, null));
var pointers =  Clazz.newIntArray (this.slaterArray.length, 0);
for (var i = 0; i < this.slaterArray.length; i++) pointers[i] = this.slaterArray[i].index;

this.sortOrbitalCoefficients(pointers);
}this.moData.put("slaters", this.slaterArray);
this.asc.setCurrentModelInfo("moData", this.moData);
}, "~B");
Clazz.defineMethod(c$, "setMOs", 
function(units){
this.moData.put("mos", this.orbitals);
this.moData.put("energyUnits", units);
this.finalizeMOData(this.moData);
}, "~S");
Clazz.defineMethod(c$, "sortOrbitalCoefficients", 
function(pointers){
for (var i = this.orbitals.size(); --i >= 0; ) {
var mo = this.orbitals.get(i);
var coefs = mo.get("coefficients");
var sorted =  Clazz.newFloatArray (pointers.length, 0);
for (var j = 0; j < pointers.length; j++) {
var k = pointers[j];
if (k < coefs.length) sorted[j] = coefs[k];
}
mo.put("coefficients", sorted);
}
}, "~A");
Clazz.defineMethod(c$, "sortOrbitals", 
function(){
var array = this.orbitals.toArray( new Array(0));
java.util.Arrays.sort(array, Clazz.innerTypeInstance(J.adapter.readers.quantum.SlaterReader.OrbitalSorter, this, null));
this.orbitals.clear();
for (var i = 0; i < array.length; i++) this.orbitals.addLast(array[i]);

});
Clazz.defineMethod(c$, "scaleSlater", 
function(ex, ey, ez, er, zeta){
var el = ex + ey + ez;
switch (el) {
case 0:
case 1:
ez = -1;
break;
}
return J.adapter.readers.quantum.SlaterReader.getSlaterConstCartesian(el + er + 1, Math.abs(zeta), el, ex, ey, ez);
}, "~N,~N,~N,~N,~N");
c$.fact = Clazz.defineMethod(c$, "fact", 
function(f, zeta, n){
return Math.pow(2 * zeta, n + 0.5) * Math.sqrt(f * 0.07957747154594767 / J.adapter.readers.quantum.SlaterReader.fact_2n[n]);
}, "~N,~N,~N");
c$.getSlaterConstCartesian = Clazz.defineMethod(c$, "getSlaterConstCartesian", 
function(n, zeta, el, ex, ey, ez){
var f = ez < 0 ? J.adapter.readers.quantum.SlaterReader.dfact2[el + 1] : J.adapter.readers.quantum.SlaterReader.dfact2[el + 1] / J.adapter.readers.quantum.SlaterReader.dfact2[ex] / J.adapter.readers.quantum.SlaterReader.dfact2[ey] / J.adapter.readers.quantum.SlaterReader.dfact2[ez];
return J.adapter.readers.quantum.SlaterReader.fact(f, zeta, n);
}, "~N,~N,~N,~N,~N,~N");
c$.$SlaterReader$SlaterSorter$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum.SlaterReader, "SlaterSorter", null, java.util.Comparator);
Clazz.overrideMethod(c$, "compare", 
function(sd1, sd2){
return (sd1.atomNo < sd2.atomNo ? -1 : sd1.atomNo > sd2.atomNo ? 1 : 0);
}, "J.quantum.SlaterData,J.quantum.SlaterData");
/*eoif4*/})();
};
c$.$SlaterReader$OrbitalSorter$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum.SlaterReader, "OrbitalSorter", null, java.util.Comparator);
Clazz.overrideMethod(c$, "compare", 
function(mo1, mo2){
var e1 = (mo1.get("energy")).floatValue();
var e2 = (mo2.get("energy")).floatValue();
return (e1 < e2 ? -1 : e2 < e1 ? 1 : 0);
}, "java.util.Map,java.util.Map");
/*eoif4*/})();
};
c$.fact_2n =  Clazz.newDoubleArray(-1, [1, 2, 24, 720, 40320, 3628800, 479001600]);
c$.dfact2 =  Clazz.newDoubleArray(-1, [1, 1, 3, 15, 105]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
