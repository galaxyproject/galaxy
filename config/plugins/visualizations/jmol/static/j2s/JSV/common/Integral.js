Clazz.declarePackage("JSV.common");
Clazz.load(["JSV.common.Measurement"], "JSV.common.Integral", null, function(){
var c$ = Clazz.declareType(JSV.common, "Integral", JSV.common.Measurement);
Clazz.defineMethod(c$, "setInt", 
function(x1, y1, spec, value, x2, y2){
this.setA(x1, y1, spec, "", false, false, 0, 6);
this.setPt2(x2, y2);
this.setValue(value);
return this;
}, "~N,~N,JSV.common.Spectrum,~N,~N,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
