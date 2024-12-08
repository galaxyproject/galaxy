Clazz.declarePackage("jme");
Clazz.load(null, "jme.AtomDisplayLabel", [], function(){
var c$ = Clazz.decorateAsClass(function(){
this.smallAtomWidthLabel = 0;
this.fullAtomWidthLabel = 0;
this.alignment = 0;
this.noLabelAtom = false;
this.atomLabelBoundingBox = null;
this.labelX = 0;
this.labelY = 0;
this.str = null;
this.boundingBoxpadding = 2;
this.atomMapY = 0;
this.atomMapX = 0;
this.mapString = null;
this.subscripts = null;
this.superscripts = null;
Clazz.instantialize(this, arguments);}, jme, "AtomDisplayLabel", null);
Clazz.makeConstructor(c$, 
function(x, y, z, an, nv, sbo, nh, q, iso, map, alignment, fm, h, showHs){
if (z == null || z.length < 1) {
z = "*";
System.err.println("Z error!");
}this.alignment = alignment;
var padding = 2;
this.noLabelAtom = (an == 3 && q == 0 && iso == 0 && nv > 0 && (nv != 2 || sbo != 4));
var hydrogenSymbols = "";
if (showHs && !this.noLabelAtom) {
if (nh > 0) {
hydrogenSymbols += "H";
if (nh > 1) {
hydrogenSymbols += nh;
}}}var isoSymbol = (iso == 0 ? "" : "[" + iso + "]");
var chargeSymbols = (q == 0 ? "" : (Math.abs(q) > 1 ? "" + Math.abs(q) : "") + (q > 0 ? "+" : "-"));
var stringForWidth = z;
if (alignment == 2) {
z = chargeSymbols + hydrogenSymbols + isoSymbol + z;
} else {
z = isoSymbol + z + hydrogenSymbols + chargeSymbols;
}this.str = z;
if (alignment == 1) {
stringForWidth = z;
}var smallWidth = fm.stringWidth(stringForWidth);
var fullWidth = fm.stringWidth(z);
this.smallAtomWidthLabel = smallWidth;
this.fullAtomWidthLabel = fullWidth;
var lineThickness = 1;
var xstart = x - smallWidth / 2.;
if (alignment == 2) {
xstart -= (fullWidth - smallWidth);
}var ystart = y - h / 2;
xstart -= lineThickness;
fullWidth += lineThickness;
var box = this.atomLabelBoundingBox =  new java.awt.geom.Rectangle2D.Double(xstart - padding, ystart - padding, fullWidth + 2 * padding, h + 2 * padding);
this.mapString = null;
this.labelX = this.atomLabelBoundingBox.x + padding + 1;
this.labelY = this.atomLabelBoundingBox.y + h + padding;
if (hydrogenSymbols.length > 1) {
var pos = z.indexOf(hydrogenSymbols);
var styleIndices =  Clazz.newIntArray(-1, [pos + 1, hydrogenSymbols.length - 1]);
this.subscripts =  Clazz.newArray(-1, [styleIndices]);
}if (chargeSymbols.length > 0) {
var pos = z.indexOf(chargeSymbols);
var styleIndices =  Clazz.newIntArray(-1, [pos, chargeSymbols.length]);
this.superscripts =  Clazz.newArray(-1, [styleIndices]);
}if (isoSymbol.length > 0) {
var pos = z.indexOf(isoSymbol);
var styleIndices =  Clazz.newIntArray(-1, [pos, isoSymbol.length]);
if (this.superscripts == null) {
this.superscripts =  Clazz.newArray(-1, [styleIndices]);
} else {
this.superscripts =  Clazz.newArray(-1, [this.superscripts[0], styleIndices]);
}}if (map < 0) return;
this.mapString = " " + map;
if (this.noLabelAtom) {
this.atomMapX = x + smallWidth / 4;
this.atomMapY = y - h * 0.1;
} else {
var atomMapStringWidth = fm.stringWidth(this.mapString);
if (alignment == 0) {
this.atomMapX = x - smallWidth / 2. + fullWidth;
} else {
box.x -= atomMapStringWidth;
this.atomMapX = x + smallWidth / 2 - fullWidth - atomMapStringWidth;
}var superscriptMove = h * 0.3;
this.atomMapY = y - superscriptMove;
box.y -= superscriptMove;
box.height += superscriptMove;
box.width += atomMapStringWidth;
}}, "~N,~N,~S,~N,~N,~N,~N,~N,~N,~N,~N,java.awt.FontMetrics,~N,~B");
Clazz.defineMethod(c$, "draw", 
function(g){
g.drawString(this.str, Clazz.doubleToInt(this.labelX), Clazz.doubleToInt(this.labelY));
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "drawRect", 
function(g){
var box = this.atomLabelBoundingBox;
g.drawRect(Clazz.doubleToInt(box.x), Clazz.doubleToInt(box.y), Clazz.doubleToInt(box.width), Clazz.doubleToInt(box.height));
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "fillRect", 
function(g){
var box = this.atomLabelBoundingBox;
g.fillRect(Clazz.doubleToInt(box.x), Clazz.doubleToInt(box.y), Clazz.doubleToInt(box.width), Clazz.doubleToInt(box.height));
}, "java.awt.Graphics");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
