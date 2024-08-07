Clazz.declarePackage("JU");
Clazz.load(null, "JU.Font", ["JU.AU"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.fid = 0;
this.fontFace = null;
this.fontStyle = null;
this.fontSizeNominal = 0;
this.idFontFace = 0;
this.idFontStyle = 0;
this.fontSize = 0;
this.font = null;
this.fontMetrics = null;
this.manager = null;
this.ascent = 0;
this.descent = 0;
this.isBold = false;
this.isItalic = false;
Clazz.instantialize(this, arguments);}, JU, "Font", null);
Clazz.makeConstructor(c$, 
function(manager, fid, idFontFace, idFontStyle, fontSize, fontSizeNominal, graphics){
this.manager = manager;
this.fid = fid;
this.fontFace = JU.Font.fontFaces[idFontFace];
this.fontStyle = JU.Font.fontStyles[idFontStyle];
this.idFontFace = idFontFace;
this.idFontStyle = idFontStyle;
this.fontSize = fontSize;
this.isBold = (idFontStyle & 1) == 1;
this.isItalic = (idFontStyle & 2) == 2;
this.fontSizeNominal = fontSizeNominal;
this.font = manager.newFont(JU.Font.fontFaces[idFontFace], this.isBold, this.isItalic, fontSize);
this.fontMetrics = manager.getFontMetrics(this, graphics);
this.descent = manager.getFontDescent(this.fontMetrics);
this.ascent = manager.getFontAscent(this.fontMetrics);
}, "J.api.FontManager,~N,~N,~N,~N,~N,~O");
c$.getFont3D = Clazz.defineMethod(c$, "getFont3D", 
function(fontID){
return JU.Font.font3ds[fontID];
}, "~N");
c$.createFont3D = Clazz.defineMethod(c$, "createFont3D", 
function(fontface, fontstyle, fontsize, fontsizeNominal, manager, graphicsForMetrics){
if (fontsize > 0xFF) fontsize = 0xFF;
var fontsizeX16 = (Clazz.floatToInt(fontsize)) << 4;
var fontkey = ((fontface & 3) | ((fontstyle & 3) << 2) | (fontsizeX16 << 4));
for (var i = JU.Font.fontkeyCount; --i > 0; ) if (fontkey == JU.Font.fontkeys[i] && JU.Font.font3ds[i].fontSizeNominal == fontsizeNominal) return JU.Font.font3ds[i];

var fontIndexNext = JU.Font.fontkeyCount++;
if (fontIndexNext == JU.Font.fontkeys.length) {
JU.Font.fontkeys = JU.AU.arrayCopyI(JU.Font.fontkeys, fontIndexNext + 8);
JU.Font.font3ds = JU.AU.arrayCopyObject(JU.Font.font3ds, fontIndexNext + 8);
}var font3d =  new JU.Font(manager, fontIndexNext, fontface, fontstyle, fontsize, fontsizeNominal, graphicsForMetrics);
JU.Font.font3ds[fontIndexNext] = font3d;
JU.Font.fontkeys[fontIndexNext] = fontkey;
return font3d;
}, "~N,~N,~N,~N,J.api.FontManager,~O");
c$.getFontFaceID = Clazz.defineMethod(c$, "getFontFaceID", 
function(fontface){
return ("Monospaced".equalsIgnoreCase(fontface) ? 2 : "Serif".equalsIgnoreCase(fontface) ? 1 : 0);
}, "~S");
c$.getFontStyleID = Clazz.defineMethod(c$, "getFontStyleID", 
function(fontstyle){
for (var i = 4; --i >= 0; ) if (JU.Font.fontStyles[i].equalsIgnoreCase(fontstyle)) return i;

return -1;
}, "~S");
Clazz.defineMethod(c$, "getAscent", 
function(){
return this.ascent;
});
Clazz.defineMethod(c$, "getDescent", 
function(){
return this.descent;
});
Clazz.defineMethod(c$, "getHeight", 
function(){
return this.getAscent() + this.getDescent();
});
Clazz.defineMethod(c$, "getFontMetrics", 
function(){
return this.fontMetrics;
});
Clazz.defineMethod(c$, "stringWidth", 
function(text){
return this.manager.fontStringWidth(this, text);
}, "~S");
Clazz.defineMethod(c$, "getInfo", 
function(){
return this.fontSizeNominal + " " + this.fontFace + " " + this.fontStyle;
});
Clazz.overrideMethod(c$, "toString", 
function(){
return "[" + this.getInfo() + "]";
});
c$.fontkeyCount = 1;
c$.fontkeys =  Clazz.newIntArray (8, 0);
c$.font3ds =  new Array(8);
c$.fontFaces =  Clazz.newArray(-1, ["SansSerif", "Serif", "Monospaced", ""]);
c$.fontStyles =  Clazz.newArray(-1, ["Plain", "Bold", "Italic", "BoldItalic"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
