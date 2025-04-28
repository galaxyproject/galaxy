Clazz.load(["java.util.AbstractSequentialList", "$.List", "$.ListIterator", "$.Queue"], "java.util.LinkedList", ["java.lang.reflect.Array"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.$size = 0;
this.voidLink = null;
Clazz.instantialize(this, arguments);}, java.util, "LinkedList", java.util.AbstractSequentialList, [java.util.List, java.util.Queue, Cloneable, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(){
Clazz.superConstructor (this, java.util.LinkedList, []);
this.voidLink =  new java.util.LinkedList.Link(null, null, null);
this.voidLink.previous = this.voidLink;
this.voidLink.next = this.voidLink;
});
Clazz.makeConstructor(c$, 
function(collection){
this.construct ();
this.addAll(collection);
}, "java.util.Collection");
Clazz.defineMethod(c$, "add", 
function(location, object){
if (0 <= location && location <= this.$size) {
var link = this.voidLink;
if (location < (Clazz.doubleToInt(this.$size / 2))) {
for (var i = 0; i <= location; i++) {
link = link.next;
}
} else {
for (var i = this.$size; i > location; i--) {
link = link.previous;
}
}var previous = link.previous;
var newLink =  new java.util.LinkedList.Link(object, previous, link);
previous.next = newLink;
link.previous = newLink;
this.$size++;
this.modCount++;
} else {
throw  new IndexOutOfBoundsException();
}}, "~N,~O");
Clazz.defineMethod(c$, "add", 
function(object){
var oldLast = this.voidLink.previous;
var newLink =  new java.util.LinkedList.Link(object, oldLast, this.voidLink);
this.voidLink.previous = newLink;
oldLast.next = newLink;
this.$size++;
this.modCount++;
return true;
}, "~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
if (location < 0 || location > this.$size) {
throw  new IndexOutOfBoundsException();
}var adding = collection.size();
if (adding == 0) {
return false;
}var previous = this.voidLink;
if (location < (Clazz.doubleToInt(this.$size / 2))) {
for (var i = 0; i < location; i++) {
previous = previous.next;
}
} else {
for (var i = this.$size; i >= location; i--) {
previous = previous.previous;
}
}var next = previous.next;
for (var e, $e = collection.iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var newLink =  new java.util.LinkedList.Link(e, previous, null);
previous.next = newLink;
previous = newLink;
}
previous.next = next;
next.previous = previous;
this.$size += adding;
this.modCount++;
return true;
}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "addAll", 
function(collection){
var adding = collection.size();
if (adding == 0) {
return false;
}var previous = this.voidLink.previous;
for (var e, $e = collection.iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var newLink =  new java.util.LinkedList.Link(e, previous, null);
previous.next = newLink;
previous = newLink;
}
previous.next = this.voidLink;
this.voidLink.previous = previous;
this.$size += adding;
this.modCount++;
return true;
}, "java.util.Collection");
Clazz.defineMethod(c$, "addFirst", 
function(object){
var oldFirst = this.voidLink.next;
var newLink =  new java.util.LinkedList.Link(object, this.voidLink, oldFirst);
this.voidLink.next = newLink;
oldFirst.previous = newLink;
this.$size++;
this.modCount++;
}, "~O");
Clazz.defineMethod(c$, "addLast", 
function(object){
var oldLast = this.voidLink.previous;
var newLink =  new java.util.LinkedList.Link(object, oldLast, this.voidLink);
this.voidLink.previous = newLink;
oldLast.next = newLink;
this.$size++;
this.modCount++;
}, "~O");
Clazz.overrideMethod(c$, "clear", 
function(){
if (this.$size > 0) {
this.$size = 0;
this.voidLink.next = this.voidLink;
this.voidLink.previous = this.voidLink;
this.modCount++;
}});
Clazz.overrideMethod(c$, "clone", 
function(){
return  new java.util.LinkedList(this);
});
Clazz.overrideMethod(c$, "contains", 
function(object){
var link = this.voidLink.next;
if (object != null) {
while (link !== this.voidLink) {
if (object.equals(link.data)) {
return true;
}link = link.next;
}
} else {
while (link !== this.voidLink) {
if (link.data == null) {
return true;
}link = link.next;
}
}return false;
}, "~O");
Clazz.overrideMethod(c$, "get", 
function(location){
if (0 <= location && location < this.$size) {
var link = this.voidLink;
if (location < (Clazz.doubleToInt(this.$size / 2))) {
for (var i = 0; i <= location; i++) {
link = link.next;
}
} else {
for (var i = this.$size; i > location; i--) {
link = link.previous;
}
}return link.data;
}throw  new IndexOutOfBoundsException();
}, "~N");
Clazz.defineMethod(c$, "getFirst", 
function(){
var first = this.voidLink.next;
if (first !== this.voidLink) {
return first.data;
}throw  new java.util.NoSuchElementException();
});
Clazz.defineMethod(c$, "getLast", 
function(){
var last = this.voidLink.previous;
if (last !== this.voidLink) {
return last.data;
}throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "indexOf", 
function(object){
var pos = 0;
var link = this.voidLink.next;
if (object != null) {
while (link !== this.voidLink) {
if (object.equals(link.data)) {
return pos;
}link = link.next;
pos++;
}
} else {
while (link !== this.voidLink) {
if (link.data == null) {
return pos;
}link = link.next;
pos++;
}
}return -1;
}, "~O");
Clazz.overrideMethod(c$, "lastIndexOf", 
function(object){
var pos = this.$size;
var link = this.voidLink.previous;
if (object != null) {
while (link !== this.voidLink) {
pos--;
if (object.equals(link.data)) {
return pos;
}link = link.previous;
}
} else {
while (link !== this.voidLink) {
pos--;
if (link.data == null) {
return pos;
}link = link.previous;
}
}return -1;
}, "~O");
Clazz.defineMethod(c$, "listIterator", 
function(location){
return  new java.util.LinkedList.LinkIterator(this, location);
}, "~N");
Clazz.defineMethod(c$, "remove", 
function(location){
if (0 <= location && location < this.$size) {
var link = this.voidLink;
if (location < (Clazz.doubleToInt(this.$size / 2))) {
for (var i = 0; i <= location; i++) {
link = link.next;
}
} else {
for (var i = this.$size; i > location; i--) {
link = link.previous;
}
}var previous = link.previous;
var next = link.next;
previous.next = next;
next.previous = previous;
this.$size--;
this.modCount++;
return link.data;
}throw  new IndexOutOfBoundsException();
}, "~N");
Clazz.defineMethod(c$, "remove", 
function(object){
var link = this.voidLink.next;
if (object != null) {
while (link !== this.voidLink && !object.equals(link.data)) {
link = link.next;
}
} else {
while (link !== this.voidLink && link.data != null) {
link = link.next;
}
}if (link === this.voidLink) {
return false;
}var next = link.next;
var previous = link.previous;
previous.next = next;
next.previous = previous;
this.$size--;
this.modCount++;
return true;
}, "~O");
Clazz.defineMethod(c$, "removeFirst", 
function(){
var first = this.voidLink.next;
if (first !== this.voidLink) {
var next = first.next;
this.voidLink.next = next;
next.previous = this.voidLink;
this.$size--;
this.modCount++;
return first.data;
}throw  new java.util.NoSuchElementException();
});
Clazz.defineMethod(c$, "removeLast", 
function(){
var last = this.voidLink.previous;
if (last !== this.voidLink) {
var previous = last.previous;
this.voidLink.previous = previous;
previous.next = this.voidLink;
this.$size--;
this.modCount++;
return last.data;
}throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "set", 
function(location, object){
if (0 <= location && location < this.$size) {
var link = this.voidLink;
if (location < (Clazz.doubleToInt(this.$size / 2))) {
for (var i = 0; i <= location; i++) {
link = link.next;
}
} else {
for (var i = this.$size; i > location; i--) {
link = link.previous;
}
}var result = link.data;
link.data = object;
return result;
}throw  new IndexOutOfBoundsException();
}, "~N,~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.$size;
});
Clazz.overrideMethod(c$, "offer", 
function(o){
this.add(o);
return true;
}, "~O");
Clazz.overrideMethod(c$, "poll", 
function(){
return this.$size == 0 ? null : this.removeFirst();
});
Clazz.defineMethod(c$, "remove", 
function(){
return this.removeFirst();
});
Clazz.overrideMethod(c$, "peek", 
function(){
var first = this.voidLink.next;
return first === this.voidLink ? null : first.data;
});
Clazz.overrideMethod(c$, "element", 
function(){
return this.getFirst();
});
Clazz.defineMethod(c$, "toArray", 
function(){
var index = 0;
var contents =  new Array(this.$size);
var link = this.voidLink.next;
while (link !== this.voidLink) {
contents[index++] = link.data;
link = link.next;
}
return contents;
});
Clazz.defineMethod(c$, "toArray", 
function(contents){
var index = 0;
if (this.$size > contents.length) {
var ct = contents.getClass().getComponentType();
contents = java.lang.reflect.Array.newInstance(ct, this.$size);
}var link = this.voidLink.next;
while (link !== this.voidLink) {
contents[index++] = link.data;
link = link.next;
}
if (index < contents.length) {
contents[index] = null;
}return contents;
}, "~A");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.data = null;
this.previous = null;
this.next = null;
Clazz.instantialize(this, arguments);}, java.util.LinkedList, "Link", null);
Clazz.makeConstructor(c$, 
function(o, p, n){
this.data = o;
this.previous = p;
this.next = n;
}, "~O,java.util.LinkedList.Link,java.util.LinkedList.Link");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.pos = 0;
this.expectedModCount = 0;
this.list = null;
this.link = null;
this.lastLink = null;
Clazz.instantialize(this, arguments);}, java.util.LinkedList, "LinkIterator", null, java.util.ListIterator);
Clazz.makeConstructor(c$, 
function(object, location){
this.list = object;
this.expectedModCount = this.list.modCount;
if (0 <= location && location <= this.list.$size) {
this.link = this.list.voidLink;
if (location < Clazz.doubleToInt(this.list.$size / 2)) {
for (this.pos = -1; this.pos + 1 < location; this.pos++) {
this.link = this.link.next;
}
} else {
for (this.pos = this.list.$size; this.pos >= location; this.pos--) {
this.link = this.link.previous;
}
}} else {
throw  new IndexOutOfBoundsException();
}}, "java.util.LinkedList,~N");
Clazz.overrideMethod(c$, "add", 
function(object){
if (this.expectedModCount == this.list.modCount) {
var next = this.link.next;
var newLink =  new java.util.LinkedList.Link(object, this.link, next);
this.link.next = newLink;
next.previous = newLink;
this.link = newLink;
this.lastLink = null;
this.pos++;
this.expectedModCount++;
this.list.$size++;
this.list.modCount++;
} else {
throw  new java.util.ConcurrentModificationException();
}}, "~O");
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.link.next !== this.list.voidLink;
});
Clazz.overrideMethod(c$, "hasPrevious", 
function(){
return this.link !== this.list.voidLink;
});
Clazz.overrideMethod(c$, "next", 
function(){
if (this.expectedModCount == this.list.modCount) {
var next = this.link.next;
if (next !== this.list.voidLink) {
this.lastLink = this.link = next;
this.pos++;
return this.link.data;
}throw  new java.util.NoSuchElementException();
}throw  new java.util.ConcurrentModificationException();
});
Clazz.overrideMethod(c$, "nextIndex", 
function(){
return this.pos + 1;
});
Clazz.overrideMethod(c$, "previous", 
function(){
if (this.expectedModCount == this.list.modCount) {
if (this.link !== this.list.voidLink) {
this.lastLink = this.link;
this.link = this.link.previous;
this.pos--;
return this.lastLink.data;
}throw  new java.util.NoSuchElementException();
}throw  new java.util.ConcurrentModificationException();
});
Clazz.overrideMethod(c$, "previousIndex", 
function(){
return this.pos;
});
Clazz.overrideMethod(c$, "remove", 
function(){
if (this.expectedModCount == this.list.modCount) {
if (this.lastLink != null) {
var next = this.lastLink.next;
var previous = this.lastLink.previous;
next.previous = previous;
previous.next = next;
if (this.lastLink === this.link) {
this.pos--;
}this.link = previous;
this.lastLink = null;
this.expectedModCount++;
this.list.$size--;
this.list.modCount++;
} else {
throw  new IllegalStateException();
}} else {
throw  new java.util.ConcurrentModificationException();
}});
Clazz.overrideMethod(c$, "set", 
function(object){
if (this.expectedModCount == this.list.modCount) {
if (this.lastLink != null) {
this.lastLink.data = object;
} else {
throw  new IllegalStateException();
}} else {
throw  new java.util.ConcurrentModificationException();
}}, "~O");
/*eoif3*/})();
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
