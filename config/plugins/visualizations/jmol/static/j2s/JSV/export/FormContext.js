Clazz.declarePackage("JSV.export");
Clazz.load(["java.util.Hashtable", "JU.Lst"], "JSV.export.FormContext", ["JU.DF", "$.PT", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.tokens = null;
this.context = null;
this.formTokens = null;
this.commandLevel = 0;
this.cmds = null;
this.strError = null;
if (!Clazz.isClassDefined("JSV.export.FormContext.FormToken")) {
JSV.export.FormContext.$FormContext$FormToken$ ();
}
Clazz.instantialize(this, arguments);}, JSV["export"], "FormContext", null);
Clazz.prepareFields (c$, function(){
this.context =  new java.util.Hashtable();
this.cmds =  new JU.Lst();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "put", 
function(key, value){
if (value == null) value = "";
this.context.put(key, value);
}, "~S,~O");
Clazz.defineMethod(c$, "setTemplate", 
function(template){
var errMsg = this.getFormTokens(template);
if (errMsg != null) return errMsg;
return null;
}, "~S");
Clazz.defineMethod(c$, "getFormTokens", 
function(template){
this.formTokens =  new JU.Lst();
if (template.indexOf("\r\n") >= 0) template = JU.PT.replaceAllCharacters(template, "\r\n", "\n");
template = template.$replace('\r', '\n');
var lines = template.$plit("\n");
var token = "";
for (var i = 0; i < lines.length && this.strError == null; i++) {
var line = lines[i];
var m = line.length;
var ch;
while (--m >= 0 && ((ch = line.charAt(m)) == ' ' || ch == '\t')) {
}
line = line.substring(0, m + 1);
if (line.length == 0) continue;
var firstChar = -1;
var nChar = line.length;
while (++firstChar < nChar && Character.isWhitespace(line.charAt(firstChar))) {
}
if (line.indexOf("#") == firstChar) {
if (token.length > 0) {
Clazz.innerTypeInstance(JSV["export"].FormContext.FormToken, this, null, token, 0);
token = "";
}if (this.strError != null) break;
Clazz.innerTypeInstance(JSV["export"].FormContext.FormToken, this, null, line, firstChar);
continue;
}token += line + "\n";
}
if (token.length > 0 && this.strError == null) {
Clazz.innerTypeInstance(JSV["export"].FormContext.FormToken, this, null, token, 0);
}return this.strError;
}, "~S");
Clazz.defineMethod(c$, "merge", 
function(out){
var ptr;
for (var i = 0; i < this.formTokens.size() && this.strError == null; i++) {
var vt = this.formTokens.get(i);
switch (vt.cmdType) {
case 0:
var data = this.fillData(vt.data);
out.append(data);
continue;
case 1:
if (this.evaluate(vt.data, true)) {
vt.endPtr = -vt.endPtr;
} else {
i = vt.endPtr - 1;
}continue;
case 2:
case 3:
if ((ptr = this.formTokens.get(vt.cmdPtr).endPtr) < 0) {
this.formTokens.get(vt.cmdPtr).endPtr = -ptr;
while ((vt = this.formTokens.get(vt.endPtr)).cmdType != 4) {
}
i = vt.ptr;
continue;
}if (vt.cmdType == 3) {
if (this.evaluate(vt.data, true)) {
vt.endPtr = -vt.endPtr;
} else {
i = vt.endPtr - 1;
}}continue;
case 5:
this.foreach(vt);
case 4:
if ((vt = this.formTokens.get(vt.cmdPtr)).cmdType != 5) continue;
if (vt.vc == null) continue;
if (++vt.pointCount == vt.vc.size()) {
i = vt.endPtr;
continue;
}var varData = vt.vc.get(vt.pointCount);
if (Clazz.instanceOf(varData,"JSV.common.Coordinate")) {
var c = varData;
this.context.put("pointCount",  new Integer(vt.pointCount));
this.context.put(vt.$var + ".xVal",  new Double(c.getXVal()));
this.context.put(vt.$var + ".yVal",  new Double(c.getYVal()));
this.context.put(vt.$var + ".getXString()", this.getXString(c));
this.context.put(vt.$var + ".getYString()", this.getYString(c));
} else if (Clazz.instanceOf(varData,"java.util.Map")) {
for (var entry, $entry = (varData).entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) this.context.put(vt.$var + "." + entry.getKey(), entry.getValue());

}i = vt.cmdPtr;
continue;
}
}
return (this.strError != null ? this.strError : out != null ? out.toString() : null);
}, "JU.OC");
Clazz.defineMethod(c$, "getXString", 
function(c){
return JU.DF.formatDecimalTrimmed0(c.getXVal(), 8);
}, "JSV.common.Coordinate");
Clazz.defineMethod(c$, "getYString", 
function(c){
return JU.DF.formatDecimalTrimmed0(c.getYVal(), 8);
}, "JSV.common.Coordinate");
Clazz.defineMethod(c$, "foreach", 
function(vt){
var data = vt.data;
data = data.$replace('(', ' ');
data = data.$replace(')', ' ');
var tokens = JU.PT.getTokens(data);
if (tokens.length != 4) {
return;
}vt.$var = tokens[1].substring(1);
var vc = this.context.get(tokens[3].substring(1));
if (Clazz.instanceOf(vc,"JU.Lst")) vt.vc = vc;
vt.cmdPtr = vt.ptr;
vt.pointCount = -1;
}, "JSV.export.FormContext.FormToken");
c$.findOp = Clazz.defineMethod(c$, "findOp", 
function(op){
for (var i = JSV["export"].FormContext.ops.length; --i >= 0; ) if (JSV["export"].FormContext.ops[i].equals(op)) return i;

return -1;
}, "~S");
Clazz.defineMethod(c$, "evaluate", 
function(data, isIf){
var pt = data.indexOf("(");
if (pt < 0) {
this.strError = "missing ( in " + data;
return false;
}data = data.substring(pt + 1);
pt = data.lastIndexOf(")");
if (pt < 0) {
this.strError = "missing ) in " + data;
return false;
}data = data.substring(0, pt);
data = JU.PT.rep(data, "=", " = ");
data = JU.PT.rep(data, "!", " ! ");
data = JU.PT.rep(data, "<", " < ");
data = JU.PT.rep(data, ">", " > ");
data = JU.PT.rep(data, "=  =", "==");
data = JU.PT.rep(data, "<  =", "<=");
data = JU.PT.rep(data, ">  =", ">=");
data = JU.PT.rep(data, "!  =", "!=");
var tokens = JU.PT.getTokens(data);
var key = tokens[0].substring(1);
var isNot = false;
var x = false;
var value = null;
var compare = "";
try {
switch (tokens.length) {
case 1:
value = this.getValue(key);
return (!value.equals("") && !value.equals("false"));
case 2:
if (key.equals("!")) {
key = JU.PT.trim(tokens[1], "$ ");
value = this.getValue(key);
return (value.equals("false") || value.equals(""));
}break;
case 3:
key = JU.PT.trim(tokens[0], "$ ");
value = this.getValue(key);
compare = JU.PT.trim(tokens[2], " \"");
switch (JSV["export"].FormContext.findOp(tokens[1])) {
case 2:
case 0:
return (value.equals(compare));
case 1:
return (!value.equals(compare));
default:
JU.Logger.warn("???? " + key + " " + compare + " " + value);
}
break;
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.warn(e.toString() + " in VelocityContext.merge");
} else {
throw e;
}
}
return isNot ? !x : x;
}, "~S,~B");
Clazz.defineMethod(c$, "getValue", 
function(key){
return (this.context.containsKey(key) ? this.context.get(key).toString() : "");
}, "~S");
Clazz.defineMethod(c$, "fillData", 
function(data){
var i = 0;
var ccData = data.length;
while (i < ccData) {
while (i < ccData && data.charAt(i++) != '$') {
}
if (i == ccData) break;
var j = i;
var ch;
while (++j < ccData && (Character.isLetterOrDigit(ch = data.charAt(j)) || ch == '.' || ch == '_')) {
}
if (j < ccData && data.charAt(j) == '(') j += 2;
var key = data.substring(i, j);
if (this.context.containsKey(key)) {
var value = this.context.get(key);
var strValue;
if (Clazz.instanceOf(value,"JSV.common.Coordinate")) {
strValue = value.toString();
} else {
strValue = value.toString();
}data = data.substring(0, i - 1) + strValue + data.substring(j);
ccData = data.length;
i += strValue.length;
}}
return data;
}, "~S");
c$.$FormContext$FormToken$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.hasVariable = false;
this.cmdType = 0;
this.cmdPtr = -1;
this.endPtr = -1;
this.ptr = 0;
this.$var = null;
this.vc = null;
this.pointCount = 0;
this.data = null;
Clazz.instantialize(this, arguments);}, JSV["export"].FormContext, "FormToken", null);
Clazz.makeConstructor(c$, 
function(token, firstChar){
this.hasVariable = token.indexOf("$") >= 0;
this.data = token;
if (token.indexOf("#") != firstChar) {
this.b$["JSV.export.FormContext"].formTokens.addLast(this);
return;
}this.ptr = this.b$["JSV.export.FormContext"].formTokens.size();
var checkIf = false;
if (token.indexOf("#end") == firstChar) {
this.cmdType = 4;
this.endPtr = this.ptr;
this.b$["JSV.export.FormContext"].commandLevel--;
if (this.b$["JSV.export.FormContext"].commandLevel < 0) {
this.b$["JSV.export.FormContext"].strError = "misplaced #end";
return;
}this.cmdPtr = this.b$["JSV.export.FormContext"].cmds.removeItemAt(0).intValue();
this.b$["JSV.export.FormContext"].formTokens.get(this.cmdPtr).endPtr = this.ptr;
} else {
this.b$["JSV.export.FormContext"].commandLevel++;
if (token.indexOf("#if") == firstChar) {
this.cmdType = 1;
this.b$["JSV.export.FormContext"].cmds.add(0,  new Integer(this.ptr));
} else if (token.indexOf("#foreach") == firstChar) {
this.cmdType = 5;
this.b$["JSV.export.FormContext"].cmds.add(0,  new Integer(this.ptr));
this.cmdPtr = this.ptr;
if (token.indexOf("#end") > 0) {
var pt = token.indexOf(")") + 1;
this.data = token.substring(0, pt);
this.b$["JSV.export.FormContext"].formTokens.addLast(this);
Clazz.innerTypeInstance(JSV["export"].FormContext.FormToken, this, null, token.substring(pt, token.indexOf("#end")), 0);
Clazz.innerTypeInstance(JSV["export"].FormContext.FormToken, this, null, "#end", 0);
return;
}} else if (token.indexOf("#elseif") == firstChar) {
if (this.b$["JSV.export.FormContext"].cmds.size() == 0) {
this.b$["JSV.export.FormContext"].strError = "misplaced #elseif";
return;
}this.cmdType = 3;
this.cmdPtr = this.b$["JSV.export.FormContext"].cmds.removeItemAt(0).intValue();
var vt = this.b$["JSV.export.FormContext"].formTokens.get(this.cmdPtr);
checkIf = true;
vt.endPtr = this.ptr;
this.b$["JSV.export.FormContext"].cmds.add(0,  new Integer(this.ptr));
} else if (token.indexOf("#else") == firstChar) {
if (this.b$["JSV.export.FormContext"].cmds.size() == 0) {
this.b$["JSV.export.FormContext"].strError = "misplaced #else";
return;
}this.cmdType = 2;
checkIf = true;
this.cmdPtr = this.b$["JSV.export.FormContext"].cmds.removeItemAt(0).intValue();
this.b$["JSV.export.FormContext"].formTokens.get(this.cmdPtr).endPtr = this.ptr;
this.b$["JSV.export.FormContext"].cmds.add(0,  new Integer(this.ptr));
} else {
JU.Logger.warn("??? " + token);
}if (checkIf) {
var vt = this.b$["JSV.export.FormContext"].formTokens.get(this.cmdPtr);
if (vt.cmdType != 1 && vt.cmdType != 3) {
this.b$["JSV.export.FormContext"].strError = "misplaced " + token.trim();
return;
}}}this.b$["JSV.export.FormContext"].formTokens.addLast(this);
}, "~S,~N");
/*eoif4*/})();
};
c$.ops =  Clazz.newArray(-1, ["==", "!=", "="]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
