Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.Shape"], "J.shape.FontLineShape", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.tickInfos = null;
this.font3d = null;
Clazz.instantialize(this, arguments);}, J.shape, "FontLineShape", J.shape.Shape);
Clazz.overrideMethod(c$, "initShape", 
function(){
this.translucentAllowed = false;
});
Clazz.defineMethod(c$, "setPropFLS", 
function(propertyName, value){
if ("tickInfo" === propertyName) {
var t = value;
var type = t.type;
if (t.ticks == null) {
if (t.type == ' ') {
this.tickInfos = null;
return;
}if (this.tickInfos != null) {
var haveTicks = false;
for (var i = 0; i < 4; i++) {
if (this.tickInfos[i] != null && this.tickInfos[i].type == t.type) {
this.tickInfos[i] = null;
} else {
haveTicks = true;
}}
if (!haveTicks) this.tickInfos = null;
}return;
}if (this.tickInfos == null) this.tickInfos =  new Array(4);
this.tickInfos["xyz".indexOf(type) + 1] = t;
return;
}if ("font" === propertyName) {
this.font3d = value;
return;
}}, "~S,~O");
Clazz.overrideMethod(c$, "getShapeState", 
function(){
return null;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
