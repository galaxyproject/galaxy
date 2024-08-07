Clazz.declarePackage("J.render");
Clazz.load(["J.render.CageRenderer", "JU.P3"], "J.render.AxesRenderer", ["JV.JC"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.originScreen = null;
this.colixes = null;
this.pt000 = null;
this.ptTemp = null;
Clazz.instantialize(this, arguments);}, J.render, "AxesRenderer", J.render.CageRenderer);
Clazz.prepareFields (c$, function(){
this.originScreen =  new JU.P3();
this.colixes =  Clazz.newShortArray (3, 0);
this.ptTemp =  new JU.P3();
});
Clazz.overrideMethod(c$, "initRenderer", 
function(){
this.endcap = 2;
this.draw000 = false;
});
Clazz.overrideMethod(c$, "render", 
function(){
var axes = this.shape;
var mad10 = this.vwr.getObjectMad10(1);
var isXY = (axes.axisXY.z != 0);
if (mad10 == 0 || !this.g3d.checkTranslucent(false)) return false;
if (isXY ? this.exportType == 1 : this.tm.isNavigating() && this.vwr.getBoolean(603979890)) return false;
var modelIndex = this.vwr.am.cmi;
if (this.ms.isJmolDataFrameForModel(modelIndex) && !this.ms.getJmolFrameType(modelIndex).equals("plot data")) return false;
var isUnitCell = (this.vwr.g.axesMode == 603979808);
var unitcell = (isUnitCell ? this.vwr.getCurrentUnitCell() : null);
if (isUnitCell && (unitcell == null || modelIndex < 0)) return false;
this.imageFontScaling = this.vwr.imageFontScaling;
if (this.vwr.areAxesTainted()) axes.reinitShape();
this.font3d = this.vwr.gdata.getFont3DScaled(axes.font3d, this.imageFontScaling);
isUnitCell = isUnitCell && (unitcell != null && this.ms.unitCells != null);
var axisType = (isUnitCell ? axes.axisType : null);
var isabcxyz = (isXY && isUnitCell && axes.axes2 != null);
this.isPolymer = isUnitCell && unitcell.isPolymer();
this.isSlab = isUnitCell && unitcell.isSlab();
var scale = axes.scale;
if (isabcxyz) {
if ("xyzabc".equals(axes.axes2)) this.render1(axes, mad10, false, axisType, isUnitCell, 2, null);
if (!"abc".equals(axes.axes2)) this.vwr.setBooleanProperty("axesmolecular", true);
axes.reinitShape();
this.render1(axes, mad10, true, null, false, scale, axes.axes2);
this.vwr.setBooleanProperty("axesunitcell", true);
} else {
this.render1(axes, mad10, isXY, axisType, isUnitCell, scale, null);
}return true;
});
Clazz.defineMethod(c$, "render1", 
function(axes, mad10, isXY, axisType, isUnitCell, scale, labels2){
var isDataFrame = this.vwr.isJmolDataFrame();
this.pt000 = (isDataFrame ? this.pt0 : axes.originPoint);
var nPoints = 6;
var labelPtr = 0;
if (isUnitCell) {
nPoints = 3;
labelPtr = 6;
} else if (isXY) {
nPoints = 3;
labelPtr = 9;
} else if (this.vwr.g.axesMode == 603979809) {
nPoints = 6;
labelPtr = (this.vwr.getBoolean(603979806) ? 15 : 9);
}if (axes.labels != null) {
if (nPoints != 3) nPoints = (axes.labels.length < 6 ? 3 : 6);
labelPtr = -1;
}var slab = this.vwr.gdata.slab;
var diameter = mad10;
var drawTicks = false;
this.ptTemp.setT(this.originScreen);
var checkAxisType = (labels2 == null && axisType != null && (isXY || this.vwr.getFloat(570425345) != 0 || axes.fixedOrigin != null));
if (isXY) {
if (mad10 >= 20) {
diameter = (mad10 > 500 ? 3 : Clazz.doubleToInt(mad10 / 200));
if (diameter == 0) diameter = 2;
}if (this.g3d.isAntialiased()) diameter += diameter;
this.g3d.setSlab(0);
this.ptTemp.setT(axes.axisXY);
this.pt0i.setT(this.tm.transformPt2D(this.ptTemp));
if (this.ptTemp.x < 0) {
var offx = Clazz.floatToInt(this.ptTemp.x);
var offy = Clazz.floatToInt(this.ptTemp.x);
this.pointT.setT(this.pt000);
for (var i = 0; i < 3; i++) this.pointT.add(axes.getAxisPoint(i, false, this.ptTemp));

this.pt0i.setT(this.tm.transformPt(this.pt000));
this.pt2i.scaleAdd(-1, this.pt0i, this.tm.transformPt(this.pointT));
if (this.pt2i.x < 0) offx = -offx;
if (this.pt2i.y < 0) offy = -offy;
this.pt0i.x += offx;
this.pt0i.y += offy;
}this.ptTemp.set(this.pt0i.x, this.pt0i.y, this.pt0i.z);
var zoomDimension = this.vwr.getScreenDim();
var scaleFactor = zoomDimension / 10 * scale;
if (this.g3d.isAntialiased()) scaleFactor *= 2;
if ((isUnitCell || "abc".equals(axes.axes2)) && isXY) scaleFactor /= 2;
for (var i = 0; i < 3; i++) {
var pt = this.p3Screens[i];
this.tm.rotatePoint(axes.getAxisPoint(i, false, this.pointT), pt);
pt.z *= -1;
pt.scaleAdd2(scaleFactor, pt, this.ptTemp);
}
} else {
drawTicks = (axes.tickInfos != null);
if (drawTicks) {
this.checkTickTemps();
this.tickA.setT(this.pt000);
}this.tm.transformPtNoClip(this.pt000, this.ptTemp);
diameter = this.getDiameter(Clazz.floatToInt(this.ptTemp.z), mad10);
for (var i = nPoints; --i >= 0; ) this.tm.transformPtNoClip(axes.getAxisPoint(i, !isDataFrame, this.pointT), this.p3Screens[i]);

}var xCenter = this.ptTemp.x;
var yCenter = this.ptTemp.y;
this.colixes[0] = this.vwr.getObjectColix(1);
this.colixes[1] = this.vwr.getObjectColix(2);
this.colixes[2] = this.vwr.getObjectColix(3);
var showOrigin = (!isXY && nPoints == 3 && (scale == 2 || isUnitCell));
for (var i = nPoints; --i >= 0; ) {
if (labels2 != null && i >= labels2.length || checkAxisType && !axisType.contains(JV.JC.axesTypes[i]) || this.exportType != 1 && (Math.abs(xCenter - this.p3Screens[i].x) + Math.abs(yCenter - this.p3Screens[i].y) <= 2) && (!(showOrigin = false))) {
continue;
}this.colix = this.colixes[i % 3];
this.g3d.setC(this.colix);
var label = (labels2 != null ? labels2.substring(i, i + 1) : axes.labels == null ? JV.JC.axisLabels[i + labelPtr] : i < axes.labels.length ? axes.labels[i] : null);
if (label != null && label.length > 0) this.renderLabel(label, this.p3Screens[i].x, this.p3Screens[i].y, this.p3Screens[i].z, xCenter, yCenter);
if (drawTicks) {
this.tickInfo = axes.tickInfos[(i % 3) + 1];
if (this.tickInfo == null) this.tickInfo = axes.tickInfos[0];
if (this.tickInfo != null) {
this.tickB.setT(axes.getAxisPoint(i, isDataFrame || isUnitCell, this.pointT));
this.tickInfo.first = 0;
this.tickInfo.signFactor = (i % 6 >= 3 ? -1 : 1);
}}var d = (this.isSlab && i == 2 || this.isPolymer && i > 0 ? -4 : diameter);
this.renderLine(this.ptTemp, this.p3Screens[i], d, drawTicks && this.tickInfo != null);
}
if (showOrigin) {
var label0 = (axes.labels == null || axes.labels.length == 3 || axes.labels[3] == null ? "0" : axes.labels[3]);
if (label0 != null && label0.length != 0) {
this.colix = this.vwr.cm.colixBackgroundContrast;
this.g3d.setC(this.colix);
this.renderLabel(label0, xCenter, yCenter, this.ptTemp.z, xCenter, yCenter);
}}if (isXY) this.g3d.setSlab(slab);
}, "J.shape.Axes,~N,~B,~S,~B,~N,~S");
Clazz.defineMethod(c$, "renderLabel", 
function(str, x, y, z, xCenter, yCenter){
var strAscent = this.font3d.getAscent();
var strWidth = this.font3d.stringWidth(str);
var dx = x - xCenter;
var dy = y - yCenter;
if ((dx != 0 || dy != 0)) {
var dist = Math.sqrt(dx * dx + dy * dy);
dx = (strWidth * 0.75 * dx / dist);
dy = (strAscent * 0.75 * dy / dist);
x += dx;
y += dy;
}var xStrBaseline = Math.floor(x - strWidth / 2);
var yStrBaseline = Math.floor(y + strAscent / 2);
this.g3d.drawString(str, this.font3d, Clazz.doubleToInt(xStrBaseline), Clazz.doubleToInt(yStrBaseline), Clazz.floatToInt(z), Clazz.floatToInt(z), 0);
}, "~S,~N,~N,~N,~N,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
