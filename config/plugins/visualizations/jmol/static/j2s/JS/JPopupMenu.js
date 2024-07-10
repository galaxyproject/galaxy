Clazz.declarePackage("JS");
Clazz.load(["JS.AbstractButton"], "JS.JPopupMenu", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.tainted = true;
Clazz.instantialize(this, arguments);}, JS, "JPopupMenu", JS.AbstractButton);
Clazz.makeConstructor(c$, 
function(name){
Clazz.superConstructor(this, JS.JPopupMenu, ["mnu"]);
this.name = name;
}, "~S");
Clazz.defineMethod(c$, "setInvoker", 
function(applet){
this.applet = applet;
{
SwingController.setMenu(this);
}}, "~O");
Clazz.defineMethod(c$, "show", 
function(applet, x, y){
if (applet != null) this.tainted = true;
{
SwingController.showMenu(this, x, y);
}}, "JS.Component,~N,~N");
Clazz.defineMethod(c$, "disposeMenu", 
function(){
{
SwingController.disposeMenu(this);
}});
Clazz.overrideMethod(c$, "toHTML", 
function(){
return this.getMenuHTML();
});
{
{
SwingController.setDraggable(JS.JPopupMenu);
}}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
