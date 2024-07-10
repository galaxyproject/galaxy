Clazz.load(["java.util.Vector"], "java.util.Stack", null, function(){
var c$ = Clazz.declareType(java.util, "Stack", java.util.Vector);
Clazz.defineMethod(c$, "empty", 
function(){
return this.elementCount == 0;
});
Clazz.defineMethod(c$, "peek", 
function(){
try {
return this.elementData[this.elementCount - 1];
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new java.util.EmptyStackException();
} else {
throw e;
}
}
});
Clazz.defineMethod(c$, "pop", 
function(){
try {
var index = this.elementCount - 1;
var obj = this.elementData[index];
this.removeElementAt(index);
return obj;
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new java.util.EmptyStackException();
} else {
throw e;
}
}
});
Clazz.defineMethod(c$, "push", 
function(object){
this.addElement(object);
return object;
}, "~O");
Clazz.defineMethod(c$, "search", 
function(o){
var index = this.lastIndexOf(o);
if (index >= 0) return (this.elementCount - index);
return -1;
}, "~O");
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
