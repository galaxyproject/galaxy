Clazz.declarePackage("J.dialog");
Clazz.load(["javax.swing.JFileChooser"], "J.dialog.FileChooser", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.dialogLocation = null;
this.dialogSize = null;
this.$dialog = null;
Clazz.instantialize(this, arguments);}, J.dialog, "FileChooser", javax.swing.JFileChooser);
Clazz.defineMethod(c$, "createDialog", 
function(parent){
this.$dialog = Clazz.superCall(this, J.dialog.FileChooser, "createDialog", [parent]);
if (this.$dialog != null) {
if (this.dialogLocation != null) {
this.$dialog.setLocation(this.dialogLocation);
}if (this.dialogSize != null) {
this.$dialog.setSize(this.dialogSize);
}}return this.$dialog;
}, "java.awt.Component");
Clazz.defineMethod(c$, "setDialogLocation", 
function(p){
this.dialogLocation = p;
}, "java.awt.Point");
Clazz.defineMethod(c$, "setDialogSize", 
function(d){
this.dialogSize = d;
}, "java.awt.Dimension");
Clazz.defineMethod(c$, "getDialog", 
function(){
return this.$dialog;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
