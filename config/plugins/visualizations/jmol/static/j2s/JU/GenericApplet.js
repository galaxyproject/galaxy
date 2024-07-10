Clazz.declarePackage("JU");
Clazz.load(["javajs.api.JSInterface", "J.api.JmolAppletInterface", "$.JmolStatusListener"], "JU.GenericApplet", ["java.net.URL", "java.util.Hashtable", "JU.Lst", "$.PT", "$.SB", "J.awtjs2d.Platform", "J.c.CBK", "J.i18n.GT", "JU.Logger", "$.Parser", "JV.JC", "$.Viewer"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.codeBase = null;
this.documentBase = null;
this.isSigned = false;
this.language = null;
this.doTranslate = true;
this.haveDocumentAccess = false;
this.isStereoSlave = false;
this.mayScript = false;
this.htmlName = null;
this.fullName = null;
this.statusForm = null;
this.statusText = null;
this.statusTextarea = null;
this.gRight = null;
this.viewer = null;
this.b$ = null;
this.vwrOptions = null;
this.haveNotifiedError = false;
this.appletObject = null;
this.loading = false;
this.syncId = null;
this.outputBuffer = null;
this.htParams = null;
Clazz.instantialize(this, arguments);}, JU, "GenericApplet", null, [javajs.api.JSInterface, J.api.JmolAppletInterface, J.api.JmolStatusListener]);
Clazz.defineMethod(c$, "setStereoGraphics", 
function(isStereo){
{
if (isStereo)
return vwr.apiPlatform.context;
}return null;
}, "~B");
Clazz.overrideMethod(c$, "processMouseEvent", 
function(id, x, y, modifiers, time){
return this.viewer.processMouseEvent(id, x, y, modifiers, time);
}, "~N,~N,~N,~N,~N");
Clazz.overrideMethod(c$, "processKeyEvent", 
function(event){
this.viewer.processKeyEvent(event);
}, "~O");
Clazz.overrideMethod(c$, "setDisplay", 
function(canvas){
this.viewer.setDisplay(canvas);
}, "~O");
Clazz.overrideMethod(c$, "setStatusDragDropped", 
function(mode, x, y, fileName, retType){
return this.viewer.setStatusDragDropped(mode, x, y, fileName, retType);
}, "~N,~N,~N,~S,~A");
Clazz.overrideMethod(c$, "startHoverWatcher", 
function(enable){
this.viewer.startHoverWatcher(enable);
}, "~B");
Clazz.overrideMethod(c$, "update", 
function(){
this.viewer.updateJS();
});
Clazz.overrideMethod(c$, "openFileAsyncSpecial", 
function(fileName, flags){
this.viewer.openFileAsyncSpecial(fileName, flags);
}, "~S,~N");
Clazz.overrideMethod(c$, "openFileAsyncSpecialType", 
function(fileName, flags, type){
this.viewer.openFileAsyncSpecialType(fileName, flags, type);
}, "~S,~N,~S");
Clazz.overrideMethod(c$, "processTwoPointGesture", 
function(touches){
this.viewer.processTwoPointGesture(touches);
}, "~A");
Clazz.overrideMethod(c$, "setScreenDimension", 
function(width, height){
this.viewer.setScreenDimension(width, height);
}, "~N,~N");
Clazz.defineMethod(c$, "resizeDisplay", 
function(width, height){
var jmol = J.awtjs2d.Platform.Jmol();
jmol.resizeApplet(this.viewer.html5Applet,  Clazz.newIntArray(-1, [width, height]));
}, "~N,~N");
Clazz.defineMethod(c$, "init", 
function(applet){
this.b$ =  new java.util.Hashtable();
if (JU.GenericApplet.htRegistry == null) JU.GenericApplet.htRegistry =  new java.util.Hashtable();
this.appletObject = applet;
this.htmlName = JU.PT.split("" + this.getJmolParameter("name"), "_object")[0];
this.syncId = this.getJmolParameter("syncId");
this.fullName = this.htmlName + "__" + this.syncId + "__";
System.out.println("Jmol JavaScript applet " + this.fullName + " initializing");
var iLevel = ((this.getValue("logLevel", (this.getBooleanValue("debug", false) ? "5" : "4"))).charAt(0)).charCodeAt(0) - 48;
if (iLevel != 4) System.out.println("setting logLevel=" + iLevel + " -- To change, use script \"set logLevel [0-5]\"");
JU.Logger.setLogLevel(iLevel);
J.i18n.GT.ignoreApplicationBundle();
this.initOptions();
JU.GenericApplet.checkIn(this.fullName, this.appletObject);
this.initApplication();
}, "~O");
Clazz.defineMethod(c$, "initApplication", 
function(){
this.vwrOptions.put("applet", Boolean.TRUE);
if (this.getJmolParameter("statusListener") == null) this.vwrOptions.put("statusListener", this);
this.language = this.getJmolParameter("language");
if (this.language != null) this.vwrOptions.put("language", this.language);
this.viewer =  new JV.Viewer(this.vwrOptions);
this.viewer.pushHoldRepaint();
var emulate = this.getValueLowerCase("emulate", "jmol");
this.setStringProperty("defaults", emulate.equals("chime") ? "RasMol" : "Jmol");
this.setStringProperty("backgroundColor", this.getValue("bgcolor", this.getValue("boxbgcolor", "black")));
this.viewer.setBooleanProperty("frank", true);
this.loading = true;
for (var item, $item = 0, $$item = J.c.CBK.values(); $item < $$item.length && ((item = $$item[$item]) || true); $item++) {
var name = item.name();
var o = this.getValue(name + "Callback", null);
if (o != null) {
if ((typeof(o)=='string')) {
this.setStringProperty(name + "Callback", o);
} else {
var def = null;
{
def = "Info." + o.name;
}this.setStringProperty(name + "Callback", def);
this.setCallback(name, o);
}}}
this.loading = false;
if (this.language != null) System.out.print("requested language=" + this.language + "; ");
this.doTranslate = (!"none".equals(this.language) && this.getBooleanValue("doTranslate", true));
this.language = J.i18n.GT.getLanguage();
System.out.println("language=" + this.language);
if (this.b$.get(J.c.CBK.SCRIPT) == null && this.b$.get(J.c.CBK.ERROR) == null) if (this.b$.get(J.c.CBK.MESSAGE) != null || this.statusForm != null || this.statusText != null) {
if (this.doTranslate && (this.getValue("doTranslate", null) == null)) {
this.doTranslate = false;
JU.Logger.warn("Note -- Presence of message callback disables disable translation; to enable message translation use jmolSetTranslation(true) prior to jmolApplet()");
}if (this.doTranslate) JU.Logger.warn("Note -- Automatic language translation may affect parsing of message callbacks messages; use scriptCallback or errorCallback to process errors");
}if (!this.doTranslate) {
J.i18n.GT.setDoTranslate(false);
JU.Logger.warn("Note -- language translation disabled");
}if (!this.getBooleanValue("popupMenu", true)) this.viewer.getProperty("DATA_API", "disablePopupMenu", null);
var menuFile = this.getJmolParameter("menuFile");
if (menuFile != null) this.viewer.setMenu(menuFile, true);
var script = this.getValue("script", "");
var loadParam = this.getValue("loadInline", null);
if (loadParam == null) {
if ((loadParam = this.getValue("load", null)) != null) script = "load \"" + loadParam + "\";" + script;
loadParam = null;
}this.viewer.popHoldRepaint("applet init");
if (loadParam != null && this.viewer.loadInline(loadParam) != null) script = "";
if (script.length > 0) this.scriptProcessor(script, null, 1);
this.viewer.notifyStatusReady(true);
});
Clazz.overrideMethod(c$, "destroy", 
function(){
this.gRight = null;
this.viewer.notifyStatusReady(false);
this.viewer = null;
JU.GenericApplet.checkOut(this.fullName);
});
Clazz.defineMethod(c$, "getBooleanValue", 
function(propertyName, defaultValue){
var value = this.getValue(propertyName, defaultValue ? "true" : "");
return (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("on") || value.equalsIgnoreCase("yes"));
}, "~S,~B");
Clazz.defineMethod(c$, "getValue", 
function(propertyName, defaultValue){
var s = this.getJmolParameter(propertyName);
System.out.println("Jmol getValue " + propertyName + " " + s);
return (s == null ? defaultValue : s);
}, "~S,~S");
Clazz.defineMethod(c$, "getValueLowerCase", 
function(paramName, defaultValue){
var value = this.getValue(paramName, defaultValue);
if (value != null) {
value = value.trim().toLowerCase();
if (value.length == 0) value = null;
}return value;
}, "~S,~S");
Clazz.defineMethod(c$, "setStringProperty", 
function(name, value){
if (value == null) return;
JU.Logger.info(name + " = \"" + value + "\"");
this.viewer.setStringProperty(name, value);
}, "~S,~S");
Clazz.defineMethod(c$, "scriptProcessor", 
function(script, statusParams, processType){
if (script == null || script.length == 0) return "";
switch (processType) {
case 0:
var err = this.viewer.scriptCheck(script);
return ((typeof(err)=='string') ? err : "");
case 1:
if (statusParams != null) return this.viewer.scriptWaitStatus(script, statusParams).toString();
return this.viewer.scriptWait(script);
case 2:
default:
return this.viewer.script(script);
}
}, "~S,~S,~N");
Clazz.overrideMethod(c$, "register", 
function(id, jsi){
JU.GenericApplet.checkIn(id, jsi);
}, "~S,J.api.JmolSyncInterface");
Clazz.overrideMethod(c$, "getJSpecViewProperty", 
function(key){
return null;
}, "~S");
Clazz.defineMethod(c$, "syncScript", 
function(script){
this.viewer.syncScript(script, "~", 0);
}, "~S");
Clazz.overrideMethod(c$, "handleEvent", 
function(e){
if (this.viewer == null) return false;
return this.viewer.processMouseEvent(e.id, e.x, e.y, e.modifiers, e.when);
}, "java.awt.Event");
Clazz.overrideMethod(c$, "getAppletInfo", 
function(){
return J.i18n.GT.o(J.i18n.GT.$("Jmol Applet version {0} {1}.\n\nAn OpenScience project.\n\nSee http://www.jmol.org for more information"),  Clazz.newArray(-1, [JV.JC.version, JV.JC.date])) + "\nhtmlName = " + JU.PT.esc(this.htmlName) + "\nsyncId = " + JU.PT.esc(this.syncId) + "\ndocumentBase = " + JU.PT.esc(this.documentBase) + "\ncodeBase = " + JU.PT.esc(this.codeBase);
});
Clazz.overrideMethod(c$, "script", 
function(script){
this.scriptNoWait(script);
}, "~S");
Clazz.overrideMethod(c$, "scriptCheck", 
function(script){
if (script == null || script.length == 0) return "";
return this.scriptProcessor(script, null, 0);
}, "~S");
Clazz.overrideMethod(c$, "scriptNoWait", 
function(script){
if (script == null || script.length == 0) return "";
return this.scriptProcessor(script, null, 2);
}, "~S");
Clazz.defineMethod(c$, "scriptWait", 
function(script){
return this.scriptWait(script, null);
}, "~S");
Clazz.defineMethod(c$, "scriptWait", 
function(script, statusParams){
if (script == null || script.length == 0) return "";
this.outputBuffer = null;
return this.scriptProcessor(script, statusParams, 1);
}, "~S,~S");
Clazz.overrideMethod(c$, "scriptWaitOutput", 
function(script){
if (script == null || script.length == 0) return "";
this.outputBuffer =  new JU.SB();
this.viewer.scriptWaitStatus(script, "");
var str = (this.outputBuffer == null ? "" : this.outputBuffer.toString());
this.outputBuffer = null;
return str;
}, "~S");
Clazz.overrideMethod(c$, "getModelIndexFromId", 
function(id){
return this.viewer.getModelIndexFromId(id);
}, "~S");
Clazz.defineMethod(c$, "getProperty", 
function(infoType){
return this.viewer.getProperty(null, infoType, "");
}, "~S");
Clazz.defineMethod(c$, "getProperty", 
function(infoType, paramInfo){
{
paramInfo || (paramInfo = "");
}return this.viewer.getProperty(null, infoType, paramInfo);
}, "~S,~S");
Clazz.defineMethod(c$, "getPropertyAsString", 
function(infoType){
return this.viewer.getProperty("readable", infoType, "").toString();
}, "~S");
Clazz.defineMethod(c$, "getPropertyAsString", 
function(infoType, paramInfo){
{
paramInfo || (paramInfo = "");
}return this.viewer.getProperty("readable", infoType, paramInfo).toString();
}, "~S,~S");
Clazz.defineMethod(c$, "getPropertyAsJSON", 
function(infoType){
return this.viewer.getProperty("JSON", infoType, "").toString();
}, "~S");
Clazz.defineMethod(c$, "getPropertyAsJSON", 
function(infoType, paramInfo){
{
paramInfo || (paramInfo = "");
}return this.viewer.getProperty("JSON", infoType, paramInfo).toString();
}, "~S,~S");
Clazz.overrideMethod(c$, "loadInlineString", 
function(strModel, script, isAppend){
var errMsg = this.viewer.loadInlineAppend(strModel, isAppend);
if (errMsg == null) this.script(script);
return errMsg;
}, "~S,~S,~B");
Clazz.overrideMethod(c$, "loadInlineArray", 
function(strModels, script, isAppend){
if (strModels == null || strModels.length == 0) return null;
var errMsg = this.viewer.loadInline(strModels, isAppend);
if (errMsg == null) this.script(script);
return errMsg;
}, "~A,~S,~B");
Clazz.overrideMethod(c$, "loadDOMNode", 
function(DOMNode){
return this.viewer.openDOM(DOMNode);
}, "~O");
Clazz.defineMethod(c$, "loadInline", 
function(strModel){
return this.loadInlineString(strModel, "", false);
}, "~S");
Clazz.defineMethod(c$, "loadInline", 
function(strModel, script){
return this.loadInlineString(strModel, script, false);
}, "~S,~S");
Clazz.defineMethod(c$, "loadInline", 
function(strModels){
return this.loadInlineArray(strModels, "", false);
}, "~A");
Clazz.defineMethod(c$, "loadInline", 
function(strModels, script){
return this.loadInlineArray(strModels, script, false);
}, "~A,~S");
Clazz.defineMethod(c$, "output", 
function(s){
if (this.outputBuffer != null && s != null) this.outputBuffer.append(s).appendC('\n');
}, "~S");
Clazz.overrideMethod(c$, "setCallback", 
function(name, callbackObject){
this.viewer.sm.setCallbackFunction(name, callbackObject);
}, "~S,~O");
Clazz.overrideMethod(c$, "setCallbackFunction", 
function(callbackName, callbackObject){
if (callbackName.equalsIgnoreCase("language")) {
this.consoleMessage("");
this.consoleMessage(null);
return;
}var callback = J.c.CBK.getCallback(callbackName);
if (callback != null && (this.loading || callback !== J.c.CBK.EVAL)) {
if (callbackObject == null) this.b$.remove(callback);
 else this.b$.put(callback, callbackObject);
return;
}this.consoleMessage("Available callbacks include: " + J.c.CBK.getNameList().$replace(';', ' ').trim());
}, "~S,~S");
Clazz.defineMethod(c$, "consoleMessage", 
function(message){
this.notifyCallback(J.c.CBK.ECHO,  Clazz.newArray(-1, ["", message]));
}, "~S");
Clazz.overrideMethod(c$, "notifyEnabled", 
function(type){
switch (type) {
case J.c.CBK.SYNC:
if (!JU.GenericApplet.isJS) return false;
case J.c.CBK.ANIMFRAME:
case J.c.CBK.DRAGDROP:
case J.c.CBK.ECHO:
case J.c.CBK.ERROR:
case J.c.CBK.EVAL:
case J.c.CBK.IMAGE:
case J.c.CBK.LOADSTRUCT:
case J.c.CBK.MEASURE:
case J.c.CBK.MESSAGE:
case J.c.CBK.PICK:
case J.c.CBK.SCRIPT:
return true;
case J.c.CBK.AUDIO:
case J.c.CBK.APPLETREADY:
case J.c.CBK.ATOMMOVED:
case J.c.CBK.CLICK:
case J.c.CBK.HOVER:
case J.c.CBK.MINIMIZATION:
case J.c.CBK.MODELKIT:
case J.c.CBK.RESIZE:
case J.c.CBK.SELECT:
case J.c.CBK.SERVICE:
case J.c.CBK.STRUCTUREMODIFIED:
break;
}
return (this.b$.get(type) != null);
}, "J.c.CBK");
Clazz.defineMethod(c$, "notifyCallback", 
function(type, data){
var callback = (type == null ? null : this.b$.get(type));
var doCallback = (type == null || callback != null && (data == null || data[0] == null));
var toConsole = false;
if (data != null) data[0] = this.htmlName;
var strInfo = (data == null || data[1] == null ? null : data[1].toString());
if (type != null) switch (type) {
case J.c.CBK.APPLETREADY:
data[3] = this.appletObject;
break;
case J.c.CBK.AUDIO:
case J.c.CBK.ERROR:
case J.c.CBK.EVAL:
case J.c.CBK.HOVER:
case J.c.CBK.IMAGE:
case J.c.CBK.MINIMIZATION:
case J.c.CBK.SERVICE:
case J.c.CBK.RESIZE:
case J.c.CBK.DRAGDROP:
case J.c.CBK.ATOMMOVED:
case J.c.CBK.SELECT:
case J.c.CBK.MODELKIT:
case J.c.CBK.STRUCTUREMODIFIED:
break;
case J.c.CBK.CLICK:
if ("alert".equals(callback)) strInfo = "x=" + data[1] + " y=" + data[2] + " action=" + data[3] + " clickCount=" + data[4];
break;
case J.c.CBK.ANIMFRAME:
var iData = data[1];
var frameNo = iData[0];
var fileNo = iData[1];
var modelNo = iData[2];
var firstNo = iData[3];
var lastNo = iData[4];
var isAnimationRunning = (frameNo <= -2);
var animationDirection = (firstNo < 0 ? -1 : 1);
var currentDirection = (lastNo < 0 ? -1 : 1);
if (doCallback) {
data =  Clazz.newArray(-1, [this.htmlName, Integer.$valueOf(Math.max(frameNo, -2 - frameNo)), Integer.$valueOf(fileNo), Integer.$valueOf(modelNo), Integer.$valueOf(Math.abs(firstNo)), Integer.$valueOf(Math.abs(lastNo)), Integer.$valueOf(isAnimationRunning ? 1 : 0), Integer.$valueOf(animationDirection), Integer.$valueOf(currentDirection), data[2], data[3]]);
}break;
case J.c.CBK.ECHO:
var isPrivate = (data.length == 2);
var isScriptQueued = (isPrivate || (data[2]).intValue() == 1);
if (!doCallback) {
if (isScriptQueued) toConsole = true;
doCallback = (!isPrivate && (callback = this.b$.get((type = J.c.CBK.MESSAGE))) != null);
}if (!toConsole) this.output(strInfo);
break;
case J.c.CBK.LOADSTRUCT:
var errorMsg = data[4];
if (errorMsg != null) {
errorMsg = (errorMsg.indexOf("NOTE:") >= 0 ? "" : J.i18n.GT.$("File Error:")) + errorMsg;
this.doShowStatus(errorMsg);
this.notifyCallback(J.c.CBK.MESSAGE,  Clazz.newArray(-1, ["", errorMsg]));
return;
}break;
case J.c.CBK.MEASURE:
if (!doCallback) doCallback = ((callback = this.b$.get((type = J.c.CBK.MESSAGE))) != null);
var status = data[3];
if (status.indexOf("Picked") >= 0 || status.indexOf("Sequence") >= 0) {
this.doShowStatus(strInfo);
toConsole = true;
} else if (status.indexOf("Completed") >= 0) {
strInfo = status + ": " + strInfo;
toConsole = true;
}break;
case J.c.CBK.MESSAGE:
toConsole = !doCallback;
doCallback = new Boolean (doCallback & (strInfo != null)).valueOf();
if (!toConsole) this.output(strInfo);
break;
case J.c.CBK.PICK:
this.doShowStatus(strInfo);
toConsole = true;
break;
case J.c.CBK.SCRIPT:
var msWalltime = (data[3]).intValue();
if (msWalltime > 0) {
} else if (!doCallback) {
doCallback = ((callback = this.b$.get((type = J.c.CBK.MESSAGE))) != null);
}this.output(strInfo);
this.doShowStatus(strInfo);
break;
case J.c.CBK.SYNC:
this.sendScript(strInfo, data[2], true, doCallback);
return;
}
if (toConsole) {
var appConsole = this.viewer.getProperty("DATA_API", "getAppConsole", null);
if (appConsole != null) {
appConsole.notifyCallback(type, data);
this.output(strInfo);
}}if (!doCallback || !this.mayScript) return;
try {
this.doSendCallback(type, callback, data, strInfo);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (!this.haveNotifiedError) if (JU.Logger.debugging) {
JU.Logger.debug(type.name() + "Callback call error to " + callback + ": " + e);
}this.haveNotifiedError = true;
} else {
throw e;
}
}
}, "J.c.CBK,~A");
Clazz.defineMethod(c$, "sendScript", 
function(script, appletName, isSync, doCallback){
if (!JU.GenericApplet.isJS) return "";
if (doCallback) {
script = this.notifySync(script, appletName);
if (script == null || script.length == 0 || script.equals("0")) return "";
}var apps =  new JU.Lst();
JU.GenericApplet.findApplets(appletName, this.syncId, this.fullName, apps);
var nApplets = apps.size();
if (nApplets == 0) {
if (!doCallback && !appletName.equals("*")) JU.Logger.error(this.fullName + " couldn't find applet " + appletName);
return "";
}var sb = (isSync ? null :  new JU.SB());
var getGraphics = (isSync && script.equals("GET_GRAPHICS"));
var setNoGraphics = (isSync && script.equals("SET_GRAPHICS_OFF"));
if (getGraphics) this.viewer.setStereo(false, (this.gRight = null));
for (var i = 0; i < nApplets; i++) {
var theApplet = apps.get(i);
var app = JU.GenericApplet.htRegistry.get(theApplet);
var isScriptable = true;
if (JU.Logger.debugging) JU.Logger.debug(this.fullName + " sending to " + theApplet + ": " + script);
try {
if (isScriptable && (getGraphics || setNoGraphics)) {
this.viewer.setStereo(this.isStereoSlave = getGraphics, this.gRight = (app).setStereoGraphics(getGraphics));
return "";
}if (isSync) app.syncScript(script);
 else if (isScriptable) sb.append((app).scriptWait(script, "output")).append("\n");
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
var msg = this.htmlName + " couldn't send to " + theApplet + ": " + script + ": " + e;
JU.Logger.error(msg);
if (!isSync) sb.append(msg);
} else {
throw e;
}
}
}
return (isSync ? "" : sb.toString());
}, "~S,~S,~B,~B");
Clazz.defineMethod(c$, "notifySync", 
function(info, appletName){
var syncCallback = this.b$.get(J.c.CBK.SYNC);
if (!this.mayScript || syncCallback == null) return info;
try {
return this.doSendCallback(J.c.CBK.SYNC, syncCallback,  Clazz.newArray(-1, [this.fullName, info, appletName]), null);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
if (!this.haveNotifiedError) if (JU.Logger.debugging) {
JU.Logger.debug("syncCallback call error to " + syncCallback + ": " + e);
}this.haveNotifiedError = true;
} else {
throw e;
}
}
return info;
}, "~S,~S");
Clazz.overrideMethod(c$, "eval", 
function(strEval){
var pt = strEval.indexOf("\1");
if (pt >= 0) return this.sendScript(strEval.substring(pt + 1), strEval.substring(0, pt), false, false);
if (!this.haveDocumentAccess) return "NO EVAL ALLOWED";
if (this.b$.get(J.c.CBK.EVAL) != null) {
this.notifyCallback(J.c.CBK.EVAL,  Clazz.newArray(-1, [null, strEval]));
return "";
}return this.doEval(strEval);
}, "~S");
Clazz.overrideMethod(c$, "createImage", 
function(fileName, type, text_or_bytes, quality){
return null;
}, "~S,~S,~O,~N");
Clazz.overrideMethod(c$, "getRegistryInfo", 
function(){
JU.GenericApplet.checkIn(null, null);
return JU.GenericApplet.htRegistry;
});
Clazz.overrideMethod(c$, "showUrl", 
function(urlString){
if (JU.Logger.debugging) JU.Logger.debug("showUrl(" + urlString + ")");
if (urlString != null && urlString.length > 0) try {
this.doShowDocument( new java.net.URL(Clazz.castNullAs("java.net.URL"), urlString, null));
} catch (mue) {
if (Clazz.exceptionOf(mue,"java.net.MalformedURLException")){
this.consoleMessage("Malformed URL:" + urlString);
} else {
throw mue;
}
}
}, "~S");
Clazz.overrideMethod(c$, "resizeInnerPanel", 
function(data){
var dims =  Clazz.newFloatArray (2, 0);
JU.Parser.parseStringInfestedFloatArray(data, null, dims);
this.resizeDisplay(Clazz.floatToInt(dims[0]), Clazz.floatToInt(dims[1]));
return  Clazz.newIntArray(-1, [Clazz.floatToInt(dims[0]), Clazz.floatToInt(dims[1])]);
}, "~S");
c$.checkIn = Clazz.defineMethod(c$, "checkIn", 
function(name, applet){
if (name != null) {
JU.Logger.info("AppletRegistry.checkIn(" + name + ")");
JU.GenericApplet.htRegistry.put(name, applet);
}if (JU.Logger.debugging) {
for (var entry, $entry = JU.GenericApplet.htRegistry.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
var theApplet = entry.getKey();
JU.Logger.debug(theApplet + " " + entry.getValue());
}
}}, "~S,~O");
c$.checkOut = Clazz.defineMethod(c$, "checkOut", 
function(name){
JU.GenericApplet.htRegistry.remove(name);
}, "~S");
c$.findApplets = Clazz.defineMethod(c$, "findApplets", 
function(appletName, mySyncId, excludeName, apps){
if (appletName != null && appletName.indexOf(",") >= 0) {
var names = JU.PT.split(appletName, ",");
for (var i = 0; i < names.length; i++) JU.GenericApplet.findApplets(names[i], mySyncId, excludeName, apps);

return;
}var ext = "__" + mySyncId + "__";
if (appletName == null || appletName.equals("*") || appletName.equals(">")) {
for (var appletName2, $appletName2 = JU.GenericApplet.htRegistry.keySet().iterator (); $appletName2.hasNext()&& ((appletName2 = $appletName2.next ()) || true);) {
if (!appletName2.equals(excludeName) && appletName2.indexOf(ext) > 0) {
apps.addLast(appletName2);
}}
return;
}if (excludeName.indexOf("_object") >= 0 && appletName.indexOf("_object") < 0) appletName += "_object";
if (appletName.indexOf("__") < 0) appletName += ext;
if (!JU.GenericApplet.htRegistry.containsKey(appletName)) appletName = "jmolApplet" + appletName;
if (!appletName.equals(excludeName) && JU.GenericApplet.htRegistry.containsKey(appletName)) {
apps.addLast(appletName);
}}, "~S,~S,~S,JU.Lst");
Clazz.overrideMethod(c$, "notifyAudioEnded", 
function(htParams){
this.viewer.sm.notifyAudioStatus(htParams);
}, "~O");
Clazz.defineMethod(c$, "setJSOptions", 
function(vwrOptions){
this.htParams =  new java.util.Hashtable();
if (vwrOptions == null) vwrOptions =  new java.util.Hashtable();
this.vwrOptions = vwrOptions;
for (var entry, $entry = vwrOptions.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) this.htParams.put(entry.getKey().toLowerCase(), entry.getValue());

this.documentBase = "" + vwrOptions.get("documentBase");
this.codeBase = "" + vwrOptions.get("codePath");
}, "java.util.Map");
Clazz.defineMethod(c$, "initOptions", 
function(){
this.vwrOptions.remove("debug");
this.vwrOptions.put("fullName", this.fullName);
this.haveDocumentAccess = "true".equalsIgnoreCase("" + this.getValue("allowjavascript", "true"));
this.mayScript = true;
});
Clazz.defineMethod(c$, "getJmolParameter", 
function(paramName){
var o = this.htParams.get(paramName.toLowerCase());
return (o == null ? null : "" + o);
}, "~S");
Clazz.overrideMethod(c$, "functionXY", 
function(functionName, nX, nY){
var fxy =  Clazz.newFloatArray (Math.abs(nX), Math.abs(nY), 0);
if (!this.mayScript || !this.haveDocumentAccess || nX == 0 || nY == 0) return fxy;
try {
if (nX > 0 && nY > 0) {
for (var i = 0; i < nX; i++) for (var j = 0; j < nY; j++) {
{
fxy[i][j] = window.eval(functionName)(this.htmlName, i, j);
}}

} else if (nY > 0) {
var data;
{
data = window.eval(functionName)(this.htmlName, nX, nY);
}nX = Math.abs(nX);
var fdata =  Clazz.newFloatArray (nX * nY, 0);
JU.Parser.parseStringInfestedFloatArray(data, null, fdata);
for (var i = 0, ipt = 0; i < nX; i++) {
for (var j = 0; j < nY; j++, ipt++) {
fxy[i][j] = fdata[ipt];
}
}
} else {
{
data = window.eval(functionName)(this.htmlName, nX, nY, fxy);
}}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.error("Exception " + e + " with nX, nY: " + nX + " " + nY);
} else {
throw e;
}
}
return fxy;
}, "~S,~N,~N");
Clazz.overrideMethod(c$, "functionXYZ", 
function(functionName, nX, nY, nZ){
var fxyz =  Clazz.newFloatArray (Math.abs(nX), Math.abs(nY), Math.abs(nZ), 0);
if (!this.mayScript || !this.haveDocumentAccess || nX == 0 || nY == 0 || nZ == 0) return fxyz;
try {
{
window.eval(functionName)(this.htmlName, nX, nY, nZ, fxyz);
}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.error("Exception " + e + " for " + functionName + " with nX, nY, nZ: " + nX + " " + nY + " " + nZ);
} else {
throw e;
}
}
return fxyz;
}, "~S,~N,~N,~N");
Clazz.defineMethod(c$, "doShowDocument", 
function(url){
var surl = JU.PT.split(url.toString(), "?POST?");
if (surl.length == 1) {
{
window.open(surl[0]);
}return;
}var f = "<form id=f method=POST action='" + surl[0] + "'>";
f += "<input type='hidden' name='name' value='nmr-1h-prediction' id='name'>";
f += "<input type='submit' value='working...'>";
var fields = surl[1].$plit("&");
for (var i = 0; i < fields.length; i++) {
var field = fields[i];
var pt = field.indexOf("=");
var name = field.substring(0, pt);
var value = field.substring(pt);
if (value.indexOf("\n") >= 0) {
f += "<textarea style='display:none' name=" + name + ">" + value + "</textarea>";
} else {
f += "<input type=hidden name=" + name + " value=\"" + value + "\">";
}}
f += "</form>";
{
var w=window.open("");w.document.write(f);w.document.getElementById("f").submit();
}}, "java.net.URL");
Clazz.defineMethod(c$, "doSendCallback", 
function(type, callback, data, strInfo){
var isString = ((typeof(callback)=='string'));
if (callback == null || isString && (callback).length == 0) {
} else {
if (isString && "alert".equals(callback)) {
{
alert(strInfo);
}return "";
}var tokens = (isString ? JU.PT.split((callback), ".") : null);
try {
{
var o;
if (isString) {
o = window[tokens[0]];
for (var i = 1; i < tokens.length; i++)
o = o[tokens[i]];
} else {
o = callback;
}
for (var i = 0; i < data.length; i++) {
data[i] && data[i].booleanValue && (data[i] = data[i].booleanValue());
data[i] instanceof Number && (data[i] = +data[i]);
}
return o.apply(this,data)
}} catch (e) {
System.out.println("callback " + type + " failed " + e);
}
}return "";
}, "J.c.CBK,~O,~A,~S");
Clazz.defineMethod(c$, "doEval", 
function(strEval){
try {
{
return window.eval(strEval);
}} catch (e) {
JU.Logger.error("# error evaluating " + strEval + ":" + e.toString());
}
return "";
}, "~S");
Clazz.defineMethod(c$, "doShowStatus", 
function(message){
try {
System.out.println(message);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
}, "~S");
Clazz.defineMethod(c$, "getGLmolView", 
function(){
return this.viewer.getGLmolView();
});
Clazz.defineMethod(c$, "openFile", 
function(fileName){
return this.viewer.openFile(fileName);
}, "~S");
Clazz.overrideMethod(c$, "cacheFileByName", 
function(fileName, isAdd){
return this.viewer.cacheFileByName(fileName, isAdd);
}, "~S,~B");
Clazz.overrideMethod(c$, "cachePut", 
function(key, data){
this.viewer.cachePut(key, data);
}, "~S,~O");
Clazz.overrideMethod(c$, "getFullName", 
function(){
return this.fullName;
});
c$.htRegistry = null;
c$.isJS = false;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
