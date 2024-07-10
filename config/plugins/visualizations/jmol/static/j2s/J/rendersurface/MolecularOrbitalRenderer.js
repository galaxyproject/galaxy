Clazz.declarePackage("J.rendersurface");
Clazz.load(["J.rendersurface.IsosurfaceRenderer"], "J.rendersurface.MolecularOrbitalRenderer", null, function(){
var c$ = Clazz.declareType(J.rendersurface, "MolecularOrbitalRenderer", J.rendersurface.IsosurfaceRenderer);
Clazz.overrideMethod(c$, "render", 
function(){
this.imageFontScaling = this.vwr.imageFontScaling;
this.renderIso();
return this.needTranslucent;
});
Clazz.overrideMethod(c$, "renderInfo", 
function(){
if (this.isExport || this.vwr.am.cmi < 0 || this.mesh.title == null || !this.g3d.setC(this.vwr.cm.colixBackgroundContrast) || this.vwr.gdata.getTextPosition() != 0) return;
var ht = this.vwr.getInt(553648145);
this.vwr.gdata.setFontBold("Serif", ht * this.imageFontScaling);
var lineheight = Math.round((ht + 1) * this.imageFontScaling);
var x = Math.round(5 * this.imageFontScaling);
var y = lineheight;
for (var i = 0; i < this.mesh.title.length; i++) if (this.mesh.title[i].length > 0) {
this.g3d.drawStringNoSlab(this.mesh.title[i], null, x, y, 0, 0);
y += lineheight;
}
this.vwr.gdata.setTextPosition(y);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
