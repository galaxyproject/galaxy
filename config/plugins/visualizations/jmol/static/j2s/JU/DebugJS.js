Clazz.declarePackage("JU");
(function(){
var c$ = Clazz.declareType(JU, "DebugJS", null);
c$._ = Clazz.defineMethod(c$, "_", 
function(msg){
{
if (Clazz._debugging) {
debugger;
}
}}, "~S");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
