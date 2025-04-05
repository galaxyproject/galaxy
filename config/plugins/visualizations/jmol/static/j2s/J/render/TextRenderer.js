Clazz.declarePackage("J.render");
Clazz.load(null, "J.render.TextRenderer", ["JM.Text"], function(){
var c$ = Clazz.declareType(J.render, "TextRenderer", null);
c$.render = Clazz.defineMethod(c$, "render", 
function(vwr, text, g3d, scalePixelsPerMicron, imageFontScaling, boxXY, temp, pTemp, pointerColix, pointerWidth, mode){
if (text == null || text.image == null && !text.doFormatText && text.lines == null) return false;
var isAbsolute = ((mode & 64) != 0);
var doPointer = ((mode & 1) != 0);
var isAntialiased = ((mode & 4) != 0);
var colix = text.colix;
var showText = g3d.setC(colix);
if (!showText && (text.image == null && (text.bgcolix == 0 || !g3d.setC(text.bgcolix)))) return false;
if (text.isEcho && text.valign == 4) J.render.TextRenderer.calcBarPixelsXYZ(vwr, text, pTemp, false);
text.setPosition(scalePixelsPerMicron, imageFontScaling, isAbsolute, boxXY);
var barPixels = (text.isEcho && text.valign == 4 ? J.render.TextRenderer.calcBarPixelsXYZ(vwr, text, pTemp, false) : text.barPixels);
if (text.image == null) {
if (text.bgcolix != 0) {
if (g3d.setC(text.bgcolix)) J.render.TextRenderer.showBox(g3d, text.colix, Clazz.floatToInt(text.boxX) - (barPixels == 0 ? 0 : barPixels + 4), Clazz.floatToInt(text.boxY) + text.boxYoff2 * 2, text.z + 2, text.zSlab, Clazz.floatToInt(text.boxWidth) + barPixels, Clazz.floatToInt(text.boxHeight), text.fontScale, !text.isEcho);
if (!showText) return false;
}for (var i = 0; i < text.lines.length; i++) {
text.setXYA(temp, i);
if (text.xyz != null) temp[1] += 2;
g3d.drawString(text.lines[i], text.font, Clazz.floatToInt(temp[0]), Clazz.floatToInt(temp[1]), text.z, text.zSlab, text.bgcolix);
}
if (text.barPixels > 0) {
J.render.TextRenderer.renderScale(g3d, text, temp, barPixels, isAntialiased);
}} else {
g3d.drawImage(text.image, Clazz.floatToInt(text.boxX), Clazz.floatToInt(text.boxY), text.z, text.zSlab, text.bgcolix, Clazz.floatToInt(text.boxWidth), Clazz.floatToInt(text.boxHeight));
}if (!doPointer) return true;
J.render.TextRenderer.drawLineXYZ(g3d, text.atomX, text.atomY, text.atomZ, text.boxX, text.boxY, text.zSlab, text.boxWidth, text.boxHeight, pointerColix, pointerWidth * (isAntialiased ? 2 : 1));
return true;
}, "JV.Viewer,JM.Text,J.api.JmolRendererInterface,~N,~N,~A,~A,JU.P3i,~N,~N,~N");
c$.calcBarPixelsXYZ = Clazz.defineMethod(c$, "calcBarPixelsXYZ", 
function(vwr, t, pTemp, andSet){
var barPixels = t.barPixels;
if (t.xyz != null) {
vwr.tm.transformPtScr(t.xyz, pTemp);
if (andSet) t.setXYZs(pTemp.x, pTemp.y, pTemp.z, pTemp.z);
if (barPixels > 0 && vwr.tm.perspectiveDepth) {
var d = vwr.tm.unscaleToScreen(pTemp.z, barPixels);
barPixels = t.barPixelsXYZ = Clazz.floatToInt(barPixels * t.barDistance / d);
}}return barPixels;
}, "JV.Viewer,JM.Text,JU.P3i,~B");
c$.renderScale = Clazz.defineMethod(c$, "renderScale", 
function(g3d, text, temp, barPixels, isAntialiased){
var z = text.z;
var xoff = (text.xyz == null ? 0 : 2);
var ia = (isAntialiased ? 2 : 1);
var i = 1;
var x1 = xoff + Clazz.floatToInt(temp[0]) - barPixels - i - ia * 2;
var x2 = xoff + Clazz.floatToInt(temp[0]) - i - ia * 2;
var h = Clazz.doubleToInt((text.lineHeight) / 2);
var y = Clazz.floatToInt(temp[1]) - i;
g3d.fillTextRect(x1, y - Clazz.doubleToInt(h / 2) - ia, z, text.zSlab, x2 - x1, 2 * ia);
g3d.fillTextRect(x1, y - Clazz.doubleToInt(h * 2 / 2), z, text.zSlab, 2 * ia, Clazz.doubleToInt(h * 2 / 2));
g3d.fillTextRect(x2, y - Clazz.doubleToInt(h * 2 / 2), z, text.zSlab, 2 * ia, Clazz.doubleToInt(h * 2 / 2));
for (var j = 1; j < 10; j++) {
var x1b = x1 + Clazz.doubleToInt(j * barPixels / 10);
var len = (j == 5 ? h : Clazz.doubleToInt(h / 2));
g3d.fillTextRect(x1b, y - len, z, text.zSlab, 2 * ia, len);
}
}, "J.api.JmolRendererInterface,JM.Text,~A,~N,~B");
c$.drawLineXYZ = Clazz.defineMethod(c$, "drawLineXYZ", 
function(g3d, x0, y0, z0, x1, y1, z1, w, h, pointerColix, pointerWidth){
var offsetX = x1 - x0;
var offsetY = y1 - y0;
if (offsetX <= 0 && -offsetX <= w && offsetY <= 0 && -offsetY <= h) return;
var setX = (offsetY > 0 || offsetY < -h);
var pt = NaN;
x1 += (setX ? (offsetX > w / 2 ? 0 : offsetX < -w * 3 / 2 ? w : (pt = w / 2)) : (offsetX > 0 ? 0 : w));
var setY = !Float.isNaN(pt);
y1 += (setY && offsetY > 0 ? 0 : setY && offsetY < -h ? h : h / 2);
if (pointerWidth > 1) {
g3d.fillCylinderXYZ(pointerColix, pointerColix, 2, pointerWidth, x0, y0, z0, Clazz.floatToInt(x1), Clazz.floatToInt(y1), z1);
} else {
g3d.setC(pointerColix);
g3d.drawLineXYZ(x0, y0, z0, Clazz.floatToInt(x1), Clazz.floatToInt(y1), z1);
}}, "J.api.JmolRendererInterface,~N,~N,~N,~N,~N,~N,~N,~N,~N,~N");
c$.renderSimpleLabel = Clazz.defineMethod(c$, "renderSimpleLabel", 
function(g3d, font, strLabel, colix, bgcolix, boxXY, z, zSlab, xOffset, yOffset, ascent, descent, pointerColix, pointerWidth, mode){
var w = font.stringWidth(strLabel) + 8;
var h = ascent + descent + 8;
var x0 = Clazz.floatToInt(boxXY[0]);
var y0 = Clazz.floatToInt(boxXY[1]);
var isAbsolute = ((mode & 64) != 0);
var doPointer = ((mode & 1) != 0);
var isAntialiased = ((mode & 4) != 0);
JM.Text.setBoxXY(w, h, xOffset, yOffset, boxXY, isAbsolute);
var x = boxXY[0];
var y = boxXY[1];
if (bgcolix != 0 && g3d.setC(bgcolix)) {
J.render.TextRenderer.showBox(g3d, colix, Clazz.floatToInt(x), Clazz.floatToInt(y), z, zSlab, Clazz.floatToInt(w), Clazz.floatToInt(h), 1, true);
} else {
g3d.setC(colix);
}g3d.drawString(strLabel, font, Clazz.floatToInt(x + 4), Clazz.floatToInt(y + 4 + ascent), z - 1, zSlab, bgcolix);
if (doPointer && (xOffset != 0 || yOffset != 0)) {
J.render.TextRenderer.drawLineXYZ(g3d, x0, y0, zSlab, x, y, zSlab, w, h, pointerColix, pointerWidth * (isAntialiased ? 2 : 1));
}}, "J.api.JmolRendererInterface,JU.Font,~S,~N,~N,~A,~N,~N,~N,~N,~N,~N,~N,~N,~N");
c$.showBox = Clazz.defineMethod(c$, "showBox", 
function(g3d, colix, x, y, z, zSlab, boxWidth, boxHeight, imageFontScaling, atomBased){
g3d.fillTextRect(x, y, z, zSlab, boxWidth, boxHeight);
g3d.setC(colix);
if (!atomBased) return;
if (imageFontScaling >= 2) {
g3d.drawRect(x + 3, y + 3, z - 1, zSlab, boxWidth - 6, boxHeight - 6);
} else {
g3d.drawRect(x + 1, y + 1, z - 1, zSlab, boxWidth - 2, boxHeight - 2);
}}, "J.api.JmolRendererInterface,~N,~N,~N,~N,~N,~N,~N,~N,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
