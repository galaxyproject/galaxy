Clazz.declarePackage("JM");
Clazz.load(["JM.Monomer"], "JM.AlphaMonomer", ["JU.Quat", "$.V3", "J.c.STR", "JM.Helix", "$.Sheet", "$.Turn"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.proteinStructure = null;
this.nitrogenHydrogenPoint = null;
Clazz.instantialize(this, arguments);}, JM, "AlphaMonomer", JM.Monomer);
Clazz.overrideConstructor(c$, 
function(){
});
Clazz.overrideMethod(c$, "isProtein", 
function(){
return true;
});
c$.validateAndAllocateA = Clazz.defineMethod(c$, "validateAndAllocateA", 
function(chain, group3, seqcode, firstIndex, lastIndex, specialAtomIndexes){
return (firstIndex != lastIndex || specialAtomIndexes[2] != firstIndex ? null :  new JM.AlphaMonomer().set2(chain, group3, seqcode, firstIndex, lastIndex, JM.AlphaMonomer.alphaOffsets));
}, "JM.Chain,~S,~N,~N,~N,~A");
Clazz.defineMethod(c$, "isAlphaMonomer", 
function(){
return true;
});
Clazz.overrideMethod(c$, "getStructure", 
function(){
return this.proteinStructure;
});
Clazz.defineMethod(c$, "setStructure", 
function(ps){
if ((this.proteinStructure = ps) == null) this.nitrogenHydrogenPoint = null;
}, "JM.ProteinStructure");
Clazz.overrideMethod(c$, "setStrucNo", 
function(n){
if (this.proteinStructure != null) this.proteinStructure.strucNo = n;
}, "~N");
Clazz.overrideMethod(c$, "getProteinStructureType", 
function(){
return this.proteinStructure == null ? J.c.STR.NONE : this.proteinStructure.type;
});
Clazz.overrideMethod(c$, "getProteinStructureSubType", 
function(){
return this.proteinStructure == null ? J.c.STR.NONE : this.proteinStructure.subtype;
});
Clazz.overrideMethod(c$, "getStrucNo", 
function(){
return this.proteinStructure != null ? this.proteinStructure.strucNo : 0;
});
Clazz.overrideMethod(c$, "isHelix", 
function(){
return this.proteinStructure != null && this.proteinStructure.type === J.c.STR.HELIX;
});
Clazz.overrideMethod(c$, "isSheet", 
function(){
return this.proteinStructure != null && this.proteinStructure.type === J.c.STR.SHEET;
});
Clazz.overrideMethod(c$, "setProteinStructureType", 
function(type, monomerIndexCurrent){
if (this.proteinStructure != null) this.proteinStructure.removeMonomer(this.monomerIndex);
if (monomerIndexCurrent < 0 || monomerIndexCurrent > 0 && this.monomerIndex == 0) {
switch (type) {
case J.c.STR.HELIX:
case J.c.STR.HELIXALPHA:
case J.c.STR.HELIX310:
case J.c.STR.HELIXPI:
this.setStructure( new JM.Helix(this.bioPolymer, this.monomerIndex, 1, type));
break;
case J.c.STR.SHEET:
this.setStructure( new JM.Sheet(this.bioPolymer, this.monomerIndex, 1, type));
break;
case J.c.STR.TURN:
this.setStructure( new JM.Turn(this.bioPolymer, this.monomerIndex, 1));
break;
case J.c.STR.NONE:
this.setStructure(null);
}
} else {
this.setStructure(this.bioPolymer.getProteinStructure(monomerIndexCurrent));
if (this.proteinStructure != null) this.proteinStructure.addMonomer(this.monomerIndex);
}return this.monomerIndex;
}, "J.c.STR,~N");
Clazz.defineMethod(c$, "getAtom", 
function(specialAtomID){
return (specialAtomID == 2 ? this.getLeadAtom() : null);
}, "~N");
Clazz.defineMethod(c$, "getAtomPoint", 
function(specialAtomID){
return (specialAtomID == 2 ? this.getLeadAtom() : null);
}, "~N");
Clazz.overrideMethod(c$, "isConnectedAfter", 
function(possiblyPreviousMonomer){
if (possiblyPreviousMonomer == null) return true;
var atom1 = this.getLeadAtom();
var atom2 = possiblyPreviousMonomer.getLeadAtom();
return atom1.isBonded(atom2) || atom1.distance(atom2) <= 4.2;
}, "JM.Monomer");
Clazz.overrideMethod(c$, "getQuaternionFrameCenter", 
function(qType){
return this.getQuaternionFrameCenterAlpha(qType);
}, "~S");
Clazz.overrideMethod(c$, "isWithinStructure", 
function(type){
return (this.proteinStructure != null && this.proteinStructure.type === type && this.proteinStructure.isWithin(this.monomerIndex));
}, "J.c.STR");
Clazz.defineMethod(c$, "getQuaternionFrameCenterAlpha", 
function(qType){
switch ((qType).charCodeAt(0)) {
case 98:
case 99:
case 67:
case 120:
return this.getLeadAtom();
default:
case 97:
case 110:
case 112:
case 80:
case 113:
return null;
}
}, "~S");
Clazz.overrideMethod(c$, "getHelixData", 
function(tokType, qType, mStep){
return this.getHelixData2(tokType, qType, mStep);
}, "~N,~S,~N");
Clazz.overrideMethod(c$, "getQuaternion", 
function(qType){
return this.getQuaternionAlpha(qType);
}, "~S");
Clazz.defineMethod(c$, "getQuaternionAlpha", 
function(qType){
if (this.monomerIndex < 0) return null;
var vA =  new JU.V3();
var vB =  new JU.V3();
var vC = null;
switch ((qType).charCodeAt(0)) {
default:
case 97:
case 110:
case 112:
case 113:
return null;
case 98:
case 99:
case 120:
if (this.monomerIndex == 0 || this.monomerIndex == this.bioPolymer.monomerCount - 1) return null;
var ptCa = this.getLeadAtom();
var ptCaNext = this.bioPolymer.getLeadPoint(this.monomerIndex + 1);
var ptCaPrev = this.bioPolymer.getLeadPoint(this.monomerIndex - 1);
vA.sub2(ptCaNext, ptCa);
vB.sub2(ptCaPrev, ptCa);
break;
}
return JU.Quat.getQuaternionFrameV(vA, vB, vC, false);
}, "~S");
c$.alphaOffsets =  Clazz.newByteArray(-1, [0]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
