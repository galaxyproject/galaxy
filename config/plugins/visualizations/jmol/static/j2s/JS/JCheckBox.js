Clazz.declarePackage("JS");
Clazz.load(["JS.AbstractButton"], "JS.JCheckBox", null, function(){
var c$ = Clazz.declareType(JS, "JCheckBox", JS.AbstractButton);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, JS.JCheckBox, ["chkJCB"]);
});
Clazz.overrideMethod(c$, "toHTML", 
function(){
var s = "<label><input type=checkbox id='" + this.id + "' class='JCheckBox' style='" + this.getCSSstyle(0, 0) + "' " + (this.selected ? "checked='checked' " : "") + "onclick='SwingController.click(this)'>" + this.text + "</label>";
return s;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
