Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.FontLineShape"], "J.shape.Bbcage", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.isVisible = false;
Clazz.instantialize(this, arguments);}, J.shape, "Bbcage", J.shape.FontLineShape);
Clazz.overrideMethod(c$, "setProperty", 
function(propertyName, value, bs){
this.setPropFLS(propertyName, value);
}, "~S,~O,JU.BS");
Clazz.defineMethod(c$, "initShape", 
function(){
Clazz.superCall(this, J.shape.Bbcage, "initShape", []);
this.font3d = this.vwr.gdata.getFont3D(16);
this.myType = "boundBox";
});
Clazz.overrideMethod(c$, "setModelVisibilityFlags", 
function(bs){
var bboxModels;
this.isVisible = (this.vwr.getShowBbcage() && ((bboxModels = this.ms.bboxModels) == null || bs.intersects(bboxModels)));
}, "JU.BS");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
