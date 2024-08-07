Clazz.declarePackage("JSV.common");
(function(){
var c$ = Clazz.declareType(JSV.common, "JSVersion", null);
{
var tmpVersion = null;
var tmpDate = null;
{
tmpVersion = Jmol.___JmolVersion; tmpDate = Jmol.___JmolDate;
}if (tmpDate != null) {
tmpDate = tmpDate.substring(7, 23);
}JSV.common.JSVersion.VERSION_SHORT = (tmpVersion != null ? tmpVersion : "(Unknown_version)");
var mv = (tmpVersion != null ? tmpVersion : "(Unknown_version)");
JSV.common.JSVersion.date = (tmpDate != null ? tmpDate : "");
JSV.common.JSVersion.VERSION = JSV.common.JSVersion.VERSION_SHORT + (JSV.common.JSVersion.date == null ? "" : " " + JSV.common.JSVersion.date);
var v = -1;
if (tmpVersion != null) try {
var s = JSV.common.JSVersion.VERSION_SHORT;
var major = "";
var i = s.indexOf(".");
if (i < 0) {
v = 100000 * Integer.parseInt(s);
s = null;
}if (s != null) {
v = 100000 * Integer.parseInt(major = s.substring(0, i));
s = s.substring(i + 1);
i = s.indexOf(".");
if (i < 0) {
v += 1000 * Integer.parseInt(s);
s = null;
}if (s != null) {
var m = s.substring(0, i);
major += "." + m;
mv = major;
v += 1000 * Integer.parseInt(m);
s = s.substring(i + 1);
i = s.indexOf("_");
if (i >= 0) s = s.substring(0, i);
i = s.indexOf(" ");
if (i >= 0) s = s.substring(0, i);
v += Integer.parseInt(s);
}}} catch (e) {
if (Clazz.exceptionOf(e,"NumberFormatException")){
} else {
throw e;
}
}
JSV.common.JSVersion.majorVersion = mv;
JSV.common.JSVersion.versionInt = v;
}})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
