Clazz.declarePackage("J.modelkit");
Clazz.load(["J.popup.JmolGenericPopup", "J.modelkit.ModelKitPopupResourceBundle"], "J.modelkit.ModelKitPopup", ["J.i18n.GT"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.modelkit = null;
this.hidden = false;
this.allowPopup = true;
this.activeMenu = null;
this.bondRotationCheckBox = null;
this.prevBondCheckBox = null;
this.bondRotationName = ".modelkitMenu.bondMenu.rotateBondP!RD";
this.haveOperators = false;
Clazz.instantialize(this, arguments);}, J.modelkit, "ModelKitPopup", J.popup.JmolGenericPopup);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, J.modelkit.ModelKitPopup, []);
});
Clazz.overrideMethod(c$, "getBundle", 
function(menu){
return J.modelkit.ModelKitPopup.bundle;
}, "~S");
Clazz.defineMethod(c$, "jpiShow", 
function(x, y){
if (!this.hidden) {
this.updateCheckBoxesForModelKit(null);
Clazz.superCall(this, J.modelkit.ModelKitPopup, "jpiShow", [x, y]);
}}, "~N,~N");
Clazz.overrideMethod(c$, "jpiUpdateComputedMenus", 
function(){
this.htMenus.get("xtalMenu").setEnabled(this.modelkit.setHasUnitCell());
if (this.modelkit.checkNewModel()) {
this.haveOperators = false;
this.updateOperatorMenu();
}this.updateAllXtalMenuOptions();
});
Clazz.overrideMethod(c$, "appUpdateForShow", 
function(){
this.jpiUpdateComputedMenus();
});
Clazz.defineMethod(c$, "hidePopup", 
function(){
this.menuHidePopup(this.popupMenu);
});
Clazz.defineMethod(c$, "clearLastModelSet", 
function(){
this.modelkit.lastModelSet = null;
});
Clazz.defineMethod(c$, "updateOperatorMenu", 
function(){
if (this.haveOperators) return;
this.haveOperators = true;
var menu = this.htMenus.get("xtalOp!PersistMenu");
if (menu != null) this.addAllCheckboxItems(menu, this.modelkit.getAllOperators());
});
Clazz.defineMethod(c$, "addAllCheckboxItems", 
function(menu, labels){
this.menuRemoveAll(menu, 0);
var subMenu = menu;
var pt = (labels.length > 32 ? 0 : -2147483648);
for (var i = 0; i < labels.length; i++) {
if (pt >= 0 && (pt++ % 32) == 0) {
var id = "mtsymop" + pt + "Menu";
subMenu = this.menuNewSubMenu((i + 1) + "..." + Math.min(i + 32, labels.length), this.menuGetId(menu) + "." + id);
this.menuAddSubMenu(menu, subMenu);
this.htMenus.put(id, subMenu);
pt = 1;
}if (i == 0) this.menuEnable(this.menuCreateItem(subMenu, J.i18n.GT.$("none"), "draw sym_* delete", null), true);
var sym = labels[i];
this.menuEnable(this.menuCreateItem(subMenu, sym, sym, subMenu.getName() + "." + "mkop_" + (i + 1)), true);
}
}, "J.api.SC,~A");
Clazz.defineMethod(c$, "updateAllXtalMenuOptions", 
function(){
var text = "";
switch (this.modelkit.getMKState()) {
case 0:
text = " (not enabled)";
break;
case 1:
text = " (view)";
break;
case 2:
text = " (edit)";
break;
}
this.setLabel("xtalModePersistMenu", "Crystal Mode: " + text);
text = this.modelkit.getCenterText();
this.setLabel("xtalSelPersistMenu", "Center: " + (text == null ? "(not selected)" : text));
text = this.modelkit.getSymopText();
this.setLabel("operator", text == null ? "(no operator selected)" : text);
switch (this.modelkit.getSymEditState()) {
case 0:
text = "do not apply symmetry";
break;
case 64:
text = "retain local symmetry";
break;
case 32:
text = "apply local symmetry";
break;
case 128:
text = "apply full symmetry";
break;
}
this.setLabel("xtalEditOptPersistMenu", "Edit option: " + text);
switch (this.modelkit.getUnitCellState()) {
case 0:
text = "packed";
break;
case 256:
text = "unpacked" + (this.modelkit.viewOffset == null ? "(no view offset)" : "(view offset=" + this.modelkit.viewOffset + ")");
break;
}
this.setLabel("xtalPackingPersistMenu", "Packing: " + text);
});
Clazz.defineMethod(c$, "setLabel", 
function(key, label){
this.menuSetLabel(this.htMenus.get(key), label);
}, "~S,~S");
Clazz.defineMethod(c$, "setActiveMenu", 
function(name){
var active = (name.indexOf("xtalMenu") >= 0 ? "xtalMenu" : name.indexOf("atomMenu") >= 0 ? "atomMenu" : name.indexOf("bondMenu") >= 0 ? "bondMenu" : null);
if (active != null) {
this.activeMenu = active;
if ((active === "xtalMenu") == (this.modelkit.getMKState() == 0)) this.modelkit.setMKState(active === "xtalMenu" ? 1 : 0);
this.vwr.refresh(1, "modelkit");
if (active === "bondMenu" && this.prevBondCheckBox == null) this.prevBondCheckBox = this.htMenus.get("assignBond_pP!RD");
} else if (name.indexOf("optionsMenu") >= 0) {
this.htMenus.get("undo").setEnabled(this.vwr.undoMoveAction(4165, 1275068425) > 0);
this.htMenus.get("redo").setEnabled(this.vwr.undoMoveAction(4140, 1275068425) > 0);
}return active;
}, "~S");
Clazz.overrideMethod(c$, "appUpdateSpecialCheckBoxValue", 
function(source, actionCommand, selected){
if (source == null || !selected) return;
var name = source.getName();
var mode;
if (!this.updatingForShow && (mode = this.setActiveMenu(name)) != null) {
var text = source.getText();
if (mode === "bondMenu") {
if (name.equals(this.bondRotationName)) {
this.bondRotationCheckBox = source;
} else {
this.prevBondCheckBox = source;
}}this.modelkit.setHoverLabel(this.activeMenu, text);
}}, "J.api.SC,~S,~B");
Clazz.defineMethod(c$, "exitBondRotation", 
function(){
this.modelkit.exitBondRotation(this.prevBondCheckBox == null ? null : this.prevBondCheckBox.getText());
this.vwr.setPickingMode(null, 33);
if (this.bondRotationCheckBox != null) this.bondRotationCheckBox.setSelected(false);
if (this.prevBondCheckBox != null) this.prevBondCheckBox.setSelected(true);
});
Clazz.overrideMethod(c$, "appGetBooleanProperty", 
function(name){
if (name.startsWith("mk")) {
return (this.modelkit.getProperty(name.substring(2))).booleanValue();
}return this.vwr.getBooleanProperty(name);
}, "~S");
Clazz.overrideMethod(c$, "getUnknownCheckBoxScriptToRun", 
function(item, name, what, TF){
if (name.startsWith("mk")) {
this.modelkit.processMKPropertyItem(name, TF);
return null;
}var element = this.modelkit.getElementFromUser();
if (element == null) return null;
this.menuSetLabel(item, element);
item.setActionCommand("assignAtom_" + element + "P!:??");
return "set picking assignAtom_" + element;
}, "J.api.SC,~S,~S,~B");
Clazz.overrideMethod(c$, "menuFocusCallback", 
function(name, actionCommand, gained){
if (gained && !this.modelkit.processSymop(name, true)) {
this.setActiveMenu(name);
}}, "~S,~S,~B");
Clazz.overrideMethod(c$, "menuClickCallback", 
function(source, script){
if (this.modelkit.processSymop(source.getName(), false)) return;
if (script.equals("clearQPersist")) {
for (var item, $item = this.htCheckbox.values().iterator (); $item.hasNext()&& ((item = $item.next ()) || true);) {
if (item.getActionCommand().indexOf(":??") < 0) continue;
this.menuSetLabel(item, "??");
item.setActionCommand("_??P!:");
}
this.appRunScript("set picking assignAtom_C");
return;
}this.doMenuClickCallback(source, script);
}, "J.api.SC,~S");
Clazz.overrideMethod(c$, "getScriptForCallback", 
function(source, id, script){
if (script.startsWith("mk")) {
this.modelkit.clickProcessXtal(id, script);
script = null;
}return script;
}, "J.api.SC,~S,~S");
Clazz.defineMethod(c$, "appRunSpecialCheckBox", 
function(item, basename, script, TF){
if (basename.indexOf("assignAtom_Xx") == 0) {
this.modelkit.resetAtomPickType();
}if (TF && !this.updatingForShow && basename.indexOf("Bond") < 0) {
this.updatingForShow = true;
this.exitBondRotation();
this.updatingForShow = false;
}return Clazz.superCall(this, J.modelkit.ModelKitPopup, "appRunSpecialCheckBox", [item, basename, script, TF]);
}, "J.api.SC,~S,~S,~B");
Clazz.defineMethod(c$, "updateCheckBoxesForModelKit", 
function(menuName){
var thisAtomType = "assignAtom_" + this.modelkit.pickAtomAssignType + "P";
var thisBondType = "assignBond_" + this.modelkit.pickBondAssignType;
for (var entry, $entry = this.htCheckbox.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) {
var item = entry.getValue();
var key = item.getActionCommand();
if (key.startsWith(thisBondType) || key.startsWith(thisAtomType)) {
this.updatingForShow = true;
item.setSelected(false);
item.setSelected(true);
this.updatingForShow = false;
}}
}, "~S");
c$.bundle =  new J.modelkit.ModelKitPopupResourceBundle(null, null);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
