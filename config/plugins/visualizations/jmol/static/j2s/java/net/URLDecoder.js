Clazz.declarePackage("java.net");
(function(){
var c$ = Clazz.declareType(java.net, "URLDecoder", null);
c$.decode = Clazz.defineMethod(c$, "decode", 
function(s){
return decodeURIComponent(s);
}, "~S");
})();
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
