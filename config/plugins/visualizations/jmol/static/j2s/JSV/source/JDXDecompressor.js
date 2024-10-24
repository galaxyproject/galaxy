Clazz.declarePackage("JSV.source");
Clazz.load(["java.util.Iterator"], "JSV.source.JDXDecompressor", ["JSV.common.Coordinate", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.xFactor = 0;
this.yFactor = 0;
this.nPoints = 0;
this.ich = 0;
this.t = null;
this.firstX = 0;
this.lastX = 0;
this.maxY = 4.9E-324;
this.minY = 1.7976931348623157E308;
this.debugging = false;
this.xyCoords = null;
this.line = null;
this.lineLen = 0;
this.errorLog = null;
this.lastDif = -2147483648;
this.dupCount = 0;
this.nptsFound = 0;
this.lastY = 0;
this.isDIF = true;
Clazz.instantialize(this, arguments);}, JSV.source, "JDXDecompressor", null, java.util.Iterator);
Clazz.makeConstructor(c$, 
function(t, firstX, lastX, xFactor, yFactor, nPoints){
this.t = t;
this.firstX = firstX;
this.lastX = lastX;
this.xFactor = xFactor;
this.yFactor = yFactor;
this.nPoints = nPoints;
this.debugging = JU.Logger.isActiveLevel(6);
}, "JSV.source.JDXSourceStreamTokenizer,~N,~N,~N,~N,~N");
Clazz.makeConstructor(c$, 
function(line, lastY){
this.line = line.trim();
this.lineLen = line.length;
this.lastY = lastY;
}, "~S,~N");
Clazz.defineMethod(c$, "getMinY", 
function(){
return this.minY;
});
Clazz.defineMethod(c$, "getMaxY", 
function(){
return this.maxY;
});
Clazz.defineMethod(c$, "decompressData", 
function(errorLog){
this.errorLog = errorLog;
var deltaXcalc = JSV.common.Coordinate.deltaX(this.lastX, this.firstX, this.nPoints);
if (this.debugging) this.logError("firstX=" + this.firstX + " lastX=" + this.lastX + " xFactor=" + this.xFactor + " yFactor=" + this.yFactor + " deltaX=" + deltaXcalc + " nPoints=" + this.nPoints);
this.xyCoords =  new Array(this.nPoints);
var difFracMax = 0.5;
var prevXcheck = 0;
var prevIpt = 0;
var lastXExpected = this.lastX;
var x = this.lastX = this.firstX;
var lastLine = null;
var ipt = 0;
var yval = 0;
var haveWarned = false;
var lineNumber = this.t.labelLineNo;
try {
while ((this.line = this.t.readLineTrimmed()) != null && this.line.indexOf("##") < 0) {
lineNumber++;
if ((this.lineLen = this.line.length) == 0) continue;
this.ich = 0;
var isCheckPoint = this.isDIF;
var xcheck = this.readSignedFloat() * this.xFactor;
yval = this.nextValue(yval);
if (!isCheckPoint && ipt > 0) x += deltaXcalc;
if (this.debugging) this.logError("Line: " + lineNumber + " isCP=" + isCheckPoint + "\t>>" + this.line + "<<\n x, xcheck " + x + " " + x / this.xFactor + " " + xcheck / this.xFactor + " " + deltaXcalc / this.xFactor);
var y = yval * this.yFactor;
var point =  new JSV.common.Coordinate().set(x, y);
if (ipt == 0 || !isCheckPoint) {
this.addPoint(point, ipt++);
} else if (ipt < this.nPoints) {
var lastY = this.xyCoords[ipt - 1].getYVal();
if (y != lastY) {
this.xyCoords[ipt - 1] = point;
this.logError(lastLine + "\n" + this.line + "\nY-value Checkpoint Error! Line " + lineNumber + " for y=" + y + " yLast=" + lastY);
}if (xcheck == prevXcheck || (xcheck < prevXcheck) != (deltaXcalc < 0)) {
this.logError(lastLine + "\n" + this.line + "\nX-sequence Checkpoint Error! Line " + lineNumber + " order for xCheck=" + xcheck + " after prevXCheck=" + prevXcheck);
}var xcheckDif = Math.abs(xcheck - prevXcheck);
var xiptDif = Math.abs((ipt - prevIpt) * deltaXcalc);
var fracDif = Math.abs((xcheckDif - xiptDif)) / xcheckDif;
if (this.debugging) System.err.println("JDXD fracDif = " + xcheck + "\t" + prevXcheck + "\txcheckDif=" + xcheckDif + "\txiptDif=" + xiptDif + "\tf=" + fracDif);
if (fracDif > difFracMax) {
this.logError(lastLine + "\n" + this.line + "\nX-value Checkpoint Error! Line " + lineNumber + " expected " + xiptDif + " but X-Sequence Check difference reads " + xcheckDif);
}}prevIpt = (ipt == 1 ? 0 : ipt);
prevXcheck = xcheck;
var nX = 0;
while (this.hasNext()) {
var ich0 = this.ich;
if (this.debugging) this.logError("line " + lineNumber + " char " + ich0 + ":" + this.line.substring(0, ich0) + ">>>>" + this.line.substring(this.ich));
if (Double.isNaN(yval = this.nextValue(yval))) {
this.logError("There was an error reading line " + lineNumber + " char " + ich0 + ":" + this.line.substring(0, ich0) + ">>>>" + this.line.substring(ich0));
} else {
x += deltaXcalc;
if (yval == 1.7976931348623157E308) {
yval = 0;
this.logError("Point marked invalid '?' for line " + lineNumber + " char " + ich0 + ":" + this.line.substring(0, ich0) + ">>>>" + this.line.substring(ich0));
}this.addPoint( new JSV.common.Coordinate().set(x, yval * this.yFactor), ipt++);
if (this.debugging) this.logError("nx=" + ++nX + " " + x + " " + x / this.xFactor + " yval=" + yval);
}}
this.lastX = x;
if (!haveWarned && ipt > this.nPoints) {
this.logError("! points overflow nPoints!");
haveWarned = true;
}lastLine = this.line;
}
} catch (ioe) {
if (Clazz.exceptionOf(ioe,"java.io.IOException")){
ioe.printStackTrace();
} else {
throw ioe;
}
}
this.checkZeroFill(ipt, lastXExpected);
return this.xyCoords;
}, "JU.SB");
Clazz.defineMethod(c$, "checkZeroFill", 
function(ipt, lastXExpected){
this.nptsFound = ipt;
if (this.nPoints == this.nptsFound) {
if (Math.abs(lastXExpected - this.lastX) > 0.00001) this.logError("Something went wrong! The last X value was " + this.lastX + " but expected " + lastXExpected);
} else {
this.logError("Decompressor did not find " + this.nPoints + " points -- instead " + this.nptsFound + " xyCoords.length set to " + this.nPoints);
for (var i = this.nptsFound; i < this.nPoints; i++) this.addPoint( new JSV.common.Coordinate().set(0, NaN), i);

}}, "~N,~N");
Clazz.defineMethod(c$, "addPoint", 
function(pt, ipt){
if (ipt >= this.nPoints) return;
this.xyCoords[ipt] = pt;
var y = pt.getYVal();
if (y > this.maxY) this.maxY = y;
 else if (y < this.minY) this.minY = y;
if (this.debugging) this.logError("Coord: " + ipt + pt);
}, "JSV.common.Coordinate,~N");
Clazz.defineMethod(c$, "logError", 
function(s){
if (this.debugging) JU.Logger.debug(s);
System.err.println(s);
this.errorLog.append(s).appendC('\n');
}, "~S");
Clazz.defineMethod(c$, "nextValue", 
function(yval){
if (this.dupCount > 0) return this.getDuplicate(yval);
var ch = this.skipUnknown();
switch (JSV.source.JDXDecompressor.actions[ch.charCodeAt(0)]) {
case 1:
this.isDIF = true;
return yval + (this.lastDif = this.readNextInteger(ch == '%' ? 0 : ch <= 'R' ? ch.charCodeAt(0) - 73 : 105 - ch.charCodeAt(0)));
case 2:
this.dupCount = this.readNextInteger((ch == 's' ? 9 : ch.charCodeAt(0) - 82)) - 1;
return this.getDuplicate(yval);
case 3:
yval = this.readNextSqueezedNumber(ch);
break;
case 4:
this.ich--;
yval = this.readSignedFloat();
break;
case -1:
yval = 1.7976931348623157E308;
break;
default:
yval = NaN;
break;
}
this.isDIF = false;
return yval;
}, "~N");
Clazz.defineMethod(c$, "skipUnknown", 
function(){
var ch = '\u0000';
while (this.ich < this.lineLen && JSV.source.JDXDecompressor.actions[(ch = this.line.charAt(this.ich++)).charCodeAt(0)] == 0) {
}
return ch;
});
Clazz.defineMethod(c$, "readSignedFloat", 
function(){
var ich0 = this.ich;
var ch = '\u0000';
while (this.ich < this.lineLen && " ,\t\n".indexOf(ch = this.line.charAt(this.ich)) >= 0) this.ich++;

var factor = 1;
switch ((ch).charCodeAt(0)) {
case 45:
factor = -1;
case 43:
ich0 = ++this.ich;
break;
}
if (this.scanToNonnumeric() == 'E' && this.ich + 3 < this.lineLen) {
switch ((this.line.charAt(this.ich + 1)).charCodeAt(0)) {
case 45:
case 43:
this.ich += 4;
if (this.ich < this.lineLen && (ch = this.line.charAt(this.ich)) >= '0' && ch <= '9') this.ich++;
break;
}
}return factor * Double.parseDouble(this.line.substring(ich0, this.ich));
});
Clazz.defineMethod(c$, "getDuplicate", 
function(yval){
this.dupCount--;
return (this.isDIF ? yval + this.lastDif : yval);
}, "~N");
Clazz.defineMethod(c$, "readNextInteger", 
function(n){
var c = String.fromCharCode(0);
while (this.ich < this.lineLen && (c = this.line.charAt(this.ich)) >= '0' && c <= '9') {
n = n * 10 + (n < 0 ? 48 - c.charCodeAt(0) : c.charCodeAt(0) - 48);
this.ich++;
}
return n;
}, "~N");
Clazz.defineMethod(c$, "readNextSqueezedNumber", 
function(ch){
var ich0 = this.ich;
this.scanToNonnumeric();
return Double.parseDouble((ch.charCodeAt(0) > 0x60 ? 0x60 - ch.charCodeAt(0) : ch.charCodeAt(0) - 0x40) + this.line.substring(ich0, this.ich));
}, "~S");
Clazz.defineMethod(c$, "scanToNonnumeric", 
function(){
var ch = String.fromCharCode(0);
while (this.ich < this.lineLen && ((ch = this.line.charAt(this.ich)) == '.' || ch >= '0' && ch <= '9')) this.ich++;

return (this.ich < this.lineLen ? ch : '\0');
});
Clazz.defineMethod(c$, "getNPointsFound", 
function(){
return this.nptsFound;
});
Clazz.overrideMethod(c$, "hasNext", 
function(){
return (this.ich < this.lineLen || this.dupCount > 0);
});
Clazz.overrideMethod(c$, "next", 
function(){
return (this.hasNext() ? Double.$valueOf(this.lastY = this.nextValue(this.lastY)) : null);
});
Clazz.overrideMethod(c$, "remove", 
function(){
});
c$.actions =  Clazz.newIntArray (255, 0);
{
for (var i = 0x25; i <= 0x73; i++) {
var c = String.fromCharCode(i);
switch ((c).charCodeAt(0)) {
case 37:
case 74:
case 75:
case 76:
case 77:
case 78:
case 79:
case 80:
case 81:
case 82:
case 106:
case 107:
case 108:
case 109:
case 110:
case 111:
case 112:
case 113:
case 114:
JSV.source.JDXDecompressor.actions[i] = 1;
break;
case 43:
case 45:
case 46:
case 48:
case 49:
case 50:
case 51:
case 52:
case 53:
case 54:
case 55:
case 56:
case 57:
JSV.source.JDXDecompressor.actions[i] = 4;
break;
case 63:
JSV.source.JDXDecompressor.actions[i] = -1;
break;
case 64:
case 65:
case 66:
case 67:
case 68:
case 69:
case 70:
case 71:
case 72:
case 73:
case 97:
case 98:
case 99:
case 100:
case 101:
case 102:
case 103:
case 104:
case 105:
JSV.source.JDXDecompressor.actions[i] = 3;
break;
case 83:
case 84:
case 85:
case 86:
case 87:
case 88:
case 89:
case 90:
case 115:
JSV.source.JDXDecompressor.actions[i] = 2;
break;
}
}
}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
