Clazz.declarePackage("JSV.source");
Clazz.load(null, "JSV.source.XMLParser", ["java.util.Hashtable", "JU.SB"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.thisEvent = null;
this.buffer = null;
if (!Clazz.isClassDefined("JSV.source.XMLParser.DataBuffer")) {
JSV.source.XMLParser.$XMLParser$DataBuffer$ ();
}
if (!Clazz.isClassDefined("JSV.source.XMLParser.DataString")) {
JSV.source.XMLParser.$XMLParser$DataString$ ();
}
if (!Clazz.isClassDefined("JSV.source.XMLParser.XmlEvent")) {
JSV.source.XMLParser.$XMLParser$XmlEvent$ ();
}
if (!Clazz.isClassDefined("JSV.source.XMLParser.Tag")) {
JSV.source.XMLParser.$XMLParser$Tag$ ();
}
Clazz.instantialize(this, arguments);}, JSV.source, "XMLParser", null);
Clazz.prepareFields (c$, function(){
this.thisEvent = Clazz.innerTypeInstance(JSV.source.XMLParser.XmlEvent, this, null, 0);
});
Clazz.makeConstructor(c$, 
function(br){
this.buffer = Clazz.innerTypeInstance(JSV.source.XMLParser.DataBuffer, this, null, br);
}, "java.io.BufferedReader");
Clazz.defineMethod(c$, "getBufferData", 
function(){
return (this.buffer == null ? null : this.buffer.data.toString().substring(0, this.buffer.ptr));
});
Clazz.defineMethod(c$, "thisValue", 
function(){
return this.buffer.nextEvent().toString().trim();
});
Clazz.defineMethod(c$, "qualifiedValue", 
function(){
this.buffer.nextTag();
var value = this.buffer.nextEvent().toString().trim();
this.buffer.nextTag();
return value;
});
Clazz.defineMethod(c$, "peek", 
function(){
this.thisEvent = this.buffer.peek();
return this.thisEvent.getEventType();
});
Clazz.defineMethod(c$, "hasNext", 
function(){
return this.buffer.hasNext();
});
Clazz.defineMethod(c$, "nextTag", 
function(){
while ((this.thisEvent = this.buffer.nextTag()).eventType == 6) {
}
});
Clazz.defineMethod(c$, "nextEvent", 
function(){
this.thisEvent = this.buffer.nextEvent();
return this.thisEvent.getEventType();
});
Clazz.defineMethod(c$, "nextStartTag", 
function(){
this.thisEvent = this.buffer.nextTag();
while (!this.thisEvent.isStartElement()) this.thisEvent = this.buffer.nextTag();

});
Clazz.defineMethod(c$, "getTagName", 
function(){
return this.thisEvent.getTagName();
});
Clazz.defineMethod(c$, "getTagType", 
function(){
return this.thisEvent.getTagType();
});
Clazz.defineMethod(c$, "getEndTag", 
function(){
return this.thisEvent.getTagName();
});
Clazz.defineMethod(c$, "nextValue", 
function(){
this.buffer.nextTag();
return this.buffer.nextEvent().toString().trim();
});
Clazz.defineMethod(c$, "getAttributeList", 
function(){
return this.thisEvent.toString().toLowerCase();
});
Clazz.defineMethod(c$, "getAttrValueLC", 
function(key){
return this.getAttrValue(key).toLowerCase();
}, "~S");
Clazz.defineMethod(c$, "getAttrValue", 
function(name){
var a = this.thisEvent.getAttributeByName(name);
return (a == null ? "" : a);
}, "~S");
Clazz.defineMethod(c$, "getCharacters", 
function(){
var sb =  new JU.SB();
this.thisEvent = this.buffer.peek();
var eventType = this.thisEvent.getEventType();
while (eventType != 4) this.thisEvent = this.buffer.nextEvent();

while (eventType == 4) {
this.thisEvent = this.buffer.nextEvent();
eventType = this.thisEvent.getEventType();
if (eventType == 4) sb.append(this.thisEvent.toString());
}
return sb.toString();
});
Clazz.defineMethod(c$, "requiresEndTag", 
function(){
var tagType = this.thisEvent.getTagType();
return tagType != 3 && tagType != 6;
});
c$.$XMLParser$DataBuffer$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
Clazz.instantialize(this, arguments);}, JSV.source.XMLParser, "DataBuffer", JSV.source.XMLParser.DataString, null, Clazz.innerTypeInstance(JSV.source.XMLParser.DataString, this, null, Clazz.inheritArgs));
Clazz.makeConstructor(c$, 
function(br){
Clazz.superConstructor (this, JSV.source.XMLParser.DataBuffer, []);
this.reader = br;
}, "java.io.BufferedReader");
Clazz.defineMethod(c$, "hasNext", 
function(){
if (this.ptr == this.ptEnd) try {
this.readLine();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return false;
} else {
throw e;
}
}
return this.ptr < this.ptEnd;
});
Clazz.overrideMethod(c$, "readLine", 
function(){
var s = this.reader.readLine();
if (s == null) {
return false;
}this.data.append(s + "\n");
this.ptEnd = this.data.length();
return true;
});
Clazz.defineMethod(c$, "peek", 
function(){
if (this.ptEnd - this.ptr < 2) try {
this.readLine();
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return Clazz.innerTypeInstance(JSV.source.XMLParser.XmlEvent, this, null, 8);
} else {
throw e;
}
}
var pt0 = this.ptr;
var e = Clazz.innerTypeInstance(JSV.source.XMLParser.XmlEvent, this, null, this);
this.ptr = pt0;
return e;
});
Clazz.defineMethod(c$, "nextTag", 
function(){
this.flush();
this.skipTo('<', false);
var e = Clazz.innerTypeInstance(JSV.source.XMLParser.XmlEvent, this, null, this);
return e;
});
Clazz.defineMethod(c$, "nextEvent", 
function(){
this.flush();
return Clazz.innerTypeInstance(JSV.source.XMLParser.XmlEvent, this, null, this);
});
/*eoif4*/})();
};
c$.$XMLParser$DataString$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.data = null;
this.reader = null;
this.ptr = 0;
this.ptEnd = 0;
Clazz.instantialize(this, arguments);}, JSV.source.XMLParser, "DataString", null);
Clazz.makeConstructor(c$, 
function(){
this.data =  new JU.SB();
});
Clazz.makeConstructor(c$, 
function(data){
this.data = data;
this.ptEnd = data.length();
}, "JU.SB");
Clazz.defineMethod(c$, "getNCharactersRemaining", 
function(){
return this.ptEnd - this.ptr;
});
Clazz.defineMethod(c$, "flush", 
function(){
if (this.data.length() < 1000 || this.ptEnd - this.ptr > 100) return;
this.data =  new JU.SB().append(this.data.substring(this.ptr));
this.ptr = 0;
this.ptEnd = this.data.length();
});
Clazz.defineMethod(c$, "substring", 
function(i, j){
return this.data.toString().substring(i, j);
}, "~N,~N");
Clazz.defineMethod(c$, "skipOver", 
function(c, inQuotes){
if (this.skipTo(c, inQuotes) > 0 && this.ptr != this.ptEnd) {
this.ptr++;
}return this.ptr;
}, "~S,~B");
Clazz.defineMethod(c$, "skipTo", 
function(toWhat, inQuotes){
if (this.data == null) return -1;
var ch;
if (this.ptr == this.ptEnd) {
if (this.reader == null) return -1;
this.readLine();
}var ptEnd1 = this.ptEnd - 1;
while (this.ptr < this.ptEnd && (ch = this.data.charAt(this.ptr)) != toWhat) {
if (inQuotes && ch == '\\' && this.ptr < ptEnd1) {
if ((ch = this.data.charAt(this.ptr + 1)) == '"' || ch == '\\') this.ptr++;
} else if (ch == '"') {
this.ptr++;
if (this.skipTo('"', true) < 0) return -1;
}if (++this.ptr == this.ptEnd) {
if (this.reader == null) return -1;
this.readLine();
}}
return this.ptr;
}, "~S,~B");
Clazz.defineMethod(c$, "readLine", 
function(){
return false;
});
/*eoif4*/})();
};
c$.$XMLParser$XmlEvent$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.eventType = 0;
this.ptr = 0;
this.tag = null;
this.data = null;
Clazz.instantialize(this, arguments);}, JSV.source.XMLParser, "XmlEvent", null);
Clazz.makeConstructor(c$, 
function(eventType){
this.eventType = eventType;
}, "~N");
Clazz.makeConstructor(c$, 
function(b){
this.ptr = b.ptr;
var n = b.getNCharactersRemaining();
this.eventType = (n == 0 ? 8 : n == 1 || b.data.charAt(b.ptr) != '<' ? 4 : b.data.charAt(b.ptr + 1) != '/' ? 1 : 2);
if (this.eventType == 8) return;
if (this.eventType == 4) {
b.skipTo('<', false);
this.data = b.data.toString().substring(this.ptr, b.ptr);
} else {
b.skipOver('>', false);
var s = b.data.toString().substring(this.ptr, b.ptr);
if (s.startsWith("<!--")) this.eventType = 6;
this.tag = Clazz.innerTypeInstance(JSV.source.XMLParser.Tag, this, null, s);
}}, "JSV.source.XMLParser.DataBuffer");
Clazz.overrideMethod(c$, "toString", 
function(){
return (this.data != null ? this.data : this.tag != null ? this.tag.text : null);
});
Clazz.defineMethod(c$, "getEventType", 
function(){
return this.eventType;
});
Clazz.defineMethod(c$, "isStartElement", 
function(){
return (this.eventType & 1) != 0;
});
Clazz.defineMethod(c$, "getTagName", 
function(){
return (this.tag == null ? null : this.tag.getName());
});
Clazz.defineMethod(c$, "getTagType", 
function(){
return (this.tag == null ? 0 : this.tag.tagType);
});
Clazz.defineMethod(c$, "getAttributeByName", 
function(name){
return (this.tag == null ? null : this.tag.getAttributeByName(name));
}, "~S");
/*eoif4*/})();
};
c$.$XMLParser$Tag$ = function(){
/*if4*/;(function(){
var c$ = Clazz.decorateAsClass(function(){
Clazz.prepareCallback(this, arguments);
this.tagType = 0;
this.name = null;
this.text = null;
this.attributes = null;
Clazz.instantialize(this, arguments);}, JSV.source.XMLParser, "Tag", null);
/*LV!1824 unnec constructor*/Clazz.makeConstructor(c$, 
function(fulltag){
this.text = fulltag;
this.tagType = (fulltag.startsWith("<!--") ? 6 : fulltag.charAt(1) == '/' ? 2 : fulltag.charAt(fulltag.length - 2) == '/' ? 3 : 1);
}, "~S");
Clazz.defineMethod(c$, "getName", 
function(){
if (this.name != null) return this.name;
var ptTemp = (this.tagType == 2 ? 2 : 1);
var n = this.text.length - (this.tagType == 3 ? 2 : 1);
while (ptTemp < n && Character.isWhitespace(this.text.charAt(ptTemp))) ptTemp++;

var pt0 = ptTemp;
while (ptTemp < n && !Character.isWhitespace(this.text.charAt(ptTemp))) ptTemp++;

return this.name = this.text.substring(pt0, ptTemp).toLowerCase().trim();
});
Clazz.defineMethod(c$, "getAttributeByName", 
function(attrName){
if (this.attributes == null) this.getAttributes();
return this.attributes.get(attrName.toLowerCase());
}, "~S");
Clazz.defineMethod(c$, "getAttributes", 
function(){
this.attributes =  new java.util.Hashtable();
var d = Clazz.innerTypeInstance(JSV.source.XMLParser.DataString, this, null,  new JU.SB().append(this.text));
try {
if (d.skipTo(' ', false) < 0) return;
var pt0;
while ((pt0 = ++d.ptr) >= 0) {
if (d.skipTo('=', false) < 0) return;
var name = d.substring(pt0, d.ptr).trim().toLowerCase();
d.skipTo('"', false);
pt0 = ++d.ptr;
d.skipTo('"', true);
var attr = d.substring(pt0, d.ptr);
this.attributes.put(name, attr);
var pt1 = name.indexOf(":");
if (pt1 >= 0) {
name = name.substring(pt1).trim();
this.attributes.put(name, attr);
}}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
} else {
throw e;
}
}
});
/*eoif4*/})();
};
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
