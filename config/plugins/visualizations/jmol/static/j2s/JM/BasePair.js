Clazz.declarePackage("JM");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.info = null;
this.g1 = null;
this.g2 = null;
Clazz.instantialize(this, arguments);}, JM, "BasePair", null);
/*LV!1824 unnec constructor*/c$.add = Clazz.defineMethod(c$, "add", 
function(info, g1, g2){
if (g1 == null || g2 == null) return null;
var bp =  new JM.BasePair();
bp.info = info;
(bp.g1 = g1).addBasePair(bp);
(bp.g2 = g2).addBasePair(bp);
return bp;
}, "java.util.Map,JM.NucleicMonomer,JM.NucleicMonomer");
Clazz.defineMethod(c$, "getPartnerAtom", 
function(g){
return (g === this.g1 ? this.g2 : this.g1).getLeadAtom().i;
}, "JM.NucleicMonomer");
Clazz.defineMethod(c$, "toString", 
function(){
return this.info.toString();
});
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
