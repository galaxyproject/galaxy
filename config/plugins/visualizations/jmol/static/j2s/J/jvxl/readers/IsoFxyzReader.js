Clazz.declarePackage("J.jvxl.readers");
Clazz.load(["J.jvxl.readers.IsoFxyReader"], "J.jvxl.readers.IsoFxyzReader", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.$data = null;
Clazz.instantialize(this, arguments);}, J.jvxl.readers, "IsoFxyzReader", J.jvxl.readers.IsoFxyReader);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.jvxl.readers.IsoFxyzReader, []);
});
Clazz.overrideMethod(c$, "setup", 
function(isMapData){
if (this.params.functionInfo.size() > 5) this.$data = this.params.functionInfo.get(5);
this.setupType("functionXYZ");
}, "~B");
Clazz.overrideMethod(c$, "getValue", 
function(x, y, z, xyz){
return (this.$data == null ? this.evaluateValue(x, y, z) : this.$data[x][y][z]);
}, "~N,~N,~N,~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
