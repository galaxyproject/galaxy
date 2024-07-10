Clazz.declarePackage("J.awtjs2d");
(function(){
var c$ = Clazz.declareType(J.awtjs2d, "JSFont", null);
c$.newFont = Clazz.defineMethod(c$, "newFont", 
function(fontFace, isBold, isItalic, fontSize, type){
fontFace = (fontFace.equals("Monospaced") ? "Courier" : fontFace.startsWith("Sans") ? "Helvetica Neue, Sans-serif" : "Serif");
return (isBold ? "bold " : "") + (isItalic ? "italic " : "") + fontSize + type + " " + fontFace;
}, "~S,~B,~B,~N,~S");
c$.getFontMetrics = Clazz.defineMethod(c$, "getFontMetrics", 
function(font, context){
{
if (context.font != font.font) {
context.font = font.font;
font.font = context.font;
context._fontAscent = Math.ceil(font.fontSize); //pt, not px
// the descent is actually (px - pt)
// but I know of no way of getting access to the drawn height
context._fontDescent = Math.ceil(font.fontSize * 0.25);//approx
}
}return context;
}, "JU.Font,~O");
c$.getAscent = Clazz.defineMethod(c$, "getAscent", 
function(context){
{
return Math.ceil(context._fontAscent);
}}, "~O");
c$.getDescent = Clazz.defineMethod(c$, "getDescent", 
function(context){
{
return Math.ceil(context._fontDescent);
}}, "~O");
c$.stringWidth = Clazz.defineMethod(c$, "stringWidth", 
function(font, context, text){
{
context.font = font.font;
return Math.ceil(context.measureText(text).width);
}}, "JU.Font,~O,~S");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
