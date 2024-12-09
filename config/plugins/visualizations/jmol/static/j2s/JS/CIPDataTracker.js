Clazz.declarePackage("JS");
Clazz.load(["JS.CIPData", "java.util.Hashtable"], "JS.CIPDataTracker", ["JU.BS", "JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.htTracker = null;
if (!Clazz.isClassDefined("JS.CIPDataTracker.CIPTracker")) {
JS.CIPDataTracker.$CIPDataTracker$CIPTracker$ ();
}
this.lastIndex = -1;
this.lastInfo = null;
Clazz.instantialize(this, arguments);}, JS, "CIPDataTracker", JS.CIPData);
Clazz.prepareFields (c$, function(){
this.htTracker =  new java.util.Hashtable();
});
Clazz.overrideMethod(c$, "isTracker", 
function(){
return true;
});
Clazz.overrideMethod(c$, "track", 
function(cip, a, b, sphere, finalScore, trackTerminal){
if (a == null || b == null || a.rootSubstituent === b.rootSubstituent) return;
var t;
var a1;
var b1;
if (finalScore > 0) {
a1 = b;
b1 = a;
} else {
a1 = a;
b1 = b;
}t = Clazz.innerTypeInstance(JS.CIPDataTracker.CIPTracker, this, null, cip.currentRule, a1, b1, sphere, Math.abs(finalScore), trackTerminal);
this.htTracker.put(JS.CIPDataTracker.getTrackerKey(cip.root, a1, b1), t);
}, "JS.CIPChirality,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,~N,~N,~B");
Clazz.overrideMethod(c$, "getRootTrackerResult", 
function(root){
var s = "";
for (var i = 0; i < 3; i++) {
s += "\t" + root.atoms[i] + "\t--------------\n";
var t = this.htTracker.get(JS.CIPDataTracker.getTrackerKey(root, root.atoms[i], root.atoms[i + 1]));
if (t != null) {
var n = Math.max(t.bsa.length(), t.bsb.length());
s += t.getTrackerLine(t.a, t.bsa, (t.rule == 8 ? t.a.listRS[2] : null), n);
s += "\t   " + JV.JC.getCIPRuleName(t.rule) + "\n";
s += t.getTrackerLine(t.b, t.bsb, (t.rule == 8 ? t.b.listRS[2] : null), n);
}}
s += "\t" + root.atoms[3] + "\t--------------\n";
System.out.println(root + "\n\n" + s);
this.setCIPInfo(s, root.atom.getIndex(), root.atom.getAtomName());
return s;
}, "JS.CIPChirality.CIPAtom");
Clazz.defineMethod(c$, "setCIPInfo", 
function(s, index, name){
var modelInfo = this.getModelAuxiliaryInfoForAtom(index);
if (modelInfo != null) {
var cipInfo = modelInfo.get("CIPInfo");
if (cipInfo == null) modelInfo.put("CIPInfo", cipInfo =  new java.util.Hashtable());
cipInfo.put(name, s);
}}, "~S,~N,~S");
Clazz.defineMethod(c$, "getModelAuxiliaryInfoForAtom", 
function(index){
return (index == this.lastIndex ? this.lastInfo : (this.lastInfo = this.vwr.ms.getModelAuxiliaryInfo(this.vwr.ms.at[this.lastIndex = index].getModelIndex())));
}, "~N");
c$.getTrackerKey = Clazz.defineMethod(c$, "getTrackerKey", 
function(root, a, b){
return (b.rootSubstituent == null ? "" : root.atom.getAtomName() + "." + a.rootSubstituent.atom.getAtomName() + "-" + b.rootSubstituent.atom.getAtomName());
}, "JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom");
c$.$CIPDataTracker$CIPTracker$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.a = null;
this.b = null;
this.sphere = 0;
this.score = 0;
this.rule = 0;
this.bsa = null;
this.bsb = null;
this.trackTerminal = false;
Clazz.instantialize(this, arguments);}, JS.CIPDataTracker, "CIPTracker", null);
Clazz.makeConstructor(c$, 
function(rule, a, b, sphere, score, trackTerminal){
this.rule = rule;
this.a = a;
this.b = b;
this.sphere = sphere;
this.score = score;
this.trackTerminal = trackTerminal;
this.bsa = a.listRS == null ?  new JU.BS() : a.listRS[0];
this.bsb = b.listRS == null ?  new JU.BS() : b.listRS[0];
}, "~N,JS.CIPChirality.CIPAtom,JS.CIPChirality.CIPAtom,~N,~N,~B");
Clazz.defineMethod(c$, "getTrackerLine", 
function(b, bsb, bsS, n){
return "\t\t" + b.myPath + (!this.trackTerminal ? "" : b.isTerminal ? "-o" : "-" + b.atoms[0].atom.getAtomName()) + (this.rule != 8 && bsb.length() == 0 ? "" : "\t" + this.getLikeUnlike(bsb, b.listRS, n) + (bsS == null ? "" : "  " + this.getLikeUnlike(bsS, b.listRS, -n))) + "\n";
}, "JS.CIPChirality.CIPAtom,JU.BS,JU.BS,~N");
Clazz.defineMethod(c$, "getLikeUnlike", 
function(bsa, listRS, n){
if (this.rule != 8 && this.rule != 6) return "";
var s = (n > 0 && (this.rule == 8 || bsa === listRS[1]) ? "(R)" : "(S)");
n = Math.abs(n);
for (var i = 0; i < n; i++) s += (bsa.get(i) ? "l" : "u");

return s;
}, "JU.BS,~A,~N");
/*eoif4*/})();
};
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
