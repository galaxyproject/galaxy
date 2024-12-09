Clazz.declarePackage("J.quantum.mo");
Clazz.load(["J.quantum.mo.DataAdder"], "J.quantum.mo.DataAdderI", null, function(){
var c$ = Clazz.declareType(J.quantum.mo, "DataAdderI", null, J.quantum.mo.DataAdder);
/*LV!1824 unnec constructor*/Clazz.overrideMethod(c$, "addData", 
function(calc, havePoints){
switch (calc.normType) {
case 0:
default:
return false;
case 3:
return false;
case 1:
return false;
case 2:
return false;
}
}, "J.quantum.MOCalculation,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
