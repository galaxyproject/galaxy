Clazz.declarePackage("JU");
(function(){
var c$ = Clazz.declareType(JU, "EigenSort", null, java.util.Comparator);
Clazz.overrideMethod(c$, "compare", 
function(o1, o2){
var a = ((o1)[1]).floatValue();
var b = ((o2)[1]).floatValue();
return (a < b ? -1 : a > b ? 1 : 0);
}, "~O,~O");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
