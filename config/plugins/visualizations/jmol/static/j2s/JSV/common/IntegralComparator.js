Clazz.declarePackage("JSV.common");
(function(){
var c$ = Clazz.declareType(JSV.common, "IntegralComparator", null, java.util.Comparator);
Clazz.overrideMethod(c$, "compare", 
function(m1, m2){
return (m1.getXVal() < m2.getXVal() ? -1 : m1.getXVal() > m2.getXVal() ? 1 : 0);
}, "JSV.common.Measurement,JSV.common.Measurement");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
