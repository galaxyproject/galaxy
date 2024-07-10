Clazz.load(["java.util.AbstractCollection", "$.Queue"], "java.util.AbstractQueue", null, function(){
var c$ = Clazz.declareType(java.util, "AbstractQueue", java.util.AbstractCollection, java.util.Queue);
Clazz.overrideMethod(c$, "add", 
function(o){
if (null == o) {
throw  new NullPointerException();
}if (this.offer(o)) {
return true;
}throw  new IllegalStateException();
}, "~O");
Clazz.overrideMethod(c$, "addAll", 
function(c){
if (null == c) {
throw  new NullPointerException();
}if (this === c) {
throw  new IllegalArgumentException();
}return Clazz.superCall(this, java.util.AbstractQueue, "addAll", [c]);
}, "java.util.Collection");
Clazz.defineMethod(c$, "remove", 
function(){
var o = this.poll();
if (null == o) {
throw  new java.util.NoSuchElementException();
}return o;
});
Clazz.overrideMethod(c$, "element", 
function(){
var o = this.peek();
if (null == o) {
throw  new java.util.NoSuchElementException();
}return o;
});
Clazz.overrideMethod(c$, "clear", 
function(){
var o;
do {
o = this.poll();
} while (null != o);
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
