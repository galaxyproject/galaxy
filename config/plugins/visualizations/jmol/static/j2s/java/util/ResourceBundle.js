Clazz.load(null, "java.util.ResourceBundle", ["java.util.Enumeration", "net.sf.j2s.ajax.HttpRequest"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.parent = null;
this.locale = null;
this.bundleName = null;
Clazz.instantialize(this, arguments);}, java.util, "ResourceBundle", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "getString", 
function(key){
return this.getObject(key);
}, "~S");
Clazz.defineMethod(c$, "getStringArray", 
function(key){
return this.getObject(key);
}, "~S");
Clazz.defineMethod(c$, "getObject", 
function(key){
var obj = this.handleGetObject(key);
if (obj == null) {
if (this.parent != null) {
obj = this.parent.getObject(key);
}if (obj == null) throw  new java.util.MissingResourceException("Can't find resource for bundle " + this.getClass().getName() + ", key " + key, this.getClass().getName(), key);
}return obj;
}, "~S");
Clazz.defineMethod(c$, "getLocale", 
function(){
return this.locale;
});
Clazz.defineMethod(c$, "setParent", 
function(parent){
this.parent = parent;
}, "java.util.ResourceBundle");
c$.getBundle = Clazz.defineMethod(c$, "getBundle", 
function(baseName){
return java.util.ResourceBundle.getBundleImpl(baseName, null, null);
}, "~S");
c$.getBundle = Clazz.defineMethod(c$, "getBundle", 
function(baseName, locale){
return java.util.ResourceBundle.getBundleImpl(baseName, locale, null);
}, "~S,java.util.Locale");
c$.getBundle = Clazz.defineMethod(c$, "getBundle", 
function(baseName, locale, loader){
if (loader == null) {
throw  new NullPointerException();
}return java.util.ResourceBundle.getBundleImpl(baseName, locale, loader);
}, "~S,java.util.Locale,ClassLoader");
c$.getBundleImpl = Clazz.defineMethod(c$, "getBundleImpl", 
function(baseName, locale, loader){
if (baseName == null) {
throw  new NullPointerException();
}for (var i = 0; i < java.util.ResourceBundle.caches.length; i++) {
if (java.util.ResourceBundle.caches[i].bundleName === baseName) {
return java.util.ResourceBundle.caches[i];
}}
var bundle =  new java.util.ResourceBundle.TextResourceBundle(baseName);
java.util.ResourceBundle.caches[java.util.ResourceBundle.caches.length] = bundle;
return bundle;
}, "~S,java.util.Locale,ClassLoader");
c$.registerBundle = Clazz.defineMethod(c$, "registerBundle", 
function(baseName, content){
for (var i = 0; i < java.util.ResourceBundle.caches.length; i++) {
if (java.util.ResourceBundle.caches[i].bundleName === baseName) {
return;
}}
java.util.ResourceBundle.caches[java.util.ResourceBundle.caches.length] =  new java.util.ResourceBundle.TextResourceBundle(baseName, content);
}, "~S,~S");
/*if3*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
this.map = null;
this.keys = null;
this.content = null;
this.initialized = false;
Clazz.instantialize(this, arguments);}, java.util.ResourceBundle, "TextResourceBundle", java.util.ResourceBundle);
Clazz.prepareFields (c$, function(){
this.map =  new Array(0);
this.keys =  new Array(0);
});
Clazz.makeConstructor(c$, 
function(bundleName){
Clazz.superConstructor (this, java.util.ResourceBundle.TextResourceBundle, []);
this.bundleName = bundleName;
}, "~S");
Clazz.makeConstructor(c$, 
function(bundleName, content){
Clazz.superConstructor (this, java.util.ResourceBundle.TextResourceBundle, []);
this.bundleName = bundleName;
this.content = content;
}, "~S,~S");
Clazz.defineMethod(c$, "evalString", 
function(a){
var r = new Array ();
var b = false;
var x = 0;
for (var i = 0; i < a.length; i++) {
var c = a.charAt (i);
if (b) {
if (c == 'f') r[r.length] = '\f';
else if (c == 't') r[r.length] = '\t';
else if (c == 'r') r[r.length] = '\r';
else if (c == 'n') r[r.length] = '\n';
else if (c == '\'') r[r.length] = '\'';
else if (c == '\"') r[r.length] = '\"';
else if (c == '\\') r[r.length] = '\\';
else if (c == 'u') {
r[r.length] =  eval ("\"\\u" + a.substring (i + 1, i + 5) + "\"");
i += 4;
}
x = i + 1;
b = false;
} else if (c == '\\') {
if (x != i) {
r[r.length] = a.substring (x, i);
}
b = true;
}
}
if (!b) {
r[r.length] = a.substring (x, a.length);
}
return r.join ('');
}, "~S");
Clazz.defineMethod(c$, "initBundle", 
function(){
if (this.initialized) {
return;
}this.initialized = true;
var a = null;
var b = this.bundleName;
if (this.content == null) {
var n = b.replace (/\./g, '/') + ".properties";
var p = Clazz.binaryFolders;
if (p == null) {
p = ["bin", "", "j2slib"];
}
var r =  new net.sf.j2s.ajax.HttpRequest ();
var x = 0;
while (a == null && x < p.length) {
var q = p[x];
if (q.length > 0 && q.lastIndexOf ("/") != q.length - 1) {
q += "/";
}
try {
r.open ("GET", q + n, false); // FIXME: using synchronized mode will freeze browser!
r.send ();
a = r.getResponseText ();
} catch (e) {
r =  new net.sf.j2s.ajax.HttpRequest ();
}
x++;
}
}if (this.content == null) {
this.content = a;
}if (this.content == null) {
return;
}var bundleLines = this.content.$plit("\n");
for (var i = 0; i < bundleLines.length; i++) {
var trimedLine = bundleLines[i].trim();
if (!trimedLine.startsWith("#")) {
var index = trimedLine.indexOf('=');
if (index != -1) {
var key = trimedLine.substring(0, index).trim();
var value = trimedLine.substring(index + 1).trim();
if (value.indexOf('\\') != -1) {
value = this.evalString(value);
}var m = this.map;
var k = this.keys;
{
if (m[key] == null) {
k[k.length] = key;
}
m[key] = value;
}}}}
});
Clazz.overrideMethod(c$, "getKeys", 
function(){
return ((Clazz.isClassDefined("java.util.ResourceBundle$TextResourceBundle$1") ? 0 : java.util.ResourceBundle.TextResourceBundle.$ResourceBundle$TextResourceBundle$1$ ()), Clazz.innerTypeInstance(java.util.ResourceBundle$TextResourceBundle$1, this, null));
});
Clazz.overrideMethod(c$, "handleGetObject", 
function(key){
if (!this.initialized) {
this.initBundle();
}var m = this.map;
{
return m[key];
}return m;
}, "~S");
c$.$ResourceBundle$TextResourceBundle$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.index = -1;
Clazz.instantialize(this, arguments);}, java.util, "ResourceBundle$TextResourceBundle$1", null, java.util.Enumeration);
Clazz.overrideMethod(c$, "nextElement", 
function(){
this.index++;
return this.b$["java.util.ResourceBundle.TextResourceBundle"].keys[this.index];
});
Clazz.overrideMethod(c$, "hasMoreElements", 
function(){
return this.index < this.b$["java.util.ResourceBundle.TextResourceBundle"].keys.length - 1;
});
/*eoif5*/})();
};
/*eoif3*/})();
c$.caches =  new Array(0);
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
