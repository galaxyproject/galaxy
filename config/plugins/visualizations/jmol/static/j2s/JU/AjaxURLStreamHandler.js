Clazz.declarePackage("JU");
Clazz.load(["java.net.URLStreamHandler"], "JU.AjaxURLStreamHandler", ["JU.AjaxURLConnection", "$.SB"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.protocol = null;
Clazz.instantialize(this, arguments);}, JU, "AjaxURLStreamHandler", java.net.URLStreamHandler);
Clazz.makeConstructor(c$, 
function(protocol){
Clazz.superConstructor (this, JU.AjaxURLStreamHandler, []);
this.protocol = protocol;
}, "~S");
Clazz.defineMethod(c$, "openConnection", 
function(url){
return  new JU.AjaxURLConnection(url);
}, "java.net.URL");
Clazz.overrideMethod(c$, "toExternalForm", 
function(u){
var result =  new JU.SB();
result.append(u.getProtocol());
result.append(":");
if (u.getAuthority() != null && u.getAuthority().length > 0) {
result.append("//");
result.append(u.getAuthority());
}if (u.getPath() != null) {
result.append(u.getPath());
}if (u.getQuery() != null) {
result.append("?");
result.append(u.getQuery());
}if (u.getRef() != null) {
result.append("#");
result.append(u.getRef());
}return result.toString();
}, "java.net.URL");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
