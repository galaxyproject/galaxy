Clazz.declarePackage("JS");
Clazz.load(["JS.JComponent"], "JS.JTextField", ["JU.SB"], function(){
var c$ = Clazz.declareType(JS, "JTextField", JS.JComponent);
Clazz.makeConstructor(c$, 
function(value){
Clazz.superConstructor(this, JS.JTextField, ["txtJT"]);
this.text = value;
}, "~S");
Clazz.overrideMethod(c$, "toHTML", 
function(){
var sb =  new JU.SB();
sb.append("<input type=text id='" + this.id + "' class='JTextField' style='" + this.getCSSstyle(0, 0) + "' value='" + this.text + "' onkeyup	=SwingController.click(this,event)	>");
return sb.toString();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
