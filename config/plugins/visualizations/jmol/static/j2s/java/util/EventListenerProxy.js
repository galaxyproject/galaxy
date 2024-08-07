Clazz.load(["java.util.EventListener"], "java.util.EventListenerProxy", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.listener = null;
Clazz.instantialize(this, arguments);}, java.util, "EventListenerProxy", null, java.util.EventListener);
Clazz.makeConstructor(c$, 
function(listener){
this.listener = listener;
}, "java.util.EventListener");
Clazz.defineMethod(c$, "getListener", 
function(){
return this.listener;
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
