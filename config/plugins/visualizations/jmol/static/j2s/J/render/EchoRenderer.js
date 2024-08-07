Clazz.declarePackage("J.render");
Clazz.load(["J.render.LabelsRenderer"], "J.render.EchoRenderer", ["J.render.TextRenderer", "JU.C"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.haveTranslucent = false;
Clazz.instantialize(this, arguments);}, J.render, "EchoRenderer", J.render.LabelsRenderer);
Clazz.overrideMethod(c$, "render", 
function(){
if (this.vwr.isPreviewOnly) return false;
var echo = this.shape;
this.sppm = (this.vwr.getBoolean(603979847) ? this.vwr.getScalePixelsPerAngstrom(true) * 10000 : 0);
this.imageFontScaling = this.vwr.imageFontScaling;
this.haveTranslucent = false;
var alias = (this.g3d.isAntialiased() ? 4 : 0);
for (var t, $t = echo.objects.values().iterator (); $t.hasNext()&& ((t = $t.next ()) || true);) {
this.renderEcho(t, alias);
}
if (echo.scaleObject != null) this.renderEcho(echo.scaleObject, alias);
if (!this.isExport) {
var frameTitle = this.vwr.getFrameTitle();
if (frameTitle != null && frameTitle.length > 0) {
if (this.g3d.setC(this.vwr.cm.colixBackgroundContrast)) {
this.renderFrameTitle(this.vwr.formatText(frameTitle));
}}}return this.haveTranslucent;
});
Clazz.defineMethod(c$, "renderEcho", 
function(t, alias){
if (!t.visible || t.hidden) {
return;
}if (Clazz.instanceOf(t.pointerPt,"JM.Atom")) {
if (!(t.pointerPt).checkVisible()) return;
}if (t.valign == 4) J.render.TextRenderer.calcBarPixelsXYZ(this.vwr, t, this.pt0i, true);
if (t.pymolOffset != null) t.getPymolScreenOffset(t.xyz, this.pt0i, this.zSlab, this.pTemp, this.sppm);
 else if (t.movableZPercent != 2147483647) {
var z = this.vwr.tm.zValueFromPercent(t.movableZPercent % 1000);
if (t.valign == 4 && Math.abs(t.movableZPercent) >= 1000) z = this.pt0i.z - this.vwr.tm.zValueFromPercent(0) + z;
t.setZs(z, z);
}if (t.pointerPt == null) {
t.pointer = 0;
} else {
t.pointer = 1;
this.tm.transformPtScr(t.pointerPt, this.pt0i);
t.atomX = this.pt0i.x;
t.atomY = this.pt0i.y;
t.atomZ = this.pt0i.z;
if (t.zSlab == -2147483648) t.zSlab = 1;
}if (J.render.TextRenderer.render(this.vwr, t, this.g3d, this.sppm, this.imageFontScaling, null, this.xy, this.pt2i, 0, 0, alias) && t.valign == 1 && t.align == 12) this.vwr.noFrankEcho = false;
if (JU.C.renderPass2(t.bgcolix) || JU.C.renderPass2(t.colix)) this.haveTranslucent = true;
}, "JM.Text,~N");
Clazz.defineMethod(c$, "renderFrameTitle", 
function(frameTitle){
this.vwr.gdata.setFontBold("arial", Clazz.floatToInt(24 * this.imageFontScaling));
var y = Clazz.doubleToInt(Math.floor(this.vwr.getScreenHeight() * (this.g3d.isAntialiased() ? 2 : 1) - 10 * this.imageFontScaling));
var x = Clazz.doubleToInt(Math.floor(5 * this.imageFontScaling));
this.g3d.drawStringNoSlab(frameTitle, null, x, y, 0, 0);
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
