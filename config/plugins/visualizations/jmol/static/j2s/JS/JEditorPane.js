Clazz.declarePackage("JS");
Clazz.load(["JS.JComponent"], "JS.JEditorPane", ["JU.SB"], function(){
var c$ = Clazz.declareType(JS, "JEditorPane", JS.JComponent);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor(this, JS.JEditorPane, ["txtJEP"]);
this.text = "";
});
Clazz.overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<textarea type=text id='" + this.id + "' class='JEditorPane' style='" + this.getCSSstyle(98, 98) + "'>" + this.text + "</textarea>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
