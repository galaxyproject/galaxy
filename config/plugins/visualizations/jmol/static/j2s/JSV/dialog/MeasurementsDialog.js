Clazz.declarePackage("JSV.dialog");
Clazz.load(["JSV.dialog.JSVDialog"], "JSV.dialog.MeasurementsDialog", ["JSV.common.Annotation"], function(){
var c$ = Clazz.declareType(JSV.dialog, "MeasurementsDialog", JSV.dialog.JSVDialog);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JSV.dialog.MeasurementsDialog, []);
this.type = JSV.common.Annotation.AType.Measurements;
});
Clazz.defineMethod(c$, "addUniqueControls", 
function(){
});
Clazz.overrideMethod(c$, "getPosXY", 
function(){
return JSV.dialog.MeasurementsDialog.posXY;
});
Clazz.overrideMethod(c$, "callback", 
function(id, msg){
return this.callbackAD(id, msg);
}, "~S,~S");
c$.posXY =  Clazz.newIntArray(-1, [-2147483648, 0]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
