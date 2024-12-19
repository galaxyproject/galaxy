Clazz.declarePackage("J.dialog");
Clazz.load(["javax.swing.JPanel", "javax.swing.event.ChangeListener", "javax.swing.filechooser.FileFilter", "J.api.JmolDialogInterface"], "J.dialog.Dialog", ["java.io.File", "javax.swing.JComboBox", "$.JFileChooser", "$.JOptionPane", "$.JSlider", "$.SwingUtilities", "$.UIManager", "javax.swing.border.TitledBorder", "J.dialog.FileChooser", "$.FilePreview", "J.i18n.GT", "JU.Logger", "JV.FileManager"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.extensions = null;
this.choice = null;
this.extension = null;
this.qSliderJPEG = null;
this.qSliderPNG = null;
this.cb = null;
this.qPanelJPEG = null;
this.qPanelPNG = null;
this.openPreview = null;
this.initialFile = null;
if (!Clazz.isClassDefined("J.dialog.Dialog.QualityListener")) {
J.dialog.Dialog.$Dialog$QualityListener$ ();
}
if (!Clazz.isClassDefined("J.dialog.Dialog.ExportChoiceListener")) {
J.dialog.Dialog.$Dialog$ExportChoiceListener$ ();
}
this.imageChoices = null;
this.imageExtensions = null;
this.outputFileName = null;
this.dialogType = null;
this.inputFileName = null;
this.vwr = null;
this.qualityJ = -1;
this.qualityP = -1;
this.imageType = null;
Clazz.instantialize(this, arguments);}, J.dialog, "Dialog", javax.swing.JPanel, J.api.JmolDialogInterface);
Clazz.prepareFields (c$, function(){
this.extensions =  new Array(10);
this.imageChoices =  Clazz.newArray(-1, ["JPEG", "PNG", "GIF", "PPM"]);
this.imageExtensions =  Clazz.newArray(-1, ["jpg", "png", "gif", "ppm"]);
});
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.dialog.Dialog, []);
});
Clazz.overrideMethod(c$, "getOpenFileNameFromDialog", 
function(vwrOptions, vwr, fileName, jmolApp, windowName, allowAppend){
if (J.dialog.Dialog.openChooser == null) {
J.dialog.Dialog.openChooser =  new J.dialog.FileChooser();
var temp = javax.swing.UIManager.get("FileChooser.fileNameLabelText");
javax.swing.UIManager.put("FileChooser.fileNameLabelText", J.i18n.GT.$("File or URL:"));
J.dialog.Dialog.getXPlatformLook(J.dialog.Dialog.openChooser);
javax.swing.UIManager.put("FileChooser.fileNameLabelText", temp);
}if (this.openPreview == null && (vwr.isApplet || Boolean.$valueOf(System.getProperty("openFilePreview", "true")).booleanValue())) {
this.openPreview =  new J.dialog.FilePreview(vwr, J.dialog.Dialog.openChooser, allowAppend, vwrOptions);
}if (jmolApp != null) {
var dim = jmolApp.getHistoryWindowSize(windowName);
if (dim != null) J.dialog.Dialog.openChooser.setDialogSize(dim);
var loc = jmolApp.getHistoryWindowPosition(windowName);
if (loc != null) J.dialog.Dialog.openChooser.setDialogLocation(loc);
}J.dialog.Dialog.openChooser.resetChoosableFileFilters();
if (this.openPreview != null) this.openPreview.setPreviewOptions(allowAppend);
if (fileName != null) {
var pt = fileName.lastIndexOf(".");
var sType = fileName.substring(pt + 1);
if (pt >= 0 && sType.length > 0) J.dialog.Dialog.openChooser.addChoosableFileFilter( new J.dialog.Dialog.TypeFilter(sType));
if (fileName.indexOf(".") == 0) fileName = "Jmol" + fileName;
if (fileName.length > 0) J.dialog.Dialog.openChooser.setSelectedFile( new java.io.File(fileName));
}if (fileName == null || fileName.indexOf(":") < 0 && fileName.indexOf("/") != 0) {
var dir = JV.FileManager.getLocalDirectory(vwr, true);
J.dialog.Dialog.openChooser.setCurrentDirectory(dir);
}var file = null;
if (J.dialog.Dialog.openChooser.showOpenDialog(this) == 0) file = J.dialog.Dialog.openChooser.getSelectedFile();
if (file == null) return this.closePreview();
if (jmolApp != null) jmolApp.addHistoryWindowInfo(windowName, J.dialog.Dialog.openChooser.getDialog(), null);
var url = vwr.getLocalUrl(file.getAbsolutePath());
if (url != null) {
fileName = url;
} else {
JV.FileManager.setLocalPath(vwr, file.getParent(), true);
fileName = file.getAbsolutePath();
}if (fileName.startsWith("/")) fileName = "file://" + fileName;
var doCartoons = (jmolApp == null || allowAppend && this.openPreview != null && this.openPreview.isCartoonsSelected());
var doAppend = (allowAppend && !JV.FileManager.isScriptType(fileName) && this.openPreview != null && this.openPreview.isAppendSelected());
this.closePreview();
return (doCartoons ? "" : "#NOCARTOONS#;") + (doAppend ? "#APPEND#;" : "") + fileName;
}, "java.util.Map,JV.Viewer,~S,J.api.JmolAppAPI,~S,~B");
Clazz.defineMethod(c$, "closePreview", 
function(){
if (this.openPreview != null) this.openPreview.doUpdatePreview(null);
return null;
});
Clazz.overrideMethod(c$, "getSaveFileNameFromDialog", 
function(vwr, fileName, type){
if (J.dialog.Dialog.saveChooser == null) {
J.dialog.Dialog.saveChooser =  new javax.swing.JFileChooser();
J.dialog.Dialog.getXPlatformLook(J.dialog.Dialog.saveChooser);
}J.dialog.Dialog.saveChooser.setCurrentDirectory(JV.FileManager.getLocalDirectory(vwr, true));
var file = null;
J.dialog.Dialog.saveChooser.resetChoosableFileFilters();
if (fileName != null) {
var pt = fileName.lastIndexOf(".");
var sType = fileName.substring(pt + 1);
if (pt >= 0 && sType.length > 0) J.dialog.Dialog.saveChooser.addChoosableFileFilter( new J.dialog.Dialog.TypeFilter(sType));
if (fileName.equals("*")) fileName = vwr.getModelSetFileName();
if (fileName.indexOf(".") == 0) fileName = "Jmol" + fileName;
file =  new java.io.File(fileName);
}if (type != null) J.dialog.Dialog.saveChooser.addChoosableFileFilter( new J.dialog.Dialog.TypeFilter(type));
J.dialog.Dialog.saveChooser.setSelectedFile(file);
if ((file = this.showSaveDialog(this, J.dialog.Dialog.saveChooser, file)) == null) return null;
JV.FileManager.setLocalPath(vwr, file.getParent(), true);
return file.getAbsolutePath();
}, "JV.Viewer,~S,~S");
Clazz.overrideMethod(c$, "getImageFileNameFromDialog", 
function(vwr, fileName, type, imageChoices, imageExtensions, qualityJPG0, qualityPNG0){
if (qualityJPG0 < 0 || qualityJPG0 > 100) qualityJPG0 = J.dialog.Dialog.qualityJPG;
if (qualityPNG0 < 0) qualityPNG0 = J.dialog.Dialog.qualityPNG;
if (qualityPNG0 > 9) qualityPNG0 = 2;
J.dialog.Dialog.qualityJPG = qualityJPG0;
J.dialog.Dialog.qualityPNG = qualityPNG0;
if (this.extension == null) this.extension = "jpg";
if (J.dialog.Dialog.imageChooser == null) {
J.dialog.Dialog.imageChooser =  new javax.swing.JFileChooser();
J.dialog.Dialog.getXPlatformLook(J.dialog.Dialog.imageChooser);
}J.dialog.Dialog.imageChooser.setCurrentDirectory(JV.FileManager.getLocalDirectory(vwr, true));
J.dialog.Dialog.imageChooser.resetChoosableFileFilters();
var file = null;
if (fileName == null) {
fileName = vwr.getModelSetFileName();
if (fileName.indexOf("?") >= 0) fileName = fileName.substring(0, fileName.indexOf("?"));
var pathName = J.dialog.Dialog.imageChooser.getCurrentDirectory().getPath();
if (fileName != null && pathName != null) {
var extensionStart = fileName.lastIndexOf('.');
if (extensionStart != -1) {
fileName = fileName.substring(0, extensionStart) + "." + this.extension;
}file =  new java.io.File(pathName, fileName);
}} else {
if (fileName.indexOf(".") == 0) fileName = "Jmol" + fileName;
file =  new java.io.File(fileName);
type = fileName.substring(fileName.lastIndexOf(".") + 1);
for (var i = 0; i < imageExtensions.length; i++) if (type.equals(imageChoices[i]) || type.toLowerCase().equals(imageExtensions[i])) {
type = imageChoices[i];
break;
}
}this.createExportPanel(imageChoices, imageExtensions, type);
J.dialog.Dialog.imageChooser.setSelectedFile(this.initialFile = file);
if ((file = this.showSaveDialog(this, J.dialog.Dialog.imageChooser, file)) == null) return null;
J.dialog.Dialog.qualityJPG = this.qSliderJPEG.getValue();
J.dialog.Dialog.qualityPNG = this.qSliderPNG.getValue();
if (this.cb.getSelectedIndex() >= 0) J.dialog.Dialog.defaultChoice = this.cb.getSelectedIndex();
JV.FileManager.setLocalPath(vwr, file.getParent(), true);
return file.getAbsolutePath();
}, "JV.Viewer,~S,~S,~A,~A,~N,~N");
Clazz.defineMethod(c$, "createExportPanel", 
function(choices, extensions, type){
J.dialog.Dialog.imageChooser.setAccessory(this);
this.setLayout( new java.awt.BorderLayout());
if (type == null || type.equals("JPG")) type = "JPEG";
for (J.dialog.Dialog.defaultChoice = choices.length; --J.dialog.Dialog.defaultChoice >= 1; ) if (choices[J.dialog.Dialog.defaultChoice].equals(type)) break;

this.extension = extensions[J.dialog.Dialog.defaultChoice];
this.choice = choices[J.dialog.Dialog.defaultChoice];
this.extensions = extensions;
J.dialog.Dialog.imageChooser.resetChoosableFileFilters();
J.dialog.Dialog.imageChooser.addChoosableFileFilter( new J.dialog.Dialog.TypeFilter(this.extension));
var cbPanel =  new javax.swing.JPanel();
cbPanel.setLayout( new java.awt.FlowLayout());
cbPanel.setBorder( new javax.swing.border.TitledBorder(J.i18n.GT.$("Image Type")));
this.cb =  new javax.swing.JComboBox();
for (var i = 0; i < choices.length; i++) {
this.cb.addItem(choices[i]);
}
cbPanel.add(this.cb);
this.cb.setSelectedIndex(J.dialog.Dialog.defaultChoice);
this.cb.addItemListener(Clazz.innerTypeInstance(J.dialog.Dialog.ExportChoiceListener, this, null));
this.add(cbPanel, "North");
var qPanel2 =  new javax.swing.JPanel();
qPanel2.setLayout( new java.awt.BorderLayout());
this.qPanelJPEG =  new javax.swing.JPanel();
this.qPanelJPEG.setLayout( new java.awt.BorderLayout());
this.qPanelJPEG.setBorder( new javax.swing.border.TitledBorder(J.i18n.GT.i(J.i18n.GT.$("JPEG Quality ({0})"), J.dialog.Dialog.qualityJPG)));
this.qSliderJPEG =  new javax.swing.JSlider(0, 50, 100, J.dialog.Dialog.qualityJPG);
this.qSliderJPEG.putClientProperty("JSlider.isFilled", Boolean.TRUE);
this.qSliderJPEG.setPaintTicks(true);
this.qSliderJPEG.setMajorTickSpacing(10);
this.qSliderJPEG.setPaintLabels(true);
this.qSliderJPEG.addChangeListener(Clazz.innerTypeInstance(J.dialog.Dialog.QualityListener, this, null, true, this.qSliderJPEG));
this.qPanelJPEG.add(this.qSliderJPEG, "South");
qPanel2.add(this.qPanelJPEG, "North");
this.qPanelPNG =  new javax.swing.JPanel();
this.qPanelPNG.setLayout( new java.awt.BorderLayout());
this.qPanelPNG.setBorder( new javax.swing.border.TitledBorder(J.i18n.GT.i(J.i18n.GT.$("PNG Compression  ({0})"), J.dialog.Dialog.qualityPNG)));
this.qSliderPNG =  new javax.swing.JSlider(0, 0, 9, J.dialog.Dialog.qualityPNG);
this.qSliderPNG.putClientProperty("JSlider.isFilled", Boolean.TRUE);
this.qSliderPNG.setPaintTicks(true);
this.qSliderPNG.setMajorTickSpacing(2);
this.qSliderPNG.setPaintLabels(true);
this.qSliderPNG.addChangeListener(Clazz.innerTypeInstance(J.dialog.Dialog.QualityListener, this, null, false, this.qSliderPNG));
this.qPanelPNG.add(this.qSliderPNG, "South");
qPanel2.add(this.qPanelPNG, "South");
this.add(qPanel2, "South");
}, "~A,~A,~S");
Clazz.overrideMethod(c$, "getType", 
function(){
return this.choice;
});
Clazz.overrideMethod(c$, "getQuality", 
function(sType){
return (sType.equals("JPEG") || sType.equals("JPG") ? J.dialog.Dialog.qualityJPG : sType.equals("PNG") ? J.dialog.Dialog.qualityPNG : -1);
}, "~S");
c$.doOverWrite = Clazz.defineMethod(c$, "doOverWrite", 
function(chooser, file){
var options =  Clazz.newArray(-1, [J.i18n.GT.$("Yes"), J.i18n.GT.$("No")]);
var opt = javax.swing.JOptionPane.showOptionDialog(chooser, J.i18n.GT.o(J.i18n.GT.$("Do you want to overwrite file {0}?"), file.getAbsolutePath()), J.i18n.GT.$("Warning"), -1, 2, null, options, options[0]);
return (opt == 0);
}, "javax.swing.JFileChooser,java.io.File");
Clazz.defineMethod(c$, "showSaveDialog", 
function(c, chooser, file){
while (true) {
if (chooser.showSaveDialog(c) != 0) return null;
if (this.cb != null && this.cb.getSelectedIndex() >= 0) J.dialog.Dialog.defaultChoice = this.cb.getSelectedIndex();
if ((file = chooser.getSelectedFile()) == null || !file.exists() || J.dialog.Dialog.doOverWrite(chooser, file)) return file;
}
}, "java.awt.Component,javax.swing.JFileChooser,java.io.File");
Clazz.overrideMethod(c$, "setupUI", 
function(forceNewTranslation){
if (forceNewTranslation || !J.dialog.Dialog.haveTranslations) J.dialog.Dialog.setupUIManager();
J.dialog.Dialog.haveTranslations = true;
}, "~B");
c$.setupUIManager = Clazz.defineMethod(c$, "setupUIManager", 
function(){
javax.swing.UIManager.put("FileChooser.acceptAllFileFilterText", J.i18n.GT.$("All Files"));
javax.swing.UIManager.put("FileChooser.cancelButtonText", J.i18n.GT.$("Cancel"));
javax.swing.UIManager.put("FileChooser.cancelButtonToolTipText", J.i18n.GT.$("Abort file chooser dialog"));
javax.swing.UIManager.put("FileChooser.detailsViewButtonAccessibleName", J.i18n.GT.$("Details"));
javax.swing.UIManager.put("FileChooser.detailsViewButtonToolTipText", J.i18n.GT.$("Details"));
javax.swing.UIManager.put("FileChooser.directoryDescriptionText", J.i18n.GT.$("Directory"));
javax.swing.UIManager.put("FileChooser.directoryOpenButtonText", J.i18n.GT.$("Open"));
javax.swing.UIManager.put("FileChooser.directoryOpenButtonToolTipText", J.i18n.GT.$("Open selected directory"));
javax.swing.UIManager.put("FileChooser.fileAttrHeaderText", J.i18n.GT.$("Attributes"));
javax.swing.UIManager.put("FileChooser.fileDateHeaderText", J.i18n.GT.$("Modified"));
javax.swing.UIManager.put("FileChooser.fileDescriptionText", J.i18n.GT.$("Generic File"));
javax.swing.UIManager.put("FileChooser.fileNameHeaderText", J.i18n.GT.$("Name"));
javax.swing.UIManager.put("FileChooser.fileNameLabelText", J.i18n.GT.$("File Name:"));
javax.swing.UIManager.put("FileChooser.fileSizeHeaderText", J.i18n.GT.$("Size"));
javax.swing.UIManager.put("FileChooser.filesOfTypeLabelText", J.i18n.GT.$("Files of Type:"));
javax.swing.UIManager.put("FileChooser.fileTypeHeaderText", J.i18n.GT.$("Type"));
javax.swing.UIManager.put("FileChooser.helpButtonText", J.i18n.GT.$("Help"));
javax.swing.UIManager.put("FileChooser.helpButtonToolTipText", J.i18n.GT.$("FileChooser help"));
javax.swing.UIManager.put("FileChooser.homeFolderAccessibleName", J.i18n.GT.$("Home"));
javax.swing.UIManager.put("FileChooser.homeFolderToolTipText", J.i18n.GT.$("Home"));
javax.swing.UIManager.put("FileChooser.listViewButtonAccessibleName", J.i18n.GT.$("List"));
javax.swing.UIManager.put("FileChooser.listViewButtonToolTipText", J.i18n.GT.$("List"));
javax.swing.UIManager.put("FileChooser.lookInLabelText", J.i18n.GT.$("Look In:"));
javax.swing.UIManager.put("FileChooser.newFolderErrorText", J.i18n.GT.$("Error creating new folder"));
javax.swing.UIManager.put("FileChooser.newFolderAccessibleName", J.i18n.GT.$("New Folder"));
javax.swing.UIManager.put("FileChooser.newFolderToolTipText", J.i18n.GT.$("Create New Folder"));
javax.swing.UIManager.put("FileChooser.openButtonText", J.i18n.GT.$("Open"));
javax.swing.UIManager.put("FileChooser.openButtonToolTipText", J.i18n.GT.$("Open selected file"));
javax.swing.UIManager.put("FileChooser.openDialogTitleText", J.i18n.GT.$("Open"));
javax.swing.UIManager.put("FileChooser.saveButtonText", J.i18n.GT.$("Save"));
javax.swing.UIManager.put("FileChooser.saveButtonToolTipText", J.i18n.GT.$("Save selected file"));
javax.swing.UIManager.put("FileChooser.saveDialogTitleText", J.i18n.GT.$("Save"));
javax.swing.UIManager.put("FileChooser.saveInLabelText", J.i18n.GT.$("Save In:"));
javax.swing.UIManager.put("FileChooser.updateButtonText", J.i18n.GT.$("Update"));
javax.swing.UIManager.put("FileChooser.updateButtonToolTipText", J.i18n.GT.$("Update directory listing"));
javax.swing.UIManager.put("FileChooser.upFolderAccessibleName", J.i18n.GT.$("Up"));
javax.swing.UIManager.put("FileChooser.upFolderToolTipText", J.i18n.GT.$("Up One Level"));
javax.swing.UIManager.put("OptionPane.cancelButtonText", J.i18n.GT.$("Cancel"));
javax.swing.UIManager.put("OptionPane.noButtonText", J.i18n.GT.$("No"));
javax.swing.UIManager.put("OptionPane.okButtonText", J.i18n.GT.$("OK"));
javax.swing.UIManager.put("OptionPane.yesButtonText", J.i18n.GT.$("Yes"));
});
c$.getXPlatformLook = Clazz.defineMethod(c$, "getXPlatformLook", 
function(fc){
if (J.dialog.Dialog.isMac) {
var lnf = javax.swing.UIManager.getLookAndFeel();
if (lnf.isNativeLookAndFeel()) {
try {
javax.swing.UIManager.setLookAndFeel(javax.swing.UIManager.getCrossPlatformLookAndFeelClassName());
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.out.println(e.getMessage());
} else {
throw e;
}
}
fc.updateUI();
try {
javax.swing.UIManager.setLookAndFeel(lnf);
} catch (e) {
if (Clazz.exceptionOf(e,"javax.swing.UnsupportedLookAndFeelException")){
System.out.println(e.getMessage());
} else {
throw e;
}
}
}} else {
fc.updateUI();
}}, "javax.swing.JFileChooser");
Clazz.overrideMethod(c$, "setImageInfo", 
function(qualityJPG, qualityPNG, imageType){
this.qualityJ = qualityJPG;
this.qualityP = qualityPNG;
this.imageType = imageType;
}, "~N,~N,~S");
Clazz.overrideMethod(c$, "getFileNameFromDialog", 
function(v, dType, iFileName){
this.vwr = v;
this.dialogType = dType;
this.inputFileName = iFileName;
this.outputFileName = null;
try {
javax.swing.SwingUtilities.invokeAndWait(((Clazz.isClassDefined("J.dialog.Dialog$1") ? 0 : J.dialog.Dialog.$Dialog$1$ ()), Clazz.innerTypeInstance(J.dialog.Dialog$1, this, null)));
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
JU.Logger.error(e.getMessage());
} else {
throw e;
}
}
return this.outputFileName;
}, "JV.Viewer,~S,~S");
c$.$Dialog$QualityListener$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.isJPEG = false;
this.slider = null;
Clazz.instantialize(this, arguments);}, J.dialog.Dialog, "QualityListener", null, javax.swing.event.ChangeListener);
Clazz.makeConstructor(c$, 
function(isJPEG, slider){
this.isJPEG = isJPEG;
this.slider = slider;
}, "~B,javax.swing.JSlider");
Clazz.overrideMethod(c$, "stateChanged", 
function(arg0){
var value = this.slider.getValue();
if (this.isJPEG) {
J.dialog.Dialog.qualityJPG = value;
this.b$["J.dialog.Dialog"].qPanelJPEG.setBorder( new javax.swing.border.TitledBorder(J.i18n.GT.i(J.i18n.GT.$("JPEG Quality ({0})"), value)));
} else {
J.dialog.Dialog.qualityPNG = value;
this.b$["J.dialog.Dialog"].qPanelPNG.setBorder( new javax.swing.border.TitledBorder(J.i18n.GT.i(J.i18n.GT.$("PNG Quality ({0})"), value)));
}}, "javax.swing.event.ChangeEvent");
/*eoif4*/})();
};
c$.$Dialog$ExportChoiceListener$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
Clazz.instantialize(this, arguments);}, J.dialog.Dialog, "ExportChoiceListener", null, java.awt.event.ItemListener);
Clazz.overrideMethod(c$, "itemStateChanged", 
function(e){
var source = e.getSource();
var selectedFile = J.dialog.Dialog.imageChooser.getSelectedFile();
if (selectedFile == null) selectedFile = this.b$["J.dialog.Dialog"].initialFile;
var newFile = null;
var name;
var newExt = this.b$["J.dialog.Dialog"].extensions[source.getSelectedIndex()];
if ((name = selectedFile.getName()) != null && name.endsWith("." + this.b$["J.dialog.Dialog"].extension)) {
name = name.substring(0, name.length - this.b$["J.dialog.Dialog"].extension.length);
name += newExt;
this.b$["J.dialog.Dialog"].initialFile = newFile =  new java.io.File(selectedFile.getParent(), name);
}this.b$["J.dialog.Dialog"].extension = newExt;
J.dialog.Dialog.imageChooser.resetChoosableFileFilters();
J.dialog.Dialog.imageChooser.addChoosableFileFilter( new J.dialog.Dialog.TypeFilter(this.b$["J.dialog.Dialog"].extension));
if (newFile != null) J.dialog.Dialog.imageChooser.setSelectedFile(newFile);
this.b$["J.dialog.Dialog"].choice = source.getSelectedItem();
}, "java.awt.event.ItemEvent");
/*eoif4*/})();
};
c$.$Dialog$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(J.dialog, "Dialog$1", null, Runnable);
Clazz.overrideMethod(c$, "run", 
function(){
if (this.b$["J.dialog.Dialog"].dialogType.equals("Load")) {
this.b$["J.dialog.Dialog"].outputFileName = this.b$["J.dialog.Dialog"].getOpenFileNameFromDialog(this.b$["J.dialog.Dialog"].vwr.vwrOptions, this.b$["J.dialog.Dialog"].vwr, this.b$["J.dialog.Dialog"].inputFileName, null, null, false);
return;
}if (this.b$["J.dialog.Dialog"].dialogType.equals("Save")) {
this.b$["J.dialog.Dialog"].outputFileName = this.b$["J.dialog.Dialog"].getSaveFileNameFromDialog(this.b$["J.dialog.Dialog"].vwr, this.b$["J.dialog.Dialog"].inputFileName, null);
return;
}if (this.b$["J.dialog.Dialog"].dialogType.startsWith("Save Image")) {
this.b$["J.dialog.Dialog"].outputFileName = this.b$["J.dialog.Dialog"].getImageFileNameFromDialog(this.b$["J.dialog.Dialog"].vwr, this.b$["J.dialog.Dialog"].inputFileName, this.b$["J.dialog.Dialog"].imageType, this.b$["J.dialog.Dialog"].imageChoices, this.b$["J.dialog.Dialog"].imageExtensions, this.b$["J.dialog.Dialog"].qualityJ, this.b$["J.dialog.Dialog"].qualityP);
return;
}this.b$["J.dialog.Dialog"].outputFileName = null;
});
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.thisType = null;
Clazz.instantialize(this, arguments);}, J.dialog.Dialog, "TypeFilter", javax.swing.filechooser.FileFilter);
Clazz.makeConstructor(c$, 
function(type){
Clazz.superConstructor (this, J.dialog.Dialog.TypeFilter, []);
this.thisType = type.toLowerCase();
}, "~S");
Clazz.overrideMethod(c$, "accept", 
function(f){
if (f.isDirectory() || this.thisType == null) {
return true;
}var ext = f.getName();
var pt = ext.lastIndexOf(".");
return (pt >= 0 && ext.substring(pt + 1).toLowerCase().equals(this.thisType));
}, "java.io.File");
Clazz.overrideMethod(c$, "getDescription", 
function(){
return this.thisType.toUpperCase() + " (*." + this.thisType + ")";
});
/*eoif3*/})();
c$.defaultChoice = 0;
c$.qualityJPG = 75;
c$.qualityPNG = 2;
c$.imageChooser = null;
c$.saveChooser = null;
c$.openChooser = null;
c$.haveTranslations = false;
c$.isMac = System.getProperty("os.name", "").startsWith("Mac");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
