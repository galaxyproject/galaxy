Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.FontLineShape", "JU.P3", "$.V3"], "J.shape.Axes", ["JU.PT", "JU.Escape", "JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.axisXY = null;
this.scale = 0;
this.fixedOrigin = null;
this.originPoint = null;
this.axisPoints = null;
this.labels = null;
this.axisType = null;
this.axes2 = null;
this.pt0 = null;
this.fixedOriginUC = null;
this.corner = null;
Clazz.instantialize(this, arguments);}, J.shape, "Axes", J.shape.FontLineShape);
Clazz.prepareFields (c$, function(){
this.axisXY =  new JU.P3();
this.originPoint =  new JU.P3();
this.axisPoints =  new Array(6);
{
for (var i = 6; --i >= 0; ) this.axisPoints[i] =  new JU.P3();

}this.pt0 =  new JU.P3();
this.fixedOriginUC =  new JU.P3();
this.corner =  new JU.V3();
});
Clazz.overrideMethod(c$, "setProperty", 
function(propertyName, value, bs){
if ("position" === propertyName) {
var doSetScale = (this.axisXY.z == 0 && (value).z != 0);
this.axisXY = value;
this.setScale(doSetScale ? 1 : this.scale);
return;
}if ("origin" === propertyName) {
if (value == null || (value).length() == 0) {
this.fixedOrigin = null;
} else {
if (this.fixedOrigin == null) this.fixedOrigin =  new JU.P3();
this.fixedOrigin.setT(value);
}this.reinitShape();
return;
}if ("labels" === propertyName) {
this.labels = value;
return;
}if ("labelsOn" === propertyName) {
this.labels = null;
return;
}if ("labelsOff" === propertyName) {
this.labels =  Clazz.newArray(-1, ["", "", ""]);
return;
}if ("type" === propertyName) {
this.axisType = value;
if ("abc".equals(this.axisType)) this.axisType = null;
}if ("axes2" === propertyName) {
this.axes2 = (value == null || value.equals("") ? null : value);
return;
}this.setPropFLS(propertyName, value);
}, "~S,~O,JU.BS");
Clazz.overrideMethod(c$, "initShape", 
function(){
this.translucentAllowed = false;
this.myType = "axes";
this.font3d = this.vwr.gdata.getFont3D(16);
this.setPoints(this.vwr.g.axesMode);
});
Clazz.defineMethod(c$, "setPoints", 
function(axesMode){
var unitcell;
if (axesMode != 603979808 || this.ms.unitCells == null || (unitcell = this.vwr.getCurrentUnitCell()) == null) {
this.originPoint.setT(this.fixedOrigin != null ? this.fixedOrigin : axesMode == 603979809 ? this.vwr.getBoundBoxCenter() : this.pt0);
this.setScale(this.vwr.getFloat(570425346) / 2);
return;
}var fset = unitcell.getUnitCellMultiplier();
unitcell = unitcell.getUnitCellMultiplied();
var voffset = this.vwr.getFloat(570425345);
this.fixedOriginUC.set(voffset, voffset, voffset);
var offset = unitcell.getCartesianOffset();
var vertices = unitcell.getUnitCellVerticesNoOffset();
this.originPoint.add2(offset, vertices[0]);
if (voffset != 0) unitcell.toCartesian(this.fixedOriginUC, false);
 else if (this.fixedOrigin != null) this.originPoint.setT(this.fixedOrigin);
if (voffset != 0) {
this.originPoint.add(this.fixedOriginUC);
}var scale = this.scale = this.vwr.getFloat(570425346) / 2;
if (fset != null && fset.z > 0) scale *= Math.abs(fset.z);
this.axisPoints[0].scaleAdd2(scale, vertices[4], this.originPoint);
this.axisPoints[1].scaleAdd2(scale, vertices[2], this.originPoint);
this.axisPoints[2].scaleAdd2(scale, vertices[1], this.originPoint);
}, "~N");
Clazz.defineMethod(c$, "reinitShape", 
function(){
var f = this.font3d;
this.initShape();
if (f != null) this.font3d = f;
});
Clazz.defineMethod(c$, "getAxisPoint", 
function(i, unscaled, ptTemp){
if (unscaled) {
ptTemp.setT(this.axisPoints[i]);
} else {
ptTemp.sub2(this.axisPoints[i], this.originPoint);
ptTemp.scale(0.5);
}return ptTemp;
}, "~N,~B,JU.P3");
Clazz.overrideMethod(c$, "getProperty", 
function(property, index){
if (property === "originPoint") return this.originPoint;
if (property === "axisPoints") return this.axisPoints;
if (property === "axesTypeXY") return (this.axisXY.z == 0 ? Boolean.FALSE : Boolean.TRUE);
if (property === "origin") return this.fixedOrigin;
return null;
}, "~S,~N");
Clazz.defineMethod(c$, "setScale", 
function(scale){
this.scale = scale;
this.corner.setT(this.vwr.getBoundBoxCornerVector());
for (var i = 6; --i >= 0; ) {
var axisPoint = this.axisPoints[i];
axisPoint.setT(JV.JC.unitAxisVectors[i]);
if (this.corner.x < 1.5) this.corner.x = 1.5;
if (this.corner.y < 1.5) this.corner.y = 1.5;
if (this.corner.z < 1.5) this.corner.z = 1.5;
if (this.axisXY.z == 0) {
axisPoint.x *= this.corner.x * scale;
axisPoint.y *= this.corner.y * scale;
axisPoint.z *= this.corner.z * scale;
}axisPoint.add(this.originPoint);
}
}, "~N");
Clazz.defineMethod(c$, "getAxesState", 
function(sb){
sb.append("  axes scale ").appendF(this.vwr.getFloat(570425346)).append(";\n");
if (this.fixedOrigin != null) sb.append("  axes center ").append(JU.Escape.eP(this.fixedOrigin)).append(";\n");
if (this.axisXY.z != 0) sb.append("  axes position [").appendI(Clazz.floatToInt(this.axisXY.x)).append(" ").appendI(Clazz.floatToInt(this.axisXY.y)).append(" ").append(this.axisXY.z < 0 ? " %" : "").append("]");
if (this.axes2 != null) sb.append(" ").append(JU.PT.esc(this.axes2));
sb.append(";\n");
if (this.labels != null) {
sb.append("  axes labels ");
for (var i = 0; i < this.labels.length; i++) if (this.labels[i] != null) sb.append(JU.PT.esc(this.labels[i])).append(" ");

sb.append(";\n");
}if (this.axisType != null) {
sb.append("  axes type " + JU.PT.esc(this.axisType));
}return sb.toString();
}, "JU.SB");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
