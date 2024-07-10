Clazz.declarePackage("J.adapter.readers.quantum");
Clazz.load(["J.adapter.readers.quantum.AdfReader"], "J.adapter.readers.quantum.AmsReader", null, function(){
var c$ = Clazz.declareType(J.adapter.readers.quantum, "AmsReader", J.adapter.readers.quantum.AdfReader);
Clazz.overrideMethod(c$, "initializeReader", 
function(){
this.isADF = false;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
