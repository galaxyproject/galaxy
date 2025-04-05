Clazz.declarePackage("J.quantum");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.isCore = false;
this.atomNo = 0;
this.elemNo = 0;
this.x = 0;
this.y = 0;
this.z = 0;
this.r = 0;
this.zeta = 0;
this.coef = 0;
this.index = 0;
Clazz.instantialize(this, arguments);}, J.quantum, "SlaterData", null);
Clazz.makeConstructor(c$, 
function(iAtom, x, y, z, r, zeta, coef){
this.atomNo = iAtom;
this.x = x;
this.y = y;
this.z = z;
this.r = r;
this.zeta = zeta;
this.coef = coef;
}, "~N,~N,~N,~N,~N,~N,~N");
Clazz.overrideMethod(c$, "toString", 
function(){
return "[" + this.atomNo + "," + this.x + "," + this.y + "," + this.z + "," + this.r + "," + this.zeta + "," + this.coef + "]";
});
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
