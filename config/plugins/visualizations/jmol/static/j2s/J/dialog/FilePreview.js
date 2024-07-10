Clazz.declarePackage("J.dialog");
Clazz.load(["java.beans.PropertyChangeListener", "javax.swing.JPanel", ], "J.dialog.FilePreview", ["JU.PT", "javax.swing.Box", "$.JCheckBox", "J.i18n.GT", "JV.Viewer"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.active = null;
this.append = null;
this.cartoons = null;
this.chooser = null;
this.display = null;
this.vwr = null;
Clazz.instantialize(this, arguments);}, J.dialog, "FilePreview", javax.swing.JPanel, java.beans.PropertyChangeListener);
Clazz.makeConstructor(c$, 
function(vwr, fileChooser, allowAppend, vwrOptions){
Clazz.superConstructor(this, J.dialog.FilePreview);
this.vwr = vwr;
this.chooser = fileChooser;
var box = javax.swing.Box.createVerticalBox();
this.active =  new javax.swing.JCheckBox(J.i18n.GT.$("Preview"), false);
this.active.addActionListener(((Clazz.isClassDefined("J.dialog.FilePreview$1") ? 0 : J.dialog.FilePreview.$FilePreview$1$ ()), Clazz.innerTypeInstance(J.dialog.FilePreview$1, this, null)));
box.add(this.active);
this.display =  new J.dialog.FilePreview.FPPanel(vwrOptions);
this.display.setPreferredSize( new java.awt.Dimension(80, 80));
this.display.setMinimumSize( new java.awt.Dimension(50, 50));
box.add(this.display);
if (allowAppend) {
this.append =  new javax.swing.JCheckBox(J.i18n.GT.$("Append models"), false);
box.add(this.append);
this.cartoons =  new javax.swing.JCheckBox(J.i18n.GT.$("PDB cartoons"), J.dialog.FilePreview.pdbCartoonChecked);
this.cartoons.addActionListener(((Clazz.isClassDefined("J.dialog.FilePreview$2") ? 0 : J.dialog.FilePreview.$FilePreview$2$ ()), Clazz.innerTypeInstance(J.dialog.FilePreview$2, this, null)));
box.add(this.cartoons);
}this.add(box);
fileChooser.setAccessory(this);
fileChooser.addPropertyChangeListener(this);
}, "JV.Viewer,javax.swing.JFileChooser,~B,java.util.Map");
Clazz.defineMethod(c$, "doPreviewAction", 
function(selected){
this.doUpdatePreview(selected ? this.chooser.getSelectedFile() : null);
}, "~B");
Clazz.defineMethod(c$, "isAppendSelected", 
function(){
return (this.append != null && this.append.isSelected());
});
Clazz.defineMethod(c$, "isCartoonsSelected", 
function(){
return J.dialog.FilePreview.pdbCartoonChecked = (this.cartoons != null && this.cartoons.isSelected());
});
Clazz.overrideMethod(c$, "propertyChange", 
function(evt){
if (this.active.isSelected()) {
var prop = evt.getPropertyName();
if ("SelectedFileChangedProperty".equals(prop)) {
this.doUpdatePreview(evt.getNewValue());
}}}, "java.beans.PropertyChangeEvent");
Clazz.defineMethod(c$, "doUpdatePreview", 
function(file){
var script;
if (file == null) {
script = "zap";
} else {
var fileName = file.getAbsolutePath();
var url = this.vwr.getLocalUrl(fileName);
if (url != null) fileName = url;
fileName = fileName.$replace('\\', '/');
script = " \"" + fileName + "\"";
if (fileName.indexOf(".spt") >= 0) {
script = "script " + script;
} else {
script = JU.PT.rep(this.display.vwr.getP("defaultdropscript"), "\"%FILE\"", script + " 1");
script = JU.PT.rep(script, "%ALLOWCARTOONS", "" + (this.isCartoonsSelected() && !this.isAppendSelected()));
System.out.println(script);
}}this.display.vwr.evalStringQuiet(script);
}, "java.io.File");
Clazz.defineMethod(c$, "setPreviewOptions", 
function(TF){
if (this.append == null) return;
this.append.setVisible(TF);
this.cartoons.setVisible(TF);
}, "~B");
c$.$FilePreview$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(J.dialog, "FilePreview$1", null, java.awt.event.ActionListener);
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
this.b$["J.dialog.FilePreview"].doPreviewAction(this.b$["J.dialog.FilePreview"].active.isSelected());
}, "java.awt.event.ActionEvent");
/*eoif5*/})();
};
c$.$FilePreview$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(J.dialog, "FilePreview$2", null, java.awt.event.ActionListener);
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
if (this.b$["J.dialog.FilePreview"].active.isSelected()) {
this.b$["J.dialog.FilePreview"].doUpdatePreview(this.b$["J.dialog.FilePreview"].chooser.getSelectedFile());
}}, "java.awt.event.ActionEvent");
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.currentSize = null;
Clazz.instantialize(this, arguments);}, J.dialog.FilePreview, "FPPanel", javax.swing.JPanel);
Clazz.prepareFields (c$, function(){
this.currentSize =  new java.awt.Dimension();
});
Clazz.makeConstructor(c$, 
function(info){
Clazz.superConstructor (this, J.dialog.FilePreview.FPPanel, []);
info.put("previewOnly", Boolean.TRUE);
var display = info.get("display");
info.put("display", this);
this.vwr =  new JV.Viewer(info);
info.put("display", display);
}, "java.util.Map");
Clazz.overrideMethod(c$, "paint", 
function(g){
this.getSize(this.currentSize);
this.vwr.setScreenDimension(this.currentSize.width, this.currentSize.height);
var rectClip =  new java.awt.Rectangle();
g.getClipBounds(rectClip);
this.vwr.renderScreenImage(g, this.currentSize.width, this.currentSize.height);
}, "java.awt.Graphics");
/*eoif3*/})();
c$.pdbCartoonChecked = true;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
