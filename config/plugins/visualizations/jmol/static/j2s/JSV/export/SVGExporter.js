Clazz.declarePackage("JSV.export");
Clazz.load(["JSV.export.FormExporter"], "JSV.export.SVGExporter", ["java.util.Hashtable", "JU.CU", "$.DF", "$.Lst", "JSV.common.ColorParameters", "$.ExportType", "$.ScaleData", "$.ScriptToken", "JU.Logger"], function(){
var c$ = Clazz.declareType(JSV["export"], "SVGExporter", JSV["export"].FormExporter);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JSV["export"].SVGExporter, []);
});
Clazz.overrideMethod(c$, "exportTheSpectrum", 
function(viewer, mode, out, spec, startIndex, endIndex, pd, asBase64){
this.initForm(viewer, out);
if (pd == null) pd = viewer.pd();
var plotAreaColor;
var backgroundColor;
var plotColor;
var gridColor;
var titleColor;
var scaleColor;
var unitsColor;
if (pd == null) {
plotAreaColor = backgroundColor = JSV.common.ColorParameters.LIGHT_GRAY;
plotColor = JSV.common.ColorParameters.BLUE;
gridColor = titleColor = scaleColor = unitsColor = JSV.common.ColorParameters.BLACK;
} else {
plotAreaColor = pd.getColor(JSV.common.ScriptToken.PLOTAREACOLOR);
backgroundColor = pd.bgcolor;
plotColor = pd.getCurrentPlotColor(0);
gridColor = pd.getColor(JSV.common.ScriptToken.GRIDCOLOR);
titleColor = pd.getColor(JSV.common.ScriptToken.TITLECOLOR);
scaleColor = pd.getColor(JSV.common.ScriptToken.SCALECOLOR);
unitsColor = pd.getColor(JSV.common.ScriptToken.UNITSCOLOR);
}var xyCoords = spec.getXYCoords();
var scaleData =  new JSV.common.ScaleData(xyCoords, startIndex, endIndex, spec.isContinuous(), spec.isInverted());
var maxXOnScale = scaleData.maxXOnScale;
var minXOnScale = scaleData.minXOnScale;
var maxYOnScale = scaleData.maxYOnScale;
var minYOnScale = scaleData.minYOnScale;
var xStep = scaleData.steps[0];
var yStep = scaleData.steps[1];
var plotAreaWidth = JSV["export"].SVGExporter.svgWidth - JSV["export"].SVGExporter.leftInset - JSV["export"].SVGExporter.rightInset;
var plotAreaHeight = JSV["export"].SVGExporter.svgHeight - JSV["export"].SVGExporter.topInset - JSV["export"].SVGExporter.bottomInset;
var xScaleFactor = (plotAreaWidth / (maxXOnScale - minXOnScale));
var yScaleFactor = (plotAreaHeight / (maxYOnScale - minYOnScale));
var leftPlotArea = JSV["export"].SVGExporter.leftInset;
var rightPlotArea = JSV["export"].SVGExporter.leftInset + plotAreaWidth;
var topPlotArea = JSV["export"].SVGExporter.topInset;
var bottomPlotArea = JSV["export"].SVGExporter.topInset + plotAreaHeight;
var titlePosition = bottomPlotArea + 60;
this.context.put("titlePosition",  new Integer(titlePosition));
var xPt;
var yPt;
var xStr;
var yStr;
var vertGridCoords =  new JU.Lst();
var horizGridCoords =  new JU.Lst();
for (var i = minXOnScale; i < maxXOnScale + xStep / 2; i += xStep) {
xPt = leftPlotArea + ((i - minXOnScale) * xScaleFactor);
yPt = topPlotArea;
xStr = JSV["export"].SVGExporter.formatDecimalTrimmed(xPt, 6);
yStr = JSV["export"].SVGExporter.formatDecimalTrimmed(yPt, 6);
var hash =  new java.util.Hashtable();
hash.put("xVal", xStr);
hash.put("yVal", yStr);
vertGridCoords.addLast(hash);
}
for (var i = minYOnScale; i < maxYOnScale + yStep / 2; i += yStep) {
xPt = leftPlotArea;
yPt = topPlotArea + ((i - minYOnScale) * yScaleFactor);
xStr = JSV["export"].SVGExporter.formatDecimalTrimmed(xPt, 6);
yStr = JSV["export"].SVGExporter.formatDecimalTrimmed(yPt, 6);
var hash =  new java.util.Hashtable();
hash.put("xVal", xStr);
hash.put("yVal", yStr);
horizGridCoords.addLast(hash);
}
var xScaleList =  new JU.Lst();
var xScaleListReversed =  new JU.Lst();
var yScaleList =  new JU.Lst();
var precisionX = scaleData.precision[0];
var precisionY = scaleData.precision[1];
for (var i = minXOnScale; i < (maxXOnScale + xStep / 2); i += xStep) {
xPt = leftPlotArea + ((i - minXOnScale) * xScaleFactor);
xPt -= 10;
yPt = bottomPlotArea + 15;
xStr = JSV["export"].SVGExporter.formatDecimalTrimmed(xPt, 6);
yStr = JSV["export"].SVGExporter.formatDecimalTrimmed(yPt, 6);
var iStr = JU.DF.formatDecimalDbl(i, precisionX);
var hash =  new java.util.Hashtable();
hash.put("xVal", xStr);
hash.put("yVal", yStr);
hash.put("number", iStr);
xScaleList.addLast(hash);
}
for (var i = minXOnScale, j = maxXOnScale; i < (maxXOnScale + xStep / 2); i += xStep, j -= xStep) {
xPt = leftPlotArea + ((j - minXOnScale) * xScaleFactor);
xPt -= 10;
yPt = bottomPlotArea + 15;
xStr = JSV["export"].SVGExporter.formatDecimalTrimmed(xPt, 6);
yStr = JSV["export"].SVGExporter.formatDecimalTrimmed(yPt, 6);
var iStr = JU.DF.formatDecimalDbl(i, precisionX);
var hash =  new java.util.Hashtable();
hash.put("xVal", xStr);
hash.put("yVal", yStr);
hash.put("number", iStr);
xScaleListReversed.addLast(hash);
}
for (var i = minYOnScale; (i < maxYOnScale + yStep / 2); i += yStep) {
xPt = leftPlotArea - 55;
yPt = bottomPlotArea - ((i - minYOnScale) * yScaleFactor);
yPt += 3;
xStr = JSV["export"].SVGExporter.formatDecimalTrimmed(xPt, 6);
yStr = JSV["export"].SVGExporter.formatDecimalTrimmed(yPt, 6);
var iStr = JU.DF.formatDecimalDbl(i, precisionY);
var hash =  new java.util.Hashtable();
hash.put("xVal", xStr);
hash.put("yVal", yStr);
hash.put("number", iStr);
yScaleList.addLast(hash);
}
var firstTranslateX;
var firstTranslateY;
var secondTranslateX;
var secondTranslateY;
var scaleX;
var scaleY;
var increasing = (pd != null && pd.getBoolean(JSV.common.ScriptToken.REVERSEPLOT));
if (increasing) {
firstTranslateX = leftPlotArea;
firstTranslateY = bottomPlotArea;
scaleX = xScaleFactor;
scaleY = -yScaleFactor;
secondTranslateX = -1 * minXOnScale;
secondTranslateY = -1 * minYOnScale;
} else {
firstTranslateX = rightPlotArea;
firstTranslateY = bottomPlotArea;
scaleX = -xScaleFactor;
scaleY = -yScaleFactor;
secondTranslateX = -minXOnScale;
secondTranslateY = -minYOnScale;
}var yTickA = minYOnScale - (yStep / 2);
var yTickB = yStep / 5;
this.context.put("plotAreaColor", JSV["export"].SVGExporter.toRGBHexString(plotAreaColor));
this.context.put("backgroundColor", JSV["export"].SVGExporter.toRGBHexString(backgroundColor));
this.context.put("plotColor", JSV["export"].SVGExporter.toRGBHexString(plotColor));
this.context.put("gridColor", JSV["export"].SVGExporter.toRGBHexString(gridColor));
this.context.put("titleColor", JSV["export"].SVGExporter.toRGBHexString(titleColor));
this.context.put("scaleColor", JSV["export"].SVGExporter.toRGBHexString(scaleColor));
this.context.put("unitsColor", JSV["export"].SVGExporter.toRGBHexString(unitsColor));
this.context.put("svgHeight",  new Integer(JSV["export"].SVGExporter.svgHeight));
this.context.put("svgWidth",  new Integer(JSV["export"].SVGExporter.svgWidth));
this.context.put("leftPlotArea",  new Integer(leftPlotArea));
this.context.put("rightPlotArea",  new Integer(rightPlotArea));
this.context.put("topPlotArea",  new Integer(topPlotArea));
this.context.put("bottomPlotArea",  new Integer(bottomPlotArea));
this.context.put("plotAreaHeight",  new Integer(plotAreaHeight));
this.context.put("plotAreaWidth",  new Integer(plotAreaWidth));
this.context.put("minXOnScale",  new Double(minXOnScale));
this.context.put("maxXOnScale",  new Double(maxXOnScale));
this.context.put("minYOnScale",  new Double(minYOnScale));
this.context.put("maxYOnScale",  new Double(maxYOnScale));
this.context.put("yTickA",  new Double(yTickA));
this.context.put("yTickB",  new Double(yTickB));
this.context.put("xScaleFactor",  new Double(xScaleFactor));
this.context.put("yScaleFactor",  new Double(yScaleFactor));
this.context.put("increasing",  new Boolean(increasing));
this.context.put("verticalGridCoords", vertGridCoords);
this.context.put("horizontalGridCoords", horizGridCoords);
var newXYCoords =  new JU.Lst();
for (var i = startIndex; i <= endIndex; i++) newXYCoords.addLast(xyCoords[i]);

var firstX;
var firstY;
var lastX;
firstX = xyCoords[startIndex].getXVal();
firstY = xyCoords[startIndex].getYVal();
lastX = xyCoords[endIndex].getXVal();
System.out.println("SVG " + spec.isXIncreasing() + " " + spec.shouldDisplayXAxisIncreasing() + " " + firstX + " " + lastX + " " + startIndex + " " + endIndex + " " + newXYCoords.get(0).toString() + " " + increasing);
this.context.put("title", spec.getTitle());
this.context.put("xyCoords", newXYCoords);
this.context.put("continuous",  new Boolean(spec.isContinuous()));
this.context.put("firstTranslateX",  new Double(firstTranslateX));
this.context.put("firstTranslateY",  new Double(firstTranslateY));
this.context.put("scaleX",  new Double(scaleX));
this.context.put("scaleY",  new Double(scaleY));
this.context.put("secondTranslateX",  new Double(secondTranslateX));
this.context.put("secondTranslateY",  new Double(secondTranslateY));
this.context.put("plotStrokeWidth", this.getPlotStrokeWidth(scaleX, scaleY));
if (increasing) {
this.context.put("xScaleList", xScaleList);
this.context.put("xScaleListReversed", xScaleListReversed);
} else {
this.context.put("xScaleList", xScaleListReversed);
this.context.put("xScaleListReversed", xScaleList);
}this.context.put("yScaleList", yScaleList);
this.context.put("xUnits", spec.getXUnits());
this.context.put("yUnits", spec.getYUnits());
this.context.put("firstX", Double.$valueOf(firstX));
this.context.put("firstY", Double.$valueOf(firstY));
this.context.put("lastX", Double.$valueOf(lastX));
var xUnitLabelX = rightPlotArea - 50;
var xUnitLabelY = bottomPlotArea + 30;
var yUnitLabelX = leftPlotArea - 80;
var yUnitLabelY = Clazz.doubleToInt(bottomPlotArea / 2);
var tempX = yUnitLabelX;
yUnitLabelX = -yUnitLabelY;
yUnitLabelY = tempX;
this.context.put("xUnitLabelX", "" + xUnitLabelX);
this.context.put("xUnitLabelY", "" + xUnitLabelY);
this.context.put("yUnitLabelX", "" + yUnitLabelX);
this.context.put("yUnitLabelY", "" + yUnitLabelY);
this.context.put("numDecimalPlacesX",  new Integer(Math.abs(scaleData.exportPrecision[0])));
this.context.put("numDecimalPlacesY",  new Integer(Math.abs(scaleData.exportPrecision[1])));
var vm = (mode === JSV.common.ExportType.SVGI ? "plot_ink.vm" : "plot.vm");
JU.Logger.info("SVGExporter using " + vm);
return this.writeForm(vm);
}, "JSV.common.JSViewer,JSV.common.ExportType,JU.OC,JSV.common.Spectrum,~N,~N,JSV.common.PanelData,~B");
Clazz.defineMethod(c$, "getPlotStrokeWidth", 
function(scaleX, scaleY){
var s = JSV["export"].SVGExporter.formatDecimalTrimmed(Math.abs(scaleY / 1e12 * 2), 10);
return s;
}, "~N,~N");
c$.toRGBHexString = Clazz.defineMethod(c$, "toRGBHexString", 
function(c){
return "#" + JU.CU.toRGBHexString(c);
}, "javajs.api.GenericColor");
c$.formatDecimalTrimmed = Clazz.defineMethod(c$, "formatDecimalTrimmed", 
function(x, precision){
return JU.DF.formatDecimalTrimmed0(x, precision);
}, "~N,~N");
c$.svgWidth = 850;
c$.svgHeight = 400;
c$.leftInset = 100;
c$.rightInset = 200;
c$.bottomInset = 80;
c$.topInset = 20;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
