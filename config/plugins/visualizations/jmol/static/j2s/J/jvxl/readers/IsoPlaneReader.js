Clazz.declarePackage("J.jvxl.readers");
Clazz.load(["J.jvxl.readers.AtomDataReader"], "J.jvxl.readers.IsoPlaneReader", null, function(){
var c$ = Clazz.declareType(J.jvxl.readers, "IsoPlaneReader", J.jvxl.readers.AtomDataReader);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.jvxl.readers.IsoPlaneReader, []);
});
Clazz.overrideMethod(c$, "init", 
function(sg){
this.initADR(sg);
this.precalculateVoxelData = false;
}, "J.jvxl.readers.SurfaceGenerator");
Clazz.overrideMethod(c$, "setup", 
function(isMapData){
this.setup2();
this.setHeader("PLANE", this.params.thePlane.toString());
this.params.cutoff = 0;
this.setVolumeForPlane();
}, "~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
