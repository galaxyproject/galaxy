Clazz.declarePackage("JV.binding");
Clazz.load(["JV.binding.JmolBinding"], "JV.binding.DragBinding", null, function(){
var c$ = Clazz.declareType(JV.binding, "DragBinding", JV.binding.JmolBinding);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, JV.binding.DragBinding, []);
this.set("drag");
});
Clazz.overrideMethod(c$, "setSelectBindings", 
function(){
this.bindAction(33040, 30);
this.bindAction(33041, 35);
this.bindAction(33048, 34);
this.bindAction(33049, 32);
this.bindAction(4368, 31);
this.bindAction(8464, 13);
this.bindAction(33040, 17);
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
