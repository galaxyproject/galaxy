Clazz.declarePackage("J.rendersurface");
Clazz.load(["J.rendersurface.IsosurfaceRenderer"], "J.rendersurface.PmeshRenderer", null, function(){
var c$ = Clazz.declareType(J.rendersurface, "PmeshRenderer", J.rendersurface.IsosurfaceRenderer);
Clazz.overrideMethod(c$, "render", 
function(){
return this.renderIso();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
