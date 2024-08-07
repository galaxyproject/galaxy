Clazz.declarePackage("JV");
Clazz.load(["JV.OutputManager"], "JV.OutputManagerAwt", ["java.io.File", "$.FileOutputStream", "java.util.Hashtable", "JU.Lst", "$.OC", "$.PT", "$.SB", "JU.Logger", "JV.Viewer"], function(){
var c$ = Clazz.declareType(JV, "OutputManagerAwt", JV.OutputManager);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JV.OutputManagerAwt, []);
});
Clazz.overrideMethod(c$, "getLogPath", 
function(fileName){
return (this.vwr.isApplet ? fileName : ( new java.io.File(fileName).getAbsolutePath()));
}, "~S");
Clazz.overrideMethod(c$, "clipImageOrPasteText", 
function(text){
var msg;
try {
if (text == null) {
var image = this.vwr.getScreenImage();
J.awt.AwtClipboard.setClipboard(image);
msg = "OK image to clipboard: " + (image.getWidth(null) * image.getHeight(null));
} else {
J.awt.AwtClipboard.setClipboard(text);
msg = "OK text to clipboard: " + text.length;
}} catch (er) {
if (Clazz.exceptionOf(er, Error)){
msg = this.vwr.getErrorMessage();
} else {
throw er;
}
} finally {
if (text == null) this.vwr.releaseScreenImage();
}
return msg;
}, "~S");
Clazz.overrideMethod(c$, "getClipboardText", 
function(){
return J.awt.AwtClipboard.getClipboardText();
});
Clazz.overrideMethod(c$, "openOutputChannel", 
function(privateKey, fileName, asWriter, asAppend){
var isLocal = JU.OC.isLocal(fileName);
if (asAppend && isLocal && fileName.indexOf("JmolLog_") < 0) asAppend = false;
return (fileName != null && !this.vwr.haveAccess(JV.Viewer.ACCESS.ALL) || !this.vwr.checkPrivateKey(privateKey) ? null : ( new JU.OC()).setParams(this.vwr.fm, fileName, asWriter, (isLocal ?  new java.io.FileOutputStream(fileName, asAppend) : null)));
}, "~N,~S,~B,~B");
Clazz.overrideMethod(c$, "createSceneSet", 
function(sceneFile, type, width, height){
var script0 = this.vwr.getFileAsString3(sceneFile, false, null);
if (script0 == null) return "no such file: " + sceneFile;
sceneFile = JU.PT.rep(sceneFile, ".spt", "");
var fileRoot = sceneFile;
var fileExt = type.toLowerCase();
var scenes = JU.PT.split(script0, "pause scene ");
var htScenes =  new java.util.Hashtable();
var list =  new JU.Lst();
var script = this.getSceneScript(scenes, htScenes, list);
if (JU.Logger.debugging) JU.Logger.debug(script);
script0 = JU.PT.rep(script0, "pause scene", "delay " + this.vwr.am.lastFrameDelay + " # scene");
var str =  Clazz.newArray(-1, [script0, script, null]);
this.vwr.stm.saveState("_scene0");
var nFiles = 0;
if (scenes[0] !== "") this.vwr.zap(true, true, false);
var iSceneLast = -1;
for (var i = 0; i < scenes.length - 1; i++) {
try {
var iScene = list.get(i).intValue();
if (iScene > iSceneLast) this.vwr.showString("Creating Scene " + iScene, false);
this.vwr.eval.runScript(scenes[i]);
if (iScene <= iSceneLast) continue;
iSceneLast = iScene;
str[2] = "all";
var fileName = fileRoot + "_scene_" + iScene + ".all." + fileExt;
var params =  new java.util.Hashtable();
params.put("fileName", fileName);
params.put("type", "PNGJ");
params.put("scripts", str);
params.put("width", Integer.$valueOf(width));
params.put("height", Integer.$valueOf(height));
var msg = this.handleOutputToFile(params, false);
str[0] = null;
str[2] = "min";
fileName = fileRoot + "_scene_" + iScene + ".min." + fileExt;
params.put("fileName", fileName);
params.put("width", Integer.$valueOf(Math.min(width, 200)));
params.put("height", Integer.$valueOf(Math.min(height, 200)));
msg += "\n" + this.handleOutputToFile(params, false);
this.vwr.showString(msg, false);
nFiles += 2;
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return "script error " + e.toString();
} else {
throw e;
}
}
}
try {
this.vwr.eval.runScript(this.vwr.stm.getSavedState("_scene0"));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
return "OK " + nFiles + " files created";
}, "~S,~S,~N,~N");
Clazz.defineMethod(c$, "getSceneScript", 
function(scenes, htScenes, list){
var iSceneLast = 0;
var iScene = 0;
var sceneScript =  new JU.SB().append("###scene.spt###").append(" Jmol ").append(JV.Viewer.getJmolVersion()).append("\n{\nsceneScripts={");
for (var i = 1; i < scenes.length; i++) {
scenes[i - 1] = JU.PT.trim(scenes[i - 1], "\t\n\r ");
var pt =  Clazz.newIntArray (1, 0);
iScene = JU.PT.parseIntNext(scenes[i], pt);
if (iScene == -2147483648) return "bad scene ID: " + iScene;
scenes[i] = scenes[i].substring(pt[0]);
list.addLast(Integer.$valueOf(iScene));
var key = iSceneLast + "-" + iScene;
htScenes.put(key, scenes[i - 1]);
if (i > 1) sceneScript.append(",");
sceneScript.appendC('\n').append(JU.PT.esc(key)).append(": ").append(JU.PT.esc(scenes[i - 1]));
iSceneLast = iScene;
}
sceneScript.append("\n}\n");
if (list.size() == 0) return "no lines 'pause scene n'";
sceneScript.append("\nthisSceneRoot = '$SCRIPT_PATH$'.split('_scene_')[1];\n").append("thisSceneID = 0 + ('$SCRIPT_PATH$'.split('_scene_')[2]).split('.')[1];\n").append("var thisSceneState = '$SCRIPT_PATH$'.replace('.min.png','.all.png') + 'state.spt';\n").append("var spath = ''+currentSceneID+'-'+thisSceneID;\n").append("print thisSceneRoot + ' ' + spath;\n").append("var sscript = sceneScripts[spath];\n").append("var isOK = true;\n").append("try{\n").append("if (thisSceneRoot != currentSceneRoot){\n").append(" isOK = false;\n").append("} else if (sscript != '') {\n").append(" isOK = true;\n").append("} else if (thisSceneID <= currentSceneID){\n").append(" isOK = false;\n").append("} else {\n").append(" sscript = '';\n").append(" for (var i = currentSceneID; i < thisSceneID; i++){\n").append("  var key = ''+i+'-'+(i + 1); var script = sceneScripts[key];\n").append("  if (script = '') {isOK = false;break;}\n").append("  sscript += ';'+script;\n").append(" }\n").append("}\n}catch(e){print e;isOK = false}\n").append("if (isOK) {" + this.wrapPathForAllFiles("script inline @sscript", "print e;isOK = false") + "}\n").append("if (!isOK){script @thisSceneState}\n").append("currentSceneRoot = thisSceneRoot; currentSceneID = thisSceneID;\n}\n");
return sceneScript.toString();
}, "~A,java.util.Map,JU.Lst");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
