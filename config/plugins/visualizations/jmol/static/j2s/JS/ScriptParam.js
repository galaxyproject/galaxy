Clazz.declarePackage("JS");
Clazz.load(["JS.ScriptError"], "JS.ScriptParam", ["java.util.Hashtable", "JU.BS", "$.CU", "$.Lst", "$.Measure", "$.P3", "$.P4", "$.PT", "$.Quat", "$.SB", "$.V3", "JM.TickInfo", "JS.SV", "$.T", "JU.BSUtil", "$.Edge", "$.Escape", "$.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.contextVariables = null;
this.contextFunctions = null;
this.thisContext = null;
this.iToken = 0;
this.theTok = 0;
this.theToken = null;
this.st = null;
this.slen = 0;
this.fractionalPoint = null;
this.coordinatesAreFractional = false;
this.isBondSet = false;
Clazz.instantialize(this, arguments);}, JS, "ScriptParam", JS.ScriptError);
Clazz.defineMethod(c$, "getToken", 
function(i){
if (!this.checkToken(i)) this.error(13);
this.theToken = this.st[i];
this.theTok = this.theToken.tok;
return this.theToken;
}, "~N");
Clazz.defineMethod(c$, "tokAt", 
function(i){
return (i < this.slen && this.st[i] != null ? this.st[i].tok : 0);
}, "~N");
Clazz.defineMethod(c$, "checkToken", 
function(i){
return (this.iToken = i) < this.slen;
}, "~N");
Clazz.defineMethod(c$, "getParameter", 
function(key, tokType, nullAsString){
var v = this.getContextVariableAsVariable(key, false);
if (v == null) {
if (nullAsString) v = this.vwr.getP(key);
 else if ((v = this.vwr.getPOrNull(key)) == null) return null;
}switch (tokType) {
case 1073742190:
return JS.SV.getVariable(v);
case 4:
if (!(Clazz.instanceOf(v,"JU.Lst"))) break;
var sv = v;
var sb =  new JU.SB();
for (var i = 0; i < sv.size(); i++) sb.append(sv.get(i).asString()).appendC('\n');

return sb.toString();
}
return JS.SV.oValue(v);
}, "~S,~N,~B");
Clazz.defineMethod(c$, "getVarParameter", 
function($var, orReturnName){
var v = this.getContextVariableAsVariable($var, false);
if (v != null) return (orReturnName ? v.asString() : JS.SV.oValue(v));
var val = this.vwr.getP($var);
return (orReturnName && ("" + val).length == 0 ? $var : val);
}, "~S,~B");
Clazz.defineMethod(c$, "getContextVariableAsVariable", 
function($var, isLocal){
if ($var.length == 0 || $var.equals("expressionBegin")) return null;
if ($var.charAt(0) == '_') {
var isCallers = $var.equalsIgnoreCase("_callers");
if (isCallers || $var.equalsIgnoreCase("_caller")) {
var sc = this.thisContext;
var h0 =  new java.util.Hashtable();
var h = null;
var h1;
while (sc != null) {
if (sc.isFunction) {
if (h == null) {
h = h0;
} else {
h1 =  new java.util.Hashtable();
h.put("_caller", JS.SV.newV(6, h1));
h = h1;
}h.putAll(sc.vars);
h.put("_name", JS.SV.newS(sc.functionName));
if (!isCallers) break;
}sc = sc.parentContext;
}
return JS.SV.newV(6, h0);
}if ($var.equalsIgnoreCase("_name")) {
var sc = this.thisContext;
while (sc != null) {
if (sc.isFunction) {
return JS.SV.newS(JS.SV.sValue(sc.statement[0]));
}sc = sc.parentContext;
}
return JS.SV.newS("");
}}$var = $var.toLowerCase();
var v = (this.contextVariables == null ? null : this.contextVariables.get($var));
if (v == null && !isLocal && this.thisContext != null) v = this.thisContext.getVariable($var);
return (v != null && v.tok == 1275068418 ? v.arrayToList(v) : v);
}, "~S,~B");
Clazz.defineMethod(c$, "paramAsStr", 
function(i){
this.getToken(i);
if (this.theToken == null) this.error(13);
return JS.SV.sValue(this.theToken);
}, "~N");
Clazz.defineMethod(c$, "stringParameter", 
function(index){
if (!this.checkToken(index) || this.getToken(index).tok != 4) this.error(41);
return this.theToken.value;
}, "~N");
Clazz.defineMethod(c$, "stringParameterSet", 
function(i){
switch (this.tokAt(i)) {
case 4:
var s = this.stringParameter(i);
if (s.startsWith("[\"")) {
var o = this.vwr.evaluateExpression(s);
if ((typeof(o)=='string')) return JU.PT.split(o, "\n");
}return  Clazz.newArray(-1, [s]);
case 1073742195:
i += 2;
break;
case 268437504:
++i;
break;
case 7:
return JS.SV.strListValue(this.getToken(i));
default:
this.invArg();
}
var tok;
var v =  new JU.Lst();
while ((tok = this.tokAt(i)) != 268437505) {
switch (tok) {
case 268436992:
break;
case 4:
v.addLast(this.stringParameter(i));
break;
default:
case 0:
this.invArg();
}
i++;
}
this.iToken = i;
var n = v.size();
var sParams =  new Array(n);
for (var j = 0; j < n; j++) {
sParams[j] = v.get(j);
}
return sParams;
}, "~N");
Clazz.defineMethod(c$, "objectNameParameter", 
function(index){
if (!this.checkToken(index)) this.error(37);
return this.paramAsStr(index);
}, "~N");
Clazz.defineMethod(c$, "atomCenterOrCoordinateParameter", 
function(i, ret){
switch (this.getToken(i).tok) {
case 10:
case 1073742325:
var bs = (this).atomExpression(this.st, i, 0, true, false, ret, true);
if (bs == null) {
if (ret == null || !(Clazz.instanceOf(ret[0],"JU.P3"))) this.invArg();
return ret[0];
}if (ret != null) {
if (ret.length == 2 && Clazz.instanceOf(ret[1],"JU.BS")) {
bs = JU.BSUtil.copy(bs);
bs.and(ret[1]);
}ret[0] = bs;
}return (bs.cardinality() == 1 ? this.vwr.ms.at[bs.nextSetBit(0)] : this.vwr.ms.getAtomSetCenter(bs));
case 1073742332:
case 8:
return this.getPoint3f(i, true, true);
}
this.invArg();
return null;
}, "~N,~A");
Clazz.defineMethod(c$, "isCenterParameter", 
function(i){
var tok = this.tokAt(i);
return (tok == 1073742330 || tok == 1073742332 || tok == 1073742325 || tok == 8 || tok == 10);
}, "~N");
Clazz.defineMethod(c$, "centerParameter", 
function(i, ret){
return this.centerParameterForModel(i, -2147483648, ret);
}, "~N,~A");
Clazz.defineMethod(c$, "centerParameterForModel", 
function(i, modelIndex, ret){
var center = null;
if (this.checkToken(i)) {
switch (this.getToken(i).tok) {
case 1814695966:
return this.getUnitCellCenter();
case 1073742330:
var id = this.objectNameParameter(++i);
var index = -2147483648;
if (this.tokAt(i + 1) == 268437504) {
index = (this).parameterExpressionList(-i - 1, -1, true).get(0).asInt();
if (this.getToken(--this.iToken).tok != 268437505) this.invArg();
}if (this.chk) return  new JU.P3();
if (this.tokAt(i + 1) == 1073742336 && (this.tokAt(i + 2) == 1140850691 || this.tokAt(i + 2) == 1140850694)) {
index = 2147483647;
this.iToken = i + 2;
}if ((center = (this).getObjectCenter(id, index, modelIndex)) == null) this.errorStr(12, id);
break;
case 10:
case 1073742325:
case 1073742332:
case 8:
if (ret == null) ret =  new Array(1);
center = this.atomCenterOrCoordinateParameter(i, ret);
break;
}
}if (center == null) this.error(11);
return center;
}, "~N,~N,~A");
Clazz.defineMethod(c$, "getUnitCellCenter", 
function(){
var center =  new JU.P3();
var uc = this.vwr.getCurrentUnitCell();
if (uc != null) {
var pts = uc.getUnitCellVerticesNoOffset();
var off = uc.getCartesianOffset();
for (var j = 0; j < 8; j++) {
center.add(pts[j]);
center.add(off);
}
}center.scale(0.125);
return center;
});
Clazz.defineMethod(c$, "planeParameter", 
function(i, isBest){
var vTemp =  new JU.V3();
var vTemp2 =  new JU.V3();
var plane = null;
var pt1 = null;
var pt2 = null;
var pt3 = null;
var have3 = false;
if (this.tokAt(i) == 134217750) i++;
var bestPoints = null;
var isNegated = (this.tokAt(i) == 268440576);
if (isNegated) i++;
try {
if (i < this.slen) {
switch (this.getToken(i).tok) {
case 1073742330:
var id = this.objectNameParameter(++i);
if (this.chk) return  new JU.P4();
plane = (this).getPlaneForObject(id, vTemp);
break;
case 1111492629:
if (!this.checkToken(++i) || this.getToken(i++).tok != 268440324) this.evalError("x=?", null);
plane = JU.P4.new4(1, 0, 0, -this.floatParameter(i));
break;
case 1111492630:
if (!this.checkToken(++i) || this.getToken(i++).tok != 268440324) this.evalError("y=?", null);
plane = JU.P4.new4(0, 1, 0, -this.floatParameter(i));
break;
case 1111492631:
if (!this.checkToken(++i) || this.getToken(i++).tok != 268440324) this.evalError("z=?", null);
plane = JU.P4.new4(0, 0, 1, -this.floatParameter(i));
break;
case 1073741824:
case 4:
case 9:
plane = this.planeValue(this.theToken);
break;
case 1073742332:
case 8:
if (!this.isPoint3f(i)) {
plane = this.getPoint4f(i);
break;
}case 10:
case 1073742325:
if (isBest) {
var bs = this.getAtomsStartingAt(i);
bestPoints =  new Array(bs.cardinality());
for (var p = 0, j = bs.nextSetBit(0); j >= 0; j = bs.nextSetBit(j + 1)) {
bestPoints[p++] = this.vwr.ms.at[j];
}
} else {
pt1 = this.atomCenterOrCoordinateParameter(i, null);
if (this.getToken(++this.iToken).tok == 268436992) ++this.iToken;
pt2 = this.atomCenterOrCoordinateParameter(this.iToken, null);
if (this.getToken(++this.iToken).tok == 268436992) ++this.iToken;
if (this.isFloatParameter(this.iToken)) {
var frac = this.floatParameter(this.iToken);
plane =  new JU.P4();
vTemp.sub2(pt2, pt1);
vTemp.scale(frac * 2);
JU.Measure.getBisectingPlane(pt1, vTemp, vTemp2, vTemp, plane);
} else {
pt3 = this.atomCenterOrCoordinateParameter(this.iToken, null);
i = this.iToken;
have3 = true;
}}break;
default:
if (this.isArrayParameter(i)) {
if (isBest) {
bestPoints = this.getPointArray(i, -1, false);
} else {
var list = this.getPointOrCenterVector(this.getToken(i));
var n = list.size();
if (n != 3) this.invArg();
pt1 = list.get(0);
pt2 = list.get(1);
pt3 = list.get(2);
have3 = true;
}}}
if (isBest) {
plane =  new JU.P4();
JU.Measure.calcBestPlaneThroughPoints(bestPoints, -1, plane);
} else if (have3) {
plane =  new JU.P4();
var norm =  new JU.P3();
var w = JU.Measure.getNormalThroughPoints(pt1, pt2, pt3, norm, vTemp);
plane.set4(norm.x, norm.y, norm.z, w);
}if (!this.chk && JU.Logger.debugging) JU.Logger.debug(" defined plane: " + plane);
}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
plane = null;
} else {
throw e;
}
}
if (plane == null) this.errorMore(38, "{a b c d}", "\"xy\" \"xz\" \"yz\" \"x=...\" \"y=...\" \"z=...\" \"ab\" \"bc\" \"ac\" \"ab1\" \"bc1\" \"ac1\"", "$xxxxx");
if (isNegated) {
plane.scale4(-1);
}return plane;
}, "~N,~B");
Clazz.defineMethod(c$, "getAtomsStartingAt", 
function(i){
var bs =  new JU.BS();
i--;
while (this.tokAt(++i) == 10 || this.tokAt(i) == 1073742325) {
bs.or((this).atomExpressionAt(i));
i = this.iToken;
}
return bs;
}, "~N");
Clazz.defineMethod(c$, "getPointOrCenterVector", 
function(t){
var data =  new JU.Lst();
var pt;
var bs;
var pts = (t).getList();
if (pts == null) this.invArg();
for (var j = 0; j < pts.size(); j++) {
if ((pt = JS.SV.ptValue(pts.get(j))) != null) {
data.addLast(pt);
} else if ((bs = JS.SV.getBitSet(pts.get(j), true)) != null) {
data.addLast(bs.cardinality() == 1 ? JU.P3.newP(this.vwr.ms.at[bs.nextSetBit(0)]) : this.vwr.ms.getAtomSetCenter(bs));
} else {
this.invArg();
}}
return data;
}, "JS.T");
Clazz.defineMethod(c$, "hklParameter", 
function(i, pts, allowOffset){
if (!this.chk && this.vwr.getCurrentUnitCell() == null) this.error(33);
var pt = this.getPointOrPlane(i, 71);
var offset = NaN;
if (allowOffset) {
offset = (Clazz.instanceOf(pt,"JU.P4") ? (pt).w : NaN);
if (this.tokAt(this.iToken + 1) == 1073742066) {
this.iToken++;
offset = this.floatParameter(++this.iToken);
}}var p = this.getHklPlane(pt, offset, pts);
if (p == null) this.error(3);
if (!this.chk && JU.Logger.debugging) JU.Logger.debug("defined plane: " + p);
return p;
}, "~N,JU.Lst,~B");
Clazz.defineMethod(c$, "getHklPlane", 
function(pt, offset, pts){
var pt1 = JU.P3.new3(pt.x == 0 ? 1 : 1 / pt.x, 0, 0);
var pt2 = JU.P3.new3(0, pt.y == 0 ? 1 : 1 / pt.y, 0);
var pt3 = JU.P3.new3(0, 0, pt.z == 0 ? 1 : 1 / pt.z);
if (pt.x == 0 && pt.y == 0 && pt.z == 0) {
return null;
} else if (pt.x == 0 && pt.y == 0) {
pt1.set(1, 0, pt3.z);
pt2.set(0, 1, pt3.z);
} else if (pt.y == 0 && pt.z == 0) {
pt2.set(pt1.x, 0, 1);
pt3.set(pt1.x, 1, 0);
} else if (pt.z == 0 && pt.x == 0) {
pt3.set(0, pt2.y, 1);
pt1.set(1, pt2.y, 0);
} else if (pt.x == 0) {
pt1.set(1, pt2.y, 0);
} else if (pt.y == 0) {
pt2.set(0, 1, pt3.z);
} else if (pt.z == 0) {
pt3.set(pt1.x, 0, 1);
}this.vwr.toCartesian(pt1, false);
this.vwr.toCartesian(pt2, false);
this.vwr.toCartesian(pt3, false);
var v3 =  new JU.V3();
var plane = JU.Measure.getPlaneThroughPoints(pt1, pt2, pt3,  new JU.V3(), v3,  new JU.P4());
if (!Float.isNaN(offset)) {
plane.w = -offset;
if (pts != null) {
JU.Measure.getPlaneProjection(pt1, plane, pt1, v3);
JU.Measure.getPlaneProjection(pt2, plane, pt2, v3);
JU.Measure.getPlaneProjection(pt3, plane, pt3, v3);
}}if (pts != null) {
pts.addLast(pt1);
pts.addLast(pt2);
pts.addLast(pt3);
}return plane;
}, "JU.T3,~N,JU.Lst");
Clazz.defineMethod(c$, "getPointOrPlane", 
function(index, mode){
var coord =  Clazz.newFloatArray (6, 0);
var code555 =  Clazz.newIntArray (6, 0);
var useCell555P4 = false;
var n = 0;
var minDim = ((mode & 7) == 4 ? 4 : 3);
var maxDim = ((mode & 7) == 3 ? 3 : 4);
var implicitFractional = ((mode & 64) != 0);
var integerOnly = ((mode & 8) != 0);
var isOK = true;
try {
this.coordinatesAreFractional = implicitFractional;
if (this.tokAt(index) == 8) {
if (minDim <= 3 && maxDim >= 3) return this.getToken(index).value;
isOK = false;
return null;
}if (this.tokAt(index) == 9) {
if (minDim <= 4 && maxDim >= 4) return this.getToken(index).value;
isOK = false;
return null;
}var multiplier = 1;
out : for (var i = index; i < this.slen; i++) {
switch (this.getToken(i).tok) {
case 1073742332:
case 268436992:
case 268438528:
case 268439552:
break;
case 1073742338:
break out;
case 268440576:
multiplier = -1;
break;
case 1073742363:
if (n == 6) {
isOK = false;
return null;
}coord[n++] = this.theToken.intValue;
multiplier = -1;
break;
case 2:
case 1073742362:
if (n == 6 || this.theToken.intValue == 2147483647) this.invArg();
if (implicitFractional && this.theToken.intValue > 999999999) useCell555P4 = true;
code555[n] = this.theToken.intValue;
coord[n++] = this.theToken.intValue * multiplier;
multiplier = 1;
break;
case 268441088:
case 1073742358:
if (!implicitFractional && (mode & 16) == 0) {
isOK = false;
return null;
}if (this.theTok == 268441088) this.getToken(++i);
n--;
if (n < 0 || integerOnly) {
isOK = false;
return null;
}if (Clazz.instanceOf(this.theToken.value, Integer) || this.theTok == 2) {
coord[n++] /= (this.theToken.intValue == 2147483647 ? (this.theToken.value).intValue() : this.theToken.intValue);
} else if (Clazz.instanceOf(this.theToken.value, Float)) {
coord[n++] /= (this.theToken.value).floatValue();
}this.coordinatesAreFractional = true;
break;
case 1073742357:
case 1073741824:
coord[n++] = NaN;
break;
case 3:
case 1073742359:
if (integerOnly) {
isOK = false;
return null;
}if (n == 6) {
isOK = false;
return null;
}coord[n++] = (this.theToken.value).floatValue();
break;
default:
this.iToken--;
break out;
}
}
if (n < minDim || n > maxDim) {
isOK = false;
return null;
}if (n == 3) {
if (useCell555P4) {
return JU.P4.new4(coord[0], coord[1], coord[2], (code555[0] % 1000) * 1000 + (code555[1] % 1000) + 1000000);
}var pt = JU.P3.new3(coord[0], coord[1], coord[2]);
if (this.coordinatesAreFractional && (mode & 32) != 0) {
this.fractionalPoint = JU.P3.newP(pt);
if (!this.chk) this.vwr.toCartesian(pt, false);
}return pt;
}if (n == 4) {
if (implicitFractional || !this.coordinatesAreFractional) {
var plane = JU.P4.new4(coord[0], coord[1], coord[2], coord[3]);
return plane;
}}isOK = false;
return null;
} finally {
if (!isOK && (mode & 128) == 0) this.invArg();
}
}, "~N,~N");
Clazz.defineMethod(c$, "isPoint3f", 
function(i){
var itok = this.tokAt(i);
if (itok == 0) return false;
var isOK;
if ((isOK = (itok == 8)) || itok == 9 || this.isFloatParameter(i + 1) && this.isFloatParameter(i + 2) && this.isFloatParameter(i + 3) && this.isFloatParameter(i + 4)) return isOK;
this.ignoreError = true;
var t = this.iToken;
isOK = true;
try {
if (this.getPoint3f(i, true, false) == null) isOK = false;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
isOK = false;
} else {
throw e;
}
}
this.ignoreError = false;
this.iToken = t;
return isOK;
}, "~N");
Clazz.defineMethod(c$, "getPoint3f", 
function(i, allowFractional, throwE){
return this.getPointOrPlane(i, 3 | 32 | (allowFractional ? 16 : 0) | (throwE ? 0 : 128));
}, "~N,~B,~B");
Clazz.defineMethod(c$, "getFractionalPoint", 
function(i){
return this.getPointOrPlane(i, 71);
}, "~N");
Clazz.defineMethod(c$, "getPoint4f", 
function(i){
return this.getPointOrPlane(i, 4);
}, "~N");
Clazz.defineMethod(c$, "xypParameter", 
function(index){
var tok = this.tokAt(index);
if (tok == 1073742195) tok = this.tokAt(++index);
if (tok != 268437504 || !this.isFloatParameter(++index)) return null;
var pt =  new JU.P3();
pt.x = this.floatParameter(index);
if (this.tokAt(++index) == 268436992) index++;
if (!this.isFloatParameter(index)) return null;
pt.y = this.floatParameter(index);
var isPercent = (this.tokAt(++index) == 268441090);
if (isPercent) ++index;
if (this.tokAt(index) != 268437505) return null;
this.iToken = index;
pt.z = (isPercent ? -1 : 1) * 3.4028235E38;
return pt;
}, "~N");
Clazz.defineMethod(c$, "xyzpParameter", 
function(index){
var tok = this.tokAt(index);
if (tok == 1073742195) tok = this.tokAt(++index);
if (tok != 268437504 || !this.isFloatParameter(++index)) return null;
var pt =  new JU.P4();
pt.x = this.floatParameter(index);
if (this.tokAt(++index) == 268436992) index++;
if (!this.isFloatParameter(index)) return null;
pt.y = this.floatParameter(index);
if (this.tokAt(++index) == 268436992) index++;
if (!this.isFloatParameter(index)) return null;
pt.z = this.floatParameter(index);
var isPercent = (this.tokAt(++index) == 268441090);
if (isPercent) ++index;
if (this.tokAt(index) != 268437505) return null;
this.iToken = index;
pt.w = (isPercent ? -1 : 1) * 3.4028235E38;
return pt;
}, "~N");
Clazz.defineMethod(c$, "optParameterAsString", 
function(i){
return (i >= this.slen ? "" : this.paramAsStr(i));
}, "~N");
Clazz.defineMethod(c$, "intParameter", 
function(index){
if (this.checkToken(index)) if (this.getToken(index).tok == 2) return this.theToken.intValue;
this.error(20);
return 0;
}, "~N");
Clazz.defineMethod(c$, "isFloatParameter", 
function(index){
switch (this.tokAt(index)) {
case 2:
case 3:
return true;
}
return false;
}, "~N");
Clazz.defineMethod(c$, "floatParameter", 
function(index){
if (this.checkToken(index)) {
this.getToken(index);
switch (this.theTok) {
case 1073742363:
return -this.theToken.intValue;
case 1073742362:
case 2:
return this.theToken.intValue;
case 1073742359:
case 3:
return (this.theToken.value).floatValue();
}
}this.error(34);
return 0;
}, "~N");
Clazz.defineMethod(c$, "getPointArray", 
function(i, nPoints, allowNull){
if (nPoints == 2147483647) nPoints = -1;
var points = (nPoints < 0 ? null :  new Array(nPoints));
var vp = (nPoints < 0 ?  new JU.Lst() : null);
var tok = (i < 0 ? 7 : this.getToken(i++).tok);
switch (tok) {
case 7:
var v = (this.theToken).getList();
if (nPoints >= 0 && v.size() != nPoints) this.invArg();
nPoints = v.size();
if (points == null) points =  new Array(nPoints);
for (var j = 0; j < nPoints; j++) if ((points[j] = JS.SV.ptValue(v.get(j))) == null && !allowNull) this.invArg();

return points;
case 1073742195:
tok = this.tokAt(i++);
break;
}
if (tok != 268437504) this.invArg();
var n = 0;
while (tok != 268437505 && tok != 0) {
tok = this.getToken(i).tok;
switch (tok) {
case 0:
case 268437505:
break;
case 268436992:
i++;
break;
default:
if (nPoints >= 0 && n == nPoints) {
tok = 0;
break;
}var pt = this.centerParameter(i, null);
if (points == null) vp.addLast(pt);
 else points[n] = pt;
n++;
i = this.iToken + 1;
}
}
if (tok != 268437505) this.invArg();
if (points == null) points = vp.toArray( new Array(vp.size()));
if (nPoints > 0 && points[nPoints - 1] == null) this.invArg();
return points;
}, "~N,~N,~B");
Clazz.defineMethod(c$, "listParameter", 
function(i, nMin, nMax){
return this.listParameter4(i, nMin, nMax, false);
}, "~N,~N,~N");
Clazz.defineMethod(c$, "listParameter4", 
function(i, nMin, nMax, allowString){
var v =  new JU.Lst();
var tok = this.tokAt(i);
if (tok == 1073742195) tok = this.tokAt(++i);
var haveBrace = (tok == 1073742332);
var haveSquare = (tok == 268437504);
if (haveBrace || haveSquare) i++;
var n = 0;
while (n < nMax) {
tok = this.tokAt(i);
if (haveBrace && tok == 1073742338 || haveSquare && tok == 268437505) break;
switch (tok) {
case 268436992:
case 268440576:
case 1073742332:
case 1073742338:
break;
case 4:
if (allowString) v.addLast(this.stringParameter(i));
break;
case 9:
var pt4 = this.getPoint4f(i);
v.addLast(Float.$valueOf(pt4.x));
v.addLast(Float.$valueOf(pt4.y));
v.addLast(Float.$valueOf(pt4.z));
v.addLast(Float.$valueOf(pt4.w));
n += 4;
break;
default:
if (this.isCenterParameter(i)) {
var pt = this.centerParameter(i, null);
i = this.iToken;
v.addLast(Float.$valueOf(pt.x));
v.addLast(Float.$valueOf(pt.y));
v.addLast(Float.$valueOf(pt.z));
n += 3;
break;
}v.addLast(Float.$valueOf(this.floatParameter(i)));
n++;
}
i += (n == nMax && haveSquare && this.tokAt(i + 1) == 1073742338 ? 2 : 1);
}
if (haveBrace && this.tokAt(i++) != 1073742338 || haveSquare && this.tokAt(i++) != 268437505 || n < nMin || n > nMax) this.invArg();
this.iToken = i - 1;
return v;
}, "~N,~N,~N,~B");
Clazz.defineMethod(c$, "floatParameterSet", 
function(i, nMin, nMax){
var v = null;
var fparams = null;
var n = 0;
var s = null;
this.iToken = i;
switch (this.tokAt(i)) {
case 4:
s = JS.SV.sValue(this.st[i]);
s = JU.PT.replaceWithCharacter(s, "{},[]\"'", ' ');
fparams = JU.PT.parseFloatArray(s);
n = fparams.length;
break;
case 7:
fparams = JS.SV.flistValue(this.st[i], 0);
n = fparams.length;
break;
default:
v = this.listParameter(i, nMin, nMax);
n = v.size();
}
if (n < nMin || n > nMax) this.invArg();
if (fparams == null) {
fparams =  Clazz.newFloatArray (n, 0);
for (var j = 0; j < n; j++) fparams[j] = (v.get(j)).floatValue();

}return fparams;
}, "~N,~N,~N");
Clazz.defineMethod(c$, "isArrayParameter", 
function(i){
switch (this.tokAt(i)) {
case 7:
case 11:
case 12:
case 1073742195:
case 268437504:
return true;
}
return false;
}, "~N");
Clazz.defineMethod(c$, "getQuaternionParameter", 
function(i, bsAtoms, divideByCurrent){
switch (this.tokAt(i)) {
case 7:
var sv = (this.getToken(i)).getList();
var p4 = null;
if (sv.size() == 0 || (p4 = JS.SV.pt4Value(sv.get(0))) == null) this.invArg();
return JU.Quat.newP4(p4);
case 1073741864:
return (this.chk ? null : this.vwr.getOrientation(1073741864, (divideByCurrent ? "best" : ""), bsAtoms, null));
default:
return JU.Quat.newP4(this.getPoint4f(i));
}
}, "~N,JU.BS,~B");
Clazz.defineMethod(c$, "checkLast", 
function(i){
return this.checkLength(i + 1) - 1;
}, "~N");
Clazz.defineMethod(c$, "checkLength", 
function(length){
if (length >= 0) return this.checkLengthErrorPt(length, 0);
if (this.slen > -length) {
this.iToken = -length;
this.bad();
}return this.slen;
}, "~N");
Clazz.defineMethod(c$, "checkLengthErrorPt", 
function(length, errorPt){
if (this.slen != length) {
this.iToken = errorPt > 0 ? errorPt : this.slen;
if (errorPt > 0) this.invArg();
 else this.bad();
}return this.slen;
}, "~N,~N");
Clazz.defineMethod(c$, "checkLength23", 
function(){
this.iToken = this.slen;
if (this.slen != 2 && this.slen != 3) this.bad();
return this.slen;
});
Clazz.defineMethod(c$, "checkLength34", 
function(){
this.iToken = this.slen;
if (this.slen != 3 && this.slen != 4) this.bad();
return this.slen;
});
Clazz.defineMethod(c$, "modelNumberParameter", 
function(index){
var iFrame = 0;
var useModelNumber = false;
switch (this.tokAt(index)) {
case 2:
useModelNumber = true;
case 3:
iFrame = this.getToken(index).intValue;
break;
case 4:
iFrame = JU.Edge.getFloatEncodedInt(this.stringParameter(index));
break;
default:
this.invArg();
}
return this.vwr.ms.getModelNumberIndex(iFrame, useModelNumber, true);
}, "~N");
Clazz.defineMethod(c$, "getMadParameter", 
function(){
var mad = 1;
var itok = this.getToken(1).tok;
switch (itok) {
case 1073742072:
(this).restrictSelected(false, false);
case 1073742335:
break;
case 1073742334:
mad = 0;
break;
case 2:
var radiusRasMol = this.intParameterRange(1, 0, 750);
mad = radiusRasMol * 4 * 2;
break;
case 3:
var f = this.floatParameterRange(1, -3, 3);
mad = (Float.isNaN(f) ? 2147483647 : Clazz.doubleToInt(Math.floor(f * 1000 * 2)));
if (mad < 0) {
(this).restrictSelected(false, false);
mad = -mad;
}break;
default:
this.error(6);
}
return mad;
});
Clazz.defineMethod(c$, "intParameterRange", 
function(i, min, max){
var val = this.intParameter(i);
if (val < min || val > max) {
this.integerOutOfRange(min, max);
return 2147483647;
}return val;
}, "~N,~N,~N");
Clazz.defineMethod(c$, "floatParameterRange", 
function(i, min, max){
var val = this.floatParameter(i);
if (val < min || val > max) {
this.numberOutOfRange(min, max);
return NaN;
}return val;
}, "~N,~N,~N");
Clazz.defineMethod(c$, "getPointVector", 
function(t, i){
switch (t.tok) {
case 10:
return this.vwr.ms.getAtomPointVector(t.value);
case 7:
var data =  new JU.Lst();
var pt;
var pts = (t).getList();
for (var j = 0; j < pts.size(); j++) {
var v = pts.get(j);
if ((pt = (v.tok == 10 ? this.vwr.ms.getAtomSetCenter(JS.SV.getBitSet(v, false)) : JS.SV.ptValue(v))) == null) return null;
data.addLast(pt);
}
return data;
}
if (i > 0) return this.vwr.ms.getAtomPointVector((this).atomExpressionAt(i));
return null;
}, "JS.T,~N");
Clazz.defineMethod(c$, "isColorParam", 
function(i){
var tok = this.tokAt(i);
return tok != 0 && (tok == 570425378 || tok == 1073742195 || tok == 268437504 || tok == 7 || tok == 8 || this.isPoint3f(i) || (tok == 4 || JS.T.tokAttr(tok, 1073741824)) && JU.CU.getArgbFromString(this.st[i].value) != 0);
}, "~N");
Clazz.defineMethod(c$, "getArgbParam", 
function(index){
return this.getArgbParamOrNone(index, false);
}, "~N");
Clazz.defineMethod(c$, "getArgbParamLast", 
function(index, allowNone){
var icolor = this.getArgbParamOrNone(index, allowNone);
this.checkLast(this.iToken);
return icolor;
}, "~N,~B");
Clazz.defineMethod(c$, "getArgbParamOrNone", 
function(index, allowNone){
var pt = null;
if (this.checkToken(index)) {
switch (this.getToken(index).tok) {
default:
if (!JS.T.tokAttr(this.theTok, 1073741824)) break;
case 570425378:
case 4:
return JU.CU.getArgbFromString(this.paramAsStr(index));
case 1073742195:
return this.getColorTriad(index + 2);
case 268437504:
return this.getColorTriad(++index);
case 7:
var rgb = JS.SV.flistValue(this.theToken, 3);
if (rgb != null && rgb.length != 3) pt = JU.P3.new3(rgb[0], rgb[1], rgb[2]);
break;
case 8:
pt = this.theToken.value;
break;
case 1073742332:
pt = this.getPoint3f(index, false, true);
break;
case 1073742333:
if (allowNone) return 0;
}
}if (pt == null) this.error(8);
return JU.CU.colorPtToFFRGB(pt);
}, "~N,~B");
Clazz.defineMethod(c$, "getColorTriad", 
function(i){
var colors =  Clazz.newFloatArray (3, 0);
var n = 0;
var hex = "";
this.getToken(i);
var pt = null;
var val = 0;
out : switch (this.theTok) {
case 2:
case 1073742362:
case 3:
for (; i < this.slen; i++) {
switch (this.getToken(i).tok) {
case 268436992:
continue;
case 1073741824:
if (n != 1 || colors[0] != 0) this.error(4);
hex = "0" + this.paramAsStr(i);
break out;
case 3:
if (n > 2) this.error(4);
val = this.floatParameter(i);
break;
case 2:
if (n > 2) this.error(4);
val = this.theToken.intValue;
break;
case 1073742362:
if (n > 2) this.error(4);
val = (this.theToken.value).intValue() % 256;
break;
case 268437505:
if (n != 3) this.error(4);
--i;
pt = JU.P3.new3(colors[0], colors[1], colors[2]);
break out;
default:
this.error(4);
}
colors[n++] = val;
}
this.error(4);
break;
case 8:
pt = this.theToken.value;
break;
case 1073741824:
hex = this.paramAsStr(i);
break;
default:
this.error(4);
}
if (this.getToken(++i).tok != 268437505) this.error(4);
if (pt != null) return JU.CU.colorPtToFFRGB(pt);
if ((n = JU.CU.getArgbFromString("[" + hex + "]")) == 0) this.error(4);
return n;
}, "~N");
Clazz.defineMethod(c$, "tickParamAsStr", 
function(index, allowUnitCell, allowScale, allowFirst){
this.iToken = index - 1;
if (this.tokAt(index) != 1073742164) return null;
var tickInfo;
var str = " ";
switch (this.tokAt(index + 1)) {
case 1111492629:
case 1111492630:
case 1111492631:
str = this.paramAsStr(++index).toLowerCase();
break;
case 1073741824:
this.invArg();
}
if (this.tokAt(++index) == 1073742333) {
tickInfo =  new JM.TickInfo(null);
tickInfo.type = str.charAt(0);
this.iToken = index;
return tickInfo;
}tickInfo =  new JM.TickInfo(this.getPointOrPlane(index, 19));
if (this.coordinatesAreFractional || this.tokAt(this.iToken + 1) == 1814695966) {
tickInfo.scale = JU.P3.new3(NaN, NaN, NaN);
allowScale = false;
}if (this.tokAt(this.iToken + 1) == 1814695966) this.iToken++;
tickInfo.type = str.charAt(0);
if (this.tokAt(this.iToken + 1) == 1287653388) tickInfo.tickLabelFormats = this.stringParameterSet(this.iToken + 2);
if (!allowScale) return tickInfo;
if (this.tokAt(this.iToken + 1) == 536875059) {
if (this.isFloatParameter(this.iToken + 2)) {
var f = this.floatParameter(this.iToken + 2);
tickInfo.scale = JU.P3.new3(f, f, f);
} else {
tickInfo.scale = this.getPoint3f(this.iToken + 2, true, true);
}}if (allowFirst) if (this.tokAt(this.iToken + 1) == 1073741942) tickInfo.first = this.floatParameter(this.iToken + 2);
return tickInfo;
}, "~N,~B,~B,~B");
Clazz.defineMethod(c$, "setBooleanProperty", 
function(key, value){
if (!this.chk) this.vwr.setBooleanProperty(key, value);
}, "~S,~B");
Clazz.defineMethod(c$, "setIntProperty", 
function(key, value){
if (!this.chk) this.vwr.setIntProperty(key, value);
return true;
}, "~S,~N");
Clazz.defineMethod(c$, "setFloatProperty", 
function(key, value){
if (!this.chk) this.vwr.setFloatProperty(key, value);
return true;
}, "~S,~N");
Clazz.defineMethod(c$, "setStringProperty", 
function(key, value){
if (!this.chk) this.vwr.setStringProperty(key, value);
}, "~S,~S");
Clazz.defineMethod(c$, "checkHKL", 
function(pt){
if (Math.abs(pt.x) < 1 || Math.abs(pt.y) < 1 || Math.abs(pt.z) < 1 || pt.x != Clazz.floatToInt(pt.x) || pt.y != Clazz.floatToInt(pt.y) || pt.z != Clazz.floatToInt(pt.z)) this.invArg();
return pt;
}, "JU.T3");
Clazz.defineMethod(c$, "planeValue", 
function(x){
var pt;
var sym = null;
var offset = NaN;
var vc = null;
switch (x.tok) {
case 9:
return x.value;
case 7:
break;
case 4:
case 1073741824:
var s = x.value;
var isMinus = s.startsWith("-");
var f = (isMinus ? -1 : 1);
if (isMinus) s = s.substring(1);
var p4 = null;
var len = s.length;
var mode = (len < 2 ? -1 : "xy yz xz x= y= z= ab bc ac a= b= c=".indexOf(s.substring(0, 2).toLowerCase()));
if (mode >= 18 && (sym = this.vwr.getCurrentUnitCell()) == null) {
mode -= 18;
}var isab = (s.indexOf("=") < 0);
if (len > 2) {
if (!isab) offset = -f * JU.PT.parseFloat(s.substring(2));
 else if (Float.isNaN(offset) && mode >= 18 && s.charAt(2) == '1') offset = -1;
}switch (mode) {
case 0:
return JU.P4.new4(1, 1, 0, f);
case 3:
return JU.P4.new4(0, 1, 1, f);
case 6:
return JU.P4.new4(1, 0, 1, f);
case 9:
p4 = JU.P4.new4(1, 0, 0, -f * JU.PT.parseFloat(s.substring(2)));
break;
case 12:
p4 = JU.P4.new4(0, 1, 0, -f * JU.PT.parseFloat(s.substring(2)));
break;
case 15:
p4 = JU.P4.new4(0, 0, 1, -f * JU.PT.parseFloat(s.substring(2)));
break;
case 18:
if (Float.isNaN(offset)) offset = 0;
case 33:
p4 = this.getHklPlane(vc = JU.P3.new3(0, 0, 1), 0, null);
p4.scale4(f = -f);
break;
case 21:
if (Float.isNaN(offset)) offset = 0;
case 27:
p4 = this.getHklPlane(vc = JU.P3.new3(1, 0, 0), 0, null);
p4.scale4(-(f = -f));
break;
case 24:
if (Float.isNaN(offset)) offset = 0;
case 30:
p4 = this.getHklPlane(vc = JU.P3.new3(0, 1, 0), 0, null);
p4.scale4(-f);
break;
}
if (p4 == null || Float.isNaN(p4.w)) break;
if (sym != null && !Float.isNaN(offset)) {
sym.toCartesian(vc, true);
if (isab || !isMinus) {
offset = -offset;
}p4.w = vc.dot(p4) * offset;
if (!isab || offset != 0) p4.scale(-1);
}return p4;
default:
return null;
}
pt = JU.Escape.uP(JS.SV.sValue(x));
return (Clazz.instanceOf(pt,"JU.P4") ? pt : null);
}, "JS.T");
Clazz.defineMethod(c$, "setScriptArguments", 
function(params, isCallback){
if (this.contextVariables == null) this.contextVariables =  new java.util.Hashtable();
this.contextVariables.put("_arguments", (params == null ? JS.SV.getVariableAI( Clazz.newIntArray(-1, [])) : isCallback ? JS.SV.newV(1275068418, params) : JS.SV.getVariableList(params)));
this.contextVariables.put("_argcount", JS.SV.newI(params == null ? 0 : isCallback ? (params).length : (params).size()));
}, "~O,~B");
Clazz.defineMethod(c$, "getCallbackParameter", 
function(n){
var v = (this.contextVariables == null ? null : this.contextVariables.get("_arguments"));
if (v == null && (this.thisContext == null || (v = this.thisContext.getVariable("_arguments")) == null)) return null;
if (v.tok == 1275068418) {
if (n == -2147483648) {
return v.arrayToList(v);
}var params = v.value;
return (--n < 0 || n >= params.length ? null : (params[n] = JS.SV.getVariable(params[n])));
}var list = v.getList();
return (n == -2147483648 ? v : --n < 0 || n >= list.size() ? JS.SV.newV(7,  new JU.Lst()) : list.get(n));
}, "~N");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
