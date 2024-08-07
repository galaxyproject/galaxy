Clazz.declarePackage("JS");
Clazz.load(["J.api.JmolScriptManager", "JU.Lst"], "JS.ScriptManager", ["java.util.Hashtable", "JU.AU", "$.PT", "$.Rdr", "$.SB", "J.api.Interface", "J.i18n.GT", "JS.ScriptQueueThread", "JU.Elements", "$.Logger", "JV.FileManager"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.eval = null;
this.evalTemp = null;
this.queueThreads = null;
this.scriptQueueRunning = null;
this.commandWatcherThread = null;
this.scriptQueue = null;
this.useCommandWatcherThread = false;
this.scriptIndex = 0;
this.$isScriptQueued = true;
Clazz.instantialize(this, arguments);}, JS, "ScriptManager", null, J.api.JmolScriptManager);
Clazz.prepareFields (c$, function(){
this.queueThreads =  new Array(2);
this.scriptQueueRunning =  Clazz.newBooleanArray(2, false);
this.scriptQueue =  new JU.Lst();
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.overrideMethod(c$, "getScriptQueue", 
function(){
return this.scriptQueue;
});
Clazz.overrideMethod(c$, "isScriptQueued", 
function(){
return this.$isScriptQueued;
});
Clazz.overrideMethod(c$, "setViewer", 
function(vwr){
this.vwr = vwr;
this.eval = this.newScriptEvaluator();
this.eval.setCompiler();
return this.eval;
}, "JV.Viewer");
Clazz.defineMethod(c$, "newScriptEvaluator", 
function(){
return (J.api.Interface.getInterface("JS.ScriptEval", this.vwr, "setOptions")).setViewer(this.vwr);
});
Clazz.overrideMethod(c$, "clear", 
function(isAll){
if (!isAll) {
this.evalTemp = null;
return;
}this.startCommandWatcher(false);
this.interruptQueueThreads();
}, "~B");
Clazz.defineMethod(c$, "addScript", 
function(strScript, params, isQuiet){
return this.addScr("String", strScript, params, "", isQuiet);
}, "~S,~A,~B");
Clazz.defineMethod(c$, "addScr", 
function(returnType, strScript, params, statusList, isQuiet){
{
this.useCommandWatcherThread = false;
}if (!this.vwr.g.useScriptQueue) {
this.clearQueue();
this.vwr.haltScriptExecution();
}if (this.commandWatcherThread == null && this.useCommandWatcherThread) this.startCommandWatcher(true);
if (this.commandWatcherThread != null && strScript.indexOf("/*SPLIT*/") >= 0) {
var scripts = JU.PT.split(strScript, "/*SPLIT*/");
for (var i = 0; i < scripts.length; i++) this.addScr(returnType, scripts[i], params, statusList, isQuiet);

return "split into " + scripts.length + " sections for processing";
}var useCommandThread = (this.commandWatcherThread != null && (strScript.indexOf("javascript") < 0 || strScript.indexOf("#javascript ") >= 0));
var scriptItem =  new JU.Lst();
scriptItem.addLast(strScript);
scriptItem.addLast(statusList);
scriptItem.addLast(returnType);
scriptItem.addLast(isQuiet ? Boolean.TRUE : Boolean.FALSE);
scriptItem.addLast(Integer.$valueOf(useCommandThread ? -1 : 1));
scriptItem.addLast(params);
this.scriptQueue.addLast(scriptItem);
this.startScriptQueue(false);
return "pending";
}, "~S,~S,~A,~S,~B");
Clazz.overrideMethod(c$, "clearQueue", 
function(){
this.scriptQueue.clear();
});
Clazz.overrideMethod(c$, "waitForQueue", 
function(){
if (this.vwr.isSingleThreaded) return;
var n = 0;
while (this.isQueueProcessing()) {
try {
Thread.sleep(100);
if (((n++) % 10) == 0) if (JU.Logger.debugging) {
JU.Logger.debug("...scriptManager waiting for queue: " + this.scriptQueue.size() + " thread=" + Thread.currentThread().getName());
}} catch (e) {
if (Clazz.exceptionOf(e,"InterruptedException")){
} else {
throw e;
}
}
}
});
Clazz.overrideMethod(c$, "isQueueProcessing", 
function(){
return this.queueThreads[0] != null || this.queueThreads[1] != null;
});
Clazz.defineMethod(c$, "flushQueue", 
function(command){
for (var i = this.scriptQueue.size(); --i >= 0; ) {
var strScript = (this.scriptQueue.get(i).get(0));
if (strScript.indexOf(command) == 0) {
this.scriptQueue.removeItemAt(i);
if (JU.Logger.debugging) JU.Logger.debug(this.scriptQueue.size() + " scripts; removed: " + strScript);
}}
}, "~S");
Clazz.defineMethod(c$, "startScriptQueue", 
function(startedByCommandWatcher){
var pt = (startedByCommandWatcher ? 1 : 0);
if (this.scriptQueueRunning[pt]) return;
this.scriptQueueRunning[pt] = true;
this.queueThreads[pt] =  new JS.ScriptQueueThread(this, this.vwr, startedByCommandWatcher, pt);
this.queueThreads[pt].start();
}, "~B");
Clazz.overrideMethod(c$, "getScriptItem", 
function(watching, isByCommandWatcher){
if (this.vwr.isSingleThreaded && this.vwr.queueOnHold) return null;
var scriptItem = this.scriptQueue.get(0);
var flag = ((scriptItem.get(4)).intValue());
var isOK = (watching ? flag < 0 : isByCommandWatcher ? flag == 0 : flag == 1);
return (isOK ? scriptItem : null);
}, "~B,~B");
Clazz.overrideMethod(c$, "startCommandWatcher", 
function(isStart){
this.useCommandWatcherThread = isStart;
if (isStart) {
if (this.commandWatcherThread != null) return;
this.commandWatcherThread = J.api.Interface.getInterface("JS.CommandWatcherThread", this.vwr, "setOptions");
this.commandWatcherThread.setManager(this, this.vwr, null);
this.commandWatcherThread.start();
} else {
if (this.commandWatcherThread == null) return;
this.clearCommandWatcherThread();
}if (JU.Logger.debugging) {
JU.Logger.debug("command watcher " + (isStart ? "started" : "stopped") + this.commandWatcherThread);
}}, "~B");
Clazz.defineMethod(c$, "interruptQueueThreads", 
function(){
for (var i = 0; i < this.queueThreads.length; i++) {
if (this.queueThreads[i] != null) this.queueThreads[i].interrupt();
}
});
Clazz.defineMethod(c$, "clearCommandWatcherThread", 
function(){
if (this.commandWatcherThread == null) return;
this.commandWatcherThread.interrupt();
this.commandWatcherThread = null;
});
Clazz.overrideMethod(c$, "queueThreadFinished", 
function(pt){
if (pt < 0) {
this.queueThreadFinished(0);
this.queueThreadFinished(1);
return;
}if (this.queueThreads[pt] == null) return;
this.queueThreads[pt].interrupt();
this.scriptQueueRunning[pt] = false;
this.queueThreads[pt] = null;
this.vwr.setSyncDriver(4);
this.vwr.queueOnHold = false;
}, "~N");
Clazz.defineMethod(c$, "runScriptNow", 
function(){
if (this.scriptQueue.size() > 0) {
var scriptItem = this.getScriptItem(true, true);
if (scriptItem != null) {
scriptItem.set(4, Integer.$valueOf(0));
this.startScriptQueue(true);
}}});
Clazz.overrideMethod(c$, "evalFile", 
function(strFilename){
return this.evalFileArgs(strFilename, null);
}, "~S");
Clazz.overrideMethod(c$, "evalFileArgs", 
function(strFilename, args){
var ptWait = strFilename.indexOf(" -noqueue");
if (ptWait >= 0) {
return this.evalStringWaitStatusQueued("String", "script " + JU.PT.esc(strFilename.substring(0, ptWait)), "", false, false);
}return this.addScript("script " + JU.PT.esc(strFilename) + (args == null ? "" : "(" + args + ")"), null, false);
}, "~S,~S");
Clazz.overrideMethod(c$, "evalStringWaitStatusQueued", 
function(returnType, strScript, statusList, isQuiet, isQueued){
return this.evalStringWaitParamsStatusQueued(returnType, strScript, null, statusList, isQuiet, isQueued);
}, "~S,~S,~S,~B,~B");
Clazz.defineMethod(c$, "evalStringWaitParamsStatusQueued", 
function(returnType, strScript, params, statusList, isQuiet, isQueued){
if (strScript == null) return null;
var str = this.checkScriptExecution(strScript, false);
if (str != null) return str;
if (this.vwr.checkConsoleScript(strScript)) return null;
var outputBuffer = (statusList == null || statusList.equals("output") ?  new JU.SB() : null);
var oldStatusList = this.vwr.sm.statusList;
this.vwr.getStatusChanged(statusList);
if (this.vwr.isSyntaxCheck) JU.Logger.info("--checking script:\n" + this.eval.getScript() + "\n----\n");
var historyDisabled = (strScript.indexOf(")") == 0);
if (historyDisabled) strScript = strScript.substring(1);
historyDisabled = historyDisabled || !isQueued;
this.vwr.setErrorMessage(null, null);
var eval = (isQueued && params == null ? this.eval : this.newScriptEvaluator());
var isOK = eval.compileScriptString(strScript, isQuiet);
var strErrorMessage = eval.getErrorMessage();
var strErrorMessageUntranslated = eval.getErrorMessageUntranslated();
this.vwr.setErrorMessage(strErrorMessage, strErrorMessageUntranslated);
this.vwr.refresh(7, "script complete");
if (isOK) {
this.$isScriptQueued = isQueued;
if (!isQuiet) this.vwr.setScriptStatus(null, strScript, -2 - (++this.scriptIndex), null);
eval.evaluateCompiledScript(params, this.vwr.isSyntaxCheck, this.vwr.isSyntaxAndFileCheck, historyDisabled, this.vwr.listCommands, outputBuffer, isQueued);
} else {
this.vwr.scriptStatus(strErrorMessage);
this.vwr.setScriptStatus("Jmol script terminated", strErrorMessage, 1, strErrorMessageUntranslated);
if (eval.isStateScript()) JS.ScriptManager.setStateScriptVersion(this.vwr, null);
}if (strErrorMessage != null && this.vwr.autoExit) this.vwr.exitJmol();
if (this.vwr.isSyntaxCheck) {
if (strErrorMessage == null) JU.Logger.info("--script check ok");
 else JU.Logger.error("--script check error\n" + strErrorMessageUntranslated);
JU.Logger.info("(use 'exit' to stop checking)");
}this.$isScriptQueued = true;
if (returnType.equalsIgnoreCase("String")) return strErrorMessageUntranslated;
if (outputBuffer != null) return (strErrorMessageUntranslated == null ? outputBuffer.toString() : strErrorMessageUntranslated);
var info = this.vwr.getProperty(returnType, "jmolStatus", statusList);
this.vwr.getStatusChanged(oldStatusList);
return info;
}, "~S,~S,~A,~S,~B,~B");
Clazz.defineMethod(c$, "checkScriptExecution", 
function(strScript, isInsert){
var str = strScript;
var pt = str.indexOf("; ## GUI ##");
if (pt >= 0) str = str.substring(0, pt);
if ((pt = str.indexOf("\u0001##")) >= 0) str = str.substring(0, pt);
if (this.checkResume(str)) return "script processing resumed";
if (this.checkStepping(str)) return "script processing stepped";
if (this.checkHalt(str, isInsert)) return "script execution halted";
this.vwr.wasmInchiHack(strScript);
return null;
}, "~S,~B");
Clazz.defineMethod(c$, "checkResume", 
function(str){
if (str.equalsIgnoreCase("resume")) {
this.vwr.scriptStatusMsg("", "execution resumed");
this.eval.resumePausedExecution();
return true;
}return false;
}, "~S");
Clazz.defineMethod(c$, "checkStepping", 
function(str){
if (str.equalsIgnoreCase("step")) {
this.eval.stepPausedExecution();
return true;
}if (str.equalsIgnoreCase("?")) {
this.vwr.scriptStatus(this.eval.getNextStatement());
return true;
}return false;
}, "~S");
Clazz.overrideMethod(c$, "evalStringQuietSync", 
function(strScript, isQuiet, allowSyncScript){
return this.evalStringParamsQuietSync(strScript, null, isQuiet, allowSyncScript);
}, "~S,~B,~B");
Clazz.defineMethod(c$, "evalStringParamsQuietSync", 
function(strScript, params, isQuiet, allowSyncScript){
if (allowSyncScript && this.vwr.sm.syncingScripts && strScript.indexOf("#NOSYNC;") < 0) this.vwr.syncScript(strScript + " #NOSYNC;", null, 0);
if (this.eval.isPaused() && strScript.charAt(0) != '!') strScript = '!' + JU.PT.trim(strScript, "\n\r\t ");
var isInsert = (params == null && strScript.length > 0 && strScript.charAt(0) == '!');
if (isInsert) strScript = strScript.substring(1);
var msg = this.checkScriptExecution(strScript, isInsert);
if (msg != null) return msg;
if (this.vwr.isScriptExecuting() && (isInsert || this.eval.isPaused())) {
this.vwr.setInsertedCommand(strScript);
if (strScript.indexOf("moveto ") == 0) this.flushQueue("moveto ");
return "!" + strScript;
}this.vwr.setInsertedCommand("");
if (isQuiet && params == null) strScript += "\u0001## EDITOR_IGNORE ##";
return this.addScript(strScript, params, isQuiet && !this.vwr.getBoolean(603979879));
}, "~S,~A,~B,~B");
Clazz.overrideMethod(c$, "checkHalt", 
function(str, isInsert){
if (str.equalsIgnoreCase("pause") || str.equalsIgnoreCase("pause\u0001##")) {
this.vwr.pauseScriptExecution();
if (this.vwr.scriptEditorVisible) this.vwr.setScriptStatus("", "paused -- type RESUME to continue", 0, null);
return true;
}if (str.equalsIgnoreCase("menu")) {
this.vwr.getProperty("DATA_API", "getPopupMenu", "\0");
return true;
}str = str.toLowerCase();
var exitScript = false;
var haltType = null;
if (str.startsWith("exit")) {
this.vwr.haltScriptExecution();
this.vwr.clearScriptQueue();
this.vwr.clearTimeouts();
exitScript = str.equals(haltType = "exit");
} else if (str.startsWith("quit")) {
this.vwr.haltScriptExecution();
exitScript = str.equals(haltType = "quit");
}if (haltType == null) return false;
if (isInsert) {
this.vwr.clearThreads();
this.vwr.queueOnHold = false;
}if (isInsert || this.vwr.g.waitForMoveTo) {
this.vwr.tm.stopMotion();
}JU.Logger.info(this.vwr.isSyntaxCheck ? haltType + " -- stops script checking" : (isInsert ? "!" : "") + haltType + " received");
this.vwr.isSyntaxCheck = false;
return exitScript;
}, "~S,~B");
Clazz.overrideMethod(c$, "getAtomBitSetEval", 
function(eval, atomExpression){
if (eval == null) {
eval = this.evalTemp;
if (eval == null) eval = this.evalTemp = this.newScriptEvaluator();
}return this.vwr.slm.excludeAtoms(eval.getAtomBitSet(atomExpression), false);
}, "J.api.JmolScriptEvaluator,~O");
Clazz.overrideMethod(c$, "scriptCheckRet", 
function(strScript, returnContext){
if (strScript.indexOf(")") == 0 || strScript.indexOf("!") == 0) strScript = strScript.substring(1);
strScript = this.vwr.wasmInchiHack(strScript);
var sc = this.newScriptEvaluator().checkScriptSilent(strScript);
return (returnContext || sc.errorMessage == null ? sc : sc.errorMessage);
}, "~S,~B");
Clazz.overrideMethod(c$, "openFileAsync", 
function(fname, flags, type){
var scriptOnly = ((flags & 32) != 0);
if (!scriptOnly && (flags & 64) != 0 && JV.FileManager.isEmbeddable(fname)) this.checkResize(fname);
var noScript = ((flags & 2) != 0);
var noAutoPlay = ((flags & 8) != 0);
var cmd = null;
fname = fname.trim().$replace('\\', '/');
var isCached = fname.startsWith("cache://");
if (this.vwr.isApplet && fname.indexOf("://") < 0) fname = "file://" + (fname.startsWith("/") ? "" : "/") + fname;
try {
if (scriptOnly) {
cmd = "script " + JU.PT.esc(fname);
return;
}if (fname.endsWith(".pse")) {
cmd = (isCached ? "" : "zap;") + "load SYNC " + JU.PT.esc(fname) + (this.vwr.isApplet ? "" : " filter 'DORESIZE'");
return;
}if (fname.endsWith("jvxl")) {
cmd = "isosurface ";
} else if (!fname.toLowerCase().endsWith(".spt")) {
if (type == null) type = this.getDragDropFileTypeName(fname);
 else if (!type.endsWith("::")) type += "::";
if (type == null) {
try {
var bis = this.vwr.getBufferedInputStream(fname);
type = JV.FileManager.determineSurfaceFileType(JU.Rdr.getBufferedReader(bis, "ISO-8859-1"));
if (type == null) {
cmd = "script " + JU.PT.esc(fname);
return;
}} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
return;
} else {
throw e;
}
}
if (type === "MENU") {
cmd = "load MENU " + JU.PT.esc(fname);
} else {
cmd = "if (_filetype == 'Pdb') { isosurface sigma 1.0 within 2.0 {*} " + JU.PT.esc(fname) + " mesh nofill }; else; { isosurface " + JU.PT.esc(fname) + "}";
}return;
}if (type.equals("spt::")) {
cmd = "script " + JU.PT.esc((fname.startsWith("spt::") ? fname.substring(5) : fname));
return;
}if (type.equals("dssr")) {
cmd = "model {visible} property dssr ";
} else if (type.equals("Jmol")) {
cmd = "script ";
} else if (type.equals("Cube")) {
cmd = "isosurface sign red blue ";
} else if (!type.equals("spt")) {
if (flags == 16) {
flags = 1;
switch (this.vwr.ms.ac == 0 ? 0 : this.vwr.confirm(J.i18n.GT.$("Would you like to replace the current model with the selected model?"), J.i18n.GT.$("Would you like to append?"))) {
case 2:
return;
case 0:
break;
default:
flags |= 4;
break;
}
}var isAppend = ((flags & 4) != 0);
var pdbCartoons = ((flags & 1) != 0 && !isAppend);
if (type.endsWith("::")) {
var pt = type.indexOf("|");
if (pt >= 0) {
fname += type.substring(pt, type.length - 2);
type = "";
}fname = type + fname;
}cmd = this.vwr.g.defaultDropScript;
cmd = JU.PT.rep(cmd, "%FILE", fname);
cmd = JU.PT.rep(cmd, "%ALLOWCARTOONS", "" + pdbCartoons);
if (cmd.toLowerCase().startsWith("zap") && (isCached || isAppend)) cmd = cmd.substring(3);
if (isAppend) {
cmd = JU.PT.rep(cmd, "load SYNC", "load append");
}return;
}}if (cmd == null && !noScript && this.vwr.scriptEditorVisible) this.vwr.showEditor( Clazz.newArray(-1, [fname, this.vwr.getFileAsString3(fname, true, null)]));
 else cmd = (cmd == null ? "script " : cmd) + JU.PT.esc(fname);
} finally {
if (cmd != null) this.vwr.evalString(cmd + (noAutoPlay ? "#!NOAUTOPLAY" : ""));
}
}, "~S,~N,~S");
Clazz.defineMethod(c$, "checkResize", 
function(fname){
try {
var data = this.vwr.fm.getEmbeddedFileState(fname, false, "state.spt");
if (data.indexOf("preferredWidthHeight") >= 0) this.vwr.sm.resizeInnerPanelString(data);
} catch (e) {
}
}, "~S");
Clazz.defineMethod(c$, "getDragDropFileTypeName", 
function(fileName){
var pt = fileName.indexOf("::");
if (pt >= 0) return fileName.substring(0, pt + 2);
if (fileName.startsWith("=")) return "pdb";
if (fileName.endsWith(".dssr")) return "dssr";
var br = this.vwr.fm.getUnzippedReaderOrStreamFromName(fileName, null, true, false, true, true, null);
var modelType = null;
if (this.vwr.fm.isZipStream(br)) {
var zipDirectory = this.vwr.getZipDirectoryAsString(fileName);
if (zipDirectory.indexOf("JmolManifest") >= 0) return "Jmol";
modelType = this.vwr.getModelAdapter().getFileTypeName(JU.Rdr.getBR(zipDirectory));
} else if (Clazz.instanceOf(br,"java.io.BufferedReader") || Clazz.instanceOf(br,"java.io.BufferedInputStream")) {
modelType = this.vwr.getModelAdapter().getFileTypeName(br);
}if (modelType != null) return modelType + "::";
if (JU.AU.isAS(br)) {
return (br)[0];
}return null;
}, "~S");
c$.setStateScriptVersion = Clazz.defineMethod(c$, "setStateScriptVersion", 
function(vwr, version){
if (version != null) {
JS.ScriptManager.prevCovalentVersion = JU.Elements.bondingVersion;
var tokens = JU.PT.getTokens(version.$replace('.', ' ').$replace('_', ' '));
try {
var main = JU.PT.parseInt(tokens[0]);
var sub = JU.PT.parseInt(tokens[1]);
var minor = JU.PT.parseInt(tokens[2]);
if (minor == -2147483648) minor = 0;
if (main != -2147483648 && sub != -2147483648) {
var ver = vwr.stateScriptVersionInt = main * 10000 + sub * 100 + minor;
vwr.setBooleanProperty("legacyautobonding", (ver < 110924));
vwr.setBooleanProperty("legacyHAddition", (ver < 130117));
if (!vwr.getBoolean(603979831)) vwr.setBooleanProperty("legacyjavafloat", (ver < 140206 || ver >= 140300 && ver < 140306));
vwr.setIntProperty("bondingVersion", ver < 140111 ? 0 : 1);
return;
}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
}vwr.setIntProperty("bondingVersion", JS.ScriptManager.prevCovalentVersion);
vwr.setBooleanProperty("legacyautobonding", false);
vwr.setBooleanProperty("legacyHAddition", false);
vwr.stateScriptVersionInt = 2147483647;
}, "JV.Viewer,~S");
Clazz.overrideMethod(c$, "addHydrogensInline", 
function(bsAtoms, vConnections, pts, htParams){
var iatom = (bsAtoms == null ? -1 : bsAtoms.nextSetBit(0));
if (htParams == null) htParams =  new java.util.Hashtable();
var modelIndex = (iatom < 0 ? this.vwr.am.cmi : this.vwr.ms.at[iatom].mi);
if (modelIndex < 0) modelIndex = this.vwr.ms.mc - 1;
htParams.put("appendToModelIndex", Integer.$valueOf(modelIndex));
var siteFixed = (htParams.containsKey("fixedSite"));
var bsA = this.vwr.getModelUndeletedAtomsBitSet(modelIndex);
var wasAppendNew = this.vwr.g.appendNew;
this.vwr.g.appendNew = false;
var atomno = 0;
for (var i = bsA.nextSetBit(0); i >= 0; i = bsA.nextSetBit(i + 1)) {
var an = this.vwr.ms.at[i].getAtomNumber();
if (an > atomno) atomno = an;
}
var sbConnect =  new JU.SB();
for (var i = 0, atomIndex = this.vwr.ms.ac; i < vConnections.size(); i++, atomIndex++) {
var a = vConnections.get(i);
if (a != null) sbConnect.append(";  connect 0 100 ").append("({" + (atomIndex) + "}) ").append("({" + a.i + "}) group;");
}
var sb =  new JU.SB();
sb.appendI(pts.length).append("\n").append("Viewer.AddHydrogens").append("#noautobond").append("\n");
var sym = htParams.get("element");
sym = (sym == null ? "H" : sym) + " ";
for (var i = 0; i < pts.length; i++) sb.append(sym).appendF(pts[i].x).append(" ").appendF(pts[i].y).append(" ").appendF(pts[i].z).append(" - - - - ").appendI(++atomno).appendC('\n');

var wasRefreshing = this.vwr.getBoolean(603979900);
this.vwr.setBooleanProperty("refreshing", false);
this.vwr.openStringInlineParamsAppend(sb.toString(), htParams, true);
if (sbConnect.length() > 0) this.vwr.runScript(sbConnect.toString());
this.vwr.setBooleanProperty("refreshing", wasRefreshing);
var bsB = this.vwr.getModelUndeletedAtomsBitSet(modelIndex);
bsB.andNot(bsA);
this.vwr.g.appendNew = wasAppendNew;
if (!siteFixed) {
bsA = this.vwr.ms.am[modelIndex].bsAsymmetricUnit;
if (bsA != null) bsA.or(bsB);
}return bsB;
}, "JU.BS,JU.Lst,~A,java.util.Map");
Clazz.overrideMethod(c$, "evalCallback", 
function(strScript, params, doWait){
if (doWait) {
this.evalStringWaitParamsStatusQueued("String", strScript, params, "", true, true);
} else {
this.evalStringParamsQuietSync(strScript, params, true, true);
}}, "~S,~A,~B");
Clazz.defineMethod(c$, "runScriptFromThread", 
function(scriptItem){
var script = scriptItem.get(0);
var statusList = scriptItem.get(1);
var returnType = scriptItem.get(2);
var isQuiet = (scriptItem.get(3)).booleanValue();
var params = scriptItem.get(5);
this.evalStringWaitParamsStatusQueued(returnType, script, params, statusList, isQuiet, true);
}, "JU.Lst");
c$.prevCovalentVersion = 0;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
