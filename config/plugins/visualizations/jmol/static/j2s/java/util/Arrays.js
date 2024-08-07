Clazz.load(["java.util.AbstractList", "$.RandomAccess"], "java.util.Arrays", null, function(){
var c$ = Clazz.declareType(java.util, "Arrays", null);
c$.fill = Clazz.defineMethod(c$, "fill", 
function(a, fromIndex, toIndex, val){
{
if (arguments.length == 2) {
val = arguments[1];
fromIndex = 0;
toIndex = a.length;
}
}java.util.Arrays.rangeCheck(a.length, fromIndex, toIndex);
for (var i = fromIndex; i < toIndex; i++) a[i] = val;

}, "~A,~N,~N,~O");
c$.asList = Clazz.defineMethod(c$, "asList", 
function(a){
return  new java.util.Arrays.ArrayList(a);
}, "~A");
c$.rangeCheck = Clazz.defineMethod(c$, "rangeCheck", 
function(arrayLen, fromIndex, toIndex){
if (fromIndex > toIndex) throw  new IllegalArgumentException("fromIndex(" + fromIndex + ") > toIndex(" + toIndex + ")");
if (fromIndex < 0) throw  new ArrayIndexOutOfBoundsException(fromIndex);
if (toIndex > arrayLen) throw  new ArrayIndexOutOfBoundsException(toIndex);
}, "~N,~N,~N");
c$.binarySearch = Clazz.defineMethod(c$, "binarySearch", 
function(a, key){
var low = 0;
var high = a.length - 1;
while (low <= high) {
var mid = (low + high) >> 1;
var midVal = a[mid];
if (midVal < key) low = mid + 1;
 else if (midVal > key) high = mid - 1;
 else return mid;
}
return -(low + 1);
}, "~A,~N");
c$.binarySearch = Clazz.defineMethod(c$, "binarySearch", 
function(a, key){
var low = 0;
var high = a.length - 1;
while (low <= high) {
var mid = (low + high) >> 1;
var midVal = a[mid];
var cmp = (midVal).compareTo(key);
if (cmp < 0) low = mid + 1;
 else if (cmp > 0) high = mid - 1;
 else return mid;
}
return -(low + 1);
}, "~A,~O");
c$.binarySearch = Clazz.defineMethod(c$, "binarySearch", 
function(a, key, c){
if (c == null) return java.util.Arrays.binarySearch(a, key);
var low = 0;
var high = a.length - 1;
while (low <= high) {
var mid = (low + high) >> 1;
var midVal = a[mid];
var cmp = c.compare(midVal, key);
if (cmp < 0) low = mid + 1;
 else if (cmp > 0) high = mid - 1;
 else return mid;
}
return -(low + 1);
}, "~A,~O,java.util.Comparator");
c$.equals = Clazz.defineMethod(c$, "equals", 
function(a, a2){
if (a === a2) return true;
if (a == null || a2 == null) return false;
var length = a.length;
if (a2.length != length) return false;
for (var i = 0; i < length; i++) {
var o1 = a[i];
var o2 = a2[i];
{
if(!(o1==null?o2==null:(o1.equals==null?o1==o2:o1.equals(o2))))return false;
}}
return true;
}, "~A,~A");
c$.sort = Clazz.defineMethod(c$, "sort", 
function(a, fromIndex, toIndex, c){
if (a.length < 2) return;
var n = 0;
var p = null;
{
n = arguments.count; p = fromIndex;
}var temp = a;
var ret = null;
switch (n) {
case 1:
p = null;
case 2:
fromIndex = 0;
toIndex = a.length;
break;
case 3:
p = null;
case 4:
p = c;
if (fromIndex == 0 && toIndex == a.length) {
temp = a;
} else {
{
temp = a.slice(fromIndex, toIndex);
}ret = a;
}break;
}
java.util.Arrays.rangeCheck(a.length, fromIndex, toIndex);
if (p == null) p = java.util.Arrays.comp;
c = p;
{
temp.sort(c.compare);
}if (ret != null) {
System.arraycopy(temp, 0, ret, fromIndex, toIndex);
}}, "~A,~N,~N,java.util.Comparator");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.a = null;
Clazz.instantialize(this, arguments);}, java.util.Arrays, "ArrayList", java.util.AbstractList, [java.util.RandomAccess, java.io.Serializable]);
Clazz.makeConstructor(c$, 
function(array){
Clazz.superConstructor (this, java.util.Arrays.ArrayList, []);
if (array == null) throw  new NullPointerException();
this.a = array;
}, "~A");
Clazz.overrideMethod(c$, "size", 
function(){
return this.a.length;
});
Clazz.defineMethod(c$, "toArray", 
function(){
return this.a.clone();
});
Clazz.overrideMethod(c$, "get", 
function(index){
return this.a[index];
}, "~N");
Clazz.overrideMethod(c$, "set", 
function(index, element){
var oldValue = this.a[index];
this.a[index] = element;
return oldValue;
}, "~N,~O");
Clazz.overrideMethod(c$, "indexOf", 
function(o){
if (o == null) {
for (var i = 0; i < this.a.length; i++) if (this.a[i] == null) return i;

} else {
for (var i = 0; i < this.a.length; i++) if (o.equals(this.a[i])) return i;

}return -1;
}, "~O");
Clazz.overrideMethod(c$, "contains", 
function(o){
return this.indexOf(o) != -1;
}, "~O");
/*eoif3*/})();
c$.comp = null;
{
c$.comp = {compare: function (o1, o2) {
return (o1 == null ? (o2 == null ? 0 : -1) : o2 == null ? 1
: typeof o1 == "number" ? o1 - o2 : o1.compareTo(o2))}};
}});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
