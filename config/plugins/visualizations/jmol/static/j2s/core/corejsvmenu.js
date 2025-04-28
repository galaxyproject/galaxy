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
Clazz_declarePackage("J.api");
Clazz_declareInterface(J.api, "GenericMenuInterface");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JSV.js2d");
Clazz_load(["JSV.popup.JSVGenericPopup"], "JSV.js2d.JsPopup", ["JSV.popup.JSVPopupResourceBundle", "J.awtjs2d.JSPopupHelper"], function(){
var c$ = Clazz_declareType(JSV.js2d, "JsPopup", JSV.popup.JSVGenericPopup);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor (this, JSV.js2d.JsPopup, []);
this.helper =  new J.awtjs2d.JSPopupHelper(this);
});
Clazz_overrideMethod(c$, "jpiInitialize", 
function(viewer, menu){
var bundle =  new JSV.popup.JSVPopupResourceBundle();
this.initialize(viewer, bundle, menu);
}, "J.api.PlatformViewer,~S");
Clazz_overrideMethod(c$, "menuShowPopup", 
function(popup, x, y){
try {
(popup).show(this.isTainted ? this.vwr.getApplet() : null, x, y);
} catch (e) {
if (Clazz_exceptionOf(e, Exception)){
} else {
throw e;
}
}
}, "J.api.SC,~N,~N");
Clazz_overrideMethod(c$, "getImageIcon", 
function(fileName){
return null;
}, "~S");
Clazz_overrideMethod(c$, "menuFocusCallback", 
function(name, actionCommand, b){
}, "~S,~S,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JSV.popup");
Clazz_load(["J.popup.GenericPopup"], "JSV.popup.JSVGenericPopup", ["JU.PT", "JSV.common.JSVersion", "$.JSViewer", "JSV.popup.JSVPopupResourceBundle"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.vwr = null;
this.updateMode = 0;
this.cnmrPeaks = null;
this.hnmrPeaks = null;
this.aboutComputedMenuBaseCount = 0;
this.allowMenu = false;
this.zoomEnabled = false;
this.pd = null;
this.thisJsvp = null;
Clazz_instantialize(this, arguments);}, JSV.popup, "JSVGenericPopup", J.popup.GenericPopup);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor (this, JSV.popup.JSVGenericPopup, []);
});
Clazz_defineMethod(c$, "initialize", 
function(viewer, bundle, title){
this.vwr = viewer;
this.initSwing(title, bundle, viewer.getApplet(), JSV.common.JSViewer.isJS, viewer.isSigned, false);
}, "JSV.common.JSViewer,J.popup.PopupResource,~S");
Clazz_defineMethod(c$, "jpiDispose", 
function(){
this.vwr = null;
Clazz_superCall(this, JSV.popup.JSVGenericPopup, "jpiDispose", []);
});
Clazz_overrideMethod(c$, "jpiGetMenuAsObject", 
function(){
return this.popupMenu;
});
Clazz_overrideMethod(c$, "jpiShow", 
function(x, y){
this.show(x, y, false);
this.appRestorePopupMenu();
this.menuShowPopup(this.popupMenu, this.thisx, this.thisy);
}, "~N,~N");
Clazz_overrideMethod(c$, "jpiUpdateComputedMenus", 
function(){
if (this.updateMode == -1) return;
this.updateMode = 0;
this.getViewerData();
this.updateFileMenu();
this.updateFileTypeDependentMenus();
this.updateMode = 1;
this.updateAboutSubmenu();
});
Clazz_overrideMethod(c$, "appCheckItem", 
function(item, newMenu){
}, "~S,J.api.SC");
Clazz_overrideMethod(c$, "appFixLabel", 
function(label){
if (label.startsWith("_")) label = label.substring(label.indexOf("_", 2) + 1);
 else if (label.equals("VERSION")) label = JSV.common.JSVersion.VERSION;
label = JU.PT.rep(label, "JAVA", "");
label = JU.PT.rep(label, "CB", "");
label = JU.PT.rep(label, "Menu", "");
label = JU.PT.rep(label, "_", " ");
return label;
}, "~S");
Clazz_overrideMethod(c$, "getScriptForCallback", 
function(source, id, script){
return script;
}, "J.api.SC,~S,~S");
Clazz_overrideMethod(c$, "appGetMenuAsString", 
function(title){
return ( new JSV.popup.JSVPopupResourceBundle()).getMenuAsText(title);
}, "~S");
Clazz_overrideMethod(c$, "appGetBooleanProperty", 
function(name){
return false;
}, "~S");
Clazz_overrideMethod(c$, "appRunSpecialCheckBox", 
function(item, basename, what, TF){
return false;
}, "J.api.SC,~S,~S,~B");
Clazz_overrideMethod(c$, "appRestorePopupMenu", 
function(){
this.thisPopup = this.popupMenu;
});
Clazz_overrideMethod(c$, "appRunScript", 
function(script){
this.vwr.runScript(script);
}, "~S");
Clazz_overrideMethod(c$, "appUpdateForShow", 
function(){
this.thisJsvp = this.vwr.selectedPanel;
this.setEnables(this.thisJsvp);
if (this.updateMode == -1) return;
this.getViewerData();
this.updateMode = 2;
this.updateSpectraMenu();
this.updateAboutSubmenu();
});
Clazz_overrideMethod(c$, "appUpdateSpecialCheckBoxValue", 
function(item, what, TF){
}, "J.api.SC,~S,~B");
Clazz_defineMethod(c$, "getViewerData", 
function(){
});
Clazz_defineMethod(c$, "updateFileTypeDependentMenus", 
function(){
});
Clazz_defineMethod(c$, "updateFileMenu", 
function(){
var menu = this.htMenus.get("fileMenu");
if (menu == null) return;
});
Clazz_defineMethod(c$, "updateSpectraMenu", 
function(){
var menuh = this.htMenus.get("hnmrMenu");
var menuc = this.htMenus.get("cnmrMenu");
if (menuh != null) this.menuRemoveAll(menuh, 0);
if (menuc != null) this.menuRemoveAll(menuc, 0);
var menu = this.htMenus.get("spectraMenu");
if (menu == null) return;
this.menuRemoveAll(menu, 0);
var isOK =  new Boolean (this.setSpectraMenu(menuh, this.hnmrPeaks) | this.setSpectraMenu(menuc, this.cnmrPeaks)).valueOf();
if (isOK) {
if (menuh != null) this.menuAddSubMenu(menu, menuh);
if (menuc != null) this.menuAddSubMenu(menu, menuc);
}this.menuEnable(menu, isOK);
});
Clazz_defineMethod(c$, "setSpectraMenu", 
function(menu, peaks){
if (menu == null) return false;
this.menuEnable(menu, false);
var n = (peaks == null ? 0 : peaks.size());
if (n == 0) return false;
for (var i = 0; i < n; i++) {
var peak = peaks.get(i);
var title = JU.PT.getQuotedAttribute(peak, "title");
var atoms = JU.PT.getQuotedAttribute(peak, "atoms");
if (atoms != null) this.menuCreateItem(menu, title, "select visible & (@" + JU.PT.rep(atoms, ",", " or @") + ")", "Focus" + i);
}
this.menuEnable(menu, true);
return true;
}, "J.api.SC,JU.Lst");
Clazz_defineMethod(c$, "updateAboutSubmenu", 
function(){
var menu = this.htMenus.get("aboutComputedMenu");
if (menu == null) return;
this.menuRemoveAll(menu, this.aboutComputedMenuBaseCount);
});
Clazz_defineMethod(c$, "setEnabled", 
function(allowMenu, zoomEnabled){
this.allowMenu = allowMenu;
this.zoomEnabled = zoomEnabled;
this.enableMenus();
}, "~B,~B");
Clazz_defineMethod(c$, "enableMenus", 
function(){
this.setItemEnabled("_SIGNED_FileMenu", this.allowMenu);
this.setItemEnabled("ViewMenu", this.pd != null && this.allowMenu);
this.setItemEnabled("Open_File...", this.allowMenu);
this.setItemEnabled("Open_Simulation...", this.allowMenu);
this.setItemEnabled("Open_URL...", this.allowMenu);
this.setItemEnabled("Save_AsMenu", this.pd != null && this.allowMenu);
this.setItemEnabled("Export_AsMenu", this.pd != null && this.allowMenu);
this.setItemEnabled("Append_File...", this.pd != null && this.allowMenu);
this.setItemEnabled("Append_Simulation...", this.pd != null && this.allowMenu);
this.setItemEnabled("Append_URL...", this.pd != null && this.allowMenu);
this.setItemEnabled("Views...", this.pd != null && this.allowMenu);
this.setItemEnabled("Script", this.allowMenu);
this.setItemEnabled("Print...", this.pd != null && this.allowMenu);
this.setItemEnabled("ZoomMenu", this.pd != null && this.zoomEnabled);
});
Clazz_defineMethod(c$, "setEnables", 
function(jsvp){
this.pd = (jsvp == null ? null : jsvp.getPanelData());
var spec0 = (this.pd == null ? null : this.pd.getSpectrum());
var isOverlaid = this.pd != null && this.pd.isShowAllStacked();
var isSingle = this.pd != null && this.pd.haveSelectedSpectrum();
this.setItemEnabled("Integration", this.pd != null && this.pd.getSpectrum().canIntegrate());
this.setItemEnabled("Measurements", true);
this.setItemEnabled("Peaks", this.pd != null && this.pd.getSpectrum().is1D());
this.setItemEnabled("Predicted_Solution_Colour_(fitted)", isSingle && spec0.canShowSolutionColor());
this.setItemEnabled("Predicted_Solution_Colour_(interpolated)", isSingle && spec0.canShowSolutionColor());
this.setItemEnabled("Toggle_Trans/Abs", isSingle && spec0.canConvertTransAbs());
this.setItemEnabled("Show_Overlay_Key", isOverlaid && this.pd.getNumberOfGraphSets() == 1);
this.setItemEnabled("Overlay_Offset...", isOverlaid);
this.setItemEnabled("JDXMenu", this.pd != null && spec0.canSaveAsJDX());
this.setItemEnabled("Export_AsMenu", this.pd != null);
this.enableMenus();
}, "JSV.api.JSVPanel");
Clazz_defineMethod(c$, "setItemEnabled", 
function(key, TF){
this.menuEnable(this.htMenus.get(key), TF);
}, "~S,~B");
Clazz_defineMethod(c$, "setSelected", 
function(key, TF){
var item = this.htMenus.get(key);
if (item == null || item.isSelected() == TF) return;
this.menuEnable(item, false);
item.setSelected(TF);
this.menuEnable(item, true);
}, "~S,~B");
Clazz_overrideMethod(c$, "getUnknownCheckBoxScriptToRun", 
function(item, name, what, TF){
return null;
}, "J.api.SC,~S,~S,~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JSV.popup");
Clazz_load(["J.popup.PopupResource"], "JSV.popup.JSVPopupResourceBundle", null, function(){
var c$ = Clazz_declareType(JSV.popup, "JSVPopupResourceBundle", J.popup.PopupResource);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JSV.popup.JSVPopupResourceBundle, [null, null]);
});
Clazz_overrideMethod(c$, "getMenuName", 
function(){
return "appMenu";
});
Clazz_overrideMethod(c$, "buildStructure", 
function(menuStructure){
this.addItems(JSV.popup.JSVPopupResourceBundle.menuContents);
this.addItems(JSV.popup.JSVPopupResourceBundle.structureContents);
if (menuStructure != null) this.setStructure(menuStructure, null);
}, "~S");
Clazz_overrideMethod(c$, "getWordContents", 
function(){
return  Clazz_newArray(-1, []);
});
Clazz_overrideMethod(c$, "getMenuAsText", 
function(title){
return this.getStuctureAsText(title, JSV.popup.JSVPopupResourceBundle.menuContents, JSV.popup.JSVPopupResourceBundle.structureContents);
}, "~S");
c$.menuContents =  Clazz_newArray(-1, [ Clazz_newArray(-1, ["appMenu", "_SIGNED_FileMenu Spectra... ShowMenu OptionsMenu ZoomMenu - Integration Peaks Measurements - Script... Properties"]),  Clazz_newArray(-1, ["appletMenu", "_SIGNED_FileMenu Spectra... - OptionsMenu ZoomMenu - Integration Peaks Measurements - Script... - Print... - AboutMenu"]),  Clazz_newArray(-1, ["_SIGNED_FileMenu", "Open_File... Open_Simulation... Open_URL... - Add_File... Add_Simulation... Add_URL... - Save_AsMenu Export_AsMenu - Close_Views Close_Simulations Close_All"]),  Clazz_newArray(-1, ["Save_AsMenu", "Original... JDXMenu CML XML(AnIML)"]),  Clazz_newArray(-1, ["JDXMenu", "XY DIF DIFDUP FIX PAC SQZ"]),  Clazz_newArray(-1, ["Export_AsMenu", "PDF - JPG PNG SVG"]),  Clazz_newArray(-1, ["ShowMenu", "Show_Header Show_Source Show_Overlay_Key"]),  Clazz_newArray(-1, ["OptionsMenu", "Toggle_Grid Toggle_X_Axis Toggle_Y_Axis Toggle_Coordinates Toggle_Trans/Abs Reverse_Plot - Predicted_Solution_Colour Fill_Solution_Colour_(all)  Fill_Solution_Colour_(none)"]),  Clazz_newArray(-1, ["ZoomMenu", "Next_Zoom Previous_Zoom Reset_Zoom - Set_X_Scale... Reset_X_Scale"]),  Clazz_newArray(-1, ["AboutMenu", "VERSION"])]);
c$.structureContents =  Clazz_newArray(-1, [ Clazz_newArray(-1, ["Open_File...", "load ?"]),  Clazz_newArray(-1, ["Open_URL...", "load http://?"]),  Clazz_newArray(-1, ["Open_Simulation...", "load $?"]),  Clazz_newArray(-1, ["Add_File...", "load append ?"]),  Clazz_newArray(-1, ["Add_URL...", "load append http://?"]),  Clazz_newArray(-1, ["Add_Simulation...", "load append $?; view \"1HNMR\""]),  Clazz_newArray(-1, ["Close_All", "close all"]),  Clazz_newArray(-1, ["Close_Views", "close views"]),  Clazz_newArray(-1, ["Close Simulations", "close simulations"]),  Clazz_newArray(-1, ["Show_Header", "showProperties"]),  Clazz_newArray(-1, ["Show_Source", "showSource"]),  Clazz_newArray(-1, ["Show_Overlay_Key...", "showKey"]),  Clazz_newArray(-1, ["Next_Zoom", "zoom next;showMenu"]),  Clazz_newArray(-1, ["Previous_Zoom", "zoom prev;showMenu"]),  Clazz_newArray(-1, ["Reset_Zoom", "zoom clear"]),  Clazz_newArray(-1, ["Reset_X_Scale", "zoom out"]),  Clazz_newArray(-1, ["Set_X_Scale...", "zoom"]),  Clazz_newArray(-1, ["Spectra...", "view"]),  Clazz_newArray(-1, ["Overlay_Offset...", "stackOffsetY"]),  Clazz_newArray(-1, ["Script...", "script INLINE"]),  Clazz_newArray(-1, ["Properties", "showProperties"]),  Clazz_newArray(-1, ["Toggle_X_Axis", "XSCALEON toggle;showMenu"]),  Clazz_newArray(-1, ["Toggle_Y_Axis", "YSCALEON toggle;showMenu"]),  Clazz_newArray(-1, ["Toggle_Grid", "GRIDON toggle;showMenu"]),  Clazz_newArray(-1, ["Toggle_Coordinates", "COORDINATESON toggle;showMenu"]),  Clazz_newArray(-1, ["Reverse_Plot", "REVERSEPLOT toggle;showMenu"]),  Clazz_newArray(-1, ["Measurements", "SHOWMEASUREMENTS"]),  Clazz_newArray(-1, ["Peaks", "SHOWPEAKLIST"]),  Clazz_newArray(-1, ["Integration", "SHOWINTEGRATION"]),  Clazz_newArray(-1, ["Toggle_Trans/Abs", "IRMODE TOGGLE"]),  Clazz_newArray(-1, ["Predicted_Solution_Colour", "GETSOLUTIONCOLOR"]),  Clazz_newArray(-1, ["Fill_Solution_Colour_(all)", "GETSOLUTIONCOLOR fillall"]),  Clazz_newArray(-1, ["Fill_Solution_Colour_(none)", "GETSOLUTIONCOLOR fillallnone"]),  Clazz_newArray(-1, ["Print...", "print"]),  Clazz_newArray(-1, ["Original...", "write SOURCE"]),  Clazz_newArray(-1, ["CML", "write CML"]),  Clazz_newArray(-1, ["XML(AnIML)", "write XML"]),  Clazz_newArray(-1, ["XY", "write XY"]),  Clazz_newArray(-1, ["DIF", "write DIF"]),  Clazz_newArray(-1, ["DIFDUP", "write DIFDUP"]),  Clazz_newArray(-1, ["FIX", "write FIX"]),  Clazz_newArray(-1, ["PAC", "write PAC"]),  Clazz_newArray(-1, ["SQZ", "write SQZ"]),  Clazz_newArray(-1, ["JPG", "write JPG"]),  Clazz_newArray(-1, ["SVG", "write SVG"]),  Clazz_newArray(-1, ["PNG", "write PNG"]),  Clazz_newArray(-1, ["PDF", "write PDF"])]);
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
