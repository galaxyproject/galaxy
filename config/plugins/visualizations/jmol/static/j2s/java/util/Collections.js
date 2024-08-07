Clazz.load(["java.util.AbstractList", "$.AbstractMap", "$.AbstractSet", "$.Collection", "$.Enumeration", "$.Iterator", "$.List", "$.ListIterator", "$.Map", "$.RandomAccess", "$.Set", "$.SortedMap", "$.SortedSet", "java.lang.reflect.Array"], "java.util.Collections", ["java.util.ArrayList", "$.Arrays", "java.util.Map.Entry", "java.util.Random"], function(){
var c$ = Clazz.declareType(java.util, "Collections", null);
c$.emptyEnumeration = Clazz.defineMethod(c$, "emptyEnumeration", 
function(){
if (java.util.Collections.EMPTY_ENUMERATION == null) java.util.Collections.EMPTY_ENUMERATION =  new java.util.Collections.EmptyEnumeration();
return java.util.Collections.EMPTY_ENUMERATION;
});
c$.emptyIterator = Clazz.defineMethod(c$, "emptyIterator", 
function(){
if (java.util.Collections.EMPTY_ITERATOR == null) {
java.util.Collections.EMPTY_ITERATOR =  new java.util.Collections.EmptyIterator();
}return java.util.Collections.EMPTY_ITERATOR;
});
c$.binarySearch = Clazz.defineMethod(c$, "binarySearch", 
function(list, object){
if (list == null) {
throw  new NullPointerException();
}if (list.isEmpty()) {
return -1;
}var key = object;
if (!(Clazz.instanceOf(list,"java.util.RandomAccess"))) {
var it = list.listIterator();
while (it.hasNext()) {
var result;
if ((result = key.compareTo(it.next())) <= 0) {
if (result == 0) {
return it.previousIndex();
}return -it.previousIndex() - 1;
}}
return -list.size() - 1;
}var low = 0;
var mid = list.size();
var high = mid - 1;
var result = -1;
while (low <= high) {
mid = (low + high) >> 1;
if ((result = key.compareTo(list.get(mid))) > 0) {
low = mid + 1;
} else if (result == 0) {
return mid;
} else {
high = mid - 1;
}}
return -mid - (result < 0 ? 1 : 2);
}, "java.util.List,~O");
c$.binarySearch = Clazz.defineMethod(c$, "binarySearch", 
function(list, object, comparator){
if (comparator == null) {
return java.util.Collections.binarySearch(list, object);
}if (!(Clazz.instanceOf(list,"java.util.RandomAccess"))) {
var it = list.listIterator();
while (it.hasNext()) {
var result;
if ((result = comparator.compare(object, it.next())) <= 0) {
if (result == 0) {
return it.previousIndex();
}return -it.previousIndex() - 1;
}}
return -list.size() - 1;
}var low = 0;
var mid = list.size();
var high = mid - 1;
var result = -1;
while (low <= high) {
mid = (low + high) >> 1;
if ((result = comparator.compare(object, list.get(mid))) > 0) {
low = mid + 1;
} else if (result == 0) {
return mid;
} else {
high = mid - 1;
}}
return -mid - (result < 0 ? 1 : 2);
}, "java.util.List,~O,java.util.Comparator");
c$.copy = Clazz.defineMethod(c$, "copy", 
function(destination, source){
if (destination.size() < source.size()) {
throw  new ArrayIndexOutOfBoundsException();
}var srcIt = source.iterator();
var destIt = destination.listIterator();
while (srcIt.hasNext()) {
try {
destIt.next();
} catch (e) {
if (Clazz.exceptionOf(e,"java.util.NoSuchElementException")){
throw  new ArrayIndexOutOfBoundsException();
} else {
throw e;
}
}
destIt.set(srcIt.next());
}
}, "java.util.List,java.util.List");
c$.enumeration = Clazz.defineMethod(c$, "enumeration", 
function(collection){
var c = collection;
return ((Clazz.isClassDefined("java.util.Collections$1") ? 0 : java.util.Collections.$Collections$1$ ()), Clazz.innerTypeInstance(java.util.Collections$1, this, Clazz.cloneFinals("c", c)));
}, "java.util.Collection");
c$.fill = Clazz.defineMethod(c$, "fill", 
function(list, object){
var it = list.listIterator();
while (it.hasNext()) {
it.next();
it.set(object);
}
}, "java.util.List,~O");
c$.max = Clazz.defineMethod(c$, "max", 
function(collection){
var it = collection.iterator();
var max = it.next();
while (it.hasNext()) {
var next = it.next();
if (max.compareTo(next) < 0) {
max = next;
}}
return max;
}, "java.util.Collection");
c$.max = Clazz.defineMethod(c$, "max", 
function(collection, comparator){
var it = collection.iterator();
var max = it.next();
while (it.hasNext()) {
var next = it.next();
if (comparator.compare(max, next) < 0) {
max = next;
}}
return max;
}, "java.util.Collection,java.util.Comparator");
c$.min = Clazz.defineMethod(c$, "min", 
function(collection){
var it = collection.iterator();
var min = it.next();
while (it.hasNext()) {
var next = it.next();
if (min.compareTo(next) > 0) {
min = next;
}}
return min;
}, "java.util.Collection");
c$.min = Clazz.defineMethod(c$, "min", 
function(collection, comparator){
var it = collection.iterator();
var min = it.next();
while (it.hasNext()) {
var next = it.next();
if (comparator.compare(min, next) > 0) {
min = next;
}}
return min;
}, "java.util.Collection,java.util.Comparator");
c$.nCopies = Clazz.defineMethod(c$, "nCopies", 
function(length, object){
return  new java.util.Collections.CopiesList(length, object);
}, "~N,~O");
c$.reverse = Clazz.defineMethod(c$, "reverse", 
function(list){
var size = list.size();
var front = list.listIterator();
var back = list.listIterator(size);
for (var i = 0; i < Clazz.doubleToInt(size / 2); i++) {
var frontNext = front.next();
var backPrev = back.previous();
front.set(backPrev);
back.set(frontNext);
}
}, "java.util.List");
c$.reverseOrder = Clazz.defineMethod(c$, "reverseOrder", 
function(){
return  new java.util.Collections.ReverseComparator();
});
c$.reverseOrder = Clazz.defineMethod(c$, "reverseOrder", 
function(c){
if (c == null) {
return java.util.Collections.reverseOrder();
}return  new java.util.Collections.ReverseComparatorWithComparator(c);
}, "java.util.Comparator");
c$.shuffle = Clazz.defineMethod(c$, "shuffle", 
function(list){
java.util.Collections.shuffle(list,  new java.util.Random());
}, "java.util.List");
c$.shuffle = Clazz.defineMethod(c$, "shuffle", 
function(list, random){
if (!(Clazz.instanceOf(list,"java.util.RandomAccess"))) {
var array = list.toArray();
for (var i = array.length - 1; i > 0; i--) {
var index = random.nextInt() % (i + 1);
if (index < 0) {
index = -index;
}var temp = array[i];
array[i] = array[index];
array[index] = temp;
}
var i = 0;
var it = list.listIterator();
while (it.hasNext()) {
it.next();
it.set(array[i++]);
}
} else {
var rawList = list;
for (var i = rawList.size() - 1; i > 0; i--) {
var index = random.nextInt() % (i + 1);
if (index < 0) {
index = -index;
}rawList.set(index, rawList.set(i, rawList.get(index)));
}
}}, "java.util.List,java.util.Random");
c$.singleton = Clazz.defineMethod(c$, "singleton", 
function(object){
return  new java.util.Collections.SingletonSet(object);
}, "~O");
c$.singletonList = Clazz.defineMethod(c$, "singletonList", 
function(object){
return  new java.util.Collections.SingletonList(object);
}, "~O");
c$.singletonMap = Clazz.defineMethod(c$, "singletonMap", 
function(key, value){
return  new java.util.Collections.SingletonMap(key, value);
}, "~O,~O");
c$.sort = Clazz.defineMethod(c$, "sort", 
function(list){
var array = list.toArray();
java.util.Arrays.sort(array);
var i = 0;
var it = list.listIterator();
while (it.hasNext()) {
it.next();
it.set(array[i++]);
}
}, "java.util.List");
c$.sort = Clazz.defineMethod(c$, "sort", 
function(list, comparator){
var array = list.toArray( new Array(list.size()));
java.util.Arrays.sort(array, comparator);
var i = 0;
var it = list.listIterator();
while (it.hasNext()) {
it.next();
it.set(array[i++]);
}
}, "java.util.List,java.util.Comparator");
c$.swap = Clazz.defineMethod(c$, "swap", 
function(list, index1, index2){
if (list == null) {
throw  new NullPointerException();
}if (index1 == index2) {
return;
}var rawList = list;
rawList.set(index2, rawList.set(index1, rawList.get(index2)));
}, "java.util.List,~N,~N");
c$.replaceAll = Clazz.defineMethod(c$, "replaceAll", 
function(list, obj, obj2){
var index;
var found = false;
while ((index = list.indexOf(obj)) > -1) {
found = true;
list.set(index, obj2);
}
return found;
}, "java.util.List,~O,~O");
c$.rotate = Clazz.defineMethod(c$, "rotate", 
function(lst, dist){
var list = lst;
var size = list.size();
if (size == 0) {
return;
}var normdist;
if (dist > 0) {
normdist = dist % size;
} else {
normdist = size - ((dist % size) * (-1));
}if (normdist == 0 || normdist == size) {
return;
}if (Clazz.instanceOf(list,"java.util.RandomAccess")) {
var temp = list.get(0);
var index = 0;
var beginIndex = 0;
for (var i = 0; i < size; i++) {
index = (index + normdist) % size;
temp = list.set(index, temp);
if (index == beginIndex) {
index = ++beginIndex;
temp = list.get(beginIndex);
}}
} else {
var divideIndex = (size - normdist) % size;
var sublist1 = list.subList(0, divideIndex);
var sublist2 = list.subList(divideIndex, size);
java.util.Collections.reverse(sublist1);
java.util.Collections.reverse(sublist2);
java.util.Collections.reverse(list);
}}, "java.util.List,~N");
c$.indexOfSubList = Clazz.defineMethod(c$, "indexOfSubList", 
function(list, sublist){
var size = list.size();
var sublistSize = sublist.size();
if (sublistSize > size) {
return -1;
}if (sublistSize == 0) {
return 0;
}var firstObj = sublist.get(0);
var index = list.indexOf(firstObj);
if (index == -1) {
return -1;
}while (index < size && (size - index >= sublistSize)) {
var listIt = list.listIterator(index);
if ((firstObj == null) ? listIt.next() == null : firstObj.equals(listIt.next())) {
var sublistIt = sublist.listIterator(1);
var difFound = false;
while (sublistIt.hasNext()) {
var element = sublistIt.next();
if (!listIt.hasNext()) {
return -1;
}if ((element == null) ? listIt.next() != null : !element.equals(listIt.next())) {
difFound = true;
break;
}}
if (!difFound) {
return index;
}}index++;
}
return -1;
}, "java.util.List,java.util.List");
c$.lastIndexOfSubList = Clazz.defineMethod(c$, "lastIndexOfSubList", 
function(list, sublist){
var sublistSize = sublist.size();
var size = list.size();
if (sublistSize > size) {
return -1;
}if (sublistSize == 0) {
return size;
}var lastObj = sublist.get(sublistSize - 1);
var index = list.lastIndexOf(lastObj);
while ((index > -1) && (index + 1 >= sublistSize)) {
var listIt = list.listIterator(index + 1);
if ((lastObj == null) ? listIt.previous() == null : lastObj.equals(listIt.previous())) {
var sublistIt = sublist.listIterator(sublistSize - 1);
var difFound = false;
while (sublistIt.hasPrevious()) {
var element = sublistIt.previous();
if (!listIt.hasPrevious()) {
return -1;
}if ((element == null) ? listIt.previous() != null : !element.equals(listIt.previous())) {
difFound = true;
break;
}}
if (!difFound) {
return listIt.nextIndex();
}}index--;
}
return -1;
}, "java.util.List,java.util.List");
c$.list = Clazz.defineMethod(c$, "list", 
function(enumeration){
var list =  new java.util.ArrayList();
while (enumeration.hasMoreElements()) {
list.add(enumeration.nextElement());
}
return list;
}, "java.util.Enumeration");
c$.synchronizedCollection = Clazz.defineMethod(c$, "synchronizedCollection", 
function(collection){
if (collection == null) {
throw  new NullPointerException();
}return  new java.util.Collections.SynchronizedCollection(collection);
}, "java.util.Collection");
c$.synchronizedList = Clazz.defineMethod(c$, "synchronizedList", 
function(list){
if (list == null) {
throw  new NullPointerException();
}if (Clazz.instanceOf(list,"java.util.RandomAccess")) {
return  new java.util.Collections.SynchronizedRandomAccessList(list);
}return  new java.util.Collections.SynchronizedList(list);
}, "java.util.List");
c$.synchronizedMap = Clazz.defineMethod(c$, "synchronizedMap", 
function(map){
if (map == null) {
throw  new NullPointerException();
}return  new java.util.Collections.SynchronizedMap(map);
}, "java.util.Map");
c$.synchronizedSet = Clazz.defineMethod(c$, "synchronizedSet", 
function(set){
if (set == null) {
throw  new NullPointerException();
}return  new java.util.Collections.SynchronizedSet(set);
}, "java.util.Set");
c$.synchronizedSortedMap = Clazz.defineMethod(c$, "synchronizedSortedMap", 
function(map){
if (map == null) {
throw  new NullPointerException();
}return  new java.util.Collections.SynchronizedSortedMap(map);
}, "java.util.SortedMap");
c$.synchronizedSortedSet = Clazz.defineMethod(c$, "synchronizedSortedSet", 
function(set){
if (set == null) {
throw  new NullPointerException();
}return  new java.util.Collections.SynchronizedSortedSet(set);
}, "java.util.SortedSet");
c$.unmodifiableCollection = Clazz.defineMethod(c$, "unmodifiableCollection", 
function(collection){
if (collection == null) {
throw  new NullPointerException();
}return  new java.util.Collections.UnmodifiableCollection(collection);
}, "java.util.Collection");
c$.unmodifiableList = Clazz.defineMethod(c$, "unmodifiableList", 
function(list){
if (list == null) {
throw  new NullPointerException();
}if (Clazz.instanceOf(list,"java.util.RandomAccess")) {
return  new java.util.Collections.UnmodifiableRandomAccessList(list);
}return  new java.util.Collections.UnmodifiableList(list);
}, "java.util.List");
c$.unmodifiableMap = Clazz.defineMethod(c$, "unmodifiableMap", 
function(map){
if (map == null) {
throw  new NullPointerException();
}return  new java.util.Collections.UnmodifiableMap(map);
}, "java.util.Map");
c$.unmodifiableSet = Clazz.defineMethod(c$, "unmodifiableSet", 
function(set){
if (set == null) {
throw  new NullPointerException();
}return  new java.util.Collections.UnmodifiableSet(set);
}, "java.util.Set");
c$.unmodifiableSortedMap = Clazz.defineMethod(c$, "unmodifiableSortedMap", 
function(map){
if (map == null) {
throw  new NullPointerException();
}return  new java.util.Collections.UnmodifiableSortedMap(map);
}, "java.util.SortedMap");
c$.unmodifiableSortedSet = Clazz.defineMethod(c$, "unmodifiableSortedSet", 
function(set){
if (set == null) {
throw  new NullPointerException();
}return  new java.util.Collections.UnmodifiableSortedSet(set);
}, "java.util.SortedSet");
c$.frequency = Clazz.defineMethod(c$, "frequency", 
function(c, o){
if (c == null) {
throw  new NullPointerException();
}if (c.isEmpty()) {
return 0;
}var result = 0;
var itr = c.iterator();
while (itr.hasNext()) {
var e = itr.next();
if (o == null ? e == null : o.equals(e)) {
result++;
}}
return result;
}, "java.util.Collection,~O");
c$.emptyList = Clazz.defineMethod(c$, "emptyList", 
function(){
return java.util.Collections.EMPTY_LIST;
});
c$.emptySet = Clazz.defineMethod(c$, "emptySet", 
function(){
return java.util.Collections.EMPTY_SET;
});
c$.emptyMap = Clazz.defineMethod(c$, "emptyMap", 
function(){
return java.util.Collections.EMPTY_MAP;
});
c$.checkedCollection = Clazz.defineMethod(c$, "checkedCollection", 
function(c, type){
return  new java.util.Collections.CheckedCollection(c, type);
}, "java.util.Collection,Class");
c$.checkedMap = Clazz.defineMethod(c$, "checkedMap", 
function(m, keyType, valueType){
return  new java.util.Collections.CheckedMap(m, keyType, valueType);
}, "java.util.Map,Class,Class");
c$.checkedList = Clazz.defineMethod(c$, "checkedList", 
function(list, type){
if (Clazz.instanceOf(list,"java.util.RandomAccess")) {
return  new java.util.Collections.CheckedRandomAccessList(list, type);
}return  new java.util.Collections.CheckedList(list, type);
}, "java.util.List,Class");
c$.checkedSet = Clazz.defineMethod(c$, "checkedSet", 
function(s, type){
return  new java.util.Collections.CheckedSet(s, type);
}, "java.util.Set,Class");
c$.checkedSortedMap = Clazz.defineMethod(c$, "checkedSortedMap", 
function(m, keyType, valueType){
return  new java.util.Collections.CheckedSortedMap(m, keyType, valueType);
}, "java.util.SortedMap,Class,Class");
c$.checkedSortedSet = Clazz.defineMethod(c$, "checkedSortedSet", 
function(s, type){
return  new java.util.Collections.CheckedSortedSet(s, type);
}, "java.util.SortedSet,Class");
c$.addAll = Clazz.defineMethod(c$, "addAll", 
function(c, a){
var modified = false;
for (var i = 0; i < a.length; i++) {
modified = new Boolean (modified | c.add(a[i])).valueOf();
}
return modified;
}, "java.util.Collection,~A");
c$.disjoint = Clazz.defineMethod(c$, "disjoint", 
function(c1, c2){
if ((Clazz.instanceOf(c1,"java.util.Set")) && !(Clazz.instanceOf(c2,"java.util.Set")) || (c2.size()) > c1.size()) {
var tmp = c1;
c1 = c2;
c2 = tmp;
}var it = c1.iterator();
while (it.hasNext()) {
if (c2.contains(it.next())) {
return false;
}}
return true;
}, "java.util.Collection,java.util.Collection");
c$.checkType = Clazz.defineMethod(c$, "checkType", 
function(obj, type){
if (!type.isInstance(obj)) {
throw  new ClassCastException("Attempt to insert " + obj.getClass() + " element into collection with element type " + type);
}return obj;
}, "~O,Class");
c$.$Collections$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.it = null;
Clazz.instantialize(this, arguments);}, java.util, "Collections$1", null, java.util.Enumeration);
Clazz.prepareFields (c$, function(){
this.it = this.f$.c.iterator();
});
Clazz.defineMethod(c$, "hasMoreElements", 
function(){
return this.it.hasNext();
});
Clazz.defineMethod(c$, "nextElement", 
function(){
return this.it.next();
});
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "EmptyEnumeration", null, java.util.Enumeration);
Clazz.overrideMethod(c$, "hasMoreElements", 
function(){
return false;
});
Clazz.overrideMethod(c$, "nextElement", 
function(){
throw  new java.util.NoSuchElementException();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "EmptyIterator", null, java.util.Iterator);
Clazz.overrideMethod(c$, "hasNext", 
function(){
return false;
});
Clazz.overrideMethod(c$, "next", 
function(){
throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new IllegalStateException();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.n = 0;
this.element = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CopiesList", java.util.AbstractList, java.io.Serializable);
Clazz.makeConstructor(c$, 
function(length, object){
Clazz.superConstructor (this, java.util.Collections.CopiesList, []);
if (length < 0) {
throw  new IllegalArgumentException();
}this.n = length;
this.element = object;
}, "~N,~O");
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.element == null ? object == null : this.element.equals(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return this.n;
});
Clazz.overrideMethod(c$, "get", 
function(location){
if (0 <= location && location < this.n) {
return this.element;
}throw  new IndexOutOfBoundsException();
}, "~N");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "EmptyList", java.util.AbstractList, java.io.Serializable);
Clazz.overrideMethod(c$, "contains", 
function(object){
return false;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return 0;
});
Clazz.overrideMethod(c$, "get", 
function(location){
throw  new IndexOutOfBoundsException();
}, "~N");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "EmptySet", java.util.AbstractSet, java.io.Serializable);
Clazz.overrideMethod(c$, "contains", 
function(object){
return false;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return 0;
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$EmptySet$1") ? 0 : java.util.Collections.EmptySet.$Collections$EmptySet$1$ ()), Clazz.innerTypeInstance(java.util.Collections$EmptySet$1, this, null));
});
c$.$Collections$EmptySet$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "Collections$EmptySet$1", null, java.util.Iterator);
Clazz.overrideMethod(c$, "hasNext", 
function(){
return false;
});
Clazz.overrideMethod(c$, "next", 
function(){
throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
/*eoif5*/})();
};
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "EmptyMap", java.util.AbstractMap, java.io.Serializable);
Clazz.overrideMethod(c$, "containsKey", 
function(key){
return false;
}, "~O");
Clazz.overrideMethod(c$, "containsValue", 
function(value){
return false;
}, "~O");
Clazz.overrideMethod(c$, "entrySet", 
function(){
return java.util.Collections.EMPTY_SET;
});
Clazz.overrideMethod(c$, "get", 
function(key){
return null;
}, "~O");
Clazz.overrideMethod(c$, "keySet", 
function(){
return java.util.Collections.EMPTY_SET;
});
Clazz.overrideMethod(c$, "values", 
function(){
return java.util.Collections.EMPTY_LIST;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "ReverseComparator", null, [java.util.Comparator, java.io.Serializable]);
Clazz.overrideMethod(c$, "compare", 
function(o1, o2){
var c2 = o2;
return c2.compareTo(o1);
}, "~O,~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.comparator = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "ReverseComparatorWithComparator", null, [java.util.Comparator, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(comparator){
this.comparator = comparator;
}, "java.util.Comparator");
Clazz.defineMethod(c$, "compare", 
function(o1, o2){
return this.comparator.compare(o2, o1);
}, "~O,~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.element = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SingletonSet", java.util.AbstractSet, java.io.Serializable);
Clazz.makeConstructor(c$, 
function(object){
Clazz.superConstructor (this, java.util.Collections.SingletonSet, []);
this.element = object;
}, "~O");
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.element == null ? object == null : this.element.equals(object);
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return 1;
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$SingletonSet$1") ? 0 : java.util.Collections.SingletonSet.$Collections$SingletonSet$1$ ()), Clazz.innerTypeInstance(java.util.Collections$SingletonSet$1, this, null));
});
c$.$Collections$SingletonSet$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.$hasNext = true;
Clazz.instantialize(this, arguments);}, java.util, "Collections$SingletonSet$1", null, java.util.Iterator);
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.$hasNext;
});
Clazz.overrideMethod(c$, "next", 
function(){
if (this.$hasNext) {
this.$hasNext = false;
return this.b$["java.util.Collections.SingletonSet"].element;
}throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
/*eoif5*/})();
};
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.element = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SingletonList", java.util.AbstractList, java.io.Serializable);
Clazz.makeConstructor(c$, 
function(object){
Clazz.superConstructor (this, java.util.Collections.SingletonList, []);
this.element = object;
}, "~O");
Clazz.overrideMethod(c$, "contains", 
function(object){
return this.element == null ? object == null : this.element.equals(object);
}, "~O");
Clazz.overrideMethod(c$, "get", 
function(location){
if (location == 0) {
return this.element;
}throw  new IndexOutOfBoundsException();
}, "~N");
Clazz.overrideMethod(c$, "size", 
function(){
return 1;
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.k = null;
this.v = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SingletonMap", java.util.AbstractMap, java.io.Serializable);
Clazz.makeConstructor(c$, 
function(key, value){
Clazz.superConstructor (this, java.util.Collections.SingletonMap, []);
this.k = key;
this.v = value;
}, "~O,~O");
Clazz.overrideMethod(c$, "containsKey", 
function(key){
return this.k == null ? key == null : this.k.equals(key);
}, "~O");
Clazz.overrideMethod(c$, "containsValue", 
function(value){
return this.v == null ? value == null : this.v.equals(value);
}, "~O");
Clazz.overrideMethod(c$, "get", 
function(key){
if (this.containsKey(key)) {
return this.v;
}return null;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return 1;
});
Clazz.overrideMethod(c$, "entrySet", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$SingletonMap$1") ? 0 : java.util.Collections.SingletonMap.$Collections$SingletonMap$1$ ()), Clazz.innerTypeInstance(java.util.Collections$SingletonMap$1, this, null));
});
c$.$Collections$SingletonMap$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "Collections$SingletonMap$1", java.util.AbstractSet);
Clazz.overrideMethod(c$, "contains", 
function(object){
if (Clazz.instanceOf(object,"java.util.Map.Entry")) {
var entry = object;
return this.b$["java.util.Collections.SingletonMap"].containsKey(entry.getKey()) && this.b$["java.util.Collections.SingletonMap"].containsValue(entry.getValue());
}return false;
}, "~O");
Clazz.overrideMethod(c$, "size", 
function(){
return 1;
});
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$SingletonMap$1$1") ? 0 : java.util.Collections.$Collections$SingletonMap$1$1$ ()), Clazz.innerTypeInstance(java.util.Collections$SingletonMap$1$1, this, null));
});
/*eoif5*/})();
};
c$.$Collections$SingletonMap$1$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.$hasNext = true;
Clazz.instantialize(this, arguments);}, java.util, "Collections$SingletonMap$1$1", null, java.util.Iterator);
Clazz.overrideMethod(c$, "hasNext", 
function(){
return this.$hasNext;
});
Clazz.overrideMethod(c$, "next", 
function(){
if (this.$hasNext) {
this.$hasNext = false;
return ((Clazz.isClassDefined("java.util.Collections$SingletonMap$1$1$1") ? 0 : java.util.Collections.$Collections$SingletonMap$1$1$1$ ()), Clazz.innerTypeInstance(java.util.Collections$SingletonMap$1$1$1, this, null));
}throw  new java.util.NoSuchElementException();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
/*eoif5*/})();
};
c$.$Collections$SingletonMap$1$1$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(java.util, "Collections$SingletonMap$1$1$1", null, java.util.Map.Entry);
Clazz.overrideMethod(c$, "equals", 
function(object){
return this.b$["java.util.Collections$SingletonMap$1"].contains(object);
}, "~O");
Clazz.overrideMethod(c$, "getKey", 
function(){
return this.b$["java.util.Collections.SingletonMap"].k;
});
Clazz.overrideMethod(c$, "getValue", 
function(){
return this.b$["java.util.Collections.SingletonMap"].v;
});
Clazz.overrideMethod(c$, "hashCode", 
function(){
return (this.b$["java.util.Collections.SingletonMap"].k == null ? 0 : this.b$["java.util.Collections.SingletonMap"].k.hashCode()) ^ (this.b$["java.util.Collections.SingletonMap"].v == null ? 0 : this.b$["java.util.Collections.SingletonMap"].v.hashCode());
});
Clazz.overrideMethod(c$, "setValue", 
function(value){
throw  new UnsupportedOperationException();
}, "~O");
/*eoif5*/})();
};
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.c = null;
this.mutex = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SynchronizedCollection", null, [java.util.Collection, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(collection){
this.c = collection;
this.mutex = this;
}, "java.util.Collection");
Clazz.makeConstructor(c$, 
function(collection, mutex){
this.c = collection;
this.mutex = mutex;
}, "java.util.Collection,~O");
Clazz.defineMethod(c$, "add", 
function(object){
{
return this.c.add(object);
}}, "~O");
Clazz.defineMethod(c$, "addAll", 
function(collection){
{
return this.c.addAll(collection);
}}, "java.util.Collection");
Clazz.defineMethod(c$, "clear", 
function(){
{
this.c.clear();
}});
Clazz.defineMethod(c$, "contains", 
function(object){
{
return this.c.contains(object);
}}, "~O");
Clazz.defineMethod(c$, "containsAll", 
function(collection){
{
return this.c.containsAll(collection);
}}, "java.util.Collection");
Clazz.defineMethod(c$, "isEmpty", 
function(){
{
return this.c.isEmpty();
}});
Clazz.defineMethod(c$, "iterator", 
function(){
{
return this.c.iterator();
}});
Clazz.defineMethod(c$, "remove", 
function(object){
{
return this.c.remove(object);
}}, "~O");
Clazz.defineMethod(c$, "removeAll", 
function(collection){
{
return this.c.removeAll(collection);
}}, "java.util.Collection");
Clazz.defineMethod(c$, "retainAll", 
function(collection){
{
return this.c.retainAll(collection);
}}, "java.util.Collection");
Clazz.defineMethod(c$, "size", 
function(){
{
return this.c.size();
}});
Clazz.defineMethod(c$, "toArray", 
function(){
{
return this.c.toArray();
}});
Clazz.defineMethod(c$, "toString", 
function(){
{
return this.c.toString();
}});
Clazz.defineMethod(c$, "toArray", 
function(array){
{
return this.c.toArray(array);
}}, "~A");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "SynchronizedRandomAccessList", java.util.Collections.SynchronizedList, java.util.RandomAccess);
Clazz.overrideMethod(c$, "subList", 
function(start, end){
{
return  new java.util.Collections.SynchronizedRandomAccessList(this.list.subList(start, end), this.mutex);
}}, "~N,~N");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.list = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SynchronizedList", java.util.Collections.SynchronizedCollection, java.util.List);
Clazz.makeConstructor(c$, 
function(l){
Clazz.superConstructor(this, java.util.Collections.SynchronizedList, [l]);
this.list = l;
}, "java.util.List");
Clazz.makeConstructor(c$, 
function(l, mutex){
Clazz.superConstructor(this, java.util.Collections.SynchronizedList, [l, mutex]);
this.list = l;
}, "java.util.List,~O");
Clazz.defineMethod(c$, "add", 
function(location, object){
{
this.list.add(location, object);
}}, "~N,~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
{
return this.list.addAll(location, collection);
}}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "equals", 
function(object){
{
return this.list.equals(object);
}}, "~O");
Clazz.defineMethod(c$, "get", 
function(location){
{
return this.list.get(location);
}}, "~N");
Clazz.defineMethod(c$, "hashCode", 
function(){
{
return this.list.hashCode();
}});
Clazz.defineMethod(c$, "indexOf", 
function(object){
{
return this.list.indexOf(object);
}}, "~O");
Clazz.defineMethod(c$, "lastIndexOf", 
function(object){
{
return this.list.lastIndexOf(object);
}}, "~O");
Clazz.defineMethod(c$, "listIterator", 
function(){
{
return this.list.listIterator();
}});
Clazz.defineMethod(c$, "listIterator", 
function(location){
{
return this.list.listIterator(location);
}}, "~N");
Clazz.defineMethod(c$, "remove", 
function(location){
{
return this.list.remove(location);
}}, "~N");
Clazz.defineMethod(c$, "set", 
function(location, object){
{
return this.list.set(location, object);
}}, "~N,~O");
Clazz.defineMethod(c$, "subList", 
function(start, end){
{
return  new java.util.Collections.SynchronizedList(this.list.subList(start, end), this.mutex);
}}, "~N,~N");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.m = null;
this.mutex = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SynchronizedMap", null, [java.util.Map, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(map){
this.m = map;
this.mutex = this;
}, "java.util.Map");
Clazz.makeConstructor(c$, 
function(map, mutex){
this.m = map;
this.mutex = mutex;
}, "java.util.Map,~O");
Clazz.defineMethod(c$, "clear", 
function(){
{
this.m.clear();
}});
Clazz.defineMethod(c$, "containsKey", 
function(key){
{
return this.m.containsKey(key);
}}, "~O");
Clazz.defineMethod(c$, "containsValue", 
function(value){
{
return this.m.containsValue(value);
}}, "~O");
Clazz.defineMethod(c$, "entrySet", 
function(){
{
return  new java.util.Collections.SynchronizedSet(this.m.entrySet(), this.mutex);
}});
Clazz.defineMethod(c$, "equals", 
function(object){
{
return this.m.equals(object);
}}, "~O");
Clazz.defineMethod(c$, "get", 
function(key){
{
return this.m.get(key);
}}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
{
return this.m.hashCode();
}});
Clazz.defineMethod(c$, "isEmpty", 
function(){
{
return this.m.isEmpty();
}});
Clazz.defineMethod(c$, "keySet", 
function(){
{
return  new java.util.Collections.SynchronizedSet(this.m.keySet(), this.mutex);
}});
Clazz.defineMethod(c$, "put", 
function(key, value){
{
return this.m.put(key, value);
}}, "~O,~O");
Clazz.defineMethod(c$, "putAll", 
function(map){
{
this.m.putAll(map);
}}, "java.util.Map");
Clazz.defineMethod(c$, "remove", 
function(key){
{
return this.m.remove(key);
}}, "~O");
Clazz.defineMethod(c$, "size", 
function(){
{
return this.m.size();
}});
Clazz.defineMethod(c$, "values", 
function(){
{
return  new java.util.Collections.SynchronizedCollection(this.m.values(), this.mutex);
}});
Clazz.defineMethod(c$, "toString", 
function(){
{
return this.m.toString();
}});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "SynchronizedSet", java.util.Collections.SynchronizedCollection, java.util.Set);
Clazz.overrideMethod(c$, "equals", 
function(object){
{
return this.c.equals(object);
}}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
{
return this.c.hashCode();
}});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.sm = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SynchronizedSortedMap", java.util.Collections.SynchronizedMap, java.util.SortedMap);
Clazz.makeConstructor(c$, 
function(map){
Clazz.superConstructor(this, java.util.Collections.SynchronizedSortedMap, [map]);
this.sm = map;
}, "java.util.SortedMap");
Clazz.makeConstructor(c$, 
function(map, mutex){
Clazz.superConstructor(this, java.util.Collections.SynchronizedSortedMap, [map, mutex]);
this.sm = map;
}, "java.util.SortedMap,~O");
Clazz.defineMethod(c$, "comparator", 
function(){
{
return this.sm.comparator();
}});
Clazz.defineMethod(c$, "firstKey", 
function(){
{
return this.sm.firstKey();
}});
Clazz.defineMethod(c$, "headMap", 
function(endKey){
{
return  new java.util.Collections.SynchronizedSortedMap(this.sm.headMap(endKey), this.mutex);
}}, "~O");
Clazz.defineMethod(c$, "lastKey", 
function(){
{
return this.sm.lastKey();
}});
Clazz.defineMethod(c$, "subMap", 
function(startKey, endKey){
{
return  new java.util.Collections.SynchronizedSortedMap(this.sm.subMap(startKey, endKey), this.mutex);
}}, "~O,~O");
Clazz.defineMethod(c$, "tailMap", 
function(startKey){
{
return  new java.util.Collections.SynchronizedSortedMap(this.sm.tailMap(startKey), this.mutex);
}}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.ss = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "SynchronizedSortedSet", java.util.Collections.SynchronizedSet, java.util.SortedSet);
Clazz.makeConstructor(c$, 
function(set){
Clazz.superConstructor(this, java.util.Collections.SynchronizedSortedSet, [set]);
this.ss = set;
}, "java.util.SortedSet");
Clazz.makeConstructor(c$, 
function(set, mutex){
Clazz.superConstructor(this, java.util.Collections.SynchronizedSortedSet, [set, mutex]);
this.ss = set;
}, "java.util.SortedSet,~O");
Clazz.defineMethod(c$, "comparator", 
function(){
{
return this.ss.comparator();
}});
Clazz.defineMethod(c$, "first", 
function(){
{
return this.ss.first();
}});
Clazz.defineMethod(c$, "headSet", 
function(end){
{
return  new java.util.Collections.SynchronizedSortedSet(this.ss.headSet(end), this.mutex);
}}, "~O");
Clazz.defineMethod(c$, "last", 
function(){
{
return this.ss.last();
}});
Clazz.defineMethod(c$, "subSet", 
function(start, end){
{
return  new java.util.Collections.SynchronizedSortedSet(this.ss.subSet(start, end), this.mutex);
}}, "~O,~O");
Clazz.defineMethod(c$, "tailSet", 
function(start){
{
return  new java.util.Collections.SynchronizedSortedSet(this.ss.tailSet(start), this.mutex);
}}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.c = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "UnmodifiableCollection", null, [java.util.Collection, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(collection){
this.c = collection;
}, "java.util.Collection");
Clazz.overrideMethod(c$, "add", 
function(object){
throw  new UnsupportedOperationException();
}, "~O");
Clazz.overrideMethod(c$, "addAll", 
function(collection){
throw  new UnsupportedOperationException();
}, "java.util.Collection");
Clazz.overrideMethod(c$, "clear", 
function(){
throw  new UnsupportedOperationException();
});
Clazz.defineMethod(c$, "contains", 
function(object){
return this.c.contains(object);
}, "~O");
Clazz.defineMethod(c$, "containsAll", 
function(collection){
return this.c.containsAll(collection);
}, "java.util.Collection");
Clazz.defineMethod(c$, "isEmpty", 
function(){
return this.c.isEmpty();
});
Clazz.defineMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$UnmodifiableCollection$1") ? 0 : java.util.Collections.UnmodifiableCollection.$Collections$UnmodifiableCollection$1$ ()), Clazz.innerTypeInstance(java.util.Collections$UnmodifiableCollection$1, this, null));
});
Clazz.overrideMethod(c$, "remove", 
function(object){
throw  new UnsupportedOperationException();
}, "~O");
Clazz.overrideMethod(c$, "removeAll", 
function(collection){
throw  new UnsupportedOperationException();
}, "java.util.Collection");
Clazz.overrideMethod(c$, "retainAll", 
function(collection){
throw  new UnsupportedOperationException();
}, "java.util.Collection");
Clazz.defineMethod(c$, "size", 
function(){
return this.c.size();
});
Clazz.defineMethod(c$, "toArray", 
function(){
return this.c.toArray();
});
Clazz.defineMethod(c$, "toArray", 
function(array){
return this.c.toArray(array);
}, "~A");
Clazz.defineMethod(c$, "toString", 
function(){
return this.c.toString();
});
c$.$Collections$UnmodifiableCollection$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.iterator = null;
Clazz.instantialize(this, arguments);}, java.util, "Collections$UnmodifiableCollection$1", null, java.util.Iterator);
Clazz.prepareFields (c$, function(){
this.iterator = this.b$["java.util.Collections.UnmodifiableCollection"].c.iterator();
});
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.iterator.hasNext();
});
Clazz.defineMethod(c$, "next", 
function(){
return this.iterator.next();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
/*eoif5*/})();
};
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "UnmodifiableRandomAccessList", java.util.Collections.UnmodifiableList, java.util.RandomAccess);
Clazz.overrideMethod(c$, "subList", 
function(start, end){
return  new java.util.Collections.UnmodifiableRandomAccessList(this.list.subList(start, end));
}, "~N,~N");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.list = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "UnmodifiableList", java.util.Collections.UnmodifiableCollection, java.util.List);
Clazz.makeConstructor(c$, 
function(l){
Clazz.superConstructor(this, java.util.Collections.UnmodifiableList, [l]);
this.list = l;
}, "java.util.List");
Clazz.defineMethod(c$, "add", 
function(location, object){
throw  new UnsupportedOperationException();
}, "~N,~O");
Clazz.defineMethod(c$, "addAll", 
function(location, collection){
throw  new UnsupportedOperationException();
}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "equals", 
function(object){
return this.list.equals(object);
}, "~O");
Clazz.defineMethod(c$, "get", 
function(location){
return this.list.get(location);
}, "~N");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.list.hashCode();
});
Clazz.defineMethod(c$, "indexOf", 
function(object){
return this.list.indexOf(object);
}, "~O");
Clazz.defineMethod(c$, "lastIndexOf", 
function(object){
return this.list.lastIndexOf(object);
}, "~O");
Clazz.defineMethod(c$, "listIterator", 
function(){
return this.listIterator(0);
});
Clazz.defineMethod(c$, "listIterator", 
function(location){
return ((Clazz.isClassDefined("java.util.Collections$UnmodifiableList$1") ? 0 : java.util.Collections.UnmodifiableList.$Collections$UnmodifiableList$1$ ()), Clazz.innerTypeInstance(java.util.Collections$UnmodifiableList$1, this, Clazz.cloneFinals("location", location)));
}, "~N");
Clazz.defineMethod(c$, "remove", 
function(location){
throw  new UnsupportedOperationException();
}, "~N");
Clazz.overrideMethod(c$, "set", 
function(location, object){
throw  new UnsupportedOperationException();
}, "~N,~O");
Clazz.defineMethod(c$, "subList", 
function(start, end){
return  new java.util.Collections.UnmodifiableList(this.list.subList(start, end));
}, "~N,~N");
c$.$Collections$UnmodifiableList$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.iterator = null;
Clazz.instantialize(this, arguments);}, java.util, "Collections$UnmodifiableList$1", null, java.util.ListIterator);
Clazz.prepareFields (c$, function(){
this.iterator = this.b$["java.util.Collections.UnmodifiableList"].list.listIterator(this.f$.location);
});
Clazz.overrideMethod(c$, "add", 
function(object){
throw  new UnsupportedOperationException();
}, "~O");
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.iterator.hasNext();
});
Clazz.defineMethod(c$, "hasPrevious", 
function(){
return this.iterator.hasPrevious();
});
Clazz.defineMethod(c$, "next", 
function(){
return this.iterator.next();
});
Clazz.defineMethod(c$, "nextIndex", 
function(){
return this.iterator.nextIndex();
});
Clazz.defineMethod(c$, "previous", 
function(){
return this.iterator.previous();
});
Clazz.defineMethod(c$, "previousIndex", 
function(){
return this.iterator.previousIndex();
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
Clazz.overrideMethod(c$, "set", 
function(object){
throw  new UnsupportedOperationException();
}, "~O");
/*eoif5*/})();
};
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.m = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "UnmodifiableMap", null, [java.util.Map, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(map){
this.m = map;
}, "java.util.Map");
Clazz.overrideMethod(c$, "clear", 
function(){
throw  new UnsupportedOperationException();
});
Clazz.defineMethod(c$, "containsKey", 
function(key){
return this.m.containsKey(key);
}, "~O");
Clazz.defineMethod(c$, "containsValue", 
function(value){
return this.m.containsValue(value);
}, "~O");
Clazz.defineMethod(c$, "entrySet", 
function(){
return  new java.util.Collections.UnmodifiableMap.UnmodifiableEntrySet(this.m.entrySet());
});
Clazz.defineMethod(c$, "equals", 
function(object){
return this.m.equals(object);
}, "~O");
Clazz.defineMethod(c$, "get", 
function(key){
return this.m.get(key);
}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.m.hashCode();
});
Clazz.defineMethod(c$, "isEmpty", 
function(){
return this.m.isEmpty();
});
Clazz.defineMethod(c$, "keySet", 
function(){
return  new java.util.Collections.UnmodifiableSet(this.m.keySet());
});
Clazz.overrideMethod(c$, "put", 
function(key, value){
throw  new UnsupportedOperationException();
}, "~O,~O");
Clazz.overrideMethod(c$, "putAll", 
function(map){
throw  new UnsupportedOperationException();
}, "java.util.Map");
Clazz.overrideMethod(c$, "remove", 
function(key){
throw  new UnsupportedOperationException();
}, "~O");
Clazz.defineMethod(c$, "size", 
function(){
return this.m.size();
});
Clazz.defineMethod(c$, "values", 
function(){
return  new java.util.Collections.UnmodifiableCollection(this.m.values());
});
Clazz.defineMethod(c$, "toString", 
function(){
return this.m.toString();
});
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections.UnmodifiableMap, "UnmodifiableEntrySet", java.util.Collections.UnmodifiableSet);
Clazz.overrideMethod(c$, "iterator", 
function(){
return ((Clazz.isClassDefined("java.util.Collections$UnmodifiableMap$UnmodifiableEntrySet$1") ? 0 : java.util.Collections.UnmodifiableMap.UnmodifiableEntrySet.$Collections$UnmodifiableMap$UnmodifiableEntrySet$1$ ()), Clazz.innerTypeInstance(java.util.Collections$UnmodifiableMap$UnmodifiableEntrySet$1, this, null));
});
Clazz.defineMethod(c$, "toArray", 
function(){
var length = this.c.size();
var result =  new Array(length);
var it = this.iterator();
for (var i = length; --i >= 0; ) {
result[i] = it.next();
}
return result;
});
Clazz.defineMethod(c$, "toArray", 
function(contents){
var size = this.c.size();
var index = 0;
var it = this.iterator();
if (size > contents.length) {
var ct = contents.getClass().getComponentType();
contents = java.lang.reflect.Array.newInstance(ct, size);
}while (index < size) {
contents[index++] = it.next();
}
if (index < contents.length) {
contents[index] = null;
}return contents;
}, "~A");
c$.$Collections$UnmodifiableMap$UnmodifiableEntrySet$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.iterator = null;
Clazz.instantialize(this, arguments);}, java.util, "Collections$UnmodifiableMap$UnmodifiableEntrySet$1", null, java.util.Iterator);
Clazz.prepareFields (c$, function(){
this.iterator = this.b$["java.util.Collections.UnmodifiableMap.UnmodifiableEntrySet"].c.iterator();
});
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.iterator.hasNext();
});
Clazz.defineMethod(c$, "next", 
function(){
return  new java.util.Collections.UnmodifiableMap.UnmodifiableEntrySet.UnmodifiableMapEntry(this.iterator.next());
});
Clazz.overrideMethod(c$, "remove", 
function(){
throw  new UnsupportedOperationException();
});
/*eoif5*/})();
};
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.mapEntry = null;
Clazz.instantialize(this, arguments);}, java.util.Collections.UnmodifiableMap.UnmodifiableEntrySet, "UnmodifiableMapEntry", null, java.util.Map.Entry);
Clazz.makeConstructor(c$, 
function(entry){
this.mapEntry = entry;
}, "java.util.Map.Entry");
Clazz.defineMethod(c$, "equals", 
function(object){
return this.mapEntry.equals(object);
}, "~O");
Clazz.defineMethod(c$, "getKey", 
function(){
return this.mapEntry.getKey();
});
Clazz.defineMethod(c$, "getValue", 
function(){
return this.mapEntry.getValue();
});
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.mapEntry.hashCode();
});
Clazz.overrideMethod(c$, "setValue", 
function(object){
throw  new UnsupportedOperationException();
}, "~O");
Clazz.defineMethod(c$, "toString", 
function(){
return this.mapEntry.toString();
});
/*eoif3*/})();
/*eoif3*/})();
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "UnmodifiableSet", java.util.Collections.UnmodifiableCollection, java.util.Set);
Clazz.overrideMethod(c$, "equals", 
function(object){
return this.c.equals(object);
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
return this.c.hashCode();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.sm = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "UnmodifiableSortedMap", java.util.Collections.UnmodifiableMap, java.util.SortedMap);
Clazz.makeConstructor(c$, 
function(map){
Clazz.superConstructor(this, java.util.Collections.UnmodifiableSortedMap, [map]);
this.sm = map;
}, "java.util.SortedMap");
Clazz.defineMethod(c$, "comparator", 
function(){
return this.sm.comparator();
});
Clazz.defineMethod(c$, "firstKey", 
function(){
return this.sm.firstKey();
});
Clazz.defineMethod(c$, "headMap", 
function(before){
return  new java.util.Collections.UnmodifiableSortedMap(this.sm.headMap(before));
}, "~O");
Clazz.defineMethod(c$, "lastKey", 
function(){
return this.sm.lastKey();
});
Clazz.defineMethod(c$, "subMap", 
function(start, end){
return  new java.util.Collections.UnmodifiableSortedMap(this.sm.subMap(start, end));
}, "~O,~O");
Clazz.defineMethod(c$, "tailMap", 
function(after){
return  new java.util.Collections.UnmodifiableSortedMap(this.sm.tailMap(after));
}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.ss = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "UnmodifiableSortedSet", java.util.Collections.UnmodifiableSet, java.util.SortedSet);
Clazz.makeConstructor(c$, 
function(set){
Clazz.superConstructor(this, java.util.Collections.UnmodifiableSortedSet, [set]);
this.ss = set;
}, "java.util.SortedSet");
Clazz.defineMethod(c$, "comparator", 
function(){
return this.ss.comparator();
});
Clazz.defineMethod(c$, "first", 
function(){
return this.ss.first();
});
Clazz.defineMethod(c$, "headSet", 
function(before){
return  new java.util.Collections.UnmodifiableSortedSet(this.ss.headSet(before));
}, "~O");
Clazz.defineMethod(c$, "last", 
function(){
return this.ss.last();
});
Clazz.defineMethod(c$, "subSet", 
function(start, end){
return  new java.util.Collections.UnmodifiableSortedSet(this.ss.subSet(start, end));
}, "~O,~O");
Clazz.defineMethod(c$, "tailSet", 
function(after){
return  new java.util.Collections.UnmodifiableSortedSet(this.ss.tailSet(after));
}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.c = null;
this.type = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedCollection", null, [java.util.Collection, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(c, type){
if (c == null || type == null) {
throw  new NullPointerException();
}this.c = c;
this.type = type;
}, "java.util.Collection,Class");
Clazz.defineMethod(c$, "size", 
function(){
return this.c.size();
});
Clazz.defineMethod(c$, "isEmpty", 
function(){
return this.c.isEmpty();
});
Clazz.defineMethod(c$, "contains", 
function(obj){
return this.c.contains(obj);
}, "~O");
Clazz.defineMethod(c$, "iterator", 
function(){
var i = this.c.iterator();
if (Clazz.instanceOf(i,"java.util.ListIterator")) {
i =  new java.util.Collections.CheckedListIterator(i, this.type);
}return i;
});
Clazz.defineMethod(c$, "toArray", 
function(){
return this.c.toArray();
});
Clazz.defineMethod(c$, "toArray", 
function(arr){
return this.c.toArray(arr);
}, "~A");
Clazz.defineMethod(c$, "add", 
function(obj){
return this.c.add(java.util.Collections.checkType(obj, this.type));
}, "~O");
Clazz.defineMethod(c$, "remove", 
function(obj){
return this.c.remove(obj);
}, "~O");
Clazz.defineMethod(c$, "containsAll", 
function(c1){
return this.c.containsAll(c1);
}, "java.util.Collection");
Clazz.overrideMethod(c$, "addAll", 
function(c1){
var size = c1.size();
if (size == 0) {
return false;
}var arr =  new Array(size);
var it = c1.iterator();
for (var i = 0; i < size; i++) {
arr[i] = java.util.Collections.checkType(it.next(), this.type);
}
var added = false;
for (var i = 0; i < size; i++) {
added = new Boolean (added | this.c.add(arr[i])).valueOf();
}
return added;
}, "java.util.Collection");
Clazz.defineMethod(c$, "removeAll", 
function(c1){
return this.c.removeAll(c1);
}, "java.util.Collection");
Clazz.defineMethod(c$, "retainAll", 
function(c1){
return this.c.retainAll(c1);
}, "java.util.Collection");
Clazz.defineMethod(c$, "clear", 
function(){
this.c.clear();
});
Clazz.defineMethod(c$, "toString", 
function(){
return this.c.toString();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.i = null;
this.type = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedListIterator", null, java.util.ListIterator);
Clazz.makeConstructor(c$, 
function(i, type){
this.i = i;
this.type = type;
}, "java.util.ListIterator,Class");
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.i.hasNext();
});
Clazz.defineMethod(c$, "next", 
function(){
return this.i.next();
});
Clazz.defineMethod(c$, "remove", 
function(){
this.i.remove();
});
Clazz.defineMethod(c$, "hasPrevious", 
function(){
return this.i.hasPrevious();
});
Clazz.defineMethod(c$, "previous", 
function(){
return this.i.previous();
});
Clazz.defineMethod(c$, "nextIndex", 
function(){
return this.i.nextIndex();
});
Clazz.defineMethod(c$, "previousIndex", 
function(){
return this.i.previousIndex();
});
Clazz.defineMethod(c$, "set", 
function(obj){
this.i.set(java.util.Collections.checkType(obj, this.type));
}, "~O");
Clazz.defineMethod(c$, "add", 
function(obj){
this.i.add(java.util.Collections.checkType(obj, this.type));
}, "~O");
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.l = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedList", java.util.Collections.CheckedCollection, java.util.List);
Clazz.makeConstructor(c$, 
function(l, type){
Clazz.superConstructor(this, java.util.Collections.CheckedList, [l, type]);
this.l = l;
}, "java.util.List,Class");
Clazz.defineMethod(c$, "addAll", 
function(index, c1){
var size = c1.size();
if (size == 0) {
return false;
}var arr =  new Array(size);
var it = c1.iterator();
for (var i = 0; i < size; i++) {
arr[i] = java.util.Collections.checkType(it.next(), this.type);
}
return this.l.addAll(index, java.util.Arrays.asList(arr));
}, "~N,java.util.Collection");
Clazz.defineMethod(c$, "get", 
function(index){
return this.l.get(index);
}, "~N");
Clazz.defineMethod(c$, "set", 
function(index, obj){
return this.l.set(index, java.util.Collections.checkType(obj, this.type));
}, "~N,~O");
Clazz.defineMethod(c$, "add", 
function(index, obj){
this.l.add(index, java.util.Collections.checkType(obj, this.type));
}, "~N,~O");
Clazz.defineMethod(c$, "remove", 
function(index){
return this.l.remove(index);
}, "~N");
Clazz.defineMethod(c$, "indexOf", 
function(obj){
return this.l.indexOf(obj);
}, "~O");
Clazz.defineMethod(c$, "lastIndexOf", 
function(obj){
return this.l.lastIndexOf(obj);
}, "~O");
Clazz.defineMethod(c$, "listIterator", 
function(){
return  new java.util.Collections.CheckedListIterator(this.l.listIterator(), this.type);
});
Clazz.defineMethod(c$, "listIterator", 
function(index){
return  new java.util.Collections.CheckedListIterator(this.l.listIterator(index), this.type);
}, "~N");
Clazz.defineMethod(c$, "subList", 
function(fromIndex, toIndex){
return java.util.Collections.checkedList(this.l.subList(fromIndex, toIndex), this.type);
}, "~N,~N");
Clazz.defineMethod(c$, "equals", 
function(obj){
return this.l.equals(obj);
}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.l.hashCode();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "CheckedRandomAccessList", java.util.Collections.CheckedList, java.util.RandomAccess);
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.declareType(java.util.Collections, "CheckedSet", java.util.Collections.CheckedCollection, java.util.Set);
Clazz.overrideMethod(c$, "equals", 
function(obj){
return this.c.equals(obj);
}, "~O");
Clazz.overrideMethod(c$, "hashCode", 
function(){
return this.c.hashCode();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.m = null;
this.keyType = null;
this.valueType = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedMap", null, [java.util.Map, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(m, keyType, valueType){
if (m == null || keyType == null || valueType == null) {
throw  new NullPointerException();
}this.m = m;
this.keyType = keyType;
this.valueType = valueType;
}, "java.util.Map,Class,Class");
Clazz.defineMethod(c$, "size", 
function(){
return this.m.size();
});
Clazz.defineMethod(c$, "isEmpty", 
function(){
return this.m.isEmpty();
});
Clazz.defineMethod(c$, "containsKey", 
function(key){
return this.m.containsKey(key);
}, "~O");
Clazz.defineMethod(c$, "containsValue", 
function(value){
return this.m.containsValue(value);
}, "~O");
Clazz.defineMethod(c$, "get", 
function(key){
return this.m.get(key);
}, "~O");
Clazz.defineMethod(c$, "put", 
function(key, value){
return this.m.put(java.util.Collections.checkType(key, this.keyType), java.util.Collections.checkType(value, this.valueType));
}, "~O,~O");
Clazz.defineMethod(c$, "remove", 
function(key){
return this.m.remove(key);
}, "~O");
Clazz.overrideMethod(c$, "putAll", 
function(map){
var size = map.size();
if (size == 0) {
return;
}var entries =  new Array(size);
var it = map.entrySet().iterator();
for (var i = 0; i < size; i++) {
var e = it.next();
java.util.Collections.checkType(e.getKey(), this.keyType);
java.util.Collections.checkType(e.getValue(), this.valueType);
entries[i] = e;
}
for (var i = 0; i < size; i++) {
this.m.put(entries[i].getKey(), entries[i].getValue());
}
}, "java.util.Map");
Clazz.defineMethod(c$, "clear", 
function(){
this.m.clear();
});
Clazz.defineMethod(c$, "keySet", 
function(){
return this.m.keySet();
});
Clazz.defineMethod(c$, "values", 
function(){
return this.m.values();
});
Clazz.defineMethod(c$, "entrySet", 
function(){
return  new java.util.Collections.CheckedMap.CheckedEntrySet(this.m.entrySet(), this.valueType);
});
Clazz.defineMethod(c$, "equals", 
function(obj){
return this.m.equals(obj);
}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.m.hashCode();
});
Clazz.defineMethod(c$, "toString", 
function(){
return this.m.toString();
});
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.e = null;
this.valueType = null;
Clazz.instantialize(this, arguments);}, java.util.Collections.CheckedMap, "CheckedEntry", null, java.util.Map.Entry);
Clazz.makeConstructor(c$, 
function(e, valueType){
if (e == null) {
throw  new NullPointerException();
}this.e = e;
this.valueType = valueType;
}, "java.util.Map.Entry,Class");
Clazz.defineMethod(c$, "getKey", 
function(){
return this.e.getKey();
});
Clazz.defineMethod(c$, "getValue", 
function(){
return this.e.getValue();
});
Clazz.defineMethod(c$, "setValue", 
function(obj){
return this.e.setValue(java.util.Collections.checkType(obj, this.valueType));
}, "~O");
Clazz.defineMethod(c$, "equals", 
function(obj){
return this.e.equals(obj);
}, "~O");
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.e.hashCode();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.s = null;
this.valueType = null;
Clazz.instantialize(this, arguments);}, java.util.Collections.CheckedMap, "CheckedEntrySet", null, java.util.Set);
Clazz.makeConstructor(c$, 
function(s, valueType){
this.s = s;
this.valueType = valueType;
}, "java.util.Set,Class");
Clazz.defineMethod(c$, "iterator", 
function(){
return  new java.util.Collections.CheckedMap.CheckedEntrySet.CheckedEntryIterator(this.s.iterator(), this.valueType);
});
Clazz.defineMethod(c$, "toArray", 
function(){
var thisSize = this.size();
var array =  new Array(thisSize);
var it = this.iterator();
for (var i = 0; i < thisSize; i++) {
array[i] = it.next();
}
return array;
});
Clazz.defineMethod(c$, "toArray", 
function(array){
var thisSize = this.size();
if (array.length < thisSize) {
var ct = array.getClass().getComponentType();
array = java.lang.reflect.Array.newInstance(ct, thisSize);
}var it = this.iterator();
for (var i = 0; i < thisSize; i++) {
array[i] = it.next();
}
if (thisSize < array.length) {
array[thisSize] = null;
}return array;
}, "~A");
Clazz.defineMethod(c$, "retainAll", 
function(c){
return this.s.retainAll(c);
}, "java.util.Collection");
Clazz.defineMethod(c$, "removeAll", 
function(c){
return this.s.removeAll(c);
}, "java.util.Collection");
Clazz.defineMethod(c$, "containsAll", 
function(c){
return this.s.containsAll(c);
}, "java.util.Collection");
Clazz.overrideMethod(c$, "addAll", 
function(c){
throw  new UnsupportedOperationException();
}, "java.util.Collection");
Clazz.defineMethod(c$, "remove", 
function(o){
return this.s.remove(o);
}, "~O");
Clazz.defineMethod(c$, "contains", 
function(o){
return this.s.contains(o);
}, "~O");
Clazz.overrideMethod(c$, "add", 
function(o){
throw  new UnsupportedOperationException();
}, "java.util.Map.Entry");
Clazz.defineMethod(c$, "isEmpty", 
function(){
return this.s.isEmpty();
});
Clazz.defineMethod(c$, "clear", 
function(){
this.s.clear();
});
Clazz.defineMethod(c$, "size", 
function(){
return this.s.size();
});
Clazz.defineMethod(c$, "hashCode", 
function(){
return this.s.hashCode();
});
Clazz.defineMethod(c$, "equals", 
function(object){
return this.s.equals(object);
}, "~O");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.i = null;
this.valueType = null;
Clazz.instantialize(this, arguments);}, java.util.Collections.CheckedMap.CheckedEntrySet, "CheckedEntryIterator", null, java.util.Iterator);
Clazz.makeConstructor(c$, 
function(i, valueType){
this.i = i;
this.valueType = valueType;
}, "java.util.Iterator,Class");
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.i.hasNext();
});
Clazz.defineMethod(c$, "remove", 
function(){
this.i.remove();
});
Clazz.defineMethod(c$, "next", 
function(){
return  new java.util.Collections.CheckedMap.CheckedEntry(this.i.next(), this.valueType);
});
/*eoif3*/})();
/*eoif3*/})();
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.ss = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedSortedSet", java.util.Collections.CheckedSet, java.util.SortedSet);
Clazz.makeConstructor(c$, 
function(s, type){
Clazz.superConstructor(this, java.util.Collections.CheckedSortedSet, [s, type]);
this.ss = s;
}, "java.util.SortedSet,Class");
Clazz.defineMethod(c$, "comparator", 
function(){
return this.ss.comparator();
});
Clazz.defineMethod(c$, "subSet", 
function(fromElement, toElement){
return  new java.util.Collections.CheckedSortedSet(this.ss.subSet(fromElement, toElement), this.type);
}, "~O,~O");
Clazz.defineMethod(c$, "headSet", 
function(toElement){
return  new java.util.Collections.CheckedSortedSet(this.ss.headSet(toElement), this.type);
}, "~O");
Clazz.defineMethod(c$, "tailSet", 
function(fromElement){
return  new java.util.Collections.CheckedSortedSet(this.ss.tailSet(fromElement), this.type);
}, "~O");
Clazz.defineMethod(c$, "first", 
function(){
return this.ss.first();
});
Clazz.defineMethod(c$, "last", 
function(){
return this.ss.last();
});
/*eoif3*/})();
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.sm = null;
Clazz.instantialize(this, arguments);}, java.util.Collections, "CheckedSortedMap", java.util.Collections.CheckedMap, java.util.SortedMap);
Clazz.makeConstructor(c$, 
function(m, keyType, valueType){
Clazz.superConstructor(this, java.util.Collections.CheckedSortedMap, [m, keyType, valueType]);
this.sm = m;
}, "java.util.SortedMap,Class,Class");
Clazz.defineMethod(c$, "comparator", 
function(){
return this.sm.comparator();
});
Clazz.defineMethod(c$, "subMap", 
function(fromKey, toKey){
return  new java.util.Collections.CheckedSortedMap(this.sm.subMap(fromKey, toKey), this.keyType, this.valueType);
}, "~O,~O");
Clazz.defineMethod(c$, "headMap", 
function(toKey){
return  new java.util.Collections.CheckedSortedMap(this.sm.headMap(toKey), this.keyType, this.valueType);
}, "~O");
Clazz.defineMethod(c$, "tailMap", 
function(fromKey){
return  new java.util.Collections.CheckedSortedMap(this.sm.tailMap(fromKey), this.keyType, this.valueType);
}, "~O");
Clazz.defineMethod(c$, "firstKey", 
function(){
return this.sm.firstKey();
});
Clazz.defineMethod(c$, "lastKey", 
function(){
return this.sm.lastKey();
});
/*eoif3*/})();
c$.EMPTY_ENUMERATION = null;
c$.EMPTY_ITERATOR = null;
c$.EMPTY_LIST =  new java.util.Collections.EmptyList();
c$.EMPTY_SET =  new java.util.Collections.EmptySet();
c$.EMPTY_MAP =  new java.util.Collections.EmptyMap();
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
