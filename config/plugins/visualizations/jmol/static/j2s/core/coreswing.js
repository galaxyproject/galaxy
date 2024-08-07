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
Clazz_declareInterface(J.api, "SC");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.LayoutManager"], "JS.BorderLayout", null, function(){
var c$ = Clazz_declareType(JS, "BorderLayout", JS.LayoutManager);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.Component", ["JU.CU"], function(){
var c$ = Clazz_decorateAsClass(function(){
this._visible = false;
this.enabled = true;
this.text = null;
this.name = null;
this.width = 0;
this.height = 0;
this.id = null;
this.parent = null;
this.mouseListener = null;
this.bgcolor = null;
this.minWidth = 30;
this.minHeight = 30;
this.renderWidth = 0;
this.renderHeight = 0;
Clazz_instantialize(this, arguments);}, JS, "Component", null);
Clazz_makeConstructor(c$, 
function(type){
this.id = JS.Component.newID(type);
if (type == null) return;
{
SwingController.register(this, type);
}}, "~S");
Clazz_defineMethod(c$, "setParent", 
function(p){
this.parent = p;
}, "~O");
c$.newID = Clazz_defineMethod(c$, "newID", 
function(type){
return type + ("" + Math.random()).substring(3, 10);
}, "~S");
Clazz_defineMethod(c$, "setBackground", 
function(color){
this.bgcolor = color;
}, "javajs.api.GenericColor");
Clazz_defineMethod(c$, "setText", 
function(text){
this.text = text;
{
SwingController.setText(this);
}}, "~S");
Clazz_defineMethod(c$, "setName", 
function(name){
this.name = name;
}, "~S");
Clazz_defineMethod(c$, "getName", 
function(){
return this.name;
});
Clazz_defineMethod(c$, "getParent", 
function(){
return this.parent;
});
Clazz_defineMethod(c$, "setPreferredSize", 
function(dimension){
this.width = dimension.width;
this.height = dimension.height;
}, "JS.Dimension");
Clazz_defineMethod(c$, "addMouseListener", 
function(listener){
this.mouseListener = listener;
}, "~O");
Clazz_defineMethod(c$, "getText", 
function(){
return this.text;
});
Clazz_defineMethod(c$, "isEnabled", 
function(){
return this.enabled;
});
Clazz_defineMethod(c$, "setEnabled", 
function(enabled){
this.enabled = enabled;
{
SwingController.setEnabled(this);
}}, "~B");
Clazz_defineMethod(c$, "isVisible", 
function(){
return this._visible;
});
Clazz_defineMethod(c$, "setVisible", 
function(visible){
this._visible = visible;
{
SwingController.setVisible(this);
}}, "~B");
Clazz_defineMethod(c$, "getHeight", 
function(){
return this.height;
});
Clazz_defineMethod(c$, "getWidth", 
function(){
return this.width;
});
Clazz_defineMethod(c$, "setMinimumSize", 
function(d){
this.minWidth = d.width;
this.minHeight = d.height;
}, "JS.Dimension");
Clazz_defineMethod(c$, "getSubcomponentWidth", 
function(){
return this.width;
});
Clazz_defineMethod(c$, "getSubcomponentHeight", 
function(){
return this.height;
});
Clazz_defineMethod(c$, "getCSSstyle", 
function(defaultPercentW, defaultPercentH){
var width = (this.renderWidth > 0 ? this.renderWidth : this.getSubcomponentWidth());
var height = (this.renderHeight > 0 ? this.renderHeight : this.getSubcomponentHeight());
return (width > 0 ? "width:" + width + "px;" : defaultPercentW > 0 ? "width:" + defaultPercentW + "%;" : "") + (height > 0 ? "height:" + height + "px;" : defaultPercentH > 0 ? "height:" + defaultPercentH + "%;" : "") + (this.bgcolor == null ? "" : "background-color:" + JU.CU.toCSSString(this.bgcolor) + ";");
}, "~N,~N");
Clazz_defineMethod(c$, "repaint", 
function(){
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.Component"], "JS.Container", ["JU.Lst"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.list = null;
this.cList = null;
Clazz_instantialize(this, arguments);}, JS, "Container", JS.Component);
Clazz_defineMethod(c$, "getComponent", 
function(i){
return this.list.get(i);
}, "~N");
Clazz_defineMethod(c$, "getComponentCount", 
function(){
return (this.list == null ? 0 : this.list.size());
});
Clazz_defineMethod(c$, "getComponents", 
function(){
if (this.cList == null) {
if (this.list == null) return  new Array(0);
this.cList = this.list.toArray();
}return this.cList;
});
Clazz_defineMethod(c$, "add", 
function(component){
return this.addComponent(component);
}, "JS.Component");
Clazz_defineMethod(c$, "addComponent", 
function(component){
if (this.list == null) this.list =  new JU.Lst();
this.list.addLast(component);
this.cList = null;
component.parent = this;
return component;
}, "JS.Component");
Clazz_defineMethod(c$, "insertComponent", 
function(component, index){
if (this.list == null) return this.addComponent(component);
this.list.add(index, component);
this.cList = null;
component.parent = this;
return component;
}, "JS.Component,~N");
Clazz_defineMethod(c$, "remove", 
function(i){
var c = this.list.removeItemAt(i);
c.parent = null;
this.cList = null;
}, "~N");
Clazz_defineMethod(c$, "removeAll", 
function(){
if (this.list != null) {
for (var i = this.list.size(); --i >= 0; ) this.list.get(i).parent = null;

this.list.clear();
}this.cList = null;
});
Clazz_defineMethod(c$, "getSubcomponentWidth", 
function(){
return (this.list != null && this.list.size() == 1 ? this.list.get(0).getSubcomponentWidth() : 0);
});
Clazz_defineMethod(c$, "getSubcomponentHeight", 
function(){
return (this.list != null && this.list.size() == 1 ? this.list.get(0).getSubcomponentHeight() : 0);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
(function(){
var c$ = Clazz_declareType(JS, "LayoutManager", null);
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["J.api.SC", "JS.JComponent"], "JS.AbstractButton", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.itemListener = null;
this.applet = null;
this.htmlName = null;
this.selected = false;
this.popupMenu = null;
this.icon = null;
Clazz_instantialize(this, arguments);}, JS, "AbstractButton", JS.JComponent, J.api.SC);
Clazz_makeConstructor(c$, 
function(type){
Clazz_superConstructor(this, JS.AbstractButton, [type]);
this.enabled = true;
}, "~S");
Clazz_overrideMethod(c$, "setSelected", 
function(selected){
this.selected = selected;
{
SwingController.setSelected(this);
}}, "~B");
Clazz_overrideMethod(c$, "isSelected", 
function(){
return this.selected;
});
Clazz_overrideMethod(c$, "addItemListener", 
function(listener){
this.itemListener = listener;
}, "~O");
Clazz_overrideMethod(c$, "getIcon", 
function(){
return this.icon;
});
Clazz_overrideMethod(c$, "setIcon", 
function(icon){
this.icon = icon;
}, "~O");
Clazz_overrideMethod(c$, "init", 
function(text, icon, actionCommand, popupMenu){
this.text = text;
this.icon = icon;
this.actionCommand = actionCommand;
this.popupMenu = popupMenu;
{
SwingController.initMenuItem(this);
}}, "~S,~O,~S,J.api.SC");
Clazz_defineMethod(c$, "getTopPopupMenu", 
function(){
return this.popupMenu;
});
Clazz_defineMethod(c$, "add", 
function(item){
this.addComponent(item);
}, "J.api.SC");
Clazz_overrideMethod(c$, "insert", 
function(subMenu, index){
this.insertComponent(subMenu, index);
}, "J.api.SC,~N");
Clazz_overrideMethod(c$, "getPopupMenu", 
function(){
return null;
});
Clazz_defineMethod(c$, "getMenuHTML", 
function(){
var label = (this.icon != null ? this.icon : this.text != null ? this.text : null);
var s = (label == null ? "" : "<li><a>" + label + "</a>" + this.htmlMenuOpener("ul"));
var n = this.getComponentCount();
if (n > 0) for (var i = 0; i < n; i++) s += this.getComponent(i).toHTML();

if (label != null) s += "</ul></li>";
return s;
});
Clazz_defineMethod(c$, "htmlMenuOpener", 
function(type){
return "<" + type + " id=\"" + this.id + "\"" + (this.enabled ? "" : this.getHtmlDisabled()) + ">";
}, "~S");
Clazz_defineMethod(c$, "getHtmlDisabled", 
function(){
return " disabled=\"disabled\"";
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "AbstractTableModel", JS.TableColumn);
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.ButtonGroup", ["JS.Component"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.id = null;
this.count = 0;
Clazz_instantialize(this, arguments);}, JS, "ButtonGroup", null);
Clazz_makeConstructor(c$, 
function(){
this.id = JS.Component.newID("bg");
});
Clazz_defineMethod(c$, "add", 
function(item){
this.count++;
(item).htmlName = this.id;
}, "J.api.SC");
Clazz_defineMethod(c$, "getButtonCount", 
function(){
return this.count;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
(function(){
var c$ = Clazz_decorateAsClass(function(){
this.component = null;
this.colspan = 0;
this.rowspan = 0;
this.textAlign = 0;
this.c = null;
Clazz_instantialize(this, arguments);}, JS, "Cell", null);
Clazz_makeConstructor(c$, 
function(btn, c){
this.component = btn;
this.colspan = c.gridwidth;
this.rowspan = c.gridheight;
this.c = c;
}, "JS.JComponent,JS.GridBagConstraints");
Clazz_defineMethod(c$, "toHTML", 
function(id){
var style = this.c.getStyle(false);
return "<td id='" + id + "' " + (this.colspan < 2 ? "" : "colspan='" + this.colspan + "' ") + style + "><span " + this.c.getStyle(true) + ">" + this.component.toHTML() + "</span></td>";
}, "~S");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "ColumnSelectionModel");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "Document");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.LayoutManager"], "JS.FlowLayout", null, function(){
var c$ = Clazz_declareType(JS, "FlowLayout", JS.LayoutManager);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.Grid", ["JU.AU", "$.SB", "JS.Cell"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.nrows = 0;
this.ncols = 0;
this.grid = null;
this.renderer = null;
Clazz_instantialize(this, arguments);}, JS, "Grid", null);
Clazz_makeConstructor(c$, 
function(rows, cols){
this.grid =  Clazz_newArray(0, 0, null);
}, "~N,~N");
Clazz_defineMethod(c$, "add", 
function(btn, c){
if (c.gridx >= this.ncols) {
this.ncols = c.gridx + 1;
for (var i = 0; i < this.nrows; i++) {
this.grid[i] = JU.AU.ensureLength(this.grid[i], this.ncols * 2);
}
}if (c.gridy >= this.nrows) {
var g =  new Array(c.gridy * 2 + 1);
for (var i = 0; i < this.nrows; i++) g[i] = this.grid[i];

for (var i = g.length; --i >= this.nrows; ) g[i] =  new Array(this.ncols * 2 + 1);

this.grid = g;
this.nrows = c.gridy + 1;
}this.grid[c.gridy][c.gridx] =  new JS.Cell(btn, c);
}, "JS.JComponent,JS.GridBagConstraints");
Clazz_defineMethod(c$, "toHTML", 
function(id){
var sb =  new JU.SB();
id += "_grid";
sb.append("\n<table id='" + id + "' class='Grid' style='width:100%;height:100%'><tr><td style='height:20%;width:20%'></td></tr>");
for (var i = 0; i < this.nrows; i++) {
var rowid = id + "_" + i;
sb.append("\n<tr id='" + rowid + "'><td></td>");
for (var j = 0; j < this.ncols; j++) if (this.grid[i][j] != null) sb.append(this.grid[i][j].toHTML(rowid + "_" + j));

sb.append("</tr>");
}
sb.append("\n<tr><td style='height:20%;width:20%'></td></tr></table>\n");
return sb.toString();
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(null, "JS.GridBagConstraints", ["JS.Insets"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.gridx = 0;
this.gridy = 0;
this.gridwidth = 0;
this.gridheight = 0;
this.weightx = 0;
this.weighty = 0;
this.anchor = 0;
this.fill = 0;
this.insets = null;
this.ipadx = 0;
this.ipady = 0;
Clazz_instantialize(this, arguments);}, JS, "GridBagConstraints", null);
Clazz_makeConstructor(c$, 
function(gridx, gridy, gridwidth, gridheight, weightx, weighty, anchor, fill, insets, ipadx, ipady){
this.gridx = gridx;
this.gridy = gridy;
this.gridwidth = gridwidth;
this.gridheight = gridheight;
this.weightx = weightx;
this.weighty = weighty;
this.anchor = anchor;
this.fill = fill;
if (insets == null) insets =  new JS.Insets(0, 0, 0, 0);
this.insets = insets;
this.ipadx = ipadx;
this.ipady = ipady;
}, "~N,~N,~N,~N,~N,~N,~N,~N,JS.Insets,~N,~N");
Clazz_defineMethod(c$, "getStyle", 
function(margins){
return "style='" + (margins ? "margin:" + this.insets.top + "px " + (this.ipady + this.insets.right) + "px " + this.insets.bottom + "px " + (this.ipadx + this.insets.left) + "px;" : "text-align:" + (this.anchor == 13 ? "right" : this.anchor == 17 ? "left" : "center")) + "'";
}, "~B");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.LayoutManager"], "JS.GridBagLayout", null, function(){
var c$ = Clazz_declareType(JS, "GridBagLayout", JS.LayoutManager);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
(function(){
var c$ = Clazz_decorateAsClass(function(){
this.top = 0;
this.left = 0;
this.bottom = 0;
this.right = 0;
Clazz_instantialize(this, arguments);}, JS, "Insets", null);
Clazz_makeConstructor(c$, 
function(top, left, bottom, right){
this.top = top;
this.left = left;
this.bottom = bottom;
this.right = right;
}, "~N,~N,~N,~N");
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.AbstractButton"], "JS.JButton", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JButton", JS.AbstractButton);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JButton, ["btnJB"]);
});
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<input type=button id='" + this.id + "' class='JButton' style='" + this.getCSSstyle(80, 0) + "' onclick='SwingController.click(this)' value='" + this.text + "'/>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.AbstractButton"], "JS.JCheckBox", null, function(){
var c$ = Clazz_declareType(JS, "JCheckBox", JS.AbstractButton);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JCheckBox, ["chkJCB"]);
});
Clazz_overrideMethod(c$, "toHTML", 
function(){
var s = "<label><input type=checkbox id='" + this.id + "' class='JCheckBox' style='" + this.getCSSstyle(0, 0) + "' " + (this.selected ? "checked='checked' " : "") + "onclick='SwingController.click(this)'>" + this.text + "</label>";
return s;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JMenuItem"], "JS.JCheckBoxMenuItem", null, function(){
var c$ = Clazz_declareType(JS, "JCheckBoxMenuItem", JS.JMenuItem);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JCheckBoxMenuItem, ["chk", 2]);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.AbstractButton"], "JS.JComboBox", ["JU.SB"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.info = null;
this.selectedIndex = 0;
Clazz_instantialize(this, arguments);}, JS, "JComboBox", JS.AbstractButton);
Clazz_makeConstructor(c$, 
function(info){
Clazz_superConstructor(this, JS.JComboBox, ["cmbJCB"]);
this.info = info;
}, "~A");
Clazz_defineMethod(c$, "setSelectedIndex", 
function(i){
this.selectedIndex = i;
{
SwingController.setSelectedIndex(this);
}}, "~N");
Clazz_defineMethod(c$, "getSelectedIndex", 
function(){
return this.selectedIndex;
});
Clazz_defineMethod(c$, "getSelectedItem", 
function(){
return (this.selectedIndex < 0 ? null : this.info[this.selectedIndex]);
});
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("\n<select id='" + this.id + "' class='JComboBox' onchange='SwingController.click(this)'>\n");
for (var i = 0; i < this.info.length; i++) sb.append("\n<option class='JComboBox_option'" + (i == this.selectedIndex ? "selected" : "") + ">" + this.info[i] + "</option>");

sb.append("\n</select>\n");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.Container"], "JS.JComponent", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.autoScrolls = false;
this.actionCommand = null;
this.actionListener = null;
Clazz_instantialize(this, arguments);}, JS, "JComponent", JS.Container);
Clazz_defineMethod(c$, "setAutoscrolls", 
function(b){
this.autoScrolls = b;
}, "~B");
Clazz_defineMethod(c$, "addActionListener", 
function(listener){
this.actionListener = listener;
}, "~O");
Clazz_defineMethod(c$, "getActionCommand", 
function(){
return this.actionCommand;
});
Clazz_defineMethod(c$, "setActionCommand", 
function(actionCommand){
this.actionCommand = actionCommand;
}, "~S");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JComponentImp", null, function(){
var c$ = Clazz_declareType(JS, "JComponentImp", JS.JComponent);
Clazz_overrideMethod(c$, "toHTML", 
function(){
return null;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JContentPane", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JContentPane", JS.JComponent);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JContentPane, ["JCP"]);
});
Clazz_defineMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("\n<div id='" + this.id + "' class='JContentPane' style='" + this.getCSSstyle(100, 100) + "'>\n");
if (this.list != null) for (var i = 0; i < this.list.size(); i++) sb.append(this.list.get(i).toHTML());

sb.append("\n</div>\n");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.Container"], "JS.JDialog", ["JU.SB", "JS.Color", "$.JContentPane"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.defaultWidth = 600;
this.defaultHeight = 300;
this.contentPane = null;
this.title = null;
this.html = null;
this.zIndex = 9000;
this.loc = null;
Clazz_instantialize(this, arguments);}, JS, "JDialog", JS.Container);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JDialog, ["JD"]);
this.add(this.contentPane =  new JS.JContentPane());
this.setBackground(JS.Color.get3(210, 210, 240));
this.contentPane.setBackground(JS.Color.get3(230, 230, 230));
});
Clazz_defineMethod(c$, "setZIndex", 
function(zIndex){
this.zIndex = zIndex;
}, "~N");
Clazz_defineMethod(c$, "setLocation", 
function(loc){
this.loc = loc;
}, "~A");
Clazz_defineMethod(c$, "getContentPane", 
function(){
return this.contentPane;
});
Clazz_defineMethod(c$, "setTitle", 
function(title){
this.title = title;
}, "~S");
Clazz_defineMethod(c$, "pack", 
function(){
this.html = null;
});
Clazz_defineMethod(c$, "validate", 
function(){
this.html = null;
});
Clazz_defineMethod(c$, "setVisible", 
function(tf){
if (tf && this.html == null) this.setDialog();
Clazz_superCall(this, JS.JDialog, "setVisible", [tf]);
if (tf) this.toFront();
}, "~B");
Clazz_defineMethod(c$, "dispose", 
function(){
{
{
SwingController.dispose(this);
}}});
Clazz_overrideMethod(c$, "repaint", 
function(){
this.setDialog();
});
Clazz_defineMethod(c$, "setDialog", 
function(){
this.html = this.toHTML();
{
SwingController.setDialog(this);
}});
Clazz_overrideMethod(c$, "toHTML", 
function(){
this.renderWidth = Math.max(this.width, this.getSubcomponentWidth());
if (this.renderWidth == 0) this.renderWidth = this.defaultWidth;
this.renderHeight = Math.max(this.height, this.contentPane.getSubcomponentHeight());
if (this.renderHeight == 0) this.renderHeight = this.defaultHeight;
var h = this.renderHeight - 25;
var sb =  new JU.SB();
sb.append("\n<div id='" + this.id + "' class='JDialog' style='" + this.getCSSstyle(0, 0) + "z-index:" + this.zIndex + ";position:relative;top:0px;left:0px;reize:both;'>\n");
sb.append("\n<div id='" + this.id + "_title' class='JDialogTitle' style='width:100%;height:25px;padding:5px 5px 5px 5px;height:" + 25 + "px'>" + "<span style='text-align:center;'>" + this.title + "</span><span style='position:absolute;text-align:right;right:1px;'>" + "<input type=button id='" + this.id + "_closer' onclick='SwingController.windowClosing(this)' value='x' /></span></div>\n");
sb.append("\n<div id='" + this.id + "_body' class='JDialogBody' style='width:100%;height:" + h + "px;" + "position: relative;left:0px;top:0px'>\n");
sb.append(this.contentPane.toHTML());
sb.append("\n</div></div>\n");
return sb.toString();
});
Clazz_defineMethod(c$, "toFront", 
function(){
{
SwingController.setFront(this);
}});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JEditorPane", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JEditorPane", JS.JComponent);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JEditorPane, ["txtJEP"]);
this.text = "";
});
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<textarea type=text id='" + this.id + "' class='JEditorPane' style='" + this.getCSSstyle(98, 98) + "'>" + this.text + "</textarea>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JLabel", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JLabel", JS.JComponent);
Clazz_makeConstructor(c$, 
function(text){
Clazz_superConstructor(this, JS.JLabel, ["lblJL"]);
this.text = text;
}, "~S");
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<span id='" + this.id + "' class='JLabel' style='" + this.getCSSstyle(0, 0) + "'>");
sb.append(this.text);
sb.append("</span>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JMenuItem"], "JS.JMenu", null, function(){
var c$ = Clazz_declareType(JS, "JMenu", JS.JMenuItem);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JMenu, ["mnu", 4]);
});
Clazz_defineMethod(c$, "getItemCount", 
function(){
return this.getComponentCount();
});
Clazz_defineMethod(c$, "getItem", 
function(i){
return this.getComponent(i);
}, "~N");
Clazz_overrideMethod(c$, "getPopupMenu", 
function(){
return this;
});
Clazz_overrideMethod(c$, "toHTML", 
function(){
return this.getMenuHTML();
});
{
{
// JSmolMenu.js
// author: Bob Hanson, hansonr@stolaf.edu
// BH 10/17/2015 6:18:38 PM wraps with Jmol.__$ to use same version of jQuery as Jmol is using
// BH 5/27/2014 11:01:46 PM frank menu fix; better event handling
// BH 5/26/2014 allow for a user callback for customization of menu
//    using Jmol._showMenuCallback(menu, x, y);
// BH 2/17/2014 7:52:18 AM Jmol.Menu folded into Jmol.Swing
// BH 1/16/2014 9:20:15 AM allowing second attempt to initiate this library to gracefully skip processing
//! jQuery UI - v1.9.2 - 2012-12-17
// http://jqueryui.com
// Includes: jquery.ui.core.js, jquery.ui.widget.js, jquery.ui.mouse.js, jquery.ui.position.js, jquery.ui.menu.js
// Copyright (c) 2012 jQuery Foundation and other contributors Licensed MIT
;(function(jQuery) {
if (!jQuery.ui)
try{
(function(e,t){function i(t,n){var r,i,o,u=t.nodeName.toLowerCase();return"area"===u?(r=t.parentNode,i=r.name,!t.href||!i||r.nodeName.toLowerCase()!=="map"?!1:(o=e("img[usemap=#"+i+"]")[0],!!o&&s(o))):(/input|select|textarea|button|object/.test(u)?!t.disabled:"a"===u?t.href||n:n)&&s(t)}function s(t){return e.expr.filters.visible(t)&&!e(t).parents().andSelf().filter(function(){return e.css(this,"visibility")==="hidden"}).length}var n=0,r=/^ui-id-\d+$/;e.ui=e.ui||{};if(e.ui.version)return;e.extend(e.ui,{version:"1.9.2",keyCode:{BACKSPACE:8,COMMA:188,DELETE:46,DOWN:40,END:35,ENTER:13,ESCAPE:27,HOME:36,LEFT:37,NUMPAD_ADD:107,NUMPAD_DECIMAL:110,NUMPAD_DIVIDE:111,NUMPAD_ENTER:108,NUMPAD_MULTIPLY:106,NUMPAD_SUBTRACT:109,PAGE_DOWN:34,PAGE_UP:33,PERIOD:190,RIGHT:39,SPACE:32,TAB:9,UP:38}}),e.fn.extend({_focus:e.fn.focus,focus:function(t,n){return typeof t=="number"?this.each(function(){var r=this;setTimeout(function(){e(r).focus(),n&&n.call(r)},t)}):this._focus.apply(this,arguments)},scrollParent:function(){var t;return e.ui.ie&&/(static|relative)/.test(this.css("position"))||/absolute/.test(this.css("position"))?t=this.parents().filter(function(){return/(relative|absolute|fixed)/.test(e.css(this,"position"))&&/(auto|scroll)/.test(e.css(this,"overflow")+e.css(this,"overflow-y")+e.css(this,"overflow-x"))}).eq(0):t=this.parents().filter(function(){return/(auto|scroll)/.test(e.css(this,"overflow")+e.css(this,"overflow-y")+e.css(this,"overflow-x"))}).eq(0),/fixed/.test(this.css("position"))||!t.length?e(document):t},zIndex:function(n){if(n!==t)return this.css("zIndex",n);if(this.length){var r=e(this[0]),i,s;while(r.length&&r[0]!==document){i=r.css("position");if(i==="absolute"||i==="relative"||i==="fixed"){s=parseInt(r.css("zIndex"),10);if(!isNaN(s)&&s!==0)return s}r=r.parent()}}return 0},uniqueId:function(){return this.each(function(){this.id||(this.id="ui-id-"+ ++n)})},removeUniqueId:function(){return this.each(function(){r.test(this.id)&&e(this).removeAttr("id")})}}),e.extend(e.expr[":"],{data:e.expr.createPseudo?e.expr.createPseudo(function(t){return function(n){return!!e.data(n,t)}}):function(t,n,r){return!!e.data(t,r[3])},focusable:function(t){return i(t,!isNaN(e.attr(t,"tabindex")))},tabbable:function(t){var n=e.attr(t,"tabindex"),r=isNaN(n);return(r||n>=0)&&i(t,!r)}}),e(function(){var t=document.body,n=t.appendChild(n=document.createElement("div"));n.offsetHeight,e.extend(n.style,{minHeight:"100px",height:"auto",padding:0,borderWidth:0}),e.support.minHeight=n.offsetHeight===100,e.support.selectstart="onselectstart"in n,t.removeChild(n).style.display="none"}),e("<a>").outerWidth(1).jquery||e.each(["Width","Height"],function(n,r){function u(t,n,r,s){return e.each(i,function(){n-=parseFloat(e.css(t,"padding"+this))||0,r&&(n-=parseFloat(e.css(t,"border"+this+"Width"))||0),s&&(n-=parseFloat(e.css(t,"margin"+this))||0)}),n}var i=r==="Width"?["Left","Right"]:["Top","Bottom"],s=r.toLowerCase(),o={innerWidth:e.fn.innerWidth,innerHeight:e.fn.innerHeight,outerWidth:e.fn.outerWidth,outerHeight:e.fn.outerHeight};e.fn["inner"+r]=function(n){return n===t?o["inner"+r].call(this):this.each(function(){e(this).css(s,u(this,n)+"px")})},e.fn["outer"+r]=function(t,n){return typeof t!="number"?o["outer"+r].call(this,t):this.each(function(){e(this).css(s,u(this,t,!0,n)+"px")})}}),e("<a>").data("a-b","a").removeData("a-b").data("a-b")&&(e.fn.removeData=function(t){return function(n){return arguments.length?t.call(this,e.camelCase(n)):t.call(this)}}(e.fn.removeData)),function(){var t=/msie ([\w.]+)/.exec(navigator.userAgent.toLowerCase())||[];e.ui.ie=t.length?!0:!1,e.ui.ie6=parseFloat(t[1],10)===6}(),e.fn.extend({disableSelection:function(){return this.bind((e.support.selectstart?"selectstart":"mousedown")+".ui-disableSelection",function(e){e.preventDefault()})},enableSelection:function(){return this.unbind(".ui-disableSelection")}}),e.extend(e.ui,{plugin:{add:function(t,n,r){var i,s=e.ui[t].prototype;for(i in r)s.plugins[i]=s.plugins[i]||[],s.plugins[i].push([n,r[i]])},call:function(e,t,n){var r,i=e.plugins[t];if(!i||!e.element[0].parentNode||e.element[0].parentNode.nodeType===11)return;for(r=0;r<i.length;r++)e.options[i[r][0]]&&i[r][1].apply(e.element,n)}},contains:e.contains,hasScroll:function(t,n){if(e(t).css("overflow")==="hidden")return!1;var r=n&&n==="left"?"scrollLeft":"scrollTop",i=!1;return t[r]>0?!0:(t[r]=1,i=t[r]>0,t[r]=0,i)},isOverAxis:function(e,t,n){return e>t&&e<t+n},isOver:function(t,n,r,i,s,o){return e.ui.isOverAxis(t,r,s)&&e.ui.isOverAxis(n,i,o)}})
})(jQuery);
}catch (e) {
System.out.println("coremenu failed to load jQuery.ui.core -- jQuery version conflict?");
}
if (!jQuery.ui.widget)
try{
(function(e,t){var n=0,r=Array.prototype.slice,i=e.cleanData;e.cleanData=function(t){for(var n=0,r;(r=t[n])!=null;n++)try{e(r).triggerHandler("remove")}catch(s){}i(t)},e.widget=function(t,n,r){var i,s,o,u,a=t.split(".")[0];t=t.split(".")[1],i=a+"-"+t,r||(r=n,n=e.Widget),e.expr[":"][i.toLowerCase()]=function(t){return!!e.data(t,i)},e[a]=e[a]||{},s=e[a][t],o=e[a][t]=function(e,t){if(!this._createWidget)return new o(e,t);arguments.length&&this._createWidget(e,t)},e.extend(o,s,{version:r.version,_proto:e.extend({},r),_childConstructors:[]}),u=new n,u.options=e.widget.extend({},u.options),e.each(r,function(t,i){e.isFunction(i)&&(r[t]=function(){var e=function(){return n.prototype[t].apply(this,arguments)},r=function(e){return n.prototype[t].apply(this,e)};return function(){var t=this._super,n=this._superApply,s;return this._super=e,this._superApply=r,s=i.apply(this,arguments),this._super=t,this._superApply=n,s}}())}),o.prototype=e.widget.extend(u,{widgetEventPrefix:s?u.widgetEventPrefix:t},r,{constructor:o,namespace:a,widgetName:t,widgetBaseClass:i,widgetFullName:i}),s?(e.each(s._childConstructors,function(t,n){var r=n.prototype;e.widget(r.namespace+"."+r.widgetName,o,n._proto)}),delete s._childConstructors):n._childConstructors.push(o),e.widget.bridge(t,o)},e.widget.extend=function(n){var i=r.call(arguments,1),s=0,o=i.length,u,a;for(;s<o;s++)for(u in i[s])a=i[s][u],i[s].hasOwnProperty(u)&&a!==t&&(e.isPlainObject(a)?n[u]=e.isPlainObject(n[u])?e.widget.extend({},n[u],a):e.widget.extend({},a):n[u]=a);return n},e.widget.bridge=function(n,i){var s=i.prototype.widgetFullName||n;e.fn[n]=function(o){var u=typeof o=="string",a=r.call(arguments,1),f=this;return o=!u&&a.length?e.widget.extend.apply(null,[o].concat(a)):o,u?this.each(function(){var r,i=e.data(this,s);if(!i)return e.error("cannot call methods on "+n+" prior to initialization; "+"attempted to call method '"+o+"'");if(!e.isFunction(i[o])||o.charAt(0)==="_")return e.error("no such method '"+o+"' for "+n+" widget instance");r=i[o].apply(i,a);if(r!==i&&r!==t)return f=r&&r.jquery?f.pushStack(r.get()):r,!1}):this.each(function(){var t=e.data(this,s);t?t.option(o||{})._init():e.data(this,s,new i(o,this))}),f}},e.Widget=function(){},e.Widget._childConstructors=[],e.Widget.prototype={widgetName:"widget",widgetEventPrefix:"",defaultElement:"<div>",options:{disabled:!1,create:null},_createWidget:function(t,r){r=e(r||this.defaultElement||this)[0],this.element=e(r),this.uuid=n++,this.eventNamespace="."+this.widgetName+this.uuid,this.options=e.widget.extend({},this.options,this._getCreateOptions(),t),this.bindings=e(),this.hoverable=e(),this.focusable=e(),r!==this&&(e.data(r,this.widgetName,this),e.data(r,this.widgetFullName,this),this._on(!0,this.element,{remove:function(e){e.target===r&&this.destroy()}}),this.document=e(r.style?r.ownerDocument:r.document||r),this.window=e(this.document[0].defaultView||this.document[0].parentWindow)),this._create(),this._trigger("create",null,this._getCreateEventData()),this._init()},_getCreateOptions:e.noop,_getCreateEventData:e.noop,_create:e.noop,_init:e.noop,destroy:function(){this._destroy(),this.element.unbind(this.eventNamespace).removeData(this.widgetName).removeData(this.widgetFullName).removeData(e.camelCase(this.widgetFullName)),this.widget().unbind(this.eventNamespace).removeAttr("aria-disabled").removeClass(this.widgetFullName+"-disabled "+"ui-state-disabled"),this.bindings.unbind(this.eventNamespace),this.hoverable.removeClass("ui-state-hover"),this.focusable.removeClass("ui-state-focus")},_destroy:e.noop,widget:function(){return this.element},option:function(n,r){var i=n,s,o,u;if(arguments.length===0)return e.widget.extend({},this.options);if(typeof n=="string"){i={},s=n.split("."),n=s.shift();if(s.length){o=i[n]=e.widget.extend({},this.options[n]);for(u=0;u<s.length-1;u++)o[s[u]]=o[s[u]]||{},o=o[s[u]];n=s.pop();if(r===t)return o[n]===t?null:o[n];o[n]=r}else{if(r===t)return this.options[n]===t?null:this.options[n];i[n]=r}}return this._setOptions(i),this},_setOptions:function(e){var t;for(t in e)this._setOption(t,e[t]);return this},_setOption:function(e,t){return this.options[e]=t,e==="disabled"&&(this.widget().toggleClass(this.widgetFullName+"-disabled ui-state-disabled",!!t).attr("aria-disabled",t),this.hoverable.removeClass("ui-state-hover"),this.focusable.removeClass("ui-state-focus")),this},enable:function(){return this._setOption("disabled",!1)},disable:function(){return this._setOption("disabled",!0)},_on:function(t,n,r){var i,s=this;typeof t!="boolean"&&(r=n,n=t,t=!1),r?(n=i=e(n),this.bindings=this.bindings.add(n)):(r=n,n=this.element,i=this.widget()),e.each(r,function(r,o){function u(){if(!t&&(s.options.disabled===!0||e(this).hasClass("ui-state-disabled")))return;return(typeof o=="string"?s[o]:o).apply(s,arguments)}typeof o!="string"&&(u.guid=o.guid=o.guid||u.guid||e.guid++);var a=r.match(/^(\w+)\s*(.*)$/),f=a[1]+s.eventNamespace,l=a[2];l?i.delegate(l,f,u):n.bind(f,u)})},_off:function(e,t){t=(t||"").split(" ").join(this.eventNamespace+" ")+this.eventNamespace,e.unbind(t).undelegate(t)},_delay:function(e,t){function n(){return(typeof e=="string"?r[e]:e).apply(r,arguments)}var r=this;return setTimeout(n,t||0)},_hoverable:function(t){this.hoverable=this.hoverable.add(t),this._on(t,{mouseenter:function(t){e(t.currentTarget).addClass("ui-state-hover")},mouseleave:function(t){e(t.currentTarget).removeClass("ui-state-hover")}})},_focusable:function(t){this.focusable=this.focusable.add(t),this._on(t,{focusin:function(t){e(t.currentTarget).addClass("ui-state-focus")},focusout:function(t){e(t.currentTarget).removeClass("ui-state-focus")}})},_trigger:function(t,n,r){var i,s,o=this.options[t];r=r||{},n=e.Event(n),n.type=(t===this.widgetEventPrefix?t:this.widgetEventPrefix+t).toLowerCase(),n.target=this.element[0],s=n.originalEvent;if(s)for(i in s)i in n||(n[i]=s[i]);return this.element.trigger(n,r),!(e.isFunction(o)&&o.apply(this.element[0],[n].concat(r))===!1||n.isDefaultPrevented())}},e.each({show:"fadeIn",hide:"fadeOut"},function(t,n){e.Widget.prototype["_"+t]=function(r,i,s){typeof i=="string"&&(i={effect:i});var o,u=i?i===!0||typeof i=="number"?n:i.effect||n:t;i=i||{},typeof i=="number"&&(i={duration:i}),o=!e.isEmptyObject(i),i.complete=s,i.delay&&r.delay(i.delay),o&&e.effects&&(e.effects.effect[u]||e.uiBackCompat!==!1&&e.effects[u])?r[t](i):u!==t&&r[u]?r[u](i.duration,i.easing,s):r.queue(function(n){e(this)[t](),s&&s.call(r[0]),n()})}}),e.uiBackCompat!==!1&&(e.Widget.prototype._getCreateOptions=function(){return e.metadata&&e.metadata.get(this.element[0])[this.widgetName]})
})(jQuery);
}catch (e) {
System.out.println("coremenu failed to load jQuery.ui.widget -- jQuery version conflict?");
}
if (!jQuery.ui.mouse)
try{
(function(e,t){var n=!1;e(document).mouseup(function(e){n=!1}),e.widget("ui.mouse",{version:"1.9.2",options:{cancel:"input,textarea,button,select,option",distance:1,delay:0},_mouseInit:function(){var t=this;this.element.bind("mousedown."+this.widgetName,function(e){return t._mouseDown(e)}).bind("click."+this.widgetName,function(n){if(!0===e.data(n.target,t.widgetName+".preventClickEvent"))return e.removeData(n.target,t.widgetName+".preventClickEvent"),n.stopImmediatePropagation(),!1}),this.started=!1},_mouseDestroy:function(){this.element.unbind("."+this.widgetName),this._mouseMoveDelegate&&e(document).unbind("mousemove."+this.widgetName,this._mouseMoveDelegate).unbind("mouseup."+this.widgetName,this._mouseUpDelegate)},_mouseDown:function(t){if(n)return;this._mouseStarted&&this._mouseUp(t),this._mouseDownEvent=t;var r=this,i=t.which===1,s=typeof this.options.cancel=="string"&&t.target.nodeName?e(t.target).closest(this.options.cancel).length:!1;if(!i||s||!this._mouseCapture(t))return!0;this.mouseDelayMet=!this.options.delay,this.mouseDelayMet||(this._mouseDelayTimer=setTimeout(function(){r.mouseDelayMet=!0},this.options.delay));if(this._mouseDistanceMet(t)&&this._mouseDelayMet(t)){this._mouseStarted=this._mouseStart(t)!==!1;if(!this._mouseStarted)return t.preventDefault(),!0}return!0===e.data(t.target,this.widgetName+".preventClickEvent")&&e.removeData(t.target,this.widgetName+".preventClickEvent"),this._mouseMoveDelegate=function(e){return r._mouseMove(e)},this._mouseUpDelegate=function(e){return r._mouseUp(e)},e(document).bind("mousemove."+this.widgetName,this._mouseMoveDelegate).bind("mouseup."+this.widgetName,this._mouseUpDelegate),t.preventDefault(),n=!0,!0},_mouseMove:function(t){return!e.ui.ie||document.documentMode>=9||!!t.button?this._mouseStarted?(this._mouseDrag(t),t.preventDefault()):(this._mouseDistanceMet(t)&&this._mouseDelayMet(t)&&(this._mouseStarted=this._mouseStart(this._mouseDownEvent,t)!==!1,this._mouseStarted?this._mouseDrag(t):this._mouseUp(t)),!this._mouseStarted):this._mouseUp(t)},_mouseUp:function(t){return e(document).unbind("mousemove."+this.widgetName,this._mouseMoveDelegate).unbind("mouseup."+this.widgetName,this._mouseUpDelegate),this._mouseStarted&&(this._mouseStarted=!1,t.target===this._mouseDownEvent.target&&e.data(t.target,this.widgetName+".preventClickEvent",!0),this._mouseStop(t)),!1},_mouseDistanceMet:function(e){return Math.max(Math.abs(this._mouseDownEvent.pageX-e.pageX),Math.abs(this._mouseDownEvent.pageY-e.pageY))>=this.options.distance},_mouseDelayMet:function(e){return this.mouseDelayMet},_mouseStart:function(e){},_mouseDrag:function(e){},_mouseStop:function(e){},_mouseCapture:function(e){return!0}})
})(jQuery);
}catch (e) {
System.out.println("coremenu failed to load jQuery.ui.mouse -- jQuery version conflict?");
}
if (!jQuery.ui.position)
try{
(function(e,t){function h(e,t,n){return[parseInt(e[0],10)*(l.test(e[0])?t/100:1),parseInt(e[1],10)*(l.test(e[1])?n/100:1)]}function p(t,n){return parseInt(e.css(t,n),10)||0}e.ui=e.ui||{};var n,r=Math.max,i=Math.abs,s=Math.round,o=/left|center|right/,u=/top|center|bottom/,a=/[\+\-]\d+%?/,f=/^\w+/,l=/%$/,c=e.fn.position;e.position={scrollbarWidth:function(){if(n!==t)return n;var r,i,s=e("<div style='display:block;width:50px;height:50px;overflow:hidden;'><div style='height:100px;width:auto;'></div></div>"),o=s.children()[0];return e("body").append(s),r=o.offsetWidth,s.css("overflow","scroll"),i=o.offsetWidth,r===i&&(i=s[0].clientWidth),s.remove(),n=r-i},getScrollInfo:function(t){var n=t.isWindow?"":t.element.css("overflow-x"),r=t.isWindow?"":t.element.css("overflow-y"),i=n==="scroll"||n==="auto"&&t.width<t.element[0].scrollWidth,s=r==="scroll"||r==="auto"&&t.height<t.element[0].scrollHeight;return{width:i?e.position.scrollbarWidth():0,height:s?e.position.scrollbarWidth():0}},getWithinInfo:function(t){var n=e(t||window),r=e.isWindow(n[0]);return{element:n,isWindow:r,offset:!r&&n.offset()||{left:0,top:0},scrollLeft:n.scrollLeft(),scrollTop:n.scrollTop(),width:r?n.width():n.outerWidth(),height:r?n.height():n.outerHeight()}}},e.fn.position=function(t){if(!t||!t.of)return c.apply(this,arguments);t=e.extend({},t);var n,l,d,v,m,g=e(t.of),y=e.position.getWithinInfo(t.within),b=e.position.getScrollInfo(y),w=g[0],E=(t.collision||"flip").split(" "),S={};return w.nodeType===9?(l=g.width(),d=g.height(),v={top:0,left:0}):e.isWindow(w)?(l=g.width(),d=g.height(),v={top:g.scrollTop(),left:g.scrollLeft()}):w.preventDefault?(t.at="left top",l=d=0,v={top:w.pageY,left:w.pageX}):(l=g.outerWidth(),d=g.outerHeight(),v=g.offset()),m=e.extend({},v),e.each(["my","at"],function(){var e=(t[this]||"").split(" "),n,r;e.length===1&&(e=o.test(e[0])?e.concat(["center"]):u.test(e[0])?["center"].concat(e):["center","center"]),e[0]=o.test(e[0])?e[0]:"center",e[1]=u.test(e[1])?e[1]:"center",n=a.exec(e[0]),r=a.exec(e[1]),S[this]=[n?n[0]:0,r?r[0]:0],t[this]=[f.exec(e[0])[0],f.exec(e[1])[0]]}),E.length===1&&(E[1]=E[0]),t.at[0]==="right"?m.left+=l:t.at[0]==="center"&&(m.left+=l/2),t.at[1]==="bottom"?m.top+=d:t.at[1]==="center"&&(m.top+=d/2),n=h(S.at,l,d),m.left+=n[0],m.top+=n[1],this.each(function(){var o,u,a=e(this),f=a.outerWidth(),c=a.outerHeight(),w=p(this,"marginLeft"),x=p(this,"marginTop"),T=f+w+p(this,"marginRight")+b.width,N=c+x+p(this,"marginBottom")+b.height,C=e.extend({},m),k=h(S.my,a.outerWidth(),a.outerHeight());t.my[0]==="right"?C.left-=f:t.my[0]==="center"&&(C.left-=f/2),t.my[1]==="bottom"?C.top-=c:t.my[1]==="center"&&(C.top-=c/2),C.left+=k[0],C.top+=k[1],e.support.offsetFractions||(C.left=s(C.left),C.top=s(C.top)),o={marginLeft:w,marginTop:x},e.each(["left","top"],function(r,i){e.ui.position[E[r]]&&e.ui.position[E[r]][i](C,{targetWidth:l,targetHeight:d,elemWidth:f,elemHeight:c,collisionPosition:o,collisionWidth:T,collisionHeight:N,offset:[n[0]+k[0],n[1]+k[1]],my:t.my,at:t.at,within:y,elem:a})}),e.fn.bgiframe&&a.bgiframe(),t.using&&(u=function(e){var n=v.left-C.left,s=n+l-f,o=v.top-C.top,u=o+d-c,h={target:{element:g,left:v.left,top:v.top,width:l,height:d},element:{element:a,left:C.left,top:C.top,width:f,height:c},horizontal:s<0?"left":n>0?"right":"center",vertical:u<0?"top":o>0?"bottom":"middle"};l<f&&i(n+s)<l&&(h.horizontal="center"),d<c&&i(o+u)<d&&(h.vertical="middle"),r(i(n),i(s))>r(i(o),i(u))?h.important="horizontal":h.important="vertical",t.using.call(this,e,h)}),a.offset(e.extend(C,{using:u}))})},e.ui.position={fit:{left:function(e,t){var n=t.within,i=n.isWindow?n.scrollLeft:n.offset.left,s=n.width,o=e.left-t.collisionPosition.marginLeft,u=i-o,a=o+t.collisionWidth-s-i,f;t.collisionWidth>s?u>0&&a<=0?(f=e.left+u+t.collisionWidth-s-i,e.left+=u-f):a>0&&u<=0?e.left=i:u>a?e.left=i+s-t.collisionWidth:e.left=i:u>0?e.left+=u:a>0?e.left-=a:e.left=r(e.left-o,e.left)},top:function(e,t){var n=t.within,i=n.isWindow?n.scrollTop:n.offset.top,s=t.within.height,o=e.top-t.collisionPosition.marginTop,u=i-o,a=o+t.collisionHeight-s-i,f;t.collisionHeight>s?u>0&&a<=0?(f=e.top+u+t.collisionHeight-s-i,e.top+=u-f):a>0&&u<=0?e.top=i:u>a?e.top=i+s-t.collisionHeight:e.top=i:u>0?e.top+=u:a>0?e.top-=a:e.top=r(e.top-o,e.top)}},flip:{left:function(e,t){var n=t.within,r=n.offset.left+n.scrollLeft,s=n.width,o=n.isWindow?n.scrollLeft:n.offset.left,u=e.left-t.collisionPosition.marginLeft,a=u-o,f=u+t.collisionWidth-s-o,l=t.my[0]==="left"?-t.elemWidth:t.my[0]==="right"?t.elemWidth:0,c=t.at[0]==="left"?t.targetWidth:t.at[0]==="right"?-t.targetWidth:0,h=-2*t.offset[0],p,d;if(a<0){p=e.left+l+c+h+t.collisionWidth-s-r;if(p<0||p<i(a))e.left+=l+c+h}else if(f>0){d=e.left-t.collisionPosition.marginLeft+l+c+h-o;if(d>0||i(d)<f)e.left+=l+c+h}},top:function(e,t){var n=t.within,r=n.offset.top+n.scrollTop,s=n.height,o=n.isWindow?n.scrollTop:n.offset.top,u=e.top-t.collisionPosition.marginTop,a=u-o,f=u+t.collisionHeight-s-o,l=t.my[1]==="top",c=l?-t.elemHeight:t.my[1]==="bottom"?t.elemHeight:0,h=t.at[1]==="top"?t.targetHeight:t.at[1]==="bottom"?-t.targetHeight:0,p=-2*t.offset[1],d,v;a<0?(v=e.top+c+h+p+t.collisionHeight-s-r,e.top+c+h+p>a&&(v<0||v<i(a))&&(e.top+=c+h+p)):f>0&&(d=e.top-t.collisionPosition.marginTop+c+h+p-o,e.top+c+h+p>f&&(d>0||i(d)<f)&&(e.top+=c+h+p))}},flipfit:{left:function(){e.ui.position.flip.left.apply(this,arguments),e.ui.position.fit.left.apply(this,arguments)},top:function(){e.ui.position.flip.top.apply(this,arguments),e.ui.position.fit.top.apply(this,arguments)}}},function(){var t,n,r,i,s,o=document.getElementsByTagName("body")[0],u=document.createElement("div");t=document.createElement(o?"div":"body"),r={visibility:"hidden",width:0,height:0,border:0,margin:0,background:"none"},o&&e.extend(r,{position:"absolute",left:"-1000px",top:"-1000px"});for(s in r)t.style[s]=r[s];t.appendChild(u),n=o||document.documentElement,n.insertBefore(t,n.firstChild),u.style.cssText="position: absolute; left: 10.7432222px;",i=e(u).offset().left,e.support.offsetFractions=i>10&&i<11,t.innerHTML="",n.removeChild(t)}(),e.uiBackCompat!==!1&&function(e){var n=e.fn.position;e.fn.position=function(r){if(!r||!r.offset)return n.call(this,r);var i=r.offset.split(" "),s=r.at.split(" ");return i.length===1&&(i[1]=i[0]),/^\d/.test(i[0])&&(i[0]="+"+i[0]),/^\d/.test(i[1])&&(i[1]="+"+i[1]),s.length===1&&(/left|center|right/.test(s[0])?s[1]="center":(s[1]=s[0],s[0]="center")),n.call(this,e.extend(r,{at:s[0]+i[0]+" "+s[1]+i[1],offset:t}))}}(jQuery)
})(jQuery);
}catch (e) {
System.out.println("coremenu failed to load jQuery.ui.position -- jQuery version conflict?");
}
//! jQuery UI - v1.9.2 - 2012-12-17
//http://jqueryui.com
//Includes: jquery.ui.core.css, jquery.ui.menu.css
//To view and modify this theme, visit http://jqueryui.com/themeroller/?ffDefault=Lucida%20Grande%2CLucida%20Sans%2CArial%2Csans-serif&fwDefault=bold&fsDefault=1.1em&cornerRadius=5px&bgColorHeader=5c9ccc&bgTextureHeader=12_gloss_wave.png&bgImgOpacityHeader=55&borderColorHeader=4297d7&fcHeader=ffffff&iconColorHeader=d8e7f3&bgColorContent=fcfdfd&bgTextureContent=06_inset_hard.png&bgImgOpacityContent=100&borderColorContent=a6c9e2&fcContent=222222&iconColorContent=469bdd&bgColorDefault=dfeffc&bgTextureDefault=03_highlight_soft.png&bgImgOpacityDefault=85&borderColorDefault=c5dbec&fcDefault=2e6e9e&iconColorDefault=6da8d5&bgColorHover=d0e5f5&bgTextureHover=03_highlight_soft.png&bgImgOpacityHover=75&borderColorHover=79b7e7&fcHover=1d5987&iconColorHover=217bc0&bgColorActive=f5f8f9&bgTextureActive=06_inset_hard.png&bgImgOpacityActive=100&borderColorActive=79b7e7&fcActive=e17009&iconColorActive=f9bd01&bgColorHighlight=fbec88&bgTextureHighlight=01_flat.png&bgImgOpacityHighlight=55&borderColorHighlight=fad42e&fcHighlight=363636&iconColorHighlight=2e83ff&bgColorError=fef1ec&bgTextureError=02_glass.png&bgImgOpacityError=95&borderColorError=cd0a0a&fcError=cd0a0a&iconColorError=cd0a0a&bgColorOverlay=aaaaaa&bgTextureOverlay=01_flat.png&bgImgOpacityOverlay=0&opacityOverlay=30&bgColorShadow=aaaaaa&bgTextureShadow=01_flat.png&bgImgOpacityShadow=0&opacityShadow=30&thicknessShadow=8px&offsetTopShadow=-8px&offsetLeftShadow=-8px&cornerRadiusShadow=8px
//Copyright (c) 2012 jQuery Foundation and other contributors Licensed MIT
if (!jQuery.ui.menu)
try{
(function(e,t){var n=!1;e.widget("ui.menu",{version:"1.9.2",defaultElement:"<ul>",delay:300,options:{icons:{submenu:"ui-icon-carat-1-e"},menus:"ul",position:{my:"left top",at:"right top"},role:"menu",blur:null,focus:null,select:null},_create:function(){this.activeMenu=this.element,this.element.uniqueId().addClass("ui-menu ui-widget ui-widget-content ui-corner-all").toggleClass("ui-menu-icons",!!this.element.find(".ui-icon").length).attr({role:this.options.role,tabIndex:0}).bind("click"+this.eventNamespace,e.proxy(function(e){this.options.disabled&&e.preventDefault()},this)),this.options.disabled&&this.element.addClass("ui-state-disabled").attr("aria-disabled","true"),this._on({"mousedown .ui-menu-item > a":function(e){e.preventDefault()},"click .ui-state-disabled > a":function(e){e.preventDefault()},"click .ui-menu-item:has(a)":function(t){var r=e(t.target).closest(".ui-menu-item");!n&&r.not(".ui-state-disabled").length&&(n=!0,this.select(t),r.has(".ui-menu").length?this.expand(t):this.element.is(":focus")||(this.element.trigger("focus",[!0]),this.active&&this.active.parents(".ui-menu").length===1&&clearTimeout(this.timer)))},"mouseenter .ui-menu-item":function(t){var n=e(t.currentTarget);n.siblings().children(".ui-state-active").removeClass("ui-state-active"),this.focus(t,n)},mouseleave:"collapseAll","mouseleave .ui-menu":"collapseAll",focus:function(e,t){var n=this.active||this.element.children(".ui-menu-item").eq(0);t||this.focus(e,n)},blur:function(t){this._delay(function(){e.contains(this.element[0],this.document[0].activeElement)||this.collapseAll(t)})},keydown:"_keydown"}),this.refresh(),this._on(this.document,{click:function(t){e(t.target).closest(".ui-menu").length||this.collapseAll(t),n=!1}})},_destroy:function(){this.element.removeAttr("aria-activedescendant").find(".ui-menu").andSelf().removeClass("ui-menu ui-widget ui-widget-content ui-corner-all ui-menu-icons").removeAttr("role").removeAttr("tabIndex").removeAttr("aria-labelledby").removeAttr("aria-expanded").removeAttr("aria-hidden").removeAttr("aria-disabled").removeUniqueId().show(),this.element.find(".ui-menu-item").removeClass("ui-menu-item").removeAttr("role").removeAttr("aria-disabled").children("a").removeUniqueId().removeClass("ui-corner-all ui-state-hover").removeAttr("tabIndex").removeAttr("role").removeAttr("aria-haspopup").children().each(function(){var t=e(this);t.data("ui-menu-submenu-carat")&&t.remove()}),this.element.find(".ui-menu-divider").removeClass("ui-menu-divider ui-widget-content")},_keydown:function(t){function a(e){return e.replace(/[\-\[\]{}()*+?.,\\\^$|#\s]/g,"\\$&")}var n,r,i,s,o,u=!0;switch(t.keyCode){case e.ui.keyCode.PAGE_UP:this.previousPage(t);break;case e.ui.keyCode.PAGE_DOWN:this.nextPage(t);break;case e.ui.keyCode.HOME:this._move("first","first",t);break;case e.ui.keyCode.END:this._move("last","last",t);break;case e.ui.keyCode.UP:this.previous(t);break;case e.ui.keyCode.DOWN:this.next(t);break;case e.ui.keyCode.LEFT:this.collapse(t);break;case e.ui.keyCode.RIGHT:this.active&&!this.active.is(".ui-state-disabled")&&this.expand(t);break;case e.ui.keyCode.ENTER:case e.ui.keyCode.SPACE:this._activate(t);break;case e.ui.keyCode.ESCAPE:this.collapse(t);break;default:u=!1,r=this.previousFilter||"",i=String.fromCharCode(t.keyCode),s=!1,clearTimeout(this.filterTimer),i===r?s=!0:i=r+i,o=new RegExp("^"+a(i),"i"),n=this.activeMenu.children(".ui-menu-item").filter(function(){return o.test(e(this).children("a").text())}),n=s&&n.index(this.active.next())!==-1?this.active.nextAll(".ui-menu-item"):n,n.length||(i=String.fromCharCode(t.keyCode),o=new RegExp("^"+a(i),"i"),n=this.activeMenu.children(".ui-menu-item").filter(function(){return o.test(e(this).children("a").text())})),n.length?(this.focus(t,n),n.length>1?(this.previousFilter=i,this.filterTimer=this._delay(function(){delete this.previousFilter},1e3)):delete this.previousFilter):delete this.previousFilter}u&&t.preventDefault()},_activate:function(e){this.active.is(".ui-state-disabled")||(this.active.children("a[aria-haspopup='true']").length?this.expand(e):this.select(e))},refresh:function(){var t,n=this.options.icons.submenu,r=this.element.find(this.options.menus);r.filter(":not(.ui-menu)").addClass("ui-menu ui-widget ui-widget-content ui-corner-all").hide().attr({role:this.options.role,"aria-hidden":"true","aria-expanded":"false"}).each(function(){var t=e(this),r=t.prev("a"),i=e("<span>").addClass("ui-menu-icon ui-icon "+n).data("ui-menu-submenu-carat",!0);r.attr("aria-haspopup","true").prepend(i),t.attr("aria-labelledby",r.attr("id"))}),t=r.add(this.element),t.children(":not(.ui-menu-item):has(a)").addClass("ui-menu-item").attr("role","presentation").children("a").uniqueId().addClass("ui-corner-all").attr({tabIndex:-1,role:this._itemRole()}),t.children(":not(.ui-menu-item)").each(function(){var t=e(this);/[^\-+�G��G��+�G��G��\s]/.test(t.text())||t.addClass("ui-widget-content ui-menu-divider")}),t.children(".ui-state-disabled").attr("aria-disabled","true"),this.active&&!e.contains(this.element[0],this.active[0])&&this.blur()},_itemRole:function(){return{menu:"menuitem",listbox:"option"}[this.options.role]},focus:function(e,t){var n,r;this.blur(e,e&&e.type==="focus"),this._scrollIntoView(t),this.active=t.first(),r=this.active.children("a").addClass("ui-state-focus"),this.options.role&&this.element.attr("aria-activedescendant",r.attr("id")),this.active.parent().closest(".ui-menu-item").children("a:first").addClass("ui-state-active"),e&&e.type==="keydown"?this._close():this.timer=this._delay(function(){this._close()},this.delay),n=t.children(".ui-menu"),n.length&&/^mouse/.test(e.type)&&this._startOpening(n),this.activeMenu=t.parent(),this._trigger("focus",e,{item:t})},_scrollIntoView:function(t){var n,r,i,s,o,u;this._hasScroll()&&(n=parseFloat(e.css(this.activeMenu[0],"borderTopWidth"))||0,r=parseFloat(e.css(this.activeMenu[0],"paddingTop"))||0,i=t.offset().top-this.activeMenu.offset().top-n-r,s=this.activeMenu.scrollTop(),o=this.activeMenu.height(),u=t.height(),i<0?this.activeMenu.scrollTop(s+i):i+u>o&&this.activeMenu.scrollTop(s+i-o+u))},blur:function(e,t){t||clearTimeout(this.timer);if(!this.active)return;this.active.children("a").removeClass("ui-state-focus"),this.active=null,this._trigger("blur",e,{item:this.active})},
_startOpening:function(e){
if (e.hasClass("ui-state-disabled"))return // BH
clearTimeout(this.timer);if(e.attr("aria-hidden")!=="true")return;this.timer=this._delay(function(){this._close(),this._open(e)},this.delay)},_open:function(t){var n=e.extend({of:this.active},this.options.position);clearTimeout(this.timer),this.element.find(".ui-menu").not(t.parents(".ui-menu")).hide().attr("aria-hidden","true"),t.show().removeAttr("aria-hidden").attr("aria-expanded","true").position(n)},collapseAll:function(t,n){clearTimeout(this.timer),this.timer=this._delay(function(){var r=n?this.element:e(t&&t.target).closest(this.element.find(".ui-menu"));r.length||(r=this.element),this._close(r),this.blur(t),this.activeMenu=r},this.delay)},_close:function(e){e||(e=this.active?this.active.parent():this.element),e.find(".ui-menu").hide().attr("aria-hidden","true").attr("aria-expanded","false").end().find("a.ui-state-active").removeClass("ui-state-active")},collapse:function(e){var t=this.active&&this.active.parent().closest(".ui-menu-item",this.element);t&&t.length&&(this._close(),this.focus(e,t))},expand:function(e){var t=this.active&&this.active.children(".ui-menu ").children(".ui-menu-item").first();t&&t.length&&(this._open(t.parent()),this._delay(function(){this.focus(e,t)}))},next:function(e){this._move("next","first",e)},previous:function(e){this._move("prev","last",e)},isFirstItem:function(){return this.active&&!this.active.prevAll(".ui-menu-item").length},isLastItem:function(){return this.active&&!this.active.nextAll(".ui-menu-item").length},_move:function(e,t,n){var r;this.active&&(e==="first"||e==="last"?r=this.active[e==="first"?"prevAll":"nextAll"](".ui-menu-item").eq(-1):r=this.active[e+"All"](".ui-menu-item").eq(0));if(!r||!r.length||!this.active)r=this.activeMenu.children(".ui-menu-item")[t]();this.focus(n,r)},nextPage:function(t){var n,r,i;if(!this.active){this.next(t);return}if(this.isLastItem())return;this._hasScroll()?(r=this.active.offset().top,i=this.element.height(),this.active.nextAll(".ui-menu-item").each(function(){return n=e(this),n.offset().top-r-i<0}),this.focus(t,n)):this.focus(t,this.activeMenu.children(".ui-menu-item")[this.active?"last":"first"]())},previousPage:function(t){var n,r,i;if(!this.active){this.next(t);return}if(this.isFirstItem())return;this._hasScroll()?(r=this.active.offset().top,i=this.element.height(),this.active.prevAll(".ui-menu-item").each(function(){return n=e(this),n.offset().top-r+i>0}),this.focus(t,n)):this.focus(t,this.activeMenu.children(".ui-menu-item").first())},_hasScroll:function(){return this.element.outerHeight()<this.element.prop("scrollHeight")},select:function(t){this.active=this.active||e(t.target).closest(".ui-menu-item");var n={item:this.active};this.active.has(".ui-menu").length||this.collapseAll(t,!0),this._trigger("select",t,n)}})
})(jQuery);
}catch (e) {
System.out.println("JSmolMenu failed to load jQuery.ui.menu -- jQuery version conflict?");
}
;(function(Swing) {
//Jmol.Swing methods to coordinate with JS.JPopupMenu && JS.AbstractButton
//classes, which call SwingController (aka Jmol.Swing in this case)
//@author: Bob Hanson 2/17/2014 8:21:10 AM
if (Swing.menuInitialized)return;
Swing.menuCounter = 0;
Swing.menuInitialized = 1;
Swing.__getMenuStyle = function(applet) { return '\
.jmolPopupMenu{font-family:Arial,sans-serif;font-size:11px;position:absolute;z-index:'+Jmol._getZ(applet, "menu")+'}\
.jmolPopupMenu,.jmolPopupMenu .ui-corner-all{border-radius:5px}\
.jmolPopupMenu,.jmolPopupMenu .ui-widget-content{border:1px solid #a6c9e2;background-color:#fcfdfd;color:#222}\
.jmolPopupMenu a{color:#222;font-size:10px;}\
.jmolPopupMenu input[type="checkbox"]{vertical-align:middle;}\
.jmolPopupMenu,.jmolPopupMenu .ui-menu{list-style:none;padding:2px;margin:0;display:block;outline:none;box-shadow:1px 1px 5px rgba(50,50,50,0.75)}\
.jmolPopupMenu .ui-menu{margin-top:-3px;position:absolute}\
.jmolPopupMenu .ui-menu-item{cursor:pointer;margin:0 2ex 0 0;padding:0;width:100%}\
.jmolPopupMenu .ui-menu-divider{margin:3px 1px;height:0;font-size:0;line-height:0;border-width:1px 0 0 0}\
.jmolPopupMenu .ui-menu-item a{text-decoration:none;display:block;padding:0.05em 0.4em;white-space:nowrap;border:1px solid transparent}\
.jmolPopupMenu .ui-menu-icons{position:relative}\
.jmolPopupMenu .ui-menu-icons .ui-menu-item a{position:relative;padding-left:2em}\
.jmolPopupMenu .ui-icon{display:block;text-indent:-99999px;overflow:hidden;background-repeat:no-repeat;position:absolute;top:.2em;left:.2em}\
.jmolPopupMenu .ui-menu-icon{position:static;float:right}\
.jmolPopupMenu .ui-icon-carat-1-e{min-width:2ex;text-align:right;background-image:none;background-position:0 0}\
.jmolPopupMenu .ui-icon-carat-1-e:after{content:"\\25B8"}\
.jmolPopupMenu .ui-state-default{border:1px solid #c5dbec;background:#dfeffc;color:#2e6e9e}\
.jmolPopupMenu .ui-state-default a{color:#2e6e9e;text-decoration:none}\
.jmolPopupMenu .ui-state-hover,.jmolPopupMenu .ui-state-focus{border:1px solid #79b7e7;background:#d0e5f5;color:#1d5987}\
.jmolPopupMenu .ui-state-hover a{color:#1d5987;text-decoration:none}\
.jmolPopupMenu .ui-state-active{border:1px solid #79b7e7;background:#f5f8f9;color:#e17009}\
.jmolPopupMenu .ui-state-active a{color:#e17009;text-decoration:none}\
.jmolPopupMenu .ui-state-highlight{border:1px solid #fad42e;background:#fbec88;color:#363636}\
.jmolPopupMenu .ui-state-highlight a{color:#363636}\
.jmolPopupMenu .ui-state-disabled *{background:grey!important,color:#d6d6d6!important;font-weight:normal;cursor:default}\
.jmolPopupMenu .ui-state-disabled a:hover{background-color:transparent!important;border-color:transparent!important}\
.jmolPopupMenu .ui-state-disabled .ui-icon{filter:Alpha(Opacity=35)}'};
Swing.setMenu = function(menu) {
// called by JS.JPopupMenu
// note that the z-index is only set by the FIRST applet accessing this method
Swing.__getMenuStyle && Jmol.$after("head", '<style>'+Swing.__getMenuStyle(menu.applet)+'</style>');
Swing.__getStyle = null; // once only
menu.tainted = true;
menu.popupMenu = menu;
menu.id = "top";
menu.id = Swing.getMenuID(menu);
menu.applet._menus || (menu.applet._menus = {});
menu.applet._menus[menu.name] = menu;
Jmol.$after("body",'<ul id="' + menu.id + '" class="jmolPopupMenu"></ul>');
menu.setContainer(Jmol.$('#' + menu.id));
}
Swing.showMenu = function(menu, x, y) {
// called by JS.JPopupMenu
// allow for a user callback for customization of menu
if (Jmol._showMenuCallback)
Jmol._showMenuCallback(menu, x, y);
if (menu.tainted) {
menu.container.html(menu.toHTML());
menu.tainted = false;
Swing.bindMenuActionCommands(menu, true);
}
menu.setPosition();
menu.container.hide().menu().menu('refresh').show();
menu._visible = true;
menu.timestamp = System.currentTimeMillis();
menu.dragBind(true);
menu.container.unbind('clickoutjsmol');
if (!Jmol._persistentMenu)
menu.container.bind('clickoutjsmol mousemoveoutjsmol', function(evspecial, target, ev) {
if (System.currentTimeMillis() - menu.timestamp > 1000)
Swing.hideMenu(menu);
});
menu.container.bind("contextmenu", function() {return false;})
}
Swing.disposeMenu = function(menu) {
// called by JS.JPopupMenu
if (Jmol._persistentMenu)
return
Swing.hideMenu(menu);
Swing.bindMenuActionCommands(menu, false);
delete menu.applet._menus[menu.name];
}
Swing.initMenuItem = function(item) {
// called by JS.AbstractButton
item.applet = item.popupMenu.applet;
item.id = Swing.getMenuID(item);
item.icon && (item.icon = '<img src="' + item.applet._j2sPath + '/' + item.icon + '" style="max-height: 20px;" />')
}
Swing.getMenuID = function(item) {
// called internally
var popup = item.popupMenu;
return popup.applet._id + '_' + popup.name + "_" + item.id + '_' + (++Swing.menuCounter);
}
Swing.hideMenu = function(menu) {
// called internally
if (!menu._visible)return;
//menu.container.unbind('clickoutjsmol');
menu.dragBind(false);
menu.container.hide();
menu._visible = menu.isDragging = false;
};
var delayHide = function(menu, f) {
setTimeout(function(){Swing.hideMenus(menu.applet);f();},500);
}
Swing.bindMenuActionCommands = function(menu, isBind) {
// called internally
var n = menu.getComponentCount();
for(var i = 0; i < n; i++)
Swing.bindMenuActionCommands(menu.getComponent(i), isBind);
Jmol.$documentOff('click mouseup mouseover mousedown touchstart touchend mouseenter mouseleave', menu.id);
if (isBind) {
Jmol.$documentOn('click', menu.id, function(event) {
var name= "" + menu.name;
var dohide = (name.indexOf("Persist") < 0 || name.indexOf("!Persist") >= 0);
if (menu.itemListener) {
menu.selected = (menu.btnType == 2 ? Jmol.$prop(menu.id + "-cb", "checked") : true);
if (dohide)
delayHide(menu, function() {menu.itemListener.itemStateChanged({getSource:function(){return menu}})});
} else if (menu.actionListener) {
if (dohide)
delayHide(menu, function() {menu.actionListener.actionPerformed({getSource:function(){return menu},getActionCommand:function(){return menu.actionCommand}})});
}
});
Jmol.$documentOn('mouseup mouseover mousedown touchstart touchend mouseenter mouseleave', menu.id, function(event) {
if (menu.mouseListener && menu.mouseListener.handleEvent) {
menu.mouseListener.handleEvent({jqevent:event,getID:function(){return event.type},getSource:function(){return menu}});
}
});
}
}
})(Jmol.Swing);
})(Jmol.__$);
}}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.AbstractButton"], "JS.JMenuItem", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.btnType = 0;
Clazz_instantialize(this, arguments);}, JS, "JMenuItem", JS.AbstractButton);
Clazz_makeConstructor(c$, 
function(text){
Clazz_superConstructor(this, JS.JMenuItem, ["btn"]);
this.setText(text);
this.btnType = (text == null ? 0 : 1);
}, "~S");
Clazz_makeConstructor(c$, 
function(type, i){
Clazz_superConstructor(this, JS.JMenuItem, [type]);
this.btnType = i;
}, "~S,~N");
Clazz_overrideMethod(c$, "toHTML", 
function(){
return this.htmlMenuOpener("li") + (this.text == null ? "" : "<a>" + this.htmlLabel() + "</a>") + "</li>";
});
Clazz_overrideMethod(c$, "getHtmlDisabled", 
function(){
return " class=\"ui-state-disabled\"";
});
Clazz_defineMethod(c$, "htmlLabel", 
function(){
return (this.btnType == 1 ? this.text : "<label><input id=\"" + this.id + "-" + (this.btnType == 3 ? "r" : "c") + "b\" type=\"" + (this.btnType == 3 ? "radio\" name=\"" + this.htmlName : "checkbox") + "\" " + (this.selected ? "checked" : "") + " />" + this.text + "</label>");
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JPanel", ["JU.SB", "JS.Grid", "$.GridBagConstraints"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.grid = null;
this.nElements = 0;
this.last = null;
Clazz_instantialize(this, arguments);}, JS, "JPanel", JS.JComponent);
Clazz_makeConstructor(c$, 
function(manager){
Clazz_superConstructor(this, JS.JPanel, ["JP"]);
this.grid =  new JS.Grid(10, 10);
}, "JS.LayoutManager");
Clazz_defineMethod(c$, "add", 
function(btn, c){
this.last = (++this.nElements == 1 ? btn : null);
if ((typeof(c)=='string')) {
if (c.equals("North")) c =  new JS.GridBagConstraints(0, 0, 3, 1, 0, 0, 10, 0, null, 0, 0);
 else if (c.equals("South")) c =  new JS.GridBagConstraints(0, 2, 3, 1, 0, 0, 10, 0, null, 0, 0);
 else if (c.equals("East")) c =  new JS.GridBagConstraints(2, 1, 1, 1, 0, 0, 13, 0, null, 0, 0);
 else if (c.equals("West")) c =  new JS.GridBagConstraints(0, 1, 1, 1, 0, 0, 17, 0, null, 0, 0);
 else c =  new JS.GridBagConstraints(1, 1, 1, 1, 0, 0, 10, 0, null, 0, 0);
}this.grid.add(btn, c);
}, "JS.JComponent,~O");
Clazz_overrideMethod(c$, "toHTML", 
function(){
if (this.last != null) {
this.grid =  new JS.Grid(1, 1);
this.grid.add(this.last,  new JS.GridBagConstraints(0, 0, 1, 1, 0, 0, 10, 0, null, 0, 0));
this.last = null;
}var sb =  new JU.SB();
sb.append("\n<div id='" + this.id + "' class='JPanel' style='" + this.getCSSstyle(100, 100) + "'>\n");
sb.append("\n<span id='" + this.id + "_minimizer' style='width:" + this.minWidth + "px;height:" + this.minHeight + "px;'>");
sb.append(this.grid.toHTML(this.id));
sb.append("</span>");
sb.append("\n</div>\n");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.AbstractButton"], "JS.JPopupMenu", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.tainted = true;
Clazz_instantialize(this, arguments);}, JS, "JPopupMenu", JS.AbstractButton);
Clazz_makeConstructor(c$, 
function(name){
Clazz_superConstructor(this, JS.JPopupMenu, ["mnu"]);
this.name = name;
}, "~S");
Clazz_defineMethod(c$, "setInvoker", 
function(applet){
this.applet = applet;
{
SwingController.setMenu(this);
}}, "~O");
Clazz_defineMethod(c$, "show", 
function(applet, x, y){
if (applet != null) this.tainted = true;
{
SwingController.showMenu(this, x, y);
}}, "JS.Component,~N,~N");
Clazz_defineMethod(c$, "disposeMenu", 
function(){
{
SwingController.disposeMenu(this);
}});
Clazz_overrideMethod(c$, "toHTML", 
function(){
return this.getMenuHTML();
});
{
{
SwingController.setDraggable(JS.JPopupMenu);
}}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JMenuItem"], "JS.JRadioButtonMenuItem", null, function(){
var c$ = Clazz_decorateAsClass(function(){
this.isRadio = true;
Clazz_instantialize(this, arguments);}, JS, "JRadioButtonMenuItem", JS.JMenuItem);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JRadioButtonMenuItem, ["rad", 3]);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JScrollPane", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JScrollPane", JS.JComponent);
Clazz_makeConstructor(c$, 
function(component){
Clazz_superConstructor(this, JS.JScrollPane, ["JScP"]);
this.add(component);
}, "JS.JComponent");
Clazz_defineMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("\n<div id='" + this.id + "' class='JScrollPane' style='" + this.getCSSstyle(98, 98) + "overflow:auto'>\n");
if (this.list != null) {
var c = this.list.get(0);
sb.append(c.toHTML());
}sb.append("\n</div>\n");
return sb.toString();
});
Clazz_overrideMethod(c$, "setMinimumSize", 
function(dimension){
}, "JS.Dimension");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JSplitPane", ["JU.SB", "JS.JComponentImp"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.isH = true;
this.split = 1;
this.right = null;
this.left = null;
Clazz_instantialize(this, arguments);}, JS, "JSplitPane", JS.JComponent);
Clazz_makeConstructor(c$, 
function(split){
Clazz_superConstructor(this, JS.JSplitPane, ["JSpP"]);
this.split = split;
this.isH = (split == 1);
}, "~N");
Clazz_defineMethod(c$, "setRightComponent", 
function(r){
this.right =  new JS.JComponentImp(null);
this.right.add(r);
}, "JS.JComponent");
Clazz_defineMethod(c$, "setLeftComponent", 
function(l){
this.left =  new JS.JComponentImp(null);
this.left.add(l);
}, "JS.JComponent");
Clazz_defineMethod(c$, "getSubcomponentWidth", 
function(){
var w = this.width;
if (w == 0) {
var wleft = this.left.getSubcomponentWidth();
var wright = this.right.getSubcomponentWidth();
if (wleft > 0 && wright > 0) {
if (this.isH) w = wleft + wright;
 else w = Math.max(wleft, wright);
}}return w;
});
Clazz_defineMethod(c$, "getSubcomponentHeight", 
function(){
var h = this.height;
if (h == 0) {
var hleft = this.left.getSubcomponentHeight();
var hright = this.right.getSubcomponentHeight();
if (hleft > 0 && hright > 0) {
if (this.isH) h = Math.max(hleft, hright);
 else h = hleft + hright;
}}return h;
});
Clazz_defineMethod(c$, "toHTML", 
function(){
if (this.left == null || this.right == null) return "";
var isH = (this.split == 1);
if (this.width == 0) this.width = this.getSubcomponentWidth();
if (this.height == 0) this.height = this.getSubcomponentHeight();
var sb =  new JU.SB();
sb.append("<div id='" + this.id + "' class='JSplitPane' style='" + this.getCSSstyle(100, 100) + "'>");
if (isH) sb.append("<div id='" + this.id + "_left' style='width:50%;height:100%;position:absolute;top:0%;left:0%'>");
 else sb.append("<div id='" + this.id + "_top' style='width:100%;height:50%;position:absolute;top:0%;left:0%'>");
sb.append(this.left.getComponents()[0].toHTML());
if (isH) sb.append("</div><div id='" + this.id + "_right' style='width:50%;height:100%;position:absolute;top:0%;left:50%'>");
 else sb.append("</div><div id='" + this.id + "_bottom' style='width:100%;height:50%;position:absolute;top:50%;left:0%'>");
sb.append(this.right.getComponents()[0].toHTML());
sb.append("</div></div>\n");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.ColumnSelectionModel", "$.JComponent", "$.ListSelectionModel"], "JS.JTable", ["JU.BS", "$.SB"], function(){
var c$ = Clazz_decorateAsClass(function(){
this.tableModel = null;
this.bsSelectedCells = null;
this.bsSelectedRows = null;
this.rowSelectionAllowed = false;
this.cellSelectionEnabled = false;
this.selectionListener = null;
Clazz_instantialize(this, arguments);}, JS, "JTable", JS.JComponent, [JS.ListSelectionModel, JS.ColumnSelectionModel]);
Clazz_makeConstructor(c$, 
function(tableModel){
Clazz_superConstructor(this, JS.JTable, ["JT"]);
this.tableModel = tableModel;
this.bsSelectedCells =  new JU.BS();
this.bsSelectedRows =  new JU.BS();
}, "JS.AbstractTableModel");
Clazz_overrideMethod(c$, "getSelectionModel", 
function(){
return this;
});
Clazz_defineMethod(c$, "getColumnModel", 
function(){
return this;
});
Clazz_defineMethod(c$, "setPreferredScrollableViewportSize", 
function(dimension){
this.width = dimension.width;
this.height = dimension.height;
}, "JS.Dimension");
Clazz_defineMethod(c$, "clearSelection", 
function(){
this.bsSelectedCells.clearAll();
this.bsSelectedRows.clearAll();
});
Clazz_defineMethod(c$, "setRowSelectionAllowed", 
function(b){
this.rowSelectionAllowed = b;
}, "~B");
Clazz_defineMethod(c$, "setRowSelectionInterval", 
function(i, j){
this.bsSelectedRows.clearAll();
this.bsSelectedRows.setBits(i, j);
this.bsSelectedCells.clearAll();
}, "~N,~N");
Clazz_defineMethod(c$, "setCellSelectionEnabled", 
function(enabled){
this.cellSelectionEnabled = enabled;
}, "~B");
Clazz_overrideMethod(c$, "addListSelectionListener", 
function(listener){
this.selectionListener = listener;
}, "~O");
Clazz_overrideMethod(c$, "getColumn", 
function(i){
return this.tableModel.getColumn(i);
}, "~N");
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("\n<table id='" + this.id + "_table' class='JTable' >");
this.tableModel.toHTML(sb, this.id, this.bsSelectedRows);
sb.append("\n</table>\n");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.JComponent"], "JS.JTextField", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JTextField", JS.JComponent);
Clazz_makeConstructor(c$, 
function(value){
Clazz_superConstructor(this, JS.JTextField, ["txtJT"]);
this.text = value;
}, "~S");
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<input type=text id='" + this.id + "' class='JTextField' style='" + this.getCSSstyle(0, 0) + "' value='" + this.text + "' onkeyup	=SwingController.click(this,event)	>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_load(["JS.Document", "$.JComponent"], "JS.JTextPane", ["JU.SB"], function(){
var c$ = Clazz_declareType(JS, "JTextPane", JS.JComponent, JS.Document);
Clazz_makeConstructor(c$, 
function(){
Clazz_superConstructor(this, JS.JTextPane, ["txtJTP"]);
this.text = "";
});
Clazz_defineMethod(c$, "getDocument", 
function(){
return this;
});
Clazz_overrideMethod(c$, "insertString", 
function(i, s, object){
i = Math.min(i, this.text.length);
this.text = this.text.substring(0, i) + s + this.text.substring(i);
}, "~N,~S,~O");
Clazz_overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<textarea type=text id='" + this.id + "' class='JTextPane' style='" + this.getCSSstyle(98, 98) + "'>" + this.text + "</textarea>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "ListSelectionModel");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
(function(){
var c$ = Clazz_declareType(JS, "SwingConstants", null);
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "TableCellRenderer");
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
Clazz_declarePackage("JS");
Clazz_declareInterface(JS, "TableColumn");
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
