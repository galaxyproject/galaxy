Clazz.declarePackage("JSV.common");
Clazz.load(["JSV.common.Measurement"], "JSV.common.PeakPick", null, function(){
var c$ = Clazz.declareType(JSV.common, "PeakPick", JSV.common.Measurement);
Clazz.defineMethod(c$, "setValue", 
function(x, y, spec, text, value){
if (text == null) {
this.set(x, y);
this.setPt2(spec, false);
} else {
this.setA(x, y, spec, text, false, false, 0, 6);
this.value = value;
this.setPt2(this.getXVal(), this.getYVal());
}return this;
}, "~N,~N,JSV.common.Spectrum,~S,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
