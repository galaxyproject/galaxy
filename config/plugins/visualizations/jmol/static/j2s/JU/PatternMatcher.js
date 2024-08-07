Clazz.declarePackage("JU");
Clazz.load(null, "JU.PatternMatcher", ["JV.Viewer"], function(){
var c$ = Clazz.declareType(JU, "PatternMatcher", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "compile", 
function(regex, isCaseInsensitive){
if (JV.Viewer.isJS && !JV.Viewer.isSwingJS) {
return  new JU.PatternMatcher.JSPattern(regex, isCaseInsensitive);
}{
}}, "~S,~B");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.regexp = null;
this.strString = null;
this.leftBound = -1;
this.rightBound = -1;
this.results = null;
Clazz.instantialize(this, arguments);}, JU.PatternMatcher, "JSPattern", null);
Clazz.makeConstructor(c$, 
function(regex, isCaseInsensitive){
var flagStr = (isCaseInsensitive ? "gi" : "g");
{
this.regexp = new RegExp(regex, flagStr);
}}, "~S,~B");
Clazz.defineMethod(c$, "find", 
function(){
var s = (this.rightBound == this.strString.length ? this.strString : this.strString.substring(0, this.rightBound));
{
this.regexp.lastIndex = this.leftBound;
this.results = this.regexp.exec(s);
this.leftBound = this.regexp.lastIndex;
}return (this.results != null);
});
Clazz.defineMethod(c$, "start", 
function(){
{
return this.regexp.lastIndex - this.results[0].length;
}});
Clazz.defineMethod(c$, "end", 
function(){
{
return this.regexp.lastIndex;
}});
Clazz.defineMethod(c$, "group", 
function(){
if (this.results == null || this.results.length == 0) {
return null;
}return this.results[0];
});
Clazz.defineMethod(c$, "matcher", 
function(s){
this.strString = s;
this.leftBound = 0;
this.rightBound = s.length;
return this;
}, "~S");
/*eoif3*/})();
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
