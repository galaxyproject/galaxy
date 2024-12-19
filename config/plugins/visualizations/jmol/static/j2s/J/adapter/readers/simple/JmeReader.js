Clazz.declarePackage("J.adapter.readers.simple");
Clazz.load(["J.adapter.smarter.AtomSetCollectionReader"], "J.adapter.readers.simple.JmeReader", ["JU.PT", "J.adapter.smarter.Bond"], function(){
var c$ = Clazz.declareType(J.adapter.readers.simple, "JmeReader", J.adapter.smarter.AtomSetCollectionReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.asc.setCollectionName("JME");
this.asc.newAtomSet();
this.line = this.rd().$replace('\t', ' ');
this.checkCurrentLineForScript();
this.addJmolScript("jmeString='" + this.line + "'");
var ac = this.parseInt();
var bondCount = this.parseInt();
this.readAtoms(ac);
this.readBonds(bondCount);
if (this.asc.ac == 0 && this.line.equals("0") && !this.merging) {
var atom = this.asc.addNewAtom();
this.setAtomCoordXYZ(atom, NaN, NaN, 0);
this.addJmolScript("delete thisModel");
} else {
this.set2D();
}this.continuing = false;
});
Clazz.defineMethod(c$, "readAtoms", 
function(ac){
for (var i = 0; i < ac; ++i) {
var strAtom = this.parseToken();
var atom = this.asc.addNewAtom();
this.setAtomCoordXYZ(atom, this.parseFloat(), this.parseFloat(), 0);
var indexColon = strAtom.indexOf(':');
var elementSymbol = (indexColon > 0 ? strAtom.substring(0, indexColon) : strAtom);
if (elementSymbol.indexOf("+") >= 0) {
elementSymbol = JU.PT.trim(elementSymbol, "+");
atom.formalCharge = 1;
} else if (elementSymbol.indexOf("-") >= 0) {
elementSymbol = JU.PT.trim(elementSymbol, "-");
atom.formalCharge = -1;
}atom.elementSymbol = elementSymbol;
}
if (ac > 0) this.asc.setModelInfoForSet("dimension", "2D", this.asc.iSet);
}, "~N");
Clazz.defineMethod(c$, "readBonds", 
function(bondCount){
for (var i = 0; i < bondCount; ++i) {
var atomIndex1 = this.parseInt() - 1;
var atomIndex2 = this.parseInt() - 1;
var order = this.parseInt();
switch (order) {
default:
continue;
case 1:
case 2:
case 3:
break;
case -1:
order = 1025;
break;
case -2:
order = 1041;
break;
}
this.asc.addBond( new J.adapter.smarter.Bond(atomIndex1, atomIndex2, order));
}
}, "~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
