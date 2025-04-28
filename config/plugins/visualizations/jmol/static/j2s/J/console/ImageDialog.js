Clazz.declarePackage("J.console");
Clazz.load(["javax.swing.JDialog", "$.JPanel", "J.api.GenericImageDialog"], "J.console.ImageDialog", ["java.util.Hashtable", "JU.PT", "javax.swing.JMenuBar", ], function(){
var c$ = Clazz.decorateAsClass(function(){
this.menubar = null;
this.image = null;
this.vwr = null;
this.canvas = null;
this.$title = null;
this.imageMap = null;
this.console = null;
if (!Clazz.isClassDefined("J.console.ImageDialog.ImageCanvas")) {
J.console.ImageDialog.$ImageDialog$ImageCanvas$ ();
}
Clazz.instantialize(this, arguments);}, J.console, "ImageDialog", javax.swing.JDialog, [J.api.GenericImageDialog, java.awt.event.WindowListener, java.awt.event.ActionListener]);
Clazz.makeConstructor(c$, 
function(vwr, title, imageMap){
Clazz.superConstructor(this, J.console.ImageDialog, [Clazz.instanceOf(J.awt.Platform.getWindow(vwr.display),"javax.swing.JFrame") ? J.awt.Platform.getWindow(vwr.display) : null, title, false]);
this.vwr = vwr;
this.setResizable(false);
this.console = vwr.getConsole();
this.addWindowListener(this);
this.$title = title;
this.imageMap = imageMap;
imageMap.put(title, this);
var wrapper =  new javax.swing.JPanel( new java.awt.BorderLayout());
wrapper.setBackground( new java.awt.Color(255, 0, 0));
this.canvas = Clazz.innerTypeInstance(J.console.ImageDialog.ImageCanvas, this, null);
wrapper.add(this.canvas, "Center");
var container =  new javax.swing.JPanel();
container.setLayout( new java.awt.BorderLayout());
this.menubar =  new javax.swing.JMenuBar();
this.menubar.add(this.createMenu());
this.setJMenuBar(this.menubar);
container.add(wrapper, "Center");
this.getContentPane().add(container);
this.pack();
this.setLocation(100, 100);
this.setVisible(true);
}, "JV.Viewer,~S,java.util.Map");
Clazz.defineMethod(c$, "createMenu", 
function(){
var itemKeys = JU.PT.getTokens("saveas close");
this.vwr.getConsole();
var menu = this.console.newJMenu("file");
for (var i = 0; i < itemKeys.length; i++) {
var item = itemKeys[i];
var mi = this.createMenuItem(item);
menu.add(mi);
}
menu.setVisible(true);
return menu;
});
Clazz.defineMethod(c$, "createMenuItem", 
function(cmd){
var mi = this.console.newJMenuItem(cmd);
mi.setActionCommand(cmd);
mi.addActionListener(this);
mi.setVisible(true);
return mi;
}, "~S");
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
var cmd = e.getActionCommand();
if (cmd.equals("close")) {
this.closeMe();
} else if (cmd.equals("saveas")) {
this.saveAs();
}}, "java.awt.event.ActionEvent");
Clazz.defineMethod(c$, "saveAs", 
function(){
(((Clazz.isClassDefined("J.console.ImageDialog$2") ? 0 : J.console.ImageDialog.$ImageDialog$2$ ()), Clazz.innerTypeInstance(J.console.ImageDialog$2, this, null, ((Clazz.isClassDefined("J.console.ImageDialog$1") ? 0 : J.console.ImageDialog.$ImageDialog$1$ ()), Clazz.innerTypeInstance(J.console.ImageDialog$1, this, null))))).start();
});
Clazz.overrideMethod(c$, "closeMe", 
function(){
this.imageMap.remove(this.$title);
this.dispose();
});
Clazz.overrideMethod(c$, "setImage", 
function(oimage){
if (oimage == null) {
this.closeMe();
return;
}var w = (oimage).getWidth(null);
var h = (oimage).getHeight(null);
this.image =  new java.awt.image.BufferedImage(w, h, 1);
var g = this.image.getGraphics();
g.setColor(java.awt.Color.white);
g.fillRect(0, 0, w, h);
g.drawImage(oimage, 0, 0, null);
g.dispose();
this.setTitle(this.$title + " [" + w + " x " + h + "]");
var d =  new java.awt.Dimension(w, h);
this.canvas.setPreferredSize(d);
this.setBackground(java.awt.Color.WHITE);
this.getContentPane().setBackground(java.awt.Color.WHITE);
this.pack();
}, "~O");
Clazz.overrideMethod(c$, "windowClosed", 
function(e){
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowOpened", 
function(e){
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowClosing", 
function(e){
this.closeMe();
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowIconified", 
function(e){
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowDeiconified", 
function(e){
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowActivated", 
function(e){
}, "java.awt.event.WindowEvent");
Clazz.overrideMethod(c$, "windowDeactivated", 
function(e){
}, "java.awt.event.WindowEvent");
c$.$ImageDialog$ImageCanvas$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
Clazz.instantialize(this, arguments);}, J.console.ImageDialog, "ImageCanvas", javax.swing.JPanel);
Clazz.overrideMethod(c$, "paintComponent", 
function(g){
System.out.println(this.b$["J.console.ImageDialog"].image.getClass().getName());
g.setColor(java.awt.Color.white);
g.fillRect(0, 0, this.b$["J.console.ImageDialog"].image.getWidth(null), this.b$["J.console.ImageDialog"].image.getHeight(null));
g.drawImage(this.b$["J.console.ImageDialog"].image, 0, 0, null);
}, "java.awt.Graphics");
/*eoif4*/})();
};
c$.$ImageDialog$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(J.console, "ImageDialog$2", Thread);
/*eoif5*/})();
};
c$.$ImageDialog$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(J.console, "ImageDialog$1", null, Runnable);
Clazz.overrideMethod(c$, "run", 
function(){
var params =  new java.util.Hashtable();
var fname = this.b$["J.console.ImageDialog"].vwr.dialogAsk("Save Image", "jmol.png", params);
if (fname == null) return;
var type = "PNG";
var pt = fname.lastIndexOf(".");
if (pt > 0) type = fname.substring(pt + 1).toUpperCase();
params.put("fileName", fname);
params.put("type", type);
params.put("image", this.b$["J.console.ImageDialog"].image);
this.b$["J.console.ImageDialog"].vwr.showString(this.b$["J.console.ImageDialog"].vwr.processWriteOrCapture(params), false);
});
/*eoif5*/})();
};
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
