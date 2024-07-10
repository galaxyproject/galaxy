Clazz.load(["java.util.AbstractCollection", "$.Iterator", "$.List", "$.ListIterator", "$.RandomAccess"], "java.util.AbstractList", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.modCount = 0;
Clazz.instantialize(this, arguments);}, java.util, "AbstractList", java.util.AbstractCollection, java.util.List);
Clazz.defineMethod(c$, "add", 
function(location, object){
throw  new UnsupportedOperationException();
}, "~N,~O");
Clazz.defineMethod(c$, "add", 
function(object){
this.add(this.size(), object);
return true;
}, "~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
var it = collection.iterator();
while (it.hasNext()) {
this.add(location++, it.next());
}
return !collection.isEmpty();
}, "~N,java.util.Collection");
Clazz.overrideMethod(c$, "clear", 
function(){
this.removeRange(0, this.size());
});
Clazz.overrideMethod(c$, "equals", 
function(object){
if (this === object) {
return true;
}if (Clazz.instanceOf(object,"java.util.List")) {
var list = object;
if (list.size() != this.size()) {
return false;
}var it1 = this.iterator();
var it2 = list.iterator();
while (it1.hasNext()) {
var e1 = it1.next();
var e2 = it2.next();
if (!(e1 == null ? e2 == null : e1.equals(e2))) {
return false;
}}
return true;
}return false;
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
var result = 1;
var it = this.iterator();
while (it.hasNext()) {
var object = it.next();
result = (31 * result) + (object == null ? 0 : object.hashCode());
}
return result;
});
Clazz.overrideMethod(c$, "indexOf", 
function(object){
var it = this.listIterator();
if (object != null) {
while (it.hasNext()) {
if (object.equals(it.next())) {
return it.previousIndex();
}}
} else {
while (it.hasNext()) {
if (it.next() == null) {
return it.previousIndex();
}}
}return -1;
}, "~O");
Clazz.overrideMethod(c$, "iterator", 
function(){
return  new java.util.AbstractList.SimpleListIterator(this);
});
Clazz.overrideMethod(c$, "lastIndexOf", 
function(object){
var it = this.listIterator(this.size());
if (object != null) {
while (it.hasPrevious()) {
if (object.equals(it.previous())) {
return it.nextIndex();
}}
} else {
while (it.hasPrevious()) {
if (it.previous() == null) {
return it.nextIndex();
}}
}return -1;
}, "~O");
Clazz.defineMethod(c$, "listIterator", 
function(){
return this.listIterator(0);
});
Clazz.defineMethod(c$, "listIterator", 
function(location){
return  new java.util.AbstractList.FullListIterator(this, location);
}, "~N");
Clazz.defineMethod(c$, "remove", 
function(location){
throw  new UnsupportedOperationException();
}, "~N");
Clazz.defineMethod(c$, "removeRange", 
function(start, end){
var it = this.listIterator(start);
for (var i = start; i < end; i++) {
it.next();
it.remove();
}
}, "~N,~N");
Clazz.overrideMethod(c$, "set", 
function(location, object){
throw  new UnsupportedOperationException();
}, "~N,~O");
Clazz.overrideMethod(c$, "subList", 
function(start, end){
if (0 <= start && end <= this.size()) {
if (start <= end) {
if (Clazz.instanceOf(this,"java.util.RandomAccess")) {
return  new java.util.AbstractList.SubAbstractListRandomAccess(this, start, end);
}return  new java.util.AbstractList.SubAbstractList(this, start, end);
}throw  new IllegalArgumentException();
}throw  new IndexOutOfBoundsException();
}, "~N,~N");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.pos = -1;
this.expectedModCount = 0;
this.lastPosition = -1;
this.list = null;
Clazz.instantialize(this, arguments);}, java.util.AbstractList, "SimpleListIterator", null, java.util.Iterator);
Clazz.makeConstructor(c$, 
function(l){
this.list = l;
this.expectedModCount = l.modCount;
}, "java.util.AbstractList");
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.pos + 1 < this.list.size();
});
Clazz.overrideMethod(c$, "next", 
function(){
if (this.expectedModCount == this.list.modCount) {
try {
var result = this.list.get(this.pos + 1);
this.lastPosition = ++this.pos;
return result;
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new java.util.NoSuchElementException();
} else {
throw e;
}
}
}throw  new java.util.ConcurrentModificationException();
});
Clazz.overrideMethod(c$, "remove", 
function(){
if (this.expectedModCount == this.list.modCount) {
try {
this.list.remove(this.lastPosition);
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new IllegalStateException();
} else {
throw e;
}
}
if (this.list.modCount != this.expectedModCount) {
this.expectedModCount++;
}if (this.pos == this.lastPosition) {
this.pos--;
}this.lastPosition = -1;
} else {
throw  new java.util.ConcurrentModificationException();
}});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.AbstractList, "FullListIterator", java.util.AbstractList.SimpleListIterator, java.util.ListIterator);
Clazz.makeConstructor(c$, 
function(list, start){
Clazz.superConstructor(this, java.util.AbstractList.FullListIterator, [list]);
if (0 <= start && start <= list.size()) {
this.pos = start - 1;
} else {
throw  new IndexOutOfBoundsException();
}}, "java.util.AbstractList,~N");
Clazz.overrideMethod(c$, "add", 
function(object){
if (this.expectedModCount == this.list.modCount) {
try {
this.list.add(this.pos + 1, object);
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new java.util.NoSuchElementException();
} else {
throw e;
}
}
this.pos++;
this.lastPosition = -1;
if (this.list.modCount != this.expectedModCount) {
this.expectedModCount++;
}} else {
throw  new java.util.ConcurrentModificationException();
}}, "~O");
Clazz.overrideMethod(c$, "hasPrevious", 
function(){
return this.pos >= 0;
});
Clazz.overrideMethod(c$, "nextIndex", 
function(){
return this.pos + 1;
});
Clazz.overrideMethod(c$, "previous", 
function(){
if (this.expectedModCount == this.list.modCount) {
try {
var result = this.list.get(this.pos);
this.lastPosition = this.pos;
this.pos--;
return result;
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new java.util.NoSuchElementException();
} else {
throw e;
}
}
}throw  new java.util.ConcurrentModificationException();
});
Clazz.overrideMethod(c$, "previousIndex", 
function(){
return this.pos;
});
Clazz.overrideMethod(c$, "set", 
function(object){
if (this.expectedModCount == this.list.modCount) {
try {
this.list.set(this.lastPosition, object);
} catch (e) {
if (Clazz.exceptionOf(e,"IndexOutOfBoundsException")){
throw  new IllegalStateException();
} else {
throw e;
}
}
} else {
throw  new java.util.ConcurrentModificationException();
}}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.AbstractList, "SubAbstractListRandomAccess", java.util.AbstractList.SubAbstractList, java.util.RandomAccess);
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.fullList = null;
this.offset = 0;
this.$size = 0;
Clazz.instantialize(this, arguments);}, java.util.AbstractList, "SubAbstractList", java.util.AbstractList);
Clazz.makeConstructor(c$, 
function(list, start, end){
Clazz.superConstructor(this, java.util.AbstractList.SubAbstractList);
this.fullList = list;
this.modCount = this.fullList.modCount;
this.offset = start;
this.$size = end - start;
}, "java.util.AbstractList,~N,~N");
Clazz.defineMethod(c$, "add", 
function(location, object){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location <= this.$size) {
this.fullList.add(location + this.offset, object);
this.$size++;
this.modCount = this.fullList.modCount;
} else {
throw  new IndexOutOfBoundsException();
}} else {
throw  new java.util.ConcurrentModificationException();
}}, "~N,~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location <= this.$size) {
var result = this.fullList.addAll(location + this.offset, collection);
if (result) {
this.$size += collection.size();
this.modCount = this.fullList.modCount;
}return result;
}throw  new IndexOutOfBoundsException();
}throw  new java.util.ConcurrentModificationException();
}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "addAll", 
function(collection){
if (this.modCount == this.fullList.modCount) {
var result = this.fullList.addAll(this.offset + this.$size, collection);
if (result) {
this.$size += collection.size();
this.modCount = this.fullList.modCount;
}return result;
}throw  new java.util.ConcurrentModificationException();
}, "java.util.Collection");
Clazz.defineMethod(c$, "get", 
function(location){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location < this.$size) {
return this.fullList.get(location + this.offset);
}throw  new IndexOutOfBoundsException();
}throw  new java.util.ConcurrentModificationException();
}, "~N");
Clazz.overrideMethod(c$, "iterator", 
function(){
return this.listIterator(0);
});
Clazz.defineMethod(c$, "listIterator", 
function(location){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location <= this.$size) {
return  new java.util.AbstractList.SubAbstractList.SubAbstractListIterator(this.fullList.listIterator(location + this.offset), this, this.offset, this.$size);
}throw  new IndexOutOfBoundsException();
}throw  new java.util.ConcurrentModificationException();
}, "~N");
Clazz.defineMethod(c$, "remove", 
function(location){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location < this.$size) {
var result = this.fullList.remove(location + this.offset);
this.$size--;
this.modCount = this.fullList.modCount;
return result;
}throw  new IndexOutOfBoundsException();
}throw  new java.util.ConcurrentModificationException();
}, "~N");
Clazz.defineMethod(c$, "removeRange", 
function(start, end){
if (start != end) {
if (this.modCount == this.fullList.modCount) {
this.fullList.removeRange(start + this.offset, end + this.offset);
this.$size -= end - start;
this.modCount = this.fullList.modCount;
} else {
throw  new java.util.ConcurrentModificationException();
}}}, "~N,~N");
Clazz.defineMethod(c$, "set", 
function(location, object){
if (this.modCount == this.fullList.modCount) {
if (0 <= location && location < this.$size) {
return this.fullList.set(location + this.offset, object);
}throw  new IndexOutOfBoundsException();
}throw  new java.util.ConcurrentModificationException();
}, "~N,~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.$size;
});
Clazz.defineMethod(c$, "sizeChanged", 
function(increment){
if (increment) {
this.$size++;
} else {
this.$size--;
}this.modCount = this.fullList.modCount;
}, "~B");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.subList = null;
this.iterator = null;
this.start = 0;
this.end = 0;
Clazz.instantialize(this, arguments);}, java.util.AbstractList.SubAbstractList, "SubAbstractListIterator", null, java.util.ListIterator);
Clazz.makeConstructor(c$, 
function(it, list, offset, length){
this.iterator = it;
this.subList = list;
this.start = offset;
this.end = this.start + length;
}, "java.util.ListIterator,java.util.AbstractList.SubAbstractList,~N,~N");
Clazz.defineMethod(c$, "add", 
function(object){
this.iterator.add(object);
this.subList.sizeChanged(true);
this.end++;
}, "~O");
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.iterator.nextIndex() < this.end;
});
Clazz.overrideMethod(c$, "hasPrevious", 
function(){
return this.iterator.previousIndex() >= this.start;
});
Clazz.defineMethod(c$, "next", 
function(){
if (this.iterator.nextIndex() < this.end) {
return this.iterator.next();
}throw  new java.util.NoSuchElementException();
});
Clazz.defineMethod(c$, "nextIndex", 
function(){
return this.iterator.nextIndex() - this.start;
});
Clazz.defineMethod(c$, "previous", 
function(){
if (this.iterator.previousIndex() >= this.start) {
return this.iterator.previous();
}throw  new java.util.NoSuchElementException();
});
Clazz.defineMethod(c$, "previousIndex", 
function(){
var previous = this.iterator.previousIndex();
if (previous >= this.start) {
return previous - this.start;
}return -1;
});
Clazz.defineMethod(c$, "remove", 
function(){
this.iterator.remove();
this.subList.sizeChanged(false);
this.end--;
});
Clazz.defineMethod(c$, "set", 
function(object){
this.iterator.set(object);
}, "~O");
/*eoif3*/})();
/*eoif3*/})();
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
