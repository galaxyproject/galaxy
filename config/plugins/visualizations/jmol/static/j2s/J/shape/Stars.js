Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.AtomShape"], "J.shape.Stars", null, function(){
var c$ = Clazz.declareType(J.shape, "Stars", J.shape.AtomShape);
Clazz.overrideMethod(c$, "setProperty", 
function(propertyName, value, bs){
this.setPropAS(propertyName, value, bs);
}, "~S,~O,JU.BS");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
