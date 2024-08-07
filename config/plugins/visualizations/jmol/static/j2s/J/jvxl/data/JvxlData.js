Clazz.declarePackage("J.jvxl.data");
Clazz.load(null, "J.jvxl.data.JvxlData", ["JU.SB", "J.jvxl.data.JvxlCoder"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.msg = "";
this.wasJvxl = false;
this.wasCubic = false;
this.jvxlFileSource = null;
this.jvxlFileTitle = null;
this.jvxlFileMessage = null;
this.jvxlSurfaceData = null;
this.jvxlEdgeData = null;
this.jvxlColorData = null;
this.jvxlVolumeDataXml = null;
this.jvxlExcluded = null;
this.jvxlPlane = null;
this.isJvxlPrecisionColor = false;
this.jvxlDataIsColorMapped = false;
this.jvxlDataIs2dContour = false;
this.jvxlDataIsColorDensity = false;
this.isColorReversed = false;
this.thisSet = null;
this.edgeFractionBase = 35;
this.edgeFractionRange = 90;
this.colorFractionBase = 35;
this.colorFractionRange = 90;
this.isValid = true;
this.insideOut = false;
this.isXLowToHigh = false;
this.isContoured = false;
this.isBicolorMap = false;
this.isTruncated = false;
this.isCutoffAbsolute = false;
this.isModelConnected = false;
this.vertexDataOnly = false;
this.mappedDataMin = 0;
this.mappedDataMax = 0;
this.valueMappedToRed = 0;
this.valueMappedToBlue = 0;
this.cutoff = 0;
this.cutoffRange = null;
this.pointsPerAngstrom = 0;
this.nPointsX = 0;
this.nPointsY = 0;
this.nPointsZ = 0;
this.nBytes = 0;
this.nContours = 0;
this.nEdges = 0;
this.nSurfaceInts = 0;
this.vertexCount = 0;
this.vContours = null;
this.contourColixes = null;
this.contourColors = null;
this.contourValues = null;
this.contourValuesUsed = null;
this.thisContour = -1;
this.scale3d = 0;
this.minColorIndex = -1;
this.maxColorIndex = 0;
this.title = null;
this.version = null;
this.boundingBox = null;
this.excludedTriangleCount = 0;
this.excludedVertexCount = 0;
this.colorDensity = false;
this.pointSize = 0;
this.moleculeXml = null;
this.dataMin = 0;
this.dataMax = 0;
this.saveVertexCount = 0;
this.vertexColorMap = null;
this.nVertexColors = 0;
this.vertexColors = null;
this.color = null;
this.meshColor = null;
this.translucency = 0;
this.colorScheme = null;
this.rendering = null;
this.slabValue = -2147483648;
this.isSlabbable = false;
this.diameter = 0;
this.slabInfo = null;
this.allowVolumeRender = false;
this.voxelVolume = 0;
this.mapLattice = null;
this.fixedLattice = null;
this.baseColor = null;
this.integration = NaN;
this.sbOut = null;
Clazz.instantialize(this, arguments);}, J.jvxl.data, "JvxlData", null);
Clazz.prepareFields (c$, function(){
this.jvxlExcluded =  new Array(4);
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "clear", 
function(){
this.allowVolumeRender = true;
this.jvxlSurfaceData = "";
this.jvxlEdgeData = "";
this.jvxlColorData = "";
this.jvxlVolumeDataXml = "";
this.color = null;
this.colorScheme = null;
this.colorDensity = false;
this.pointSize = NaN;
this.contourValues = null;
this.contourValuesUsed = null;
this.contourColixes = null;
this.contourColors = null;
this.integration = NaN;
this.isSlabbable = false;
this.isValid = true;
this.mapLattice = null;
this.meshColor = null;
this.msg = "";
this.nPointsX = 0;
this.nVertexColors = 0;
this.fixedLattice = null;
this.slabInfo = null;
this.slabValue = -2147483648;
this.thisSet = null;
this.rendering = null;
this.thisContour = -1;
this.translucency = 0;
this.vContours = null;
this.vertexColorMap = null;
this.vertexColors = null;
this.voxelVolume = 0;
});
Clazz.defineMethod(c$, "setSurfaceInfo", 
function(thePlane, mapLattice, nSurfaceInts, surfaceData){
this.jvxlSurfaceData = surfaceData;
this.jvxlPlane = thePlane;
this.mapLattice = mapLattice;
this.nSurfaceInts = nSurfaceInts;
}, "JU.P4,JU.P3,~N,~S");
Clazz.defineMethod(c$, "setSurfaceInfoFromBitSet", 
function(bs, thePlane){
this.setSurfaceInfoFromBitSetPts(bs, thePlane, null);
}, "JU.BS,JU.P4");
Clazz.defineMethod(c$, "setSurfaceInfoFromBitSetPts", 
function(bs, thePlane, mapLattice){
var sb =  new JU.SB();
var nSurfaceInts = (thePlane != null ? 0 : J.jvxl.data.JvxlCoder.jvxlEncodeBitSetBuffer(bs, this.nPointsX * this.nPointsY * this.nPointsZ, sb));
this.setSurfaceInfo(thePlane, mapLattice, nSurfaceInts, sb.toString());
}, "JU.BS,JU.P4,JU.P3");
Clazz.defineMethod(c$, "jvxlUpdateInfo", 
function(title, nBytes){
this.title = title;
this.nBytes = nBytes;
}, "~A,~N");
c$.updateSurfaceData = Clazz.defineMethod(c$, "updateSurfaceData", 
function(edgeData, vertexValues, vertexCount, vertexIncrement, isNaN){
if (edgeData.length == 0) return "";
var chars = edgeData.toCharArray();
for (var i = 0, ipt = 0; i < vertexCount; i += vertexIncrement, ipt++) if (Float.isNaN(vertexValues[i])) chars[ipt] = isNaN;

return String.copyValueOf(chars);
}, "~S,~A,~N,~N,~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
