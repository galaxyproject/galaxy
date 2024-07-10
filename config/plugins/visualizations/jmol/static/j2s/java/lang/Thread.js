Clazz.load(null, "java.lang.Thread", ["java.util.Date"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.target = null;
this.group = null;
this.name = null;
this.priority = 0;
Clazz.instantialize(this, arguments);}, java.lang, "Thread", null, Runnable);
/*LV!1824 unnec constructor*/Clazz.makeConstructor(c$, 
function(target){
this.init(null, target, "Thread-" +  new java.util.Date().getTime() + Math.random(), 0);
}, "Runnable");
Clazz.makeConstructor(c$, 
function(group, target){
this.init(group, target, "Thread-" +  new java.util.Date().getTime() + Math.random(), 0);
}, "ThreadGroup,Runnable");
Clazz.makeConstructor(c$, 
function(name){
this.init(null, null, name, 0);
}, "~S");
Clazz.makeConstructor(c$, 
function(group, name){
this.init(group, null, name, 0);
}, "ThreadGroup,~S");
Clazz.makeConstructor(c$, 
function(target, name){
this.init(null, target, name, 0);
}, "Runnable,~S");
Clazz.makeConstructor(c$, 
function(group, target, name){
this.init(group, target, name, 0);
}, "ThreadGroup,Runnable,~S");
Clazz.makeConstructor(c$, 
function(group, target, name, stackSize){
this.init(group, target, name, stackSize);
}, "ThreadGroup,Runnable,~S,~N");
c$.currentThread = Clazz.defineMethod(c$, "currentThread", 
function(){
if (Thread.J2S_THREAD == null) {
Thread.J2S_THREAD =  new Thread();
}return Thread.J2S_THREAD;
});
c$.sleep = Clazz.defineMethod(c$, "sleep", 
function(millis){
alert ("Thread.sleep is not implemented in Java2Script!");
}, "~N");
Clazz.defineMethod(c$, "init", 
function(g, target, name, stackSize){
if (g == null) {
g =  new ThreadGroup();
}this.group = g;
this.target = target;
this.name = name;
this.priority = 5;
}, "ThreadGroup,Runnable,~S,~N");
Clazz.defineMethod(c$, "start", 
function(){
this.startT();
});
Clazz.defineMethod(c$, "startT", 
function(){
{
window.setTimeout ((function (runnable) {
return function () {
runnable.run ();
};
}) (this), 0);
}});
Clazz.defineMethod(c$, "run", 
function(){
if (this.target != null) {
this.target.run();
}});
Clazz.defineMethod(c$, "setPriority", 
function(newPriority){
if (newPriority > 10 || newPriority < 1) {
throw  new IllegalArgumentException();
}this.priority = newPriority;
}, "~N");
Clazz.defineMethod(c$, "getPriority", 
function(){
return this.priority;
});
Clazz.defineMethod(c$, "setName", 
function(name){
this.name = name;
}, "~S");
Clazz.defineMethod(c$, "getName", 
function(){
return String.valueOf(this.name);
});
Clazz.defineMethod(c$, "getThreadGroup", 
function(){
return this.group;
});
Clazz.overrideMethod(c$, "toString", 
function(){
var group = this.getThreadGroup();
if (group != null) {
return "Thread[" + this.getName() + "," + this.getPriority() + "," + group.getName() + "]";
} else {
return "Thread[" + this.getName() + "," + this.getPriority() + "," + "" + "]";
}});
c$.J2S_THREAD = null;
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
