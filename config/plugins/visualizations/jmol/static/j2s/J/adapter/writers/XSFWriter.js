Clazz.declarePackage("J.adapter.writers");
Clazz.load(["J.api.JmolWriter"], "J.adapter.writers.XSFWriter", ["JU.PT"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.oc = null;
this.uc = null;
this.len = 0;
Clazz.instantialize(this, arguments);}, J.adapter.writers, "XSFWriter", null, J.api.JmolWriter);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "set", 
function(viewer, oc, data){
this.vwr = viewer;
this.oc = (oc == null ? this.vwr.getOutputChannel(null, null) : oc);
}, "JV.Viewer,JU.OC,~A");
Clazz.overrideMethod(c$, "write", 
function(bs){
if (bs == null) bs = this.vwr.bsA();
this.len = bs.length();
if (this.len == 0) return "";
try {
var a = this.vwr.ms.at;
var i0 = bs.nextSetBit(0);
this.uc = this.vwr.ms.getUnitCellForAtom(i0);
var model1 = a[i0].getModelIndex();
var model2 = a[this.len - 1].getModelIndex();
var isAnim = (model2 != model1);
if (isAnim) {
var nModels = this.vwr.ms.getModelBS(bs, false).cardinality();
this.oc.append("ANIMSTEPS " + nModels + "\n");
}if (this.uc != null) this.oc.append("CRYSTAL\n");
var f = "%4i%18.12p%18.12p%18.12p\n";
var prefix = (this.uc == null ? "ATOMS" : "PRIMCOORD");
for (var lastmi = -1, imodel = 0, i = bs.nextSetBit(0); i >= 0; i = bs.nextSetBit(i + 1)) {
var atom = a[i];
var mi = atom.getModelIndex();
if (mi != lastmi) {
var sn = (isAnim ? " " + (++imodel) : "");
var header = prefix + sn + "\n";
this.uc = this.vwr.ms.getUnitCellForAtom(i);
if (this.uc == null) {
this.oc.append(header);
} else {
this.writeLattice(sn);
this.oc.append(header);
var bsm = this.vwr.restrictToModel(bs, mi);
this.oc.append(JU.PT.formatStringI("%6i 1\n", "i", bsm.cardinality()));
}lastmi = mi;
}this.oc.append(JU.PT.sprintf(f, "ip",  Clazz.newArray(-1, [Integer.$valueOf(atom.getElementNumber()), atom])));
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return this.toString();
}, "JU.BS");
Clazz.defineMethod(c$, "writeLattice", 
function(sn){
var abc = this.uc.getUnitCellVectors();
var f = "%18.10p%18.10p%18.10p\n";
var s = JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[1]])) + JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[2]])) + JU.PT.sprintf(f, "p",  Clazz.newArray(-1, [abc[3]]));
this.oc.append("PRIMVEC" + sn + "\n").append(s).append("CONVVEC" + sn + "\n").append(s);
}, "~S");
Clazz.overrideMethod(c$, "toString", 
function(){
return (this.oc == null ? "" : this.oc.toString());
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
