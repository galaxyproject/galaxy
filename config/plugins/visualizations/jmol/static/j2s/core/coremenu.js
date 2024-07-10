(function(Clazz
,Clazz_getClassName
,Clazz_newLongArray
,Clazz_doubleToByte
,Clazz_doubleToInt
,Clazz_doubleToLong
,Clazz_declarePackage
,Clazz_instanceOf
,Clazz_load
,Clazz_instantialize
,Clazz_decorateAsClass
,Clazz_floatToInt
,Clazz_floatToLong
,Clazz_makeConstructor
,Clazz_defineEnumConstant
,Clazz_exceptionOf
,Clazz_newIntArray
,Clazz_newFloatArray
,Clazz_declareType
,Clazz_prepareFields
,Clazz_superConstructor
,Clazz_newByteArray
,Clazz_declareInterface
,Clazz_newShortArray
,Clazz_innerTypeInstance
,Clazz_isClassDefined
,Clazz_prepareCallback
,Clazz_newArray
,Clazz_castNullAs
,Clazz_floatToShort
,Clazz_superCall
,Clazz_decorateAsType
,Clazz_newBooleanArray
,Clazz_newCharArray
,Clazz_implementOf
,Clazz_newDoubleArray
,Clazz_overrideConstructor
,Clazz_clone
,Clazz_doubleToShort
,Clazz_getInheritedLevel
,Clazz_getParamsType
,Clazz_isAF
,Clazz_isAB
,Clazz_isAI
,Clazz_isAS
,Clazz_isASS
,Clazz_isAP
,Clazz_isAFloat
,Clazz_isAII
,Clazz_isAFF
,Clazz_isAFFF
,Clazz_tryToSearchAndExecute
,Clazz_getStackTrace
,Clazz_inheritArgs
,Clazz_alert
,Clazz_defineMethod
,Clazz_overrideMethod
,Clazz_declareAnonymous
//,Clazz_checkPrivateMethod
,Clazz_cloneFinals
){
var $t$;
//var c$;
Clazz_declarePackage("J.popup");
Clazz_load(["J.api.GenericMenuInterface", "java.util.Hashtable", "JU.Lst"], "J.popup.GenericPopup", ["java.util.StringTokenizer", "JU.PT", "$.SB", "JU.Logger"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.helper = null;
this.strMenuStructure = null;
this.allowSignedFeatures = false;
this.isJS = false;
this.isApplet = false;
this.isSigned = false;
this.isWebGL = false;
this.thisx = 0;
this.thisy = 0;
this.isTainted = true;
this.menuName = null;
this.popupMenu = null;
this.thisPopup = null;
this.htCheckbox = null;
this.buttonGroup = null;
this.currentMenuItemId = null;
this.htMenus = null;
this.SignedOnly = null;
this.updatingForShow = false;
Clazz_instantialize(this, arguments);}, J.popup, "GenericPopup", null, J.api.GenericMenuInterface);
Clazz_prepareFields (c$, function(){
this.htCheckbox =  new java.util.Hashtable();
this.htMenus =  new java.util.Hashtable();
this.SignedOnly =  new JU.Lst();
});
Clazz_defineMethod(c$, "appCheckItem", 
function(item, newMenu){
}, "~S,J.api.SC");
Clazz_defineMethod(c$, "appCheckSpecialMenu", 
function(item, subMenu, word){
}, "~S,J.api.SC,~S");
Clazz_defineMethod(c$, "initSwing", 
function(title, bundle, applet, isJS, isSigned, isWebGL){
this.isJS = isJS;
this.isApplet = (applet != null);
this.isSigned = isSigned;
this.isWebGL = isWebGL;
this.allowSignedFeatures = (!this.isApplet || isSigned);
this.menuName = title;
this.popupMenu = this.helper.menuCreatePopup(title, applet);
this.thisPopup = this.popupMenu;
this.htMenus.put(title, this.popupMenu);
this.addMenuItems("", title, this.popupMenu, bundle);
}, "~S,J.popup.PopupResource,~O,~B,~B,~B");
Clazz_defineMethod(c$, "addMenuItems", 
function(parentId, key, menu, popupResourceBundle){
var id = parentId + "." + key;
var value = popupResourceBundle.getStructure(key);
if (JU.Logger.debugging) JU.Logger.debug(id + " --- " + value);
if (value == null) {
this.menuCreateItem(menu, "#" + key, "", "");
return;
}var st =  new java.util.StringTokenizer(value);
var item;
while (value.indexOf("@") >= 0) {
var s = "";
while (st.hasMoreTokens()) s += " " + ((item = st.nextToken()).startsWith("@") ? popupResourceBundle.getStructure(item) : item);

value = s.substring(1);
st =  new java.util.StringTokenizer(value);
}
while (st.hasMoreTokens()) {
item = st.nextToken();
if (!this.checkKey(item)) continue;
if ("-".equals(item)) {
this.menuAddSeparator(menu);
this.helper.menuAddButtonGroup(null);
continue;
}if (",".equals(item)) {
this.menuAddSeparator(menu);
continue;
}var label = popupResourceBundle.getWord(item);
var newItem = null;
var script = "";
var isCB = false;
label = this.appFixLabel(label == null ? item : label);
if (label.equals("null")) {
continue;
}if (item.indexOf("Menu") >= 0) {
if (item.indexOf("more") < 0) this.helper.menuAddButtonGroup(null);
var subMenu = this.menuNewSubMenu(label, id + "." + item);
this.menuAddSubMenu(menu, subMenu);
this.addMenu(id, item, subMenu, label, popupResourceBundle);
newItem = subMenu;
} else if (item.endsWith("Checkbox") || (isCB = (item.endsWith("CB") || item.endsWith("RD")))) {
script = popupResourceBundle.getStructure(item);
var basename = item.substring(0, item.length - (!isCB ? 8 : 2));
var isRadio = (isCB && item.endsWith("RD"));
if (script == null || script.length == 0 && !isRadio) script = "set " + basename + " T/F";
newItem = this.menuCreateCheckboxItem(menu, label, basename + ":" + script, id + "." + item, false, isRadio);
this.rememberCheckbox(basename, newItem);
if (isRadio) this.helper.menuAddButtonGroup(newItem);
} else {
script = popupResourceBundle.getStructure(item);
if (script == null) script = item;
newItem = this.menuCreateItem(menu, label, script, id + "." + item);
}this.htMenus.put(item, newItem);
if (item.startsWith("SIGNED")) {
this.SignedOnly.addLast(newItem);
if (!this.allowSignedFeatures) this.menuEnable(newItem, false);
}this.appCheckItem(item, newItem);
}
}, "~S,~S,J.api.SC,J.popup.PopupResource");
Clazz_defineMethod(c$, "addMenu", 
function(id, item, subMenu, label, popupResourceBundle){
if (item.indexOf("Computed") < 0) this.addMenuItems(id, item, subMenu, popupResourceBundle);
this.appCheckSpecialMenu(item, subMenu, label);
}, "~S,~S,J.api.SC,~S,J.popup.PopupResource");
Clazz_defineMethod(c$, "updateSignedAppletItems", 
function(){
for (var i = this.SignedOnly.size(); --i >= 0; ) this.menuEnable(this.SignedOnly.get(i), this.allowSignedFeatures);

});
Clazz_defineMethod(c$, "checkKey", 
function(key){
return (key.indexOf(this.isApplet ? "JAVA" : "APPLET") < 0 && (!this.isWebGL || key.indexOf("NOGL") < 0));
}, "~S");
Clazz_defineMethod(c$, "rememberCheckbox", 
function(key, checkboxMenuItem){
this.htCheckbox.put(key + "::" + this.htCheckbox.size(), checkboxMenuItem);
}, "~S,J.api.SC");
Clazz_defineMethod(c$, "updateButton", 
function(b, entry, script){
var ret =  Clazz_newArray(-1, [entry]);
var icon = this.getEntryIcon(ret);
entry = ret[0];
b.init(entry, icon, script, this.thisPopup);
this.isTainted = true;
}, "J.api.SC,~S,~S");
Clazz_defineMethod(c$, "getEntryIcon", 
function(ret){
var entry = ret[0];
if (!entry.startsWith("<")) return null;
var pt = entry.indexOf(">");
ret[0] = entry.substring(pt + 1);
var fileName = entry.substring(1, pt);
return this.getImageIcon(fileName);
}, "~A");
Clazz_defineMethod(c$, "addMenuItem", 
function(menuItem, entry){
return this.menuCreateItem(menuItem, entry, "", null);
}, "J.api.SC,~S");
Clazz_defineMethod(c$, "menuSetLabel", 
function(m, entry){
if (m == null) return;
m.setText(entry);
this.isTainted = true;
}, "J.api.SC,~S");
Clazz_defineMethod(c$, "menuClickCallback", 
function(source, script){
this.doMenuClickCallback(source, script);
}, "J.api.SC,~S");
Clazz_defineMethod(c$, "doMenuClickCallback", 
function(source, script){
this.appRestorePopupMenu();
if (script == null || script.length == 0) return;
if (script.equals("MAIN")) {
this.show(this.thisx, this.thisy, true);
return;
}var id = this.menuGetId(source);
if (id != null) {
script = this.getScriptForCallback(source, id, script);
this.currentMenuItemId = id;
}if (script != null) this.appRunScript(script);
}, "J.api.SC,~S");
Clazz_defineMethod(c$, "menuCheckBoxCallback", 
function(source){
this.doMenuCheckBoxCallback(source);
}, "J.api.SC");
Clazz_defineMethod(c$, "doMenuCheckBoxCallback", 
function(source){
this.appRestorePopupMenu();
var isSelected = source.isSelected();
var what = source.getActionCommand();
this.runCheckBoxScript(source, what, isSelected);
this.appUpdateSpecialCheckBoxValue(source, what, isSelected);
this.isTainted = true;
var id = this.menuGetId(source);
if (id != null) {
this.currentMenuItemId = id;
}}, "J.api.SC");
Clazz_defineMethod(c$, "runCheckBoxScript", 
function(item, what, TF){
if (!item.isEnabled()) return;
if (what.indexOf("##") < 0) {
var pt = what.indexOf(":");
if (pt < 0) {
JU.Logger.error("check box " + item + " IS " + what);
return;
}var basename = what.substring(0, pt);
if (this.appRunSpecialCheckBox(item, basename, what, TF)) return;
what = what.substring(pt + 1);
if ((pt = what.indexOf("|")) >= 0) what = (TF ? what.substring(0, pt) : what.substring(pt + 1)).trim();
what = JU.PT.rep(what, "T/F", (TF ? " TRUE" : " FALSE"));
}this.appRunScript(what);
}, "J.api.SC,~S,~B");
Clazz_defineMethod(c$, "menuCreateItem", 
function(menu, entry, script, id){
var item = this.helper.getMenuItem(entry);
item.addActionListener(this.helper);
return this.newMenuItem(item, menu, entry, script, id);
}, "J.api.SC,~S,~S,~S");
Clazz_defineMethod(c$, "menuCreateCheckboxItem", 
function(menu, entry, basename, id, state, isRadio){
var jmi = (isRadio ? this.helper.getRadio(entry) : this.helper.getCheckBox(entry));
jmi.setSelected(state);
jmi.addItemListener(this.helper);
return this.newMenuItem(jmi, menu, entry, basename, id);
}, "J.api.SC,~S,~S,~S,~B,~B");
Clazz_defineMethod(c$, "menuAddSeparator", 
function(menu){
menu.add(this.helper.getMenuItem(null));
this.isTainted = true;
}, "J.api.SC");
Clazz_defineMethod(c$, "menuNewSubMenu", 
function(entry, id){
var jm = this.helper.getMenu(entry);
jm.addMouseListener(this.helper);
this.updateButton(jm, entry, null);
jm.setName(id);
jm.setAutoscrolls(true);
return jm;
}, "~S,~S");
Clazz_defineMethod(c$, "menuRemoveAll", 
function(menu, indexFrom){
if (indexFrom <= 0) menu.removeAll();
 else for (var i = menu.getComponentCount(); --i >= indexFrom; ) menu.remove(i);

this.isTainted = true;
}, "J.api.SC,~N");
Clazz_defineMethod(c$, "newMenuItem", 
function(item, menu, text, script, id){
this.updateButton(item, text, script);
item.addMouseListener(this.helper);
item.setName(id == null ? menu.getName() + "." : id);
this.menuAddItem(menu, item);
return item;
}, "J.api.SC,J.api.SC,~S,~S,~S");
Clazz_defineMethod(c$, "setText", 
function(item, text){
var m = this.htMenus.get(item);
if (m != null) m.setText(text);
return m;
}, "~S,~S");
Clazz_defineMethod(c$, "menuAddItem", 
function(menu, item){
menu.add(item);
this.isTainted = true;
}, "J.api.SC,J.api.SC");
Clazz_defineMethod(c$, "menuAddSubMenu", 
function(menu, subMenu){
subMenu.addMouseListener(this.helper);
this.menuAddItem(menu, subMenu);
}, "J.api.SC,J.api.SC");
Clazz_defineMethod(c$, "menuEnable", 
function(component, enable){
if (component == null || component.isEnabled() == enable) return;
component.setEnabled(enable);
}, "J.api.SC,~B");
Clazz_defineMethod(c$, "menuGetId", 
function(menu){
return menu.getName();
}, "J.api.SC");
Clazz_defineMethod(c$, "menuSetAutoscrolls", 
function(menu){
menu.setAutoscrolls(true);
this.isTainted = true;
}, "J.api.SC");
Clazz_defineMethod(c$, "menuGetListPosition", 
function(item){
var p = item.getParent();
var i;
for (i = p.getComponentCount(); --i >= 0; ) if (this.helper.getSwingComponent(p.getComponent(i)) === item) break;

return i;
}, "J.api.SC");
Clazz_defineMethod(c$, "show", 
function(x, y, doPopup){
this.appUpdateForShow();
this.updateCheckBoxesForShow();
if (doPopup) this.menuShowPopup(this.popupMenu, this.thisx, this.thisy);
}, "~N,~N,~B");
Clazz_defineMethod(c$, "updateCheckBoxesForShow", 
function(){
for (var entry, $entry = this.htCheckbox.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
var key = entry.getKey();
var item = entry.getValue();
var basename = key.substring(0, key.indexOf(":"));
var b = this.appGetBooleanProperty(basename);
var updateShow = this.updatingForShow;
this.updatingForShow = true;
if (item.isSelected() != b) {
item.setSelected(b);
this.isTainted = true;
}this.updatingForShow = updateShow;
}
});
Clazz_overrideMethod(c$, "jpiGetMenuAsString", 
function(title){
this.appUpdateForShow();
var pt = title.indexOf("|");
if (pt >= 0) {
var type = title.substring(pt);
title = title.substring(0, pt);
if (type.indexOf("current") >= 0) {
var sb =  new JU.SB();
var menu = this.htMenus.get(this.menuName);
this.menuGetAsText(sb, 0, menu, "PopupMenu");
return sb.toString();
}}return this.appGetMenuAsString(title);
}, "~S");
Clazz_defineMethod(c$, "appGetMenuAsString", 
function(title){
return null;
}, "~S");
Clazz_defineMethod(c$, "menuGetAsText", 
function(sb, level, menu, menuName){
var name = menuName;
var subMenus = menu.getComponents();
var flags = null;
var script = null;
var text = null;
var key = 'S';
for (var i = 0; i < subMenus.length; i++) {
var source = this.helper.getSwingComponent(subMenus[i]);
var type = this.helper.getItemType(source);
switch (type) {
case 4:
key = 'M';
name = source.getName();
flags = "enabled:" + source.isEnabled();
text = source.getText();
script = null;
break;
case 0:
key = 'S';
flags = script = text = null;
break;
default:
key = 'I';
flags = "enabled:" + source.isEnabled();
if (type == 2 || type == 3) flags += ";checked:" + source.isSelected();
script = this.getScriptForCallback(source, source.getName(), source.getActionCommand());
name = source.getName();
text = source.getText();
break;
}
J.popup.GenericPopup.addItemText(sb, key, level, name, text, script, flags);
if (type == 2) this.menuGetAsText(sb, level + 1, this.helper.getSwingComponent(source.getPopupMenu()), name);
}
}, "JU.SB,~N,J.api.SC,~S");
c$.addItemText = Clazz_defineMethod(c$, "addItemText", 
function(sb, type, level, name, label, script, flags){
sb.appendC(type).appendI(level).appendC('\t').append(name);
if (label == null) {
sb.append(".\n");
return;
}sb.append("\t").append(label).append("\t").append(script == null || script.length == 0 ? "-" : script).append("\t").append(flags).append("\n");
}, "JU.SB,~S,~N,~S,~S,~S,~S");
c$.convertToMegabytes = Clazz_defineMethod(c$, "convertToMegabytes", 
function(num){
if (num <= 9223372036854251519) num += 524288;
return (Clazz_doubleToInt(num / (1048576)));
}, "~N");
Clazz_overrideMethod(c$, "jpiDispose", 
function(){
this.popupMenu = this.thisPopup = null;
this.helper.dispose(this.popupMenu);
this.helper = null;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.popup");
Clazz_load(["J.popup.GenericPopup", "java.util.Properties"], "J.popup.JmolGenericPopup", ["J.i18n.GT"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.frankPopup = null;
this.nFrankList = 0;
this.vwr = null;
this.menuText = null;
Clazz_instantialize(this, arguments);}, J.popup, "JmolGenericPopup", J.popup.GenericPopup);
Clazz_prepareFields (c$, function(){
this.menuText =  new java.util.Properties();
});
Clazz_overrideMethod(c$, "jpiInitialize", 
function(vwr, menu){
var doTranslate = J.i18n.GT.setDoTranslate(true);
var bundle = this.getBundle(menu);
this.initialize(vwr, bundle, bundle.getMenuName());
J.i18n.GT.setDoTranslate(doTranslate);
}, "J.api.PlatformViewer,~S");
Clazz_defineMethod(c$, "initialize", 
function(vwr, bundle, title){
this.vwr = vwr;
this.initSwing(title, bundle, vwr.isJSNoAWT ? vwr.html5Applet : null, vwr.isJSNoAWT, vwr.getBooleanProperty("_signedApplet"), vwr.isWebGL);
}, "JV.Viewer,J.popup.PopupResource,~S");
Clazz_overrideMethod(c$, "jpiShow", 
function(x, y){
if (!this.vwr.haveDisplay) return;
this.thisx = x;
this.thisy = y;
this.show(x, y, false);
if (x < 0 && this.showFrankMenu()) return;
this.appRestorePopupMenu();
this.menuShowPopup(this.popupMenu, this.thisx, this.thisy);
}, "~N,~N");
Clazz_defineMethod(c$, "showFrankMenu", 
function(){
return true;
});
Clazz_defineMethod(c$, "jpiDispose", 
function(){
this.vwr = null;
Clazz_superCall(this, J.popup.JmolGenericPopup, "jpiDispose", []);
});
Clazz_overrideMethod(c$, "jpiGetMenuAsObject", 
function(){
return this.popupMenu;
});
Clazz_overrideMethod(c$, "appFixLabel", 
function(label){
return label;
}, "~S");
Clazz_overrideMethod(c$, "appGetBooleanProperty", 
function(name){
return this.vwr.getBooleanProperty(name);
}, "~S");
Clazz_overrideMethod(c$, "appRunSpecialCheckBox", 
function(item, basename, script, TF){
if (this.appGetBooleanProperty(basename) == TF) return true;
if (basename.indexOf("mk") < 0 && !basename.endsWith("P!")) return false;
if (basename.indexOf("mk") >= 0 || basename.indexOf("??") >= 0) {
script = this.getUnknownCheckBoxScriptToRun(item, basename, script, TF);
} else {
if (!TF) return true;
script = "set picking " + basename.substring(0, basename.length - 2);
}if (script != null) this.appRunScript(script);
return true;
}, "J.api.SC,~S,~S,~B");
Clazz_overrideMethod(c$, "appRestorePopupMenu", 
function(){
this.thisPopup = this.popupMenu;
});
Clazz_overrideMethod(c$, "appRunScript", 
function(script){
this.vwr.evalStringGUI(script);
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.popup");
Clazz_load(["J.popup.JmolGenericPopup", "JU.Lst"], "J.popup.JmolPopup", ["java.util.Arrays", "$.Hashtable", "JU.PT", "J.i18n.GT", "JM.Group", "J.popup.MainPopupResourceBundle", "JU.Elements", "JV.JC"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.updateMode = 0;
this.titleWidthMax = 20;
this.nullModelSetName = null;
this.modelSetName = null;
this.modelSetFileName = null;
this.modelSetRoot = null;
this.currentFrankId = null;
this.configurationSelected = "";
this.altlocs = null;
this.frankList = null;
this.modelSetInfo = null;
this.modelInfo = null;
this.NotPDB = null;
this.PDBOnly = null;
this.FileUnitOnly = null;
this.FileMolOnly = null;
this.UnitcellOnly = null;
this.SingleModelOnly = null;
this.FramesOnly = null;
this.VibrationOnly = null;
this.Special = null;
this.SymmetryOnly = null;
this.ChargesOnly = null;
this.TemperatureOnly = null;
this.fileHasUnitCell = false;
this.haveBFactors = false;
this.haveCharges = false;
this.isLastFrame = false;
this.isMultiConfiguration = false;
this.isMultiFrame = false;
this.isPDB = false;
this.hasSymmetry = false;
this.isUnitCell = false;
this.isVibration = false;
this.isZapped = false;
this.modelIndex = 0;
this.modelCount = 0;
this.ac = 0;
this.group3List = null;
this.group3Counts = null;
this.cnmrPeaks = null;
this.hnmrPeaks = null;
this.noZapped = null;
Clazz_instantialize(this, arguments);}, J.popup, "JmolPopup", J.popup.JmolGenericPopup);
Clazz_prepareFields (c$, function(){
this.frankList =  new Array(10);
this.NotPDB =  new JU.Lst();
this.PDBOnly =  new JU.Lst();
this.FileUnitOnly =  new JU.Lst();
this.FileMolOnly =  new JU.Lst();
this.UnitcellOnly =  new JU.Lst();
this.SingleModelOnly =  new JU.Lst();
this.FramesOnly =  new JU.Lst();
this.VibrationOnly =  new JU.Lst();
this.Special =  new JU.Lst();
this.SymmetryOnly =  new JU.Lst();
this.ChargesOnly =  new JU.Lst();
this.TemperatureOnly =  new JU.Lst();
this.noZapped =  Clazz_newArray(-1, ["surfaceMenu", "measureMenu", "pickingMenu", "computationMenu", "SIGNEDJAVAcaptureMenuSPECIAL"]);
});
Clazz_defineMethod(c$, "jpiDispose", 
function(){
this.helper.menuClearListeners(this.frankPopup);
this.frankPopup = null;
Clazz_superCall(this, J.popup.JmolPopup, "jpiDispose", []);
});
Clazz_overrideMethod(c$, "getBundle", 
function(menu){
return  new J.popup.MainPopupResourceBundle(this.strMenuStructure = menu, this.menuText);
}, "~S");
Clazz_overrideMethod(c$, "showFrankMenu", 
function(){
this.getViewerData();
this.setFrankMenu(this.currentMenuItemId);
this.thisx = -this.thisx - 50;
if (this.nFrankList > 1) {
this.thisy -= this.nFrankList * 20;
this.menuShowPopup(this.frankPopup, this.thisx, this.thisy);
return true;
}return false;
});
Clazz_overrideMethod(c$, "jpiUpdateComputedMenus", 
function(){
if (this.updateMode == -1) return;
this.isTainted = true;
this.getViewerData();
this.updateMode = 0;
this.updateMenus();
});
Clazz_defineMethod(c$, "updateMenus", 
function(){
this.updateSelectMenu();
this.updateModelSetComputedMenu();
this.updateAboutSubmenu();
if (this.updateMode == 0) {
this.updateFileMenu();
this.updateElementsComputedMenu(this.vwr.getElementsPresentBitSet(this.modelIndex));
this.updateHeteroComputedMenu(this.vwr.ms.getHeteroList(this.modelIndex));
this.updateSurfMoComputedMenu(this.modelInfo.get("moData"));
this.updateFileTypeDependentMenus();
this.updatePDBResidueComputedMenus();
this.updateMode = 1;
this.updateConfigurationComputedMenu();
this.updateSYMMETRYComputedMenus();
this.updateFRAMESbyModelComputedMenu();
this.updateLanguageSubmenu();
} else {
this.updateSpectraMenu();
this.updateFRAMESbyModelComputedMenu();
this.updateSceneComputedMenu();
for (var i = this.Special.size(); --i >= 0; ) this.updateSpecialMenuItem(this.Special.get(i));

}});
Clazz_overrideMethod(c$, "appCheckItem", 
function(item, newMenu){
if (item.indexOf("!PDB") >= 0) {
this.NotPDB.addLast(newMenu);
} else if (item.indexOf("PDB") >= 0) {
this.PDBOnly.addLast(newMenu);
}if (item.indexOf("CHARGE") >= 0) {
this.ChargesOnly.addLast(newMenu);
} else if (item.indexOf("BFACTORS") >= 0) {
this.TemperatureOnly.addLast(newMenu);
} else if (item.indexOf("UNITCELL") >= 0) {
this.UnitcellOnly.addLast(newMenu);
} else if (item.indexOf("FILEUNIT") >= 0) {
this.FileUnitOnly.addLast(newMenu);
} else if (item.indexOf("FILEMOL") >= 0) {
this.FileMolOnly.addLast(newMenu);
}if (item.indexOf("!FRAMES") >= 0) {
this.SingleModelOnly.addLast(newMenu);
} else if (item.indexOf("FRAMES") >= 0) {
this.FramesOnly.addLast(newMenu);
}if (item.indexOf("VIBRATION") >= 0) {
this.VibrationOnly.addLast(newMenu);
} else if (item.indexOf("SYMMETRY") >= 0) {
this.SymmetryOnly.addLast(newMenu);
}if (item.indexOf("SPECIAL") >= 0) this.Special.addLast(newMenu);
}, "~S,J.api.SC");
Clazz_overrideMethod(c$, "appGetMenuAsString", 
function(title){
return ( new J.popup.MainPopupResourceBundle(this.strMenuStructure, null)).getMenuAsText(title);
}, "~S");
Clazz_overrideMethod(c$, "getScriptForCallback", 
function(source, id, script){
var pt;
if (script === "" || id.endsWith("Checkbox")) return script;
if (script.indexOf("SELECT") == 0) {
return "select thisModel and (" + script.substring(6) + ")";
}if ((pt = id.lastIndexOf("[")) >= 0) {
id = id.substring(pt + 1);
if ((pt = id.indexOf("]")) >= 0) id = id.substring(0, pt);
id = id.$replace('_', ' ');
if (script.indexOf("[]") < 0) script = "[] " + script;
script = script.$replace('_', ' ');
return JU.PT.rep(script, "[]", id);
} else if (script.indexOf("?FILEROOT?") >= 0) {
script = JU.PT.rep(script, "FILEROOT?", this.modelSetRoot);
} else if (script.indexOf("?FILE?") >= 0) {
script = JU.PT.rep(script, "FILE?", this.modelSetFileName);
} else if (script.indexOf("?PdbId?") >= 0) {
script = JU.PT.rep(script, "PdbId?", "=xxxx");
}return script;
}, "J.api.SC,~S,~S");
Clazz_overrideMethod(c$, "appRestorePopupMenu", 
function(){
this.thisPopup = this.popupMenu;
if (this.vwr.isJSNoAWT || this.nFrankList < 2) return;
for (var i = this.nFrankList; --i > 0; ) {
var f = this.frankList[i];
this.helper.menuInsertSubMenu(f[0], f[1], (f[2]).intValue());
}
this.nFrankList = 1;
});
Clazz_overrideMethod(c$, "appUpdateSpecialCheckBoxValue", 
function(item, what, TF){
if (!this.updatingForShow && what.indexOf("#CONFIG") >= 0) {
this.configurationSelected = what;
this.updateConfigurationComputedMenu();
this.updateModelSetComputedMenu();
}}, "J.api.SC,~S,~B");
Clazz_defineMethod(c$, "setFrankMenu", 
function(id){
if (this.currentFrankId != null && this.currentFrankId === id && this.nFrankList > 0) return;
if (this.frankPopup == null) this.frankPopup = this.helper.menuCreatePopup("Frank", this.vwr.html5Applet);
this.thisPopup = this.frankPopup;
this.menuRemoveAll(this.frankPopup, 0);
this.menuCreateItem(this.frankPopup, this.getMenuText("mainMenuText"), "MAIN", "");
this.currentFrankId = id;
this.nFrankList = 0;
this.frankList[this.nFrankList++] =  Clazz_newArray(-1, [null, null, null]);
if (id != null) for (var i = id.indexOf(".", 2) + 1; ; ) {
var iNew = id.indexOf(".", i);
if (iNew < 0) break;
var menu = this.htMenus.get(id.substring(i, iNew));
this.frankList[this.nFrankList++] =  Clazz_newArray(-1, [menu.getParent(), menu, Integer.$valueOf(this.vwr.isJSNoAWT ? 0 : this.menuGetListPosition(menu))]);
this.menuAddSubMenu(this.frankPopup, menu);
i = iNew + 1;
}
this.thisPopup = this.popupMenu;
}, "~S");
Clazz_defineMethod(c$, "checkBoolean", 
function(key){
return (this.modelSetInfo != null && this.modelSetInfo.get(key) === Boolean.TRUE);
}, "~S");
Clazz_defineMethod(c$, "getViewerData", 
function(){
this.modelSetName = this.vwr.ms.modelSetName;
this.modelSetFileName = this.vwr.getModelSetFileName();
var i = this.modelSetFileName.lastIndexOf(".");
this.isZapped = ("zapped".equals(this.modelSetName));
if (this.isZapped || "string".equals(this.modelSetFileName) || "String[]".equals(this.modelSetFileName)) this.modelSetFileName = "";
this.modelSetRoot = this.modelSetFileName.substring(0, i < 0 ? this.modelSetFileName.length : i);
if (this.modelSetRoot.length == 0) this.modelSetRoot = "Jmol";
this.modelIndex = this.vwr.am.cmi;
this.modelCount = this.vwr.ms.mc;
this.ac = this.vwr.ms.getAtomCountInModel(this.modelIndex);
this.modelSetInfo = this.vwr.getModelSetAuxiliaryInfo();
this.modelInfo = this.vwr.ms.getModelAuxiliaryInfo(this.modelIndex);
if (this.modelInfo == null) this.modelInfo =  new java.util.Hashtable();
this.isPDB = this.checkBoolean(JV.JC.getBoolName(4));
this.isMultiFrame = (this.modelCount > 1);
this.hasSymmetry = !this.isPDB && this.modelInfo.containsKey("hasSymmetry");
this.isUnitCell = this.modelInfo.containsKey("unitCellParams");
this.fileHasUnitCell = (this.isPDB && this.isUnitCell || this.checkBoolean("fileHasUnitCell"));
this.isLastFrame = (this.modelIndex == this.modelCount - 1);
this.altlocs = this.vwr.ms.getAltLocListInModel(this.modelIndex);
this.isMultiConfiguration = (this.altlocs.length > 0);
this.isVibration = (this.vwr.modelHasVibrationVectors(this.modelIndex));
this.haveCharges = (this.vwr.ms.getPartialCharges() != null);
this.haveBFactors = (this.vwr.getBooleanProperty("haveBFactors"));
this.cnmrPeaks = this.modelInfo.get("jdxAtomSelect_13CNMR");
this.hnmrPeaks = this.modelInfo.get("jdxAtomSelect_1HNMR");
});
Clazz_overrideMethod(c$, "appCheckSpecialMenu", 
function(item, subMenu, word){
if ("modelSetMenu".equals(item)) {
this.nullModelSetName = word;
this.menuEnable(subMenu, false);
}}, "~S,J.api.SC,~S");
Clazz_overrideMethod(c$, "appUpdateForShow", 
function(){
if (this.updateMode == -1) return;
this.isTainted = true;
this.getViewerData();
this.updateMode = 2;
this.updateMenus();
});
Clazz_defineMethod(c$, "updateFileMenu", 
function(){
var menu = this.htMenus.get("fileMenu");
if (menu == null) return;
var text = this.getMenuText("writeFileTextVARIABLE");
menu = this.htMenus.get("writeFileTextVARIABLE");
if (menu == null) return;
var ignore = (this.modelSetFileName.equals("zapped") || this.modelSetFileName.equals(""));
if (ignore) {
this.menuSetLabel(menu, "");
this.menuEnable(menu, false);
} else {
this.menuSetLabel(menu, J.i18n.GT.o(J.i18n.GT.$(text), this.modelSetFileName));
this.menuEnable(menu, true);
}});
Clazz_defineMethod(c$, "getMenuText", 
function(key){
var str = this.menuText.getProperty(key);
return (str == null ? key : str);
}, "~S");
Clazz_defineMethod(c$, "updateSelectMenu", 
function(){
var menu = this.htMenus.get("selectMenuText");
if (menu == null) return;
this.menuEnable(menu, this.ac != 0);
this.menuSetLabel(menu, this.gti("selectMenuText", this.vwr.slm.getSelectionCount()));
});
Clazz_defineMethod(c$, "updateElementsComputedMenu", 
function(elementsPresentBitSet){
var menu = this.htMenus.get("elementsComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuEnable(menu, false);
if (elementsPresentBitSet == null) return;
for (var i = elementsPresentBitSet.nextSetBit(0); i >= 0; i = elementsPresentBitSet.nextSetBit(i + 1)) {
var elementName = JU.Elements.elementNameFromNumber(i);
var elementSymbol = JU.Elements.elementSymbolFromNumber(i);
var entryName = elementSymbol + " - " + elementName;
this.menuCreateItem(menu, entryName, "SELECT " + elementName, null);
}
for (var i = 4; i < JU.Elements.altElementMax; ++i) {
var n = JU.Elements.elementNumberMax + i;
if (elementsPresentBitSet.get(n)) {
n = JU.Elements.altElementNumberFromIndex(i);
var elementName = JU.Elements.elementNameFromNumber(n);
var elementSymbol = JU.Elements.elementSymbolFromNumber(n);
var entryName = elementSymbol + " - " + elementName;
this.menuCreateItem(menu, entryName, "SELECT " + elementName, null);
}}
this.menuEnable(menu, true);
}, "JU.BS");
Clazz_defineMethod(c$, "updateSpectraMenu", 
function(){
var menu = this.htMenus.get("spectraMenu");
if (menu == null) return;
var menuh = this.htMenus.get("hnmrMenu");
if (menuh != null) this.menuRemoveAll(menuh, 0);
var menuc = this.htMenus.get("cnmrMenu");
if (menuc != null) this.menuRemoveAll(menuc, 0);
this.menuRemoveAll(menu, 0);
var isOK =  new Boolean (this.setSpectraMenu(menuh, this.hnmrPeaks) | this.setSpectraMenu(menuc, this.cnmrPeaks)).valueOf();
if (isOK) {
if (menuh != null) this.menuAddSubMenu(menu, menuh);
if (menuc != null) this.menuAddSubMenu(menu, menuc);
}this.menuEnable(menu, isOK);
});
Clazz_defineMethod(c$, "setSpectraMenu", 
function(menu, peaks){
var n = (peaks == null ? 0 : peaks.size());
if (n == 0) return false;
if (menu == null) return false;
this.menuEnable(menu, false);
for (var i = 0; i < n; i++) {
var peak = peaks.get(i);
var title = JU.PT.getQuotedAttribute(peak, "title");
var atoms = JU.PT.getQuotedAttribute(peak, "atoms");
if (atoms != null) this.menuCreateItem(menu, title, "select visible & (@" + JU.PT.rep(atoms, ",", " or @") + ")", "Focus" + i);
}
this.menuEnable(menu, true);
return true;
}, "J.api.SC,JU.Lst");
Clazz_defineMethod(c$, "updateHeteroComputedMenu", 
function(htHetero){
var menu = this.htMenus.get("PDBheteroComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuEnable(menu, false);
if (htHetero == null) return;
var n = 0;
for (var hetero, $hetero = htHetero.entrySet().iterator (); $hetero.hasNext()&& ((hetero = $hetero.next ()) || true);) {
var heteroCode = hetero.getKey();
var heteroName = hetero.getValue();
if (heteroName.length > 20) heteroName = heteroName.substring(0, 20) + "...";
var entryName = heteroCode + " - " + heteroName;
this.menuCreateItem(menu, entryName, "SELECT [" + heteroCode + "]", null);
n++;
}
this.menuEnable(menu, (n > 0));
}, "java.util.Map");
Clazz_defineMethod(c$, "updateSurfMoComputedMenu", 
function(moData){
var menu = this.htMenus.get("surfMoComputedMenuText");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
var mos = (moData == null ? null : (moData.get("mos")));
var nOrb = (mos == null ? 0 : mos.size());
var text = this.getMenuText("surfMoComputedMenuText");
if (nOrb == 0) {
this.menuSetLabel(menu, J.i18n.GT.o(J.i18n.GT.$(text), ""));
this.menuEnable(menu, false);
return;
}this.menuSetLabel(menu, J.i18n.GT.i(J.i18n.GT.$(text), nOrb));
this.menuEnable(menu, true);
var subMenu = menu;
var nmod = (nOrb % 25);
if (nmod == 0) nmod = 25;
var pt = (nOrb > 25 ? 0 : -2147483648);
for (var i = nOrb; --i >= 0; ) {
if (pt >= 0 && (pt++ % nmod) == 0) {
if (pt == nmod + 1) nmod = 25;
var id = "mo" + pt + "Menu";
subMenu = this.menuNewSubMenu(Math.max(i + 2 - nmod, 1) + "..." + (i + 1), this.menuGetId(menu) + "." + id);
this.menuAddSubMenu(menu, subMenu);
this.htMenus.put(id, subMenu);
pt = 1;
}var mo = mos.get(i);
var entryName = "#" + (i + 1) + " " + (mo.containsKey("type") ? mo.get("type") + " " : "") + (mo.containsKey("symmetry") ? mo.get("symmetry") + " " : "") + (mo.containsKey("occupancy") ? "(" + mo.get("occupancy") + ") " : "") + (mo.containsKey("energy") ? mo.get("energy") : "");
var script = "mo " + (i + 1);
this.menuCreateItem(subMenu, entryName, script, null);
}
}, "java.util.Map");
Clazz_defineMethod(c$, "updateFileTypeDependentMenus", 
function(){
for (var i = this.NotPDB.size(); --i >= 0; ) this.menuEnable(this.NotPDB.get(i), !this.isPDB);

for (var i = this.PDBOnly.size(); --i >= 0; ) this.menuEnable(this.PDBOnly.get(i), this.isPDB);

for (var i = this.UnitcellOnly.size(); --i >= 0; ) this.menuEnable(this.UnitcellOnly.get(i), this.isUnitCell);

for (var i = this.FileUnitOnly.size(); --i >= 0; ) this.menuEnable(this.FileUnitOnly.get(i), this.isUnitCell || this.fileHasUnitCell);

for (var i = this.FileMolOnly.size(); --i >= 0; ) this.menuEnable(this.FileMolOnly.get(i), this.isUnitCell || this.fileHasUnitCell);

for (var i = this.SingleModelOnly.size(); --i >= 0; ) this.menuEnable(this.SingleModelOnly.get(i), this.isLastFrame);

for (var i = this.FramesOnly.size(); --i >= 0; ) this.menuEnable(this.FramesOnly.get(i), this.isMultiFrame);

for (var i = this.VibrationOnly.size(); --i >= 0; ) this.menuEnable(this.VibrationOnly.get(i), this.isVibration);

for (var i = this.SymmetryOnly.size(); --i >= 0; ) this.menuEnable(this.SymmetryOnly.get(i), this.hasSymmetry && this.isUnitCell);

for (var i = this.ChargesOnly.size(); --i >= 0; ) this.menuEnable(this.ChargesOnly.get(i), this.haveCharges);

for (var i = this.TemperatureOnly.size(); --i >= 0; ) this.menuEnable(this.TemperatureOnly.get(i), this.haveBFactors);

this.updateSignedAppletItems();
});
Clazz_defineMethod(c$, "updateSceneComputedMenu", 
function(){
var menu = this.htMenus.get("sceneComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuEnable(menu, false);
var scenes = this.vwr.ms.getInfoM("scenes");
if (scenes == null) return;
for (var i = 0; i < scenes.length; i++) this.menuCreateItem(menu, scenes[i], "restore scene " + JU.PT.esc(scenes[i]) + " 1.0", null);

this.menuEnable(menu, true);
});
Clazz_defineMethod(c$, "updatePDBResidueComputedMenus", 
function(){
var haveMenu = false;
var menu3 = this.htMenus.get("PDBaaResiduesComputedMenu");
if (menu3 != null) {
this.menuRemoveAll(menu3, 0);
this.menuEnable(menu3, false);
haveMenu = true;
}var menu1 = this.htMenus.get("PDBnucleicResiduesComputedMenu");
if (menu1 != null) {
this.menuRemoveAll(menu1, 0);
this.menuEnable(menu1, false);
haveMenu = true;
}var menu2 = this.htMenus.get("PDBcarboResiduesComputedMenu");
if (menu2 != null) {
this.menuRemoveAll(menu2, 0);
this.menuEnable(menu2, false);
haveMenu = true;
}if (this.modelSetInfo == null || !haveMenu) return;
var n = (this.modelIndex < 0 ? 0 : this.modelIndex + 1);
var lists = (this.modelSetInfo.get("group3Lists"));
this.group3List = (lists == null ? null : lists[n]);
this.group3Counts = (lists == null ? null : (this.modelSetInfo.get("group3Counts"))[n]);
if (this.group3List == null) return;
var nItems = 0;
var groupList = JM.Group.standardGroupList;
if (menu3 != null) {
for (var i = 1; i < 24; ++i) nItems += this.updateGroup3List(menu3, groupList.substring(i * 6 - 4, i * 6 - 1).trim());

nItems += this.augmentGroup3List(menu3, "p>", true);
this.menuEnable(menu3, (nItems > 0));
this.menuEnable(this.htMenus.get("PDBproteinMenu"), (nItems > 0));
}if (menu1 != null) {
nItems = this.augmentGroup3List(menu1, "n>", false);
this.menuEnable(menu1, nItems > 0);
this.menuEnable(this.htMenus.get("PDBnucleicMenu"), (nItems > 0));
var dssr = (nItems > 0 && this.modelIndex >= 0 ? this.vwr.ms.getInfo(this.modelIndex, "dssr") : null);
if (dssr != null) this.setSecStrucMenu(this.htMenus.get("aaStructureMenu"), dssr);
}if (menu2 != null) {
nItems = this.augmentGroup3List(menu2, "c>", false);
this.menuEnable(menu2, nItems > 0);
this.menuEnable(this.htMenus.get("PDBcarboMenu"), (nItems > 0));
}});
Clazz_defineMethod(c$, "setSecStrucMenu", 
function(menu, dssr){
var counts = dssr.get("counts");
if (counts == null) return false;
var keys =  new Array(counts.size());
counts.keySet().toArray(keys);
java.util.Arrays.sort(keys);
if (keys.length == 0) return false;
menu.removeAll();
for (var i = 0; i < keys.length; i++) this.menuCreateItem(menu, keys[i] + " (" + counts.get(keys[i]) + ")", "select modelIndex=" + this.modelIndex + " && within('dssr', '" + keys[i] + "');", null);

return true;
}, "J.api.SC,java.util.Map");
Clazz_defineMethod(c$, "updateGroup3List", 
function(menu, name){
var nItems = 0;
var n = this.group3Counts[Clazz_doubleToInt(this.group3List.indexOf(name) / 6)];
name = name.trim();
var script = null;
if (n > 0) {
script = "SELECT " + name;
name += "  (" + n + ")";
nItems++;
}var item = this.menuCreateItem(menu, name, script, this.menuGetId(menu) + "." + name);
if (n == 0) this.menuEnable(item, false);
return nItems;
}, "J.api.SC,~S");
Clazz_defineMethod(c$, "augmentGroup3List", 
function(menu, type, addSeparator){
var pt = 138;
var nItems = 0;
while (true) {
pt = this.group3List.indexOf(type, pt);
if (pt < 0) break;
if (nItems++ == 0 && addSeparator) this.menuAddSeparator(menu);
var n = this.group3Counts[Clazz_doubleToInt(pt / 6)];
var heteroCode = this.group3List.substring(pt + 2, pt + 5);
var name = heteroCode + "  (" + n + ")";
this.menuCreateItem(menu, name, "SELECT [" + heteroCode + "]", this.menuGetId(menu) + "." + name);
pt++;
}
return nItems;
}, "J.api.SC,~S,~B");
Clazz_defineMethod(c$, "updateSYMMETRYComputedMenus", 
function(){
this.updateSYMMETRYSelectComputedMenu();
this.updateSYMMETRYShowComputedMenu();
});
Clazz_defineMethod(c$, "updateSYMMETRYShowComputedMenu", 
function(){
var menu = this.htMenus.get("SYMMETRYShowComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuEnable(menu, false);
if (!this.hasSymmetry || this.modelIndex < 0) return;
var info = this.vwr.getProperty("DATA_API", "spaceGroupInfo", null);
if (info == null) return;
var infolist = info.get("operations");
if (infolist == null) return;
var name = info.get("spaceGroupName");
this.menuSetLabel(menu, name == null ? J.i18n.GT.$("Space Group") : name);
var subMenu = menu;
var pt = (infolist.length > 25 ? 0 : -2147483648);
for (var i = 0; i < infolist.length; i++) {
if (pt >= 0 && (pt++ % 25) == 0) {
var id = "drawsymop" + pt + "Menu";
subMenu = this.menuNewSubMenu((i + 1) + "..." + Math.min(i + 25, infolist.length), this.menuGetId(menu) + "." + id);
this.menuAddSubMenu(menu, subMenu);
this.htMenus.put(id, subMenu);
pt = 1;
}if (i == 0) this.menuEnable(this.menuCreateItem(subMenu, J.i18n.GT.$("none"), "draw sym_* delete", null), true);
var sym = infolist[i][1];
if (sym.indexOf("x1") < 0) sym = infolist[i][0];
var entryName = (i + 1) + " " + infolist[i][2] + " (" + sym + ")";
this.menuEnable(this.menuCreateItem(subMenu, entryName, "draw SYMOP " + (i + 1), null), true);
}
this.menuEnable(menu, true);
});
Clazz_defineMethod(c$, "updateSYMMETRYSelectComputedMenu", 
function(){
var menu = this.htMenus.get("SYMMETRYSelectComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuEnable(menu, false);
if (!this.hasSymmetry || this.modelIndex < 0) return;
var list = this.modelInfo.get("symmetryOperations");
if (list == null) return;
var enableSymop = (this.vwr.getOperativeSymmetry() != null);
var subMenu = menu;
var nmod = 25;
var pt = (list.length > 25 ? 0 : -2147483648);
for (var i = 0; i < list.length; i++) {
if (pt >= 0 && (pt++ % nmod) == 0) {
var id = "symop" + pt + "Menu";
subMenu = this.menuNewSubMenu((i + 1) + "..." + Math.min(i + 25, list.length), this.menuGetId(menu) + "." + id);
this.menuAddSubMenu(menu, subMenu);
this.htMenus.put(id, subMenu);
pt = 1;
}var entryName = "symop=" + (i + 1) + " # " + list[i];
this.menuEnable(this.menuCreateItem(subMenu, entryName, "SELECT symop=" + (i + 1), null), enableSymop);
}
this.menuEnable(menu, true);
});
Clazz_defineMethod(c$, "updateFRAMESbyModelComputedMenu", 
function(){
var menu = this.htMenus.get("FRAMESbyModelComputedMenu");
if (menu == null) return;
this.menuEnable(menu, (this.modelCount > 0));
this.menuSetLabel(menu, (this.modelIndex < 0 ? this.gti("allModelsText", this.modelCount) : this.gto("modelMenuText", (this.modelIndex + 1) + "/" + this.modelCount)));
this.menuRemoveAll(menu, 0);
if (this.modelCount < 1) return;
if (this.modelCount > 1) this.menuCreateCheckboxItem(menu, J.i18n.GT.$("All"), "frame 0 ##", null, (this.modelIndex < 0), false);
var subMenu = menu;
var pt = (this.modelCount > 25 ? 0 : -2147483648);
for (var i = 0; i < this.modelCount; i++) {
if (pt >= 0 && (pt++ % 25) == 0) {
var id = "model" + pt + "Menu";
subMenu = this.menuNewSubMenu((i + 1) + "..." + Math.min(i + 25, this.modelCount), this.menuGetId(menu) + "." + id);
this.menuAddSubMenu(menu, subMenu);
this.htMenus.put(id, subMenu);
pt = 1;
}var script = "" + this.vwr.getModelNumberDotted(i);
var entryName = this.vwr.getModelName(i);
var spectrumTypes = this.vwr.ms.getInfo(i, "spectrumTypes");
if (spectrumTypes != null && entryName.startsWith(spectrumTypes)) spectrumTypes = null;
if (!entryName.equals(script)) {
var ipt = entryName.indexOf(";PATH");
if (ipt >= 0) entryName = entryName.substring(0, ipt);
if (entryName.indexOf("Model[") == 0 && (ipt = entryName.indexOf("]:")) >= 0) entryName = entryName.substring(ipt + 2);
entryName = script + ": " + entryName;
}if (entryName.length > 60) entryName = entryName.substring(0, 55) + "...";
if (spectrumTypes != null) entryName += " (" + spectrumTypes + ")";
this.menuCreateCheckboxItem(subMenu, entryName, "model " + script + " ##", null, (this.modelIndex == i), false);
}
});
Clazz_defineMethod(c$, "updateConfigurationComputedMenu", 
function(){
var menu = this.htMenus.get("configurationComputedMenu");
if (menu == null) return;
this.menuEnable(menu, this.isMultiConfiguration);
if (!this.isMultiConfiguration) return;
var nAltLocs = this.altlocs.length;
this.menuSetLabel(menu, this.gti("configurationMenuText", nAltLocs));
this.menuRemoveAll(menu, 0);
var script = "hide none ##CONFIG";
this.menuCreateCheckboxItem(menu, J.i18n.GT.$("All"), script, null, (this.updateMode == 1 && this.configurationSelected.equals(script)), false);
for (var i = 0; i < nAltLocs; i++) {
script = "configuration " + (i + 1) + "; hide thisModel and not selected ##CONFIG";
var entryName = "" + (i + 1) + " -- \"" + this.altlocs.charAt(i) + "\"";
this.menuCreateCheckboxItem(menu, entryName, script, null, (this.updateMode == 1 && this.configurationSelected.equals(script)), false);
}
});
Clazz_defineMethod(c$, "updateModelSetComputedMenu", 
function(){
var menu = this.htMenus.get("modelSetMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
this.menuSetLabel(menu, this.nullModelSetName);
this.menuEnable(menu, false);
for (var i = this.noZapped.length; --i >= 0; ) this.menuEnable(this.htMenus.get(this.noZapped[i]), !this.isZapped);

if (this.modelSetName == null || this.isZapped) return;
if (this.isMultiFrame) {
this.modelSetName = this.gti("modelSetCollectionText", this.modelCount);
if (this.modelSetName.length > this.titleWidthMax) this.modelSetName = this.modelSetName.substring(0, this.titleWidthMax) + "...";
} else if (this.vwr.getBooleanProperty("hideNameInPopup")) {
this.modelSetName = this.getMenuText("hiddenModelSetText");
} else if (this.modelSetName.length > this.titleWidthMax) {
this.modelSetName = this.modelSetName.substring(0, this.titleWidthMax) + "...";
}this.menuSetLabel(menu, this.modelSetName);
this.menuEnable(menu, true);
this.menuEnable(this.htMenus.get("computationMenu"), this.ac <= 100);
this.addMenuItem(menu, this.gti("atomsText", this.ac));
this.addMenuItem(menu, this.gti("bondsText", this.vwr.ms.getBondCountInModel(this.modelIndex)));
if (this.isPDB) {
this.menuAddSeparator(menu);
this.addMenuItem(menu, this.gti("groupsText", this.vwr.ms.getGroupCountInModel(this.modelIndex)));
this.addMenuItem(menu, this.gti("chainsText", this.vwr.ms.getChainCountInModelWater(this.modelIndex, false)));
this.addMenuItem(menu, this.gti("polymersText", this.vwr.ms.getBioPolymerCountInModel(this.modelIndex)));
var submenu = this.htMenus.get("BiomoleculesMenu");
if (submenu == null) {
submenu = this.menuNewSubMenu(J.i18n.GT.$(this.getMenuText("biomoleculesMenuText")), this.menuGetId(menu) + ".biomolecules");
this.menuAddSubMenu(menu, submenu);
}this.menuRemoveAll(submenu, 0);
this.menuEnable(submenu, false);
var biomolecules;
if (this.modelIndex >= 0 && (biomolecules = this.vwr.ms.getInfo(this.modelIndex, "biomolecules")) != null) {
this.menuEnable(submenu, true);
var nBiomolecules = biomolecules.size();
for (var i = 0; i < nBiomolecules; i++) {
var script = (this.isMultiFrame ? "" : "save orientation;load \"\" FILTER \"biomolecule " + (i + 1) + "\";restore orientation;");
var nAtoms = (biomolecules.get(i).get("atomCount")).intValue();
var entryName = this.gto(this.isMultiFrame ? "biomoleculeText" : "loadBiomoleculeText",  Clazz_newArray(-1, [Integer.$valueOf(i + 1), Integer.$valueOf(nAtoms)]));
this.menuCreateItem(submenu, entryName, script, null);
}
}}if (this.isApplet && !this.vwr.getBooleanProperty("hideNameInPopup")) {
this.menuAddSeparator(menu);
this.menuCreateItem(menu, this.gto("viewMenuText", this.modelSetFileName), "show url", null);
}});
Clazz_defineMethod(c$, "gti", 
function(s, n){
return J.i18n.GT.i(J.i18n.GT.$(this.getMenuText(s)), n);
}, "~S,~N");
Clazz_defineMethod(c$, "gto", 
function(s, o){
return J.i18n.GT.o(J.i18n.GT.$(this.getMenuText(s)), o);
}, "~S,~O");
Clazz_defineMethod(c$, "updateAboutSubmenu", 
function(){
if (this.isApplet) this.setText("APPLETid", this.vwr.appletName);
{
}});
Clazz_defineMethod(c$, "updateLanguageSubmenu", 
function(){
var menu = this.htMenus.get("languageComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
var language = J.i18n.GT.getLanguage();
var id = this.menuGetId(menu);
var languages = J.i18n.GT.getLanguageList(null);
for (var i = 0, p = 0; i < languages.length; i++) {
if (language.equals(languages[i].code)) languages[i].display = true;
if (languages[i].display) {
var code = languages[i].code;
var name = languages[i].language;
var nativeName = languages[i].nativeLanguage;
var menuLabel = code + " - " + J.i18n.GT.$(name);
if ((nativeName != null) && (!nativeName.equals(J.i18n.GT.$(name)))) {
menuLabel += " - " + nativeName;
}if (p++ > 0 && (p % 4 == 1)) this.menuAddSeparator(menu);
this.menuCreateCheckboxItem(menu, menuLabel, "language = \"" + code + "\" ##" + name, id + "." + code, language.equals(code), false);
}}
});
Clazz_defineMethod(c$, "updateSpecialMenuItem", 
function(m){
m.setText(this.getSpecialLabel(m.getName(), m.getText()));
}, "J.api.SC");
Clazz_defineMethod(c$, "getSpecialLabel", 
function(name, text){
var pt = text.indexOf(" (");
if (pt < 0) pt = text.length;
var info = null;
if (name.indexOf("captureLooping") >= 0) info = (this.vwr.am.animationReplayMode == 1073742070 ? "ONCE" : "LOOP");
 else if (name.indexOf("captureFps") >= 0) info = "" + this.vwr.getInt(553648132);
 else if (name.indexOf("captureMenu") >= 0) info = (this.vwr.captureParams == null ? J.i18n.GT.$("not capturing") : this.vwr.fm.getFilePath(this.vwr.captureParams.get("captureFileName"), false, true) + " " + this.vwr.captureParams.get("captureCount"));
return (info == null ? text : text.substring(0, pt) + " (" + info + ")");
}, "~S,~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.popup");
Clazz_load(["J.popup.PopupResource", "JV.JC"], "J.popup.MainPopupResourceBundle", ["JU.PT", "J.i18n.GT", "JV.Viewer"], function(){
var c$ = Clazz_declareType(J.popup, "MainPopupResourceBundle", J.popup.PopupResource);
Clazz_overrideMethod(c$, "getMenuName", 
function(){
return "popupMenu";
});
Clazz_overrideMethod(c$, "buildStructure", 
function(menuStructure){
this.addItems(J.popup.MainPopupResourceBundle.menuContents);
this.addItems(J.popup.MainPopupResourceBundle.structureContents);
if (menuStructure != null) this.setStructure(menuStructure,  new J.i18n.GT());
}, "~S");
c$.Box = Clazz_defineMethod(c$, "Box", 
function(cmd){
return "if (showBoundBox or showUnitcell) {" + cmd + "} else {boundbox on;" + cmd + ";boundbox off}";
}, "~S");
Clazz_overrideMethod(c$, "getWordContents", 
function(){
var wasTranslating = J.i18n.GT.setDoTranslate(true);
var vdw = J.i18n.GT.$("{0}% van der Waals");
var exm = J.i18n.GT.$("Export {0} 3D model");
var exi = J.i18n.GT.$("Export {0} image");
var rld = J.i18n.GT.$("Reload {0}");
var scl = J.i18n.GT.$("Scale {0}");
var ang = J.i18n.GT.$("{0} \u00C5");
var pxl = J.i18n.GT.$("{0} px");
var words =  Clazz_newArray(-1, ["cnmrMenu", J.i18n.GT.$("13C-NMR"), "hnmrMenu", J.i18n.GT.$("1H-NMR"), "aboutMenu", J.i18n.GT.$("About..."), "negativeCharge", J.i18n.GT.$("Acidic Residues (-)"), "allModelsText", J.i18n.GT.$("All {0} models"), "allHetero", J.i18n.GT.$("All PDB \"HETATM\""), "Solvent", J.i18n.GT.$("All Solvent"), "Water", J.i18n.GT.$("All Water"), "selectAll", J.i18n.GT.$("All"), "allProtein", null, "allNucleic", null, "allCarbo", null, "altloc#PDB", J.i18n.GT.$("Alternative Location"), "amino#PDB", J.i18n.GT.$("Amino Acid"), "byAngstromMenu", J.i18n.GT.$("Angstrom Width"), "animModeMenu", J.i18n.GT.$("Animation Mode"), "FRAMESanimateMenu", J.i18n.GT.$("Animation"), "atPairs", J.i18n.GT.$("AT pairs"), "atomMenu", J.i18n.GT.$("Atoms"), "[color_atoms]Menu", null, "atomsText", J.i18n.GT.$("atoms: {0}"), "auPairs", J.i18n.GT.$("AU pairs"), "[color_axes]Menu", J.i18n.GT.$("Axes"), "showAxesCB", null, "[set_axes]Menu", null, "axisA", J.i18n.GT.$("Axis a"), "axisB", J.i18n.GT.$("Axis b"), "axisC", J.i18n.GT.$("Axis c"), "axisX", J.i18n.GT.$("Axis x"), "axisY", J.i18n.GT.$("Axis y"), "axisZ", J.i18n.GT.$("Axis z"), "back", J.i18n.GT.$("Back"), "proteinBackbone", J.i18n.GT.$("Backbone"), "nucleicBackbone", null, "backbone", null, "[color_backbone]Menu", null, "[color_background]Menu", J.i18n.GT.$("Background"), "renderBallAndStick", J.i18n.GT.$("Ball and Stick"), "nucleicBases", J.i18n.GT.$("Bases"), "positiveCharge", J.i18n.GT.$("Basic Residues (+)"), "best", J.i18n.GT.$("Best"), "biomoleculeText", J.i18n.GT.$("biomolecule {0} ({1} atoms)"), "biomoleculesMenuText", J.i18n.GT.$("Biomolecules"), "black", J.i18n.GT.$("Black"), "blue", J.i18n.GT.$("Blue"), "bondMenu", J.i18n.GT.$("Bonds"), "[color_bonds]Menu", null, "bondsText", J.i18n.GT.$("bonds: {0}"), "bottom", J.i18n.GT.$("Bottom"), "[color_boundbox]Menu", J.i18n.GT.$("Boundbox"), "[set_boundbox]Menu", null, "showBoundBoxCB", null, "PDBheteroComputedMenu", J.i18n.GT.$("By HETATM"), "PDBaaResiduesComputedMenu", J.i18n.GT.$("By Residue Name"), "PDBnucleicResiduesComputedMenu", null, "PDBcarboResiduesComputedMenu", null, "schemeMenu", J.i18n.GT.$("By Scheme"), "[color_]schemeMenu", null, "hbondCalc", J.i18n.GT.$("Calculate"), "SIGNEDJAVAcaptureRock", J.i18n.GT.$("Capture rock"), "SIGNEDJAVAcaptureSpin", J.i18n.GT.$("Capture spin"), "SIGNEDJAVAcaptureMenuSPECIAL", J.i18n.GT.$("Capture"), "PDBcarboMenu", J.i18n.GT.$("Carbohydrate"), "cartoonRockets", J.i18n.GT.$("Cartoon Rockets"), "PDBrenderCartoonsOnly", J.i18n.GT.$("Cartoon"), "cartoon", null, "[color_cartoon]sMenu", null, "pickCenter", J.i18n.GT.$("Center"), "labelCentered", J.i18n.GT.$("Centered"), "chain#PDB", J.i18n.GT.$("Chain"), "chainsText", J.i18n.GT.$("chains: {0}"), "colorChargeMenu", J.i18n.GT.$("Charge"), "measureAngle", J.i18n.GT.$("Click for angle measurement"), "measureDistance", J.i18n.GT.$("Click for distance measurement"), "measureTorsion", J.i18n.GT.$("Click for torsion (dihedral) measurement"), "PDBmeasureSequence", J.i18n.GT.$("Click two atoms to display a sequence in the console"), "modelSetCollectionText", J.i18n.GT.$("Collection of {0} models"), "colorMenu", J.i18n.GT.$("Color"), "computationMenu", J.i18n.GT.$("Computation"), "configurationMenuText", J.i18n.GT.$("Configurations ({0})"), "configurationComputedMenu", J.i18n.GT.$("Configurations"), "showConsole", J.i18n.GT.$("Console"), "renderCpkSpacefill", J.i18n.GT.$("CPK Spacefill"), "stereoCrossEyed", J.i18n.GT.$("Cross-eyed viewing"), "showState", J.i18n.GT.$("Current state"), "cyan", J.i18n.GT.$("Cyan"), "darkgray", J.i18n.GT.$("Dark Gray"), "measureDelete", J.i18n.GT.$("Delete measurements"), "SIGNEDJAVAcaptureOff", J.i18n.GT.$("Disable capturing"), "hideNotSelectedCB", J.i18n.GT.$("Display Selected Only"), "distanceAngstroms", J.i18n.GT.$("Distance units Angstroms"), "distanceNanometers", J.i18n.GT.$("Distance units nanometers"), "distancePicometers", J.i18n.GT.$("Distance units picometers"), "distanceHz", J.i18n.GT.$("Distance units hz (NMR J-coupling)"), "ssbondMenu", J.i18n.GT.$("Disulfide Bonds"), "[color_ssbonds]Menu", null, "DNA", J.i18n.GT.$("DNA"), "surfDots", J.i18n.GT.$("Dot Surface"), "dotted", J.i18n.GT.$("Dotted"), "measureOff", J.i18n.GT.$("Double-Click begins and ends all measurements"), "cpk", J.i18n.GT.$("Element (CPK)"), "elementsComputedMenu", J.i18n.GT.$("Element"), "SIGNEDJAVAcaptureEnd", J.i18n.GT.$("End capturing"), "exportMenu", J.i18n.GT.$("Export"), "extractMOL", J.i18n.GT.$("Extract MOL data"), "showFile", J.i18n.GT.$("File Contents"), "showFileHeader", J.i18n.GT.$("File Header"), "fileMenu", J.i18n.GT.$("File"), "formalcharge", J.i18n.GT.$("Formal Charge"), "front", J.i18n.GT.$("Front"), "gcPairs", J.i18n.GT.$("GC pairs"), "gold", J.i18n.GT.$("Gold"), "gray", J.i18n.GT.$("Gray"), "green", J.i18n.GT.$("Green"), "group#PDB", J.i18n.GT.$("Group"), "groupsText", J.i18n.GT.$("groups: {0}"), "PDBheteroMenu", J.i18n.GT.$("Hetero"), "off#axes", J.i18n.GT.$("Hide"), "showHistory", J.i18n.GT.$("History"), "hbondMenu", J.i18n.GT.$("Hydrogen Bonds"), "[color_hbonds]Menu", null, "pickIdent", J.i18n.GT.$("Identity"), "indigo", J.i18n.GT.$("Indigo"), "none", J.i18n.GT.$("Inherit"), "invertSelection", J.i18n.GT.$("Invert Selection"), "showIsosurface", J.i18n.GT.$("Isosurface JVXL data"), "help", J.i18n.GT.$("Jmol Script Commands"), "pickLabel", J.i18n.GT.$("Label"), "labelMenu", J.i18n.GT.$("Labels"), "[color_labels]Menu", null, "languageComputedMenu", J.i18n.GT.$("Language"), "left", J.i18n.GT.$("Left"), "Ligand", J.i18n.GT.$("Ligand"), "lightgray", J.i18n.GT.$("Light Gray"), "measureList", J.i18n.GT.$("List measurements"), "loadBiomoleculeText", J.i18n.GT.$("load biomolecule {0} ({1} atoms)"), "SIGNEDloadFileUnitCell", J.i18n.GT.$("Load full unit cell"), "loadMenu", J.i18n.GT.$("Load"), "loop", J.i18n.GT.$("Loop"), "labelLowerLeft", J.i18n.GT.$("Lower Left"), "labelLowerRight", J.i18n.GT.$("Lower Right"), "mainMenuText", J.i18n.GT.$("Main Menu"), "opaque", J.i18n.GT.$("Make Opaque"), "surfOpaque", null, "translucent", J.i18n.GT.$("Make Translucent"), "surfTranslucent", null, "maroon", J.i18n.GT.$("Maroon"), "measureMenu", J.i18n.GT.$("Measurements"), "showMeasure", null, "modelMenuText", J.i18n.GT.$("model {0}"), "hiddenModelSetText", J.i18n.GT.$("Model information"), "modelkit", J.i18n.GT.$("Model kit"), "showModel", J.i18n.GT.$("Model"), "FRAMESbyModelComputedMenu", J.i18n.GT.$("Model/Frame"), "modelKitMode", J.i18n.GT.$("modelKitMode"), "surf2MEP", J.i18n.GT.$("Molecular Electrostatic Potential (range -0.1 0.1)"), "surfMEP", J.i18n.GT.$("Molecular Electrostatic Potential (range ALL)"), "showMo", J.i18n.GT.$("Molecular orbital JVXL data"), "surfMoComputedMenuText", J.i18n.GT.$("Molecular Orbitals ({0})"), "surfMolecular", J.i18n.GT.$("Molecular Surface"), "molecule", J.i18n.GT.$("Molecule"), "monomer#PDB", J.i18n.GT.$("Monomer"), "mouse", J.i18n.GT.$("Mouse Manual"), "nextframe", J.i18n.GT.$("Next Frame"), "modelSetMenu", J.i18n.GT.$("No atoms loaded"), "exceptWater", J.i18n.GT.$("Nonaqueous HETATM") + " (hetero and not water)", "nonWaterSolvent", J.i18n.GT.$("Nonaqueous Solvent") + " (solvent and not water)", "PDBnoneOfTheAbove", J.i18n.GT.$("None of the above"), "selectNone", J.i18n.GT.$("None"), "stereoNone", null, "labelNone", null, "nonpolar", J.i18n.GT.$("Nonpolar Residues"), "PDBnucleicMenu", J.i18n.GT.$("Nucleic"), "atomNone", J.i18n.GT.$("Off"), "bondNone", null, "hbondNone", null, "ssbondNone", null, "structureNone", null, "vibrationOff", null, "vectorOff", null, "spinOff", null, "pickOff", null, "surfOff", null, "olive", J.i18n.GT.$("Olive"), "bondWireframe", J.i18n.GT.$("On"), "hbondWireframe", null, "ssbondWireframe", null, "vibrationOn", null, "vectorOn", null, "spinOn", null, "on", null, "SIGNEDloadPdb", J.i18n.GT.$("Get PDB file"), "SIGNEDloadMol", J.i18n.GT.$("Get MOL file"), "SIGNEDloadFile", J.i18n.GT.$("Open local file"), "SIGNEDloadScript", J.i18n.GT.$("Open script"), "SIGNEDloadUrl", J.i18n.GT.$("Open URL"), "minimize", J.i18n.GT.$("Optimize structure"), "orange", J.i18n.GT.$("Orange"), "orchid", J.i18n.GT.$("Orchid"), "showOrient", J.i18n.GT.$("Orientation"), "palindrome", J.i18n.GT.$("Palindrome"), "partialcharge", J.i18n.GT.$("Partial Charge"), "pause", J.i18n.GT.$("Pause"), "perspectiveDepthCB", J.i18n.GT.$("Perspective Depth"), "byPixelMenu", J.i18n.GT.$("Pixel Width"), "onceThrough", J.i18n.GT.$("Play Once"), "play", J.i18n.GT.$("Play"), "polar", J.i18n.GT.$("Polar Residues"), "polymersText", J.i18n.GT.$("polymers: {0}"), "labelPositionMenu", J.i18n.GT.$("Position Label on Atom"), "prevframe", J.i18n.GT.$("Previous Frame"), "PDBproteinMenu", J.i18n.GT.$("Protein"), "colorrasmolCB", J.i18n.GT.$("RasMol Colors"), "red", J.i18n.GT.$("Red"), "stereoRedBlue", J.i18n.GT.$("Red+Blue glasses"), "stereoRedCyan", J.i18n.GT.$("Red+Cyan glasses"), "stereoRedGreen", J.i18n.GT.$("Red+Green glasses"), "SIGNEDJAVAcaptureOn", J.i18n.GT.$("Re-enable capturing"), "FILEUNITninePoly", J.i18n.GT.$("Reload + Polyhedra"), "reload", J.i18n.GT.$("Reload"), "restart", J.i18n.GT.$("Restart"), "resume", J.i18n.GT.$("Resume"), "playrev", J.i18n.GT.$("Reverse"), "rewind", J.i18n.GT.$("Rewind"), "ribbons", J.i18n.GT.$("Ribbons"), "[color_ribbon]sMenu", null, "right", J.i18n.GT.$("Right"), "RNA", J.i18n.GT.$("RNA"), "rockets", J.i18n.GT.$("Rockets"), "[color_rockets]Menu", null, "salmon", J.i18n.GT.$("Salmon"), "writeFileTextVARIABLE", J.i18n.GT.$("Save a copy of {0}"), "SIGNEDwriteJmol", J.i18n.GT.$("Save as PNG/JMOL (image+zip)"), "SIGNEDwriteIsosurface", J.i18n.GT.$("Save JVXL isosurface"), "writeHistory", J.i18n.GT.$("Save script with history"), "writeState", J.i18n.GT.$("Save script with state"), "saveMenu", J.i18n.GT.$("Save"), "sceneComputedMenu", J.i18n.GT.$("Scenes"), "renderSchemeMenu", J.i18n.GT.$("Scheme"), "aaStructureMenu", J.i18n.GT.$("Secondary Structure"), "structure#PDB", null, "selectMenuText", J.i18n.GT.$("Select ({0})"), "pickAtom", J.i18n.GT.$("Select atom"), "dragAtom", J.i18n.GT.$("Drag atom"), "dragMolecule", J.i18n.GT.$("Drag molecule"), "PDBpickChain", J.i18n.GT.$("Select chain"), "pickElement", J.i18n.GT.$("Select element"), "PDBpickGroup", J.i18n.GT.$("Select group"), "pickMolecule", J.i18n.GT.$("Select molecule"), "SYMMETRYpickSite", J.i18n.GT.$("Select site"), "showSelectionsCB", J.i18n.GT.$("Selection Halos"), "SIGNEDJAVAcaptureFpsSPECIAL", J.i18n.GT.$("Set capture replay rate"), "[set_spin_FPS]Menu", J.i18n.GT.$("Set FPS"), "FRAMESanimFpsMenu", null, "PDBhbondBackbone", J.i18n.GT.$("Set H-Bonds Backbone"), "PDBhbondSidechain", J.i18n.GT.$("Set H-Bonds Side Chain"), "pickingMenu", J.i18n.GT.$("Set picking"), "PDBssbondBackbone", J.i18n.GT.$("Set SS-Bonds Backbone"), "PDBssbondSidechain", J.i18n.GT.$("Set SS-Bonds Side Chain"), "[set_spin_X]Menu", J.i18n.GT.$("Set X Rate"), "[set_spin_Y]Menu", J.i18n.GT.$("Set Y Rate"), "[set_spin_Z]Menu", J.i18n.GT.$("Set Z Rate"), "shapely#PDB", J.i18n.GT.$("Shapely"), "showHydrogensCB", J.i18n.GT.$("Show Hydrogens"), "showMeasurementsCB", J.i18n.GT.$("Show Measurements"), "SYMMETRYpickSymmetry", J.i18n.GT.$("Show symmetry operation"), "showMenu", J.i18n.GT.$("Show"), "proteinSideChains", J.i18n.GT.$("Side Chains"), "slateblue", J.i18n.GT.$("Slate Blue"), "SYMMETRYShowComputedMenu", J.i18n.GT.$("Space Group"), "showSpacegroup", null, "spectraMenu", J.i18n.GT.$("Spectra"), "spinMenu", J.i18n.GT.$("Spin"), "pickSpin", null, "SIGNEDJAVAcaptureBegin", J.i18n.GT.$("Start capturing"), "stereoMenu", J.i18n.GT.$("Stereographic"), "renderSticks", J.i18n.GT.$("Sticks"), "stop", J.i18n.GT.$("Stop"), "strands", J.i18n.GT.$("Strands"), "[color_strands]Menu", null, "PDBstructureMenu", J.i18n.GT.$("Structures"), "colorPDBStructuresMenu", null, "renderMenu", J.i18n.GT.$("Style"), "[color_isosurface]Menu", J.i18n.GT.$("Surfaces"), "surfaceMenu", null, "SYMMETRYSelectComputedMenu", J.i18n.GT.$("Symmetry"), "SYMMETRYshowSymmetry", null, "FILEUNITMenu", null, "systemMenu", J.i18n.GT.$("System"), "relativeTemperature#BFACTORS", J.i18n.GT.$("Temperature (Relative)"), "fixedTemperature#BFACTORS", J.i18n.GT.$("Temperature (Fixed)"), "SIGNEDJAVAcaptureLoopingSPECIAL", J.i18n.GT.$("Toggle capture looping"), "top", JU.PT.split(J.i18n.GT.$("Top[as in \"view from the top, from above\" - (translators: remove this bracketed part]"), "[")[0], "PDBrenderTraceOnly", J.i18n.GT.$("Trace"), "trace", null, "[color_trace]Menu", null, "translations", J.i18n.GT.$("Translations"), "noCharge", J.i18n.GT.$("Uncharged Residues"), "[color_UNITCELL]Menu", J.i18n.GT.$("Unit cell"), "UNITCELLshow", null, "[set_UNITCELL]Menu", null, "showUNITCELLCB", null, "labelUpperLeft", J.i18n.GT.$("Upper Left"), "labelUpperRight", J.i18n.GT.$("Upper Right"), "surfVDW", J.i18n.GT.$("van der Waals Surface"), "VIBRATIONvectorMenu", J.i18n.GT.$("Vectors"), "property_vxyz#VIBRATION", null, "[color_vectors]Menu", null, "VIBRATIONMenu", J.i18n.GT.$("Vibration"), "viewMenuText", J.i18n.GT.$("View {0}"), "viewMenu", J.i18n.GT.$("View"), "violet", J.i18n.GT.$("Violet"), "stereoWallEyed", J.i18n.GT.$("Wall-eyed viewing"), "white", J.i18n.GT.$("White"), "renderWireframe", J.i18n.GT.$("Wireframe"), "labelName", J.i18n.GT.$("With Atom Name"), "labelNumber", J.i18n.GT.$("With Atom Number"), "labelSymbol", J.i18n.GT.$("With Element Symbol"), "yellow", J.i18n.GT.$("Yellow"), "zoomIn", J.i18n.GT.$("Zoom In"), "zoomOut", J.i18n.GT.$("Zoom Out"), "zoomMenu", J.i18n.GT.$("Zoom"), "vector005", J.i18n.GT.o(ang, "0.05"), "bond100", J.i18n.GT.o(ang, "0.10"), "hbond100", null, "ssbond100", null, "vector01", null, "10a", null, "bond150", J.i18n.GT.o(ang, "0.15"), "hbond150", null, "ssbond150", null, "bond200", J.i18n.GT.o(ang, "0.20"), "hbond200", null, "ssbond200", null, "20a", null, "bond250", J.i18n.GT.o(ang, "0.25"), "hbond250", null, "ssbond250", null, "25a", null, "bond300", J.i18n.GT.o(ang, "0.30"), "hbond300", null, "ssbond300", null, "50a", J.i18n.GT.o(ang, "0.50"), "100a", J.i18n.GT.o(ang, "1.0"), "1p", J.i18n.GT.i(pxl, 1), "10p", J.i18n.GT.i(pxl, 10), "3p", J.i18n.GT.i(pxl, 3), "vector3", null, "5p", J.i18n.GT.i(pxl, 5), "atom100", J.i18n.GT.i(vdw, 100), "atom15", J.i18n.GT.i(vdw, 15), "atom20", J.i18n.GT.i(vdw, 20), "atom25", J.i18n.GT.i(vdw, 25), "atom50", J.i18n.GT.i(vdw, 50), "atom75", J.i18n.GT.i(vdw, 75), "SIGNEDNOGLwriteIdtf", J.i18n.GT.o(exm, "IDTF"), "SIGNEDNOGLwriteMaya", J.i18n.GT.o(exm, "Maya"), "SIGNEDNOGLwriteVrml", J.i18n.GT.o(exm, "VRML"), "SIGNEDNOGLwriteX3d", J.i18n.GT.o(exm, "X3D"), "SIGNEDNOGLwriteSTL", J.i18n.GT.o(exm, "STL"), "SIGNEDNOGLwriteGif", J.i18n.GT.o(exi, "GIF"), "SIGNEDNOGLwriteJpg", J.i18n.GT.o(exi, "JPG"), "SIGNEDNOGLwritePng", J.i18n.GT.o(exi, "PNG"), "SIGNEDNOGLwritePngJmol", J.i18n.GT.o(exi, "PNG+JMOL"), "SIGNEDNOGLwritePovray", J.i18n.GT.o(exi, "POV-Ray"), "FILEUNITnineRestricted", J.i18n.GT.o(J.i18n.GT.$("Reload {0} + Display {1}"),  Clazz_newArray(-1, ["{444 666 1}", "555"])), "FILEMOLload", J.i18n.GT.o(rld, "(molecular)"), "FILEUNITone", J.i18n.GT.o(rld, "{1 1 1}"), "FILEUNITnine", J.i18n.GT.o(rld, "{444 666 1}"), "vectorScale02", J.i18n.GT.o(scl, "0.2"), "vectorScale05", J.i18n.GT.o(scl, "0.5"), "vectorScale1", J.i18n.GT.o(scl, "1"), "vectorScale2", J.i18n.GT.o(scl, "2"), "vectorScale5", J.i18n.GT.o(scl, "5"), "surfSolvent14", J.i18n.GT.o(J.i18n.GT.$("Solvent Surface ({0}-Angstrom probe)"), "1.4"), "surfSolventAccessible14", J.i18n.GT.o(J.i18n.GT.$("Solvent-Accessible Surface (VDW + {0} Angstrom)"), "1.4"), "vibration20", "*2", "vibration05", "/2", "JAVAmemTotal", "?", "JAVAmemMax", null, "JAVAprocessors", null, "s0", "0", "animfps10", "10", "s10", null, "zoom100", "100%", "zoom150", "150%", "animfps20", "20", "s20", null, "zoom200", "200%", "animfps30", "30", "s30", null, "s40", "40", "zoom400", "400%", "animfps5", "5", "s5", null, "animfps50", "50", "s50", null, "zoom50", "50%", "zoom800", "800%", "JSConsole", J.i18n.GT.$("JavaScript Console"), "jmolMenu", "Jmol", "date", JV.JC.date, "version", JV.JC.version, "javaVender", JV.Viewer.strJavaVendor, "javaVersion", JV.Viewer.strJavaVersion, "os", JV.Viewer.strOSName, "jmolorg", "http://www.jmol.org"]);
J.i18n.GT.setDoTranslate(wasTranslating);
for (var i = 1, n = words.length; i < n; i += 2) if (words[i] == null) words[i] = words[i - 2];

return words;
});
Clazz_overrideMethod(c$, "getMenuAsText", 
function(title){
return this.getStuctureAsText(title, J.popup.MainPopupResourceBundle.menuContents, J.popup.MainPopupResourceBundle.structureContents);
}, "~S");
c$.menuContents =  Clazz_newArray(-1, [ Clazz_newArray(-1, ["@COLOR", "black darkgray lightgray white - red orange yellow green cyan blue indigo violet"]),  Clazz_newArray(-1, ["@AXESCOLOR", "gray salmon maroon olive slateblue gold orchid"]),  Clazz_newArray(-1, ["popupMenu", "fileMenu modelSetMenu FRAMESbyModelComputedMenu configurationComputedMenu - selectMenuText viewMenu renderMenu colorMenu - surfaceMenu FILEUNITMenu - sceneComputedMenu zoomMenu spinMenu VIBRATIONMenu spectraMenu FRAMESanimateMenu - measureMenu pickingMenu - showConsole JSConsole showMenu computationMenu - languageComputedMenu aboutMenu"]),  Clazz_newArray(-1, ["fileMenu", "loadMenu saveMenu exportMenu SIGNEDJAVAcaptureMenuSPECIAL "]),  Clazz_newArray(-1, ["loadMenu", "SIGNEDloadFile SIGNEDloadUrl SIGNEDloadPdb SIGNEDloadMol SIGNEDloadScript - reload SIGNEDloadFileUnitCell"]),  Clazz_newArray(-1, ["saveMenu", "writeFileTextVARIABLE writeState writeHistory SIGNEDwriteJmol SIGNEDwriteIsosurface "]),  Clazz_newArray(-1, ["exportMenu", "SIGNEDNOGLwriteGif SIGNEDNOGLwriteJpg SIGNEDNOGLwritePng SIGNEDNOGLwritePngJmol SIGNEDNOGLwritePovray - SIGNEDNOGLwriteVrml SIGNEDNOGLwriteX3d SIGNEDNOGLwriteSTL"]),  Clazz_newArray(-1, ["selectMenuText", "hideNotSelectedCB showSelectionsCB - selectAll selectNone invertSelection - elementsComputedMenu SYMMETRYSelectComputedMenu - PDBproteinMenu PDBnucleicMenu PDBheteroMenu PDBcarboMenu PDBnoneOfTheAbove"]),  Clazz_newArray(-1, ["PDBproteinMenu", "PDBaaResiduesComputedMenu - allProtein proteinBackbone proteinSideChains - polar nonpolar - positiveCharge negativeCharge noCharge"]),  Clazz_newArray(-1, ["PDBcarboMenu", "PDBcarboResiduesComputedMenu - allCarbo"]),  Clazz_newArray(-1, ["PDBnucleicMenu", "PDBnucleicResiduesComputedMenu - allNucleic nucleicBackbone nucleicBases - DNA RNA - atPairs auPairs gcPairs - aaStructureMenu"]),  Clazz_newArray(-1, ["PDBheteroMenu", "PDBheteroComputedMenu - allHetero Solvent Water - Ligand exceptWater nonWaterSolvent"]),  Clazz_newArray(-1, ["viewMenu", "best front left right top bottom back - axisX axisY axisZ - axisA axisB axisC"]),  Clazz_newArray(-1, ["renderMenu", "renderSchemeMenu - atomMenu labelMenu bondMenu hbondMenu ssbondMenu - PDBstructureMenu - [set_axes]Menu [set_boundbox]Menu [set_UNITCELL]Menu - perspectiveDepthCB stereoMenu"]),  Clazz_newArray(-1, ["renderSchemeMenu", "renderCpkSpacefill renderBallAndStick renderSticks renderWireframe PDBrenderCartoonsOnly PDBrenderTraceOnly"]),  Clazz_newArray(-1, ["atomMenu", "showHydrogensCB - atomNone - atom15 atom20 atom25 atom50 atom75 atom100"]),  Clazz_newArray(-1, ["bondMenu", "bondNone bondWireframe - bond100 bond150 bond200 bond250 bond300"]),  Clazz_newArray(-1, ["hbondMenu", "hbondCalc hbondNone hbondWireframe - PDBhbondSidechain PDBhbondBackbone - hbond100 hbond150 hbond200 hbond250 hbond300"]),  Clazz_newArray(-1, ["ssbondMenu", "ssbondNone ssbondWireframe - PDBssbondSidechain PDBssbondBackbone - ssbond100 ssbond150 ssbond200 ssbond250 ssbond300"]),  Clazz_newArray(-1, ["PDBstructureMenu", "structureNone - backbone cartoon cartoonRockets ribbons rockets strands trace"]),  Clazz_newArray(-1, ["VIBRATIONvectorMenu", "vectorOff vectorOn vibScale20 vibScale05 vector3 vector005 vector01 - vectorScale02 vectorScale05 vectorScale1 vectorScale2 vectorScale5"]),  Clazz_newArray(-1, ["stereoMenu", "stereoNone stereoRedCyan stereoRedBlue stereoRedGreen stereoCrossEyed stereoWallEyed"]),  Clazz_newArray(-1, ["labelMenu", "labelNone - labelSymbol labelName labelNumber - labelPositionMenu"]),  Clazz_newArray(-1, ["labelPositionMenu", "labelCentered labelUpperRight labelLowerRight labelUpperLeft labelLowerLeft"]),  Clazz_newArray(-1, ["colorMenu", "colorrasmolCB [color_]schemeMenu - [color_atoms]Menu [color_bonds]Menu [color_hbonds]Menu [color_ssbonds]Menu colorPDBStructuresMenu [color_isosurface]Menu - [color_labels]Menu [color_vectors]Menu - [color_axes]Menu [color_boundbox]Menu [color_UNITCELL]Menu [color_background]Menu"]),  Clazz_newArray(-1, ["[color_atoms]Menu", "schemeMenu - @COLOR - opaque translucent"]),  Clazz_newArray(-1, ["[color_bonds]Menu", "none - @COLOR - opaque translucent"]),  Clazz_newArray(-1, ["[color_hbonds]Menu", null]),  Clazz_newArray(-1, ["[color_ssbonds]Menu", null]),  Clazz_newArray(-1, ["[color_labels]Menu", null]),  Clazz_newArray(-1, ["[color_vectors]Menu", null]),  Clazz_newArray(-1, ["[color_backbone]Menu", "none - schemeMenu - @COLOR - opaque translucent"]),  Clazz_newArray(-1, ["[color_cartoon]sMenu", null]),  Clazz_newArray(-1, ["[color_ribbon]sMenu", null]),  Clazz_newArray(-1, ["[color_rockets]Menu", null]),  Clazz_newArray(-1, ["[color_strands]Menu", null]),  Clazz_newArray(-1, ["[color_trace]Menu", null]),  Clazz_newArray(-1, ["[color_background]Menu", "@COLOR"]),  Clazz_newArray(-1, ["[color_isosurface]Menu", "@COLOR - opaque translucent"]),  Clazz_newArray(-1, ["[color_axes]Menu", "@AXESCOLOR"]),  Clazz_newArray(-1, ["[color_boundbox]Menu", null]),  Clazz_newArray(-1, ["[color_UNITCELL]Menu", null]),  Clazz_newArray(-1, ["colorPDBStructuresMenu", "[color_backbone]Menu [color_cartoon]sMenu [color_ribbon]sMenu [color_rockets]Menu [color_strands]Menu [color_trace]Menu"]),  Clazz_newArray(-1, ["schemeMenu", "cpk molecule formalcharge partialcharge - altloc#PDB amino#PDB chain#PDB group#PDB monomer#PDB shapely#PDB structure#PDB relativeTemperature#BFACTORS fixedTemperature#BFACTORS property_vxyz#VIBRATION"]),  Clazz_newArray(-1, ["[color_]schemeMenu", null]),  Clazz_newArray(-1, ["zoomMenu", "zoom50 zoom100 zoom150 zoom200 zoom400 zoom800 - zoomIn zoomOut"]),  Clazz_newArray(-1, ["spinMenu", "spinOn spinOff - [set_spin_X]Menu [set_spin_Y]Menu [set_spin_Z]Menu - [set_spin_FPS]Menu"]),  Clazz_newArray(-1, ["VIBRATIONMenu", "vibrationOff vibrationOn vibration20 vibration05 VIBRATIONvectorMenu"]),  Clazz_newArray(-1, ["spectraMenu", "hnmrMenu cnmrMenu"]),  Clazz_newArray(-1, ["FRAMESanimateMenu", "animModeMenu - play pause resume stop - nextframe prevframe rewind - playrev restart - FRAMESanimFpsMenu"]),  Clazz_newArray(-1, ["FRAMESanimFpsMenu", "animfps5 animfps10 animfps20 animfps30 animfps50"]),  Clazz_newArray(-1, ["measureMenu", "showMeasurementsCB - measureOff measureDistance measureAngle measureTorsion PDBmeasureSequence - measureDelete measureList - distanceNanometers distanceAngstroms distancePicometers distanceHz"]),  Clazz_newArray(-1, ["pickingMenu", "pickOff pickCenter pickIdent pickLabel pickAtom pickMolecule pickElement - dragAtom dragMolecule - pickSpin - modelKitMode - PDBpickChain PDBpickGroup SYMMETRYpickSite"]),  Clazz_newArray(-1, ["computationMenu", "minimize"]),  Clazz_newArray(-1, ["showMenu", "showHistory showFile showFileHeader - showOrient showMeasure - showSpacegroup showState SYMMETRYshowSymmetry UNITCELLshow - showIsosurface showMo - modelkit extractMOL"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureMenuSPECIAL", "SIGNEDJAVAcaptureRock SIGNEDJAVAcaptureSpin - SIGNEDJAVAcaptureBegin SIGNEDJAVAcaptureEnd SIGNEDJAVAcaptureOff SIGNEDJAVAcaptureOn SIGNEDJAVAcaptureFpsSPECIAL SIGNEDJAVAcaptureLoopingSPECIAL"]),  Clazz_newArray(-1, ["[set_spin_X]Menu", "s0 s5 s10 s20 s30 s40 s50"]),  Clazz_newArray(-1, ["[set_spin_Y]Menu", null]),  Clazz_newArray(-1, ["[set_spin_Z]Menu", null]),  Clazz_newArray(-1, ["[set_spin_FPS]Menu", null]),  Clazz_newArray(-1, ["animModeMenu", "onceThrough palindrome loop"]),  Clazz_newArray(-1, ["surfaceMenu", "surfDots surfVDW surfSolventAccessible14 surfSolvent14 surfMolecular surf2MEP surfMEP surfMoComputedMenuText - surfOpaque surfTranslucent surfOff"]),  Clazz_newArray(-1, ["FILEUNITMenu", "SYMMETRYShowComputedMenu FILEMOLload FILEUNITone FILEUNITnine FILEUNITnineRestricted FILEUNITninePoly"]),  Clazz_newArray(-1, ["[set_axes]Menu", "on off#axes dotted - byPixelMenu byAngstromMenu"]),  Clazz_newArray(-1, ["[set_boundbox]Menu", null]),  Clazz_newArray(-1, ["[set_UNITCELL]Menu", null]),  Clazz_newArray(-1, ["byPixelMenu", "1p 3p 5p 10p"]),  Clazz_newArray(-1, ["byAngstromMenu", "10a 20a 25a 50a 100a"]),  Clazz_newArray(-1, ["aboutMenu", "jmolMenu systemMenu"]),  Clazz_newArray(-1, ["jmolMenu", "APPLETid version date - help - mouse translations jmolorg"]),  Clazz_newArray(-1, ["systemMenu", "os javaVender javaVersion JAVAprocessors JAVAmemMax JAVAmemTotal"])]);
c$.structureContents =  Clazz_newArray(-1, [ Clazz_newArray(-1, ["jmolorg", "show url \"http://www.jmol.org\""]),  Clazz_newArray(-1, ["help", "help"]),  Clazz_newArray(-1, ["mouse", "show url \"http://wiki.jmol.org/index.php/Mouse_Manual\""]),  Clazz_newArray(-1, ["translations", "show url \"http://wiki.jmol.org/index.php/Internationalisation\""]),  Clazz_newArray(-1, ["colorrasmolCB", ""]),  Clazz_newArray(-1, ["hideNotSelectedCB", "set hideNotSelected true | set hideNotSelected false; hide(none)"]),  Clazz_newArray(-1, ["perspectiveDepthCB", ""]),  Clazz_newArray(-1, ["showAxesCB", "set showAxes true | set showAxes false;set axesMolecular"]),  Clazz_newArray(-1, ["showBoundBoxCB", ""]),  Clazz_newArray(-1, ["showHydrogensCB", ""]),  Clazz_newArray(-1, ["showMeasurementsCB", ""]),  Clazz_newArray(-1, ["showSelectionsCB", ""]),  Clazz_newArray(-1, ["showUNITCELLCB", ""]),  Clazz_newArray(-1, ["selectAll", "SELECT all"]),  Clazz_newArray(-1, ["selectNone", "SELECT none"]),  Clazz_newArray(-1, ["invertSelection", "SELECT not selected"]),  Clazz_newArray(-1, ["allProtein", "SELECT protein"]),  Clazz_newArray(-1, ["proteinBackbone", "SELECT protein and backbone"]),  Clazz_newArray(-1, ["proteinSideChains", "SELECT protein and not backbone"]),  Clazz_newArray(-1, ["polar", "SELECT protein and polar"]),  Clazz_newArray(-1, ["nonpolar", "SELECT protein and not polar"]),  Clazz_newArray(-1, ["positiveCharge", "SELECT protein and basic"]),  Clazz_newArray(-1, ["negativeCharge", "SELECT protein and acidic"]),  Clazz_newArray(-1, ["noCharge", "SELECT protein and not (acidic,basic)"]),  Clazz_newArray(-1, ["allCarbo", "SELECT carbohydrate"]),  Clazz_newArray(-1, ["allNucleic", "SELECT nucleic"]),  Clazz_newArray(-1, ["DNA", "SELECT dna"]),  Clazz_newArray(-1, ["RNA", "SELECT rna"]),  Clazz_newArray(-1, ["nucleicBackbone", "SELECT nucleic and backbone"]),  Clazz_newArray(-1, ["nucleicBases", "SELECT nucleic and not backbone"]),  Clazz_newArray(-1, ["atPairs", "SELECT a,t"]),  Clazz_newArray(-1, ["gcPairs", "SELECT g,c"]),  Clazz_newArray(-1, ["auPairs", "SELECT a,u"]),  Clazz_newArray(-1, ["A", "SELECT a"]),  Clazz_newArray(-1, ["C", "SELECT c"]),  Clazz_newArray(-1, ["G", "SELECT g"]),  Clazz_newArray(-1, ["T", "SELECT t"]),  Clazz_newArray(-1, ["U", "SELECT u"]),  Clazz_newArray(-1, ["allHetero", "SELECT hetero"]),  Clazz_newArray(-1, ["Solvent", "SELECT solvent"]),  Clazz_newArray(-1, ["Water", "SELECT water"]),  Clazz_newArray(-1, ["nonWaterSolvent", "SELECT solvent and not water"]),  Clazz_newArray(-1, ["exceptWater", "SELECT hetero and not water"]),  Clazz_newArray(-1, ["Ligand", "SELECT ligand"]),  Clazz_newArray(-1, ["PDBnoneOfTheAbove", "SELECT not(hetero,protein,nucleic,carbohydrate)"]),  Clazz_newArray(-1, ["best", "rotate best -1.0"]),  Clazz_newArray(-1, ["front", J.popup.MainPopupResourceBundle.Box("moveto 2.0 front;delay 1")]),  Clazz_newArray(-1, ["left", J.popup.MainPopupResourceBundle.Box("moveto 1.0 front;moveto 2.0 left;delay 1")]),  Clazz_newArray(-1, ["right", J.popup.MainPopupResourceBundle.Box("moveto 1.0 front;moveto 2.0 right;delay 1")]),  Clazz_newArray(-1, ["top", J.popup.MainPopupResourceBundle.Box("moveto 1.0 front;moveto 2.0 top;delay 1")]),  Clazz_newArray(-1, ["bottom", J.popup.MainPopupResourceBundle.Box("moveto 1.0 front;moveto 2.0 bottom;delay 1")]),  Clazz_newArray(-1, ["back", J.popup.MainPopupResourceBundle.Box("moveto 1.0 front;moveto 2.0 back;delay 1")]),  Clazz_newArray(-1, ["axisA", "moveto axis a"]),  Clazz_newArray(-1, ["axisB", "moveto axis b"]),  Clazz_newArray(-1, ["axisC", "moveto axis c"]),  Clazz_newArray(-1, ["axisX", "moveto axis x"]),  Clazz_newArray(-1, ["axisY", "moveto axis y"]),  Clazz_newArray(-1, ["axisZ", "moveto axis z"]),  Clazz_newArray(-1, ["renderCpkSpacefill", "restrict bonds not selected;select not selected;spacefill 100%;color cpk"]),  Clazz_newArray(-1, ["renderBallAndStick", "restrict bonds not selected;select not selected;spacefill 23%AUTO;wireframe 0.15;color cpk"]),  Clazz_newArray(-1, ["renderSticks", "restrict bonds not selected;select not selected;wireframe 0.3;color cpk"]),  Clazz_newArray(-1, ["renderWireframe", "restrict bonds not selected;select not selected;wireframe on;color cpk"]),  Clazz_newArray(-1, ["PDBrenderCartoonsOnly", "restrict bonds not selected;select not selected;cartoons on;color structure"]),  Clazz_newArray(-1, ["PDBrenderTraceOnly", "restrict bonds not selected;select not selected;trace on;color structure"]),  Clazz_newArray(-1, ["atomNone", "cpk off"]),  Clazz_newArray(-1, ["atom15", "cpk 15%"]),  Clazz_newArray(-1, ["atom20", "cpk 20%"]),  Clazz_newArray(-1, ["atom25", "cpk 25%"]),  Clazz_newArray(-1, ["atom50", "cpk 50%"]),  Clazz_newArray(-1, ["atom75", "cpk 75%"]),  Clazz_newArray(-1, ["atom100", "cpk on"]),  Clazz_newArray(-1, ["bondNone", "wireframe off"]),  Clazz_newArray(-1, ["bondWireframe", "wireframe on"]),  Clazz_newArray(-1, ["bond100", "wireframe .1"]),  Clazz_newArray(-1, ["bond150", "wireframe .15"]),  Clazz_newArray(-1, ["bond200", "wireframe .2"]),  Clazz_newArray(-1, ["bond250", "wireframe .25"]),  Clazz_newArray(-1, ["bond300", "wireframe .3"]),  Clazz_newArray(-1, ["hbondCalc", "hbonds calculate"]),  Clazz_newArray(-1, ["hbondNone", "hbonds off"]),  Clazz_newArray(-1, ["hbondWireframe", "hbonds on"]),  Clazz_newArray(-1, ["PDBhbondSidechain", "set hbonds sidechain"]),  Clazz_newArray(-1, ["PDBhbondBackbone", "set hbonds backbone"]),  Clazz_newArray(-1, ["hbond100", "hbonds .1"]),  Clazz_newArray(-1, ["hbond150", "hbonds .15"]),  Clazz_newArray(-1, ["hbond200", "hbonds .2"]),  Clazz_newArray(-1, ["hbond250", "hbonds .25"]),  Clazz_newArray(-1, ["hbond300", "hbonds .3"]),  Clazz_newArray(-1, ["ssbondNone", "ssbonds off"]),  Clazz_newArray(-1, ["ssbondWireframe", "ssbonds on"]),  Clazz_newArray(-1, ["PDBssbondSidechain", "set ssbonds sidechain"]),  Clazz_newArray(-1, ["PDBssbondBackbone", "set ssbonds backbone"]),  Clazz_newArray(-1, ["ssbond100", "ssbonds .1"]),  Clazz_newArray(-1, ["ssbond150", "ssbonds .15"]),  Clazz_newArray(-1, ["ssbond200", "ssbonds .2"]),  Clazz_newArray(-1, ["ssbond250", "ssbonds .25"]),  Clazz_newArray(-1, ["ssbond300", "ssbonds .3"]),  Clazz_newArray(-1, ["structureNone", "backbone off;cartoons off;ribbons off;rockets off;strands off;trace off;"]),  Clazz_newArray(-1, ["backbone", "restrict not selected;select not selected;backbone 0.3"]),  Clazz_newArray(-1, ["cartoon", "restrict not selected;select not selected;set cartoonRockets false;cartoons on"]),  Clazz_newArray(-1, ["cartoonRockets", "restrict not selected;select not selected;set cartoonRockets;cartoons on"]),  Clazz_newArray(-1, ["ribbons", "restrict not selected;select not selected;ribbons on"]),  Clazz_newArray(-1, ["rockets", "restrict not selected;select not selected;rockets on"]),  Clazz_newArray(-1, ["strands", "restrict not selected;select not selected;strands on"]),  Clazz_newArray(-1, ["trace", "restrict not selected;select not selected;trace 0.3"]),  Clazz_newArray(-1, ["vibrationOff", "vibration off"]),  Clazz_newArray(-1, ["vibrationOn", "vibration on"]),  Clazz_newArray(-1, ["vibration20", "vibrationScale *= 2"]),  Clazz_newArray(-1, ["vibration05", "vibrationScale /= 2"]),  Clazz_newArray(-1, ["vectorOff", "vectors off"]),  Clazz_newArray(-1, ["vectorOn", "vectors on"]),  Clazz_newArray(-1, ["vector3", "vectors 3"]),  Clazz_newArray(-1, ["vector005", "vectors 0.05"]),  Clazz_newArray(-1, ["vector01", "vectors 0.1"]),  Clazz_newArray(-1, ["vectorScale02", "vector scale 0.2"]),  Clazz_newArray(-1, ["vectorScale05", "vector scale 0.5"]),  Clazz_newArray(-1, ["vectorScale1", "vector scale 1"]),  Clazz_newArray(-1, ["vectorScale2", "vector scale 2"]),  Clazz_newArray(-1, ["vectorScale5", "vector scale 5"]),  Clazz_newArray(-1, ["stereoNone", "stereo off"]),  Clazz_newArray(-1, ["stereoRedCyan", "stereo redcyan 3"]),  Clazz_newArray(-1, ["stereoRedBlue", "stereo redblue 3"]),  Clazz_newArray(-1, ["stereoRedGreen", "stereo redgreen 3"]),  Clazz_newArray(-1, ["stereoCrossEyed", "stereo -5"]),  Clazz_newArray(-1, ["stereoWallEyed", "stereo 5"]),  Clazz_newArray(-1, ["labelNone", "label off"]),  Clazz_newArray(-1, ["labelSymbol", "label %e"]),  Clazz_newArray(-1, ["labelName", "label %a"]),  Clazz_newArray(-1, ["labelNumber", "label %i"]),  Clazz_newArray(-1, ["labelCentered", "set labeloffset 0 0"]),  Clazz_newArray(-1, ["labelUpperRight", "set labeloffset 4 4"]),  Clazz_newArray(-1, ["labelLowerRight", "set labeloffset 4 -4"]),  Clazz_newArray(-1, ["labelUpperLeft", "set labeloffset -4 4"]),  Clazz_newArray(-1, ["labelLowerLeft", "set labeloffset -4 -4"]),  Clazz_newArray(-1, ["zoom50", "zoom 50"]),  Clazz_newArray(-1, ["zoom100", "zoom 100"]),  Clazz_newArray(-1, ["zoom150", "zoom 150"]),  Clazz_newArray(-1, ["zoom200", "zoom 200"]),  Clazz_newArray(-1, ["zoom400", "zoom 400"]),  Clazz_newArray(-1, ["zoom800", "zoom 800"]),  Clazz_newArray(-1, ["zoomIn", "move 0 0 0 40 0 0 0 0 1"]),  Clazz_newArray(-1, ["zoomOut", "move 0 0 0 -40 0 0 0 0 1"]),  Clazz_newArray(-1, ["spinOn", "spin on"]),  Clazz_newArray(-1, ["spinOff", "spin off"]),  Clazz_newArray(-1, ["s0", "0"]),  Clazz_newArray(-1, ["s5", "5"]),  Clazz_newArray(-1, ["s10", "10"]),  Clazz_newArray(-1, ["s20", "20"]),  Clazz_newArray(-1, ["s30", "30"]),  Clazz_newArray(-1, ["s40", "40"]),  Clazz_newArray(-1, ["s50", "50"]),  Clazz_newArray(-1, ["onceThrough", "anim mode once#"]),  Clazz_newArray(-1, ["palindrome", "anim mode palindrome#"]),  Clazz_newArray(-1, ["loop", "anim mode loop#"]),  Clazz_newArray(-1, ["play", "anim play#"]),  Clazz_newArray(-1, ["pause", "anim pause#"]),  Clazz_newArray(-1, ["resume", "anim resume#"]),  Clazz_newArray(-1, ["stop", "anim off#"]),  Clazz_newArray(-1, ["nextframe", "frame next#"]),  Clazz_newArray(-1, ["prevframe", "frame prev#"]),  Clazz_newArray(-1, ["playrev", "anim playrev#"]),  Clazz_newArray(-1, ["rewind", "anim rewind#"]),  Clazz_newArray(-1, ["restart", "anim on#"]),  Clazz_newArray(-1, ["animfps5", "anim fps 5#"]),  Clazz_newArray(-1, ["animfps10", "anim fps 10#"]),  Clazz_newArray(-1, ["animfps20", "anim fps 20#"]),  Clazz_newArray(-1, ["animfps30", "anim fps 30#"]),  Clazz_newArray(-1, ["animfps50", "anim fps 50#"]),  Clazz_newArray(-1, ["measureOff", "set pickingstyle MEASURE OFF; set picking OFF"]),  Clazz_newArray(-1, ["measureDistance", "set pickingstyle MEASURE; set picking MEASURE DISTANCE"]),  Clazz_newArray(-1, ["measureAngle", "set pickingstyle MEASURE; set picking MEASURE ANGLE"]),  Clazz_newArray(-1, ["measureTorsion", "set pickingstyle MEASURE; set picking MEASURE TORSION"]),  Clazz_newArray(-1, ["PDBmeasureSequence", "set pickingstyle MEASURE; set picking MEASURE SEQUENCE"]),  Clazz_newArray(-1, ["measureDelete", "measure delete"]),  Clazz_newArray(-1, ["measureList", "console on;show measurements"]),  Clazz_newArray(-1, ["distanceNanometers", "select *; set measure nanometers"]),  Clazz_newArray(-1, ["distanceAngstroms", "select *; set measure angstroms"]),  Clazz_newArray(-1, ["distancePicometers", "select *; set measure picometers"]),  Clazz_newArray(-1, ["distanceHz", "select *; set measure hz"]),  Clazz_newArray(-1, ["pickOff", "set picking off"]),  Clazz_newArray(-1, ["pickCenter", "set picking center"]),  Clazz_newArray(-1, ["pickIdent", "set picking ident"]),  Clazz_newArray(-1, ["pickLabel", "set picking label"]),  Clazz_newArray(-1, ["pickAtom", "set picking atom"]),  Clazz_newArray(-1, ["dragAtom", "set picking dragAtom"]),  Clazz_newArray(-1, ["dragMolecule", "set picking dragMolecule"]),  Clazz_newArray(-1, ["PDBpickChain", "set picking chain"]),  Clazz_newArray(-1, ["pickElement", "set picking element"]),  Clazz_newArray(-1, ["modelKitMode", "set modelKitMode"]),  Clazz_newArray(-1, ["PDBpickGroup", "set picking group"]),  Clazz_newArray(-1, ["pickMolecule", "set picking molecule"]),  Clazz_newArray(-1, ["SYMMETRYpickSite", "set picking site"]),  Clazz_newArray(-1, ["pickSpin", "set picking spin"]),  Clazz_newArray(-1, ["SYMMETRYpickSymmetry", "set picking symmetry"]),  Clazz_newArray(-1, ["showConsole", "console"]),  Clazz_newArray(-1, ["JSConsole", "JSCONSOLE"]),  Clazz_newArray(-1, ["showFile", "console on;show file"]),  Clazz_newArray(-1, ["showFileHeader", "console on;getProperty FileHeader"]),  Clazz_newArray(-1, ["showHistory", "console on;show history"]),  Clazz_newArray(-1, ["showIsosurface", "console on;show isosurface"]),  Clazz_newArray(-1, ["showMeasure", "console on;show measure"]),  Clazz_newArray(-1, ["showMo", "console on;show mo"]),  Clazz_newArray(-1, ["showModel", "console on;show model"]),  Clazz_newArray(-1, ["showOrient", "console on;show orientation"]),  Clazz_newArray(-1, ["showSpacegroup", "console on;show spacegroup"]),  Clazz_newArray(-1, ["showState", "console on;show state"]),  Clazz_newArray(-1, ["reload", "load \"\""]),  Clazz_newArray(-1, ["SIGNEDloadPdb", JV.JC.getMenuScript("openPDB")]),  Clazz_newArray(-1, ["SIGNEDloadMol", JV.JC.getMenuScript("openMOL")]),  Clazz_newArray(-1, ["SIGNEDloadFile", "load ?"]),  Clazz_newArray(-1, ["SIGNEDloadUrl", "load http://?"]),  Clazz_newArray(-1, ["SIGNEDloadFileUnitCell", "load ? {1 1 1}"]),  Clazz_newArray(-1, ["SIGNEDloadScript", "script ?.spt"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureRock", "animation mode loop;capture '?Jmol.gif' rock y 10"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureSpin", "animation mode loop;capture '?Jmol.gif' spin y"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureBegin", "capture '?Jmol.gif'"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureEnd", "capture ''"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureOff", "capture off"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureOn", "capture on"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureFpsSPECIAL", "animation fps @{0+prompt('Capture replay frames per second?', animationFPS)};prompt 'animation FPS ' + animationFPS"]),  Clazz_newArray(-1, ["SIGNEDJAVAcaptureLoopingSPECIAL", "animation mode @{(animationMode=='ONCE' ? 'LOOP':'ONCE')};prompt 'animation MODE ' + animationMode"]),  Clazz_newArray(-1, ["writeFileTextVARIABLE", "if (_applet && !_signedApplet) { console;show file } else { write file \"?FILE?\"}"]),  Clazz_newArray(-1, ["writeState", "if (_applet && !_signedApplet) { console;show state } else { write state \"?FILEROOT?.spt\"}"]),  Clazz_newArray(-1, ["writeHistory", "if (_applet && !_signedApplet) { console;show history } else { write history \"?FILEROOT?.his\"}"]),  Clazz_newArray(-1, ["SIGNEDwriteJmol", "write PNGJ \"?FILEROOT?.png\""]),  Clazz_newArray(-1, ["SIGNEDwriteIsosurface", "write isosurface \"?FILEROOT?.jvxl\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteGif", "write image \"?FILEROOT?.gif\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteJpg", "write image \"?FILEROOT?.jpg\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwritePng", "write image \"?FILEROOT?.png\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwritePngJmol", "write PNGJ \"?FILEROOT?.png\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwritePovray", "write POVRAY \"?FILEROOT?.pov\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteVrml", "write VRML \"?FILEROOT?.wrl\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteX3d", "write X3D \"?FILEROOT?.x3d\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteSTL", "write STL \"?FILEROOT?.stl\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteIdtf", "write IDTF \"?FILEROOT?.idtf\""]),  Clazz_newArray(-1, ["SIGNEDNOGLwriteMaya", "write MAYA \"?FILEROOT?.ma\""]),  Clazz_newArray(-1, ["SYMMETRYshowSymmetry", "console on;show symmetry"]),  Clazz_newArray(-1, ["UNITCELLshow", "console on;show unitcell"]),  Clazz_newArray(-1, ["extractMOL", "console on;getproperty extractModel \"visible\" "]),  Clazz_newArray(-1, ["minimize", "minimize"]),  Clazz_newArray(-1, ["modelkit", "set modelkitmode"]),  Clazz_newArray(-1, ["surfDots", "dots on"]),  Clazz_newArray(-1, ["surfVDW", "isosurface delete resolution 0 solvent 0 translucent"]),  Clazz_newArray(-1, ["surfMolecular", "isosurface delete resolution 0 molecular translucent"]),  Clazz_newArray(-1, ["surfSolvent14", "isosurface delete resolution 0 solvent 1.4 translucent"]),  Clazz_newArray(-1, ["surfSolventAccessible14", "isosurface delete resolution 0 sasurface 1.4 translucent"]),  Clazz_newArray(-1, ["surfMEP", "isosurface delete resolution 0 vdw color range all map MEP translucent"]),  Clazz_newArray(-1, ["surf2MEP", "isosurface delete resolution 0 vdw color range -0.1 0.1 map MEP translucent"]),  Clazz_newArray(-1, ["surfOpaque", "mo opaque;isosurface opaque"]),  Clazz_newArray(-1, ["surfTranslucent", "mo translucent;isosurface translucent"]),  Clazz_newArray(-1, ["surfOff", "mo delete;isosurface delete;var ~~sel = {selected};select *;dots off;select ~~sel"]),  Clazz_newArray(-1, ["FILEMOLload", "save orientation;load \"\";restore orientation;center"]),  Clazz_newArray(-1, ["FILEUNITone", "save orientation;load \"\" {1 1 1} ;restore orientation;center"]),  Clazz_newArray(-1, ["FILEUNITnine", "save orientation;load \"\" {444 666 1} ;restore orientation;center"]),  Clazz_newArray(-1, ["FILEUNITnineRestricted", "save orientation;load \"\" {444 666 1} ;restore orientation; unitcell on; display cell=555;center visible;zoom 200"]),  Clazz_newArray(-1, ["FILEUNITninePoly", "save orientation;load \"\" {444 666 1} ;restore orientation; unitcell on; display cell=555; polyhedra 4,6 (displayed);center (visible);zoom 200"]),  Clazz_newArray(-1, ["1p", "on"]),  Clazz_newArray(-1, ["3p", "3"]),  Clazz_newArray(-1, ["5p", "5"]),  Clazz_newArray(-1, ["10p", "10"]),  Clazz_newArray(-1, ["10a", "0.1"]),  Clazz_newArray(-1, ["20a", "0.20"]),  Clazz_newArray(-1, ["25a", "0.25"]),  Clazz_newArray(-1, ["50a", "0.50"]),  Clazz_newArray(-1, ["100a", "1.0"])]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.popup");
Clazz_declareInterface(J.popup, "PopupHelper");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.popup");
Clazz_load(null, "J.popup.PopupResource", ["java.io.BufferedReader", "$.StringReader", "java.util.Properties", "JU.SB"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.structure = null;
this.words = null;
Clazz_instantialize(this, arguments);}, J.popup, "PopupResource", null);
Clazz_makeConstructor(c$, 
function(menuStructure, menuText){
this.structure =  new java.util.Properties();
this.words =  new java.util.Properties();
this.buildStructure(menuStructure);
this.localize(menuStructure != null, menuText);
}, "~S,java.util.Properties");
Clazz_defineMethod(c$, "getStructure", 
function(key){
return this.structure.getProperty(key);
}, "~S");
Clazz_defineMethod(c$, "getWord", 
function(key){
var str = this.words.getProperty(key);
return (str == null ? key : str);
}, "~S");
Clazz_defineMethod(c$, "setStructure", 
function(slist, gt){
var br =  new java.io.BufferedReader( new java.io.StringReader(slist));
var line;
var pt;
try {
while ((line = br.readLine()) != null) {
if (line.length == 0 || line.charAt(0) == '#') continue;
pt = line.indexOf("=");
if (pt < 0) {
pt = line.length;
line += "=";
}var name = line.substring(0, pt).trim();
var value = line.substring(pt + 1).trim();
var label = null;
if ((pt = name.indexOf("|")) >= 0) {
label = name.substring(pt + 1).trim();
name = name.substring(0, pt).trim();
}if (name.length == 0) continue;
if (value.length > 0) this.structure.setProperty(name, value);
if (label != null && label.length > 0) this.words.setProperty(name, (gt == null ? label : gt.translate(label)));
}
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
} else {
throw e;
}
}
try {
br.close();
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
} else {
throw e;
}
}
}, "~S,J.api.Translator");
Clazz_defineMethod(c$, "addItems", 
function(itemPairs){
var previous = "";
for (var i = 0; i < itemPairs.length; i++) {
var pair = itemPairs[i];
var str = pair[1];
if (str == null) str = previous;
previous = str;
this.structure.setProperty(pair[0], str);
}
}, "~A");
Clazz_defineMethod(c$, "localize", 
function(haveUserMenu, menuText){
var wordContents = this.getWordContents();
for (var i = 0; i < wordContents.length; i++) {
var item = wordContents[i++];
var word = this.words.getProperty(item);
if (word == null) word = wordContents[i];
this.words.setProperty(item, word);
if (menuText != null && item.indexOf("Text") >= 0) menuText.setProperty(item, word);
}
}, "~B,java.util.Properties");
Clazz_defineMethod(c$, "getStuctureAsText", 
function(title, menuContents, structureContents){
return "# " + this.getMenuName() + ".mnu " + title + "\n\n" + "# Part I -- Menu Structure\n" + "# ------------------------\n\n" + this.dumpStructure(menuContents) + "\n\n" + "# Part II -- Key Definitions\n" + "# --------------------------\n\n" + this.dumpStructure(structureContents) + "\n\n" + "# Part III -- Word Translations\n" + "# -----------------------------\n\n" + this.dumpWords();
}, "~S,~A,~A");
Clazz_defineMethod(c$, "dumpWords", 
function(){
var wordContents = this.getWordContents();
var s =  new JU.SB();
for (var i = 0; i < wordContents.length; i++) {
var key = wordContents[i++];
if (this.structure.getProperty(key) == null) s.append(key).append(" | ").append(wordContents[i]).appendC('\n');
}
return s.toString();
});
Clazz_defineMethod(c$, "dumpStructure", 
function(items){
var previous = "";
var s =  new JU.SB();
for (var i = 0; i < items.length; i++) {
var key = items[i][0];
var label = this.words.getProperty(key);
if (label != null) key += " | " + label;
s.append(key).append(" = ").append(items[i][1] == null ? previous : (previous = items[i][1])).appendC('\n');
}
return s.toString();
}, "~A");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.awtjs2d");
Clazz_load(["J.popup.JmolPopup"], "J.awtjs2d.JSJmolPopup", ["J.awtjs2d.JSPopupHelper"], function(){
var c$ = Clazz_declareType(J.awtjs2d, "JSJmolPopup", J.popup.JmolPopup);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor (this, J.awtjs2d.JSJmolPopup, []);
this.helper =  new J.awtjs2d.JSPopupHelper(this);
});
Clazz_overrideMethod(c$, "menuShowPopup", 
function(popup, x, y){
try {
(popup).show(this.isTainted ? this.vwr.html5Applet : null, x, y);
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
} else {
throw e;
}
}
this.isTainted = false;
}, "J.api.SC,~N,~N");
Clazz_overrideMethod(c$, "getUnknownCheckBoxScriptToRun", 
function(item, name, what, TF){
return null;
}, "J.api.SC,~S,~S,~B");
Clazz_overrideMethod(c$, "getImageIcon", 
function(fileName){
return null;
}, "~S");
Clazz_overrideMethod(c$, "menuFocusCallback", 
function(name, actionCommand, b){
}, "~S,~S,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("J.awtjs2d");
Clazz_load(["J.popup.PopupHelper"], "J.awtjs2d.JSPopupHelper", ["JS.ButtonGroup", "$.JCheckBoxMenuItem", "$.JMenu", "$.JMenuItem", "$.JPopupMenu", "$.JRadioButtonMenuItem"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.popup = null;
this.buttonGroup = null;
Clazz_instantialize(this, arguments);}, J.awtjs2d, "JSPopupHelper", null, J.popup.PopupHelper);
Clazz_makeConstructor(c$, 
function(popup){
this.popup = popup;
}, "J.popup.GenericPopup");
Clazz_overrideMethod(c$, "menuCreatePopup", 
function(name, applet){
var j =  new JS.JPopupMenu(name);
j.setInvoker(applet);
return j;
}, "~S,~O");
Clazz_overrideMethod(c$, "getMenu", 
function(name){
var jm =  new JS.JMenu();
jm.setName(name);
return jm;
}, "~S");
Clazz_overrideMethod(c$, "getMenuItem", 
function(text){
return  new JS.JMenuItem(text);
}, "~S");
Clazz_overrideMethod(c$, "getRadio", 
function(name){
return  new JS.JRadioButtonMenuItem();
}, "~S");
Clazz_overrideMethod(c$, "getCheckBox", 
function(name){
return  new JS.JCheckBoxMenuItem();
}, "~S");
Clazz_overrideMethod(c$, "menuAddButtonGroup", 
function(item){
if (item == null) {
if (this.buttonGroup != null && this.buttonGroup.getButtonCount() > 0) this.buttonGroup = null;
return;
}if (this.buttonGroup == null) this.buttonGroup =  new JS.ButtonGroup();
this.buttonGroup.add(item);
}, "J.api.SC");
Clazz_overrideMethod(c$, "getItemType", 
function(m){
return (m).btnType;
}, "J.api.SC");
Clazz_overrideMethod(c$, "menuInsertSubMenu", 
function(menu, subMenu, index){
(subMenu).setParent(menu);
}, "J.api.SC,J.api.SC,~N");
Clazz_overrideMethod(c$, "getSwingComponent", 
function(component){
return component;
}, "~O");
Clazz_overrideMethod(c$, "menuClearListeners", 
function(menu){
if (menu != null) (menu).disposeMenu();
}, "J.api.SC");
Clazz_defineMethod(c$, "itemStateChanged", 
function(e){
if (this.popup != null) this.popup.menuCheckBoxCallback(e.getSource());
}, "java.awt.event.ItemEvent");
Clazz_defineMethod(c$, "actionPerformed", 
function(e){
if (this.popup != null) this.popup.menuClickCallback(e.getSource(), e.getActionCommand());
}, "java.awt.event.ActionEvent");
Clazz_overrideMethod(c$, "getButtonGroup", 
function(){
return this.buttonGroup;
});
Clazz_defineMethod(c$, "handleEvent", 
function(e){
var type = "" + e.getID();
if (type === "mouseenter") this.mouseEntered(e);
 else if (type === "mouseleave") this.mouseExited(e);
}, "java.awt.event.MouseEvent");
Clazz_defineMethod(c$, "mouseEntered", 
function(e){
var jmi = e.getSource();
this.popup.menuFocusCallback(jmi.getName(), jmi.getActionCommand(), true);
}, "java.awt.event.MouseEvent");
Clazz_defineMethod(c$, "mouseExited", 
function(e){
var jmi = e.getSource();
this.popup.menuFocusCallback(jmi.getName(), jmi.getActionCommand(), false);
}, "java.awt.event.MouseEvent");
Clazz_overrideMethod(c$, "dispose", 
function(popupMenu){
this.menuClearListeners(popupMenu);
this.popup = null;
}, "J.api.SC");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
})(Clazz
,Clazz.getClassName
,Clazz.newLongArray
,Clazz.doubleToByte
,Clazz.doubleToInt
,Clazz.doubleToLong
,Clazz.declarePackage
,Clazz.instanceOf
,Clazz.load
,Clazz.instantialize
,Clazz.decorateAsClass
,Clazz.floatToInt
,Clazz.floatToLong
,Clazz.makeConstructor
,Clazz.defineEnumConstant
,Clazz.exceptionOf
,Clazz.newIntArray
,Clazz.newFloatArray
,Clazz.declareType
,Clazz.prepareFields
,Clazz.superConstructor
,Clazz.newByteArray
,Clazz.declareInterface
,Clazz.newShortArray
,Clazz.innerTypeInstance
,Clazz.isClassDefined
,Clazz.prepareCallback
,Clazz.newArray
,Clazz.castNullAs
,Clazz.floatToShort
,Clazz.superCall
,Clazz.decorateAsType
,Clazz.newBooleanArray
,Clazz.newCharArray
,Clazz.implementOf
,Clazz.newDoubleArray
,Clazz.overrideConstructor
,Clazz.clone
,Clazz.doubleToShort
,Clazz.getInheritedLevel
,Clazz.getParamsType
,Clazz.isAF
,Clazz.isAB
,Clazz.isAI
,Clazz.isAS
,Clazz.isASS
,Clazz.isAP
,Clazz.isAFloat
,Clazz.isAII
,Clazz.isAFF
,Clazz.isAFFF
,Clazz.tryToSearchAndExecute
,Clazz.getStackTrace
,Clazz.inheritArgs
,Clazz.alert
,Clazz.defineMethod
,Clazz.overrideMethod
,Clazz.declareAnonymous
//,Clazz.checkPrivateMethod
,Clazz.cloneFinals
);
