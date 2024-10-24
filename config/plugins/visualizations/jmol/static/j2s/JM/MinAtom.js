Clazz.declarePackage("JM");
Clazz.load(["JU.BS", "$.Lst"], "JM.MinAtom", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.atom = null;
this.index = 0;
this.sType = null;
this.coord = null;
this.force = null;
this.bonds = null;
this.nBonds = 0;
this.bondedAtoms = null;
this.bsVdw = null;
this.hCount = -1;
this.partialCharge = 0;
this.ffAtomType = null;
this.ffType = 0;
this.vdwKey = null;
this.bs14 = null;
Clazz.instantialize(this, arguments);}, JM, "MinAtom", null);
Clazz.prepareFields (c$, function(){
this.coord =  Clazz.newDoubleArray (3, 0);
this.force =  Clazz.newDoubleArray (3, 0);
this.bonds =  new JU.Lst();
this.bsVdw =  new JU.BS();
this.bs14 =  new JU.BS();
});
Clazz.makeConstructor(c$, 
function(index, atom, coord, ac){
this.index = index;
this.atom = atom;
this.coord = coord;
this.bsVdw.setBits(index + 1, ac);
this.bsVdw.clear(index);
}, "~N,JM.Atom,~A,~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return "#" + this.index + "@" + this.atom.i + " " + this.sType + " " + this.coord[0] + "," + this.coord[1] + "," + this.coord[2];
});
Clazz.defineMethod(c$, "set", 
function(){
this.coord[0] = this.atom.x;
this.coord[1] = this.atom.y;
this.coord[2] = this.atom.z;
});
Clazz.defineMethod(c$, "getBondTo", 
function(iAtom){
this.getBondedAtomIndexes();
for (var i = 0; i < this.nBonds; i++) if (this.bondedAtoms[i] == iAtom) return this.bonds.get(i);

return null;
}, "~N");
Clazz.defineMethod(c$, "getBondedAtomIndexes", 
function(){
if (this.bondedAtoms == null) {
this.bondedAtoms =  Clazz.newIntArray (this.nBonds, 0);
for (var i = this.nBonds; --i >= 0; ) this.bondedAtoms[i] = this.bonds.get(i).getOtherAtom(this.index);

}return this.bondedAtoms;
});
Clazz.defineMethod(c$, "getIdentity", 
function(){
return this.atom.getInfo();
});
Clazz.defineMethod(c$, "addBond", 
function(bond, i){
this.bonds.addLast(bond);
this.nBonds++;
this.bsVdw.clear(i);
}, "JM.MinBond,~N");
Clazz.defineMethod(c$, "getBondIndex", 
function(j){
return this.bonds.get(j).index;
}, "~N");
Clazz.defineMethod(c$, "getHCount", 
function(){
if (this.hCount < 0) this.hCount = this.atom.getCovalentHydrogenCount();
return this.hCount;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
