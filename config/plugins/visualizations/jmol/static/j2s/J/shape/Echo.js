Clazz.declarePackage("J.shape");
Clazz.load(["J.shape.TextShape"], "J.shape.Echo", ["java.util.Hashtable", "JU.Lst", "$.PT", "JM.Text", "JU.C"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.scaleObject = null;
Clazz.instantialize(this, arguments);}, J.shape, "Echo", J.shape.TextShape);
Clazz.overrideMethod(c$, "initShape", 
function(){
this.setProperty("target", "top", null);
});
Clazz.overrideMethod(c$, "setProperty", 
function(propertyName, value, bs){
if ("target" === propertyName) {
if ("%SCALE".equals(value)) {
this.currentObject = this.scaleObject;
this.thisID = "%SCALE";
if (this.currentObject != null) return;
}var target = (value).intern().toLowerCase();
if (JU.PT.isWild(target)) {
propertyName = "thisID";
} else if (target !== "none" && target !== "all") {
this.isAll = false;
var text = (this.thisID === "%SCALE" ? this.scaleObject : this.objects.get(target));
if (text == null) {
var valign = 3;
var halign = 4;
if ("top" === target) {
valign = 0;
halign = 8;
} else if ("middle" === target) {
valign = 2;
halign = 8;
} else if ("bottom" === target) {
valign = 1;
} else if ("error" === target) {
valign = 0;
}text = JM.Text.newEcho(this.vwr, this.vwr.gdata.getFont3DFS("Serif", 20), target, 10, valign, halign, 0);
text.adjustForWindow = true;
if (this.thisID === "%SCALE") {
this.scaleObject = text;
} else {
this.objects.put(target, text);
if (target.startsWith("_!_")) {
text.thisModelOnly = true;
}}if (this.currentFont != null) text.setFont(this.currentFont, true);
if (this.currentColor != null) text.colix = JU.C.getColixO(this.currentColor);
if (this.currentBgColor != null) text.bgcolix = JU.C.getColixO(this.currentBgColor);
if (this.currentTranslucentLevel != 0) text.setTranslucent(this.currentTranslucentLevel, false);
if (this.currentBgTranslucentLevel != 0) text.setTranslucent(this.currentBgTranslucentLevel, true);
}this.currentObject = text;
if (this.thisID !== "%SCALE") this.thisID = null;
return;
}}if ("thisID" === propertyName) {
if (value == null) {
this.currentObject = null;
this.thisID = null;
return;
}var target = value;
if (target === "%SCALE") {
this.currentObject = this.scaleObject;
this.thisID = target;
} else {
this.currentObject = this.objects.get(target);
if (this.currentObject == null && JU.PT.isWild(target)) this.thisID = target.toUpperCase();
}return;
}if ("%SCALE" === propertyName) {
this.currentObject = this.scaleObject = value;
this.thisID = "%SCALE";
return;
}if ("color" === propertyName || "font" === propertyName) {
if (this.scaleObject != null && this.currentObject === this.scaleObject) {
var f = this.currentFont;
var c = this.currentColor;
this.setPropTS(propertyName, value, bs);
this.currentFont = f;
this.currentColor = c;
return;
}}if ("off" === propertyName) {
if (this.currentObject != null && this.currentObject === this.scaleObject) {
this.currentObject = this.scaleObject = null;
return;
}}if ("text" === propertyName) {
if ((value).startsWith("%SCALE")) {
this.thisID = "%SCALE";
this.setPropTS("text", value, null);
this.scaleObject = this.currentObject;
if (this.scaleObject != null && this.objects.get(this.scaleObject.target) === this.scaleObject) this.setPropTS("delete", this.scaleObject, null);
this.currentObject = this.scaleObject;
return;
}}if ("scalereference" === propertyName) {
if (this.currentObject != null) {
var val = (value).floatValue();
this.currentObject.setScalePixelsPerMicron(val == 0 ? 0 : 10000 / val);
}return;
}if ("point" === propertyName) {
if (this.currentObject != null) {
var t = this.currentObject;
t.pointerPt = (value == null ? null : value);
t.pointer = (value == null ? 0 : 1);
}return;
}if ("xyz" === propertyName) {
if (this.currentObject != null) {
if (this.vwr.getBoolean(603979847)) {
this.currentObject.setScalePixelsPerMicron(this.vwr.getScalePixelsPerAngstrom(false) * 10000);
}this.currentObject.setXYZ(value, true);
}}if ("scale" === propertyName) {
if (this.currentObject != null) {
(this.currentObject).setScale((value).floatValue());
} else if (this.isAll) {
for (var t, $t = this.objects.values().iterator (); $t.hasNext()&& ((t = $t.next ()) || true);) t.setScale((value).floatValue());

}return;
}if ("image" === propertyName) {
if (this.currentObject != null) {
(this.currentObject).setImage(value);
} else if (this.isAll) {
for (var t, $t = this.objects.values().iterator (); $t.hasNext()&& ((t = $t.next ()) || true);) t.setImage(value);

}return;
}if ("hidden" === propertyName) {
var isHidden = (value).booleanValue();
if (this.currentObject != null) {
(this.currentObject).hidden = isHidden;
} else if (this.isAll || this.thisID != null) {
for (var t, $t = this.objects.values().iterator (); $t.hasNext()&& ((t = $t.next ()) || true);) if (this.isAll || JU.PT.isMatch(t.target.toUpperCase(), this.thisID, true, true)) t.hidden = isHidden;

}return;
}if ("script" === propertyName) {
if (this.currentObject != null) this.currentObject.setScript(value);
return;
}if ("xpos" === propertyName) {
if (this.currentObject != null) {
this.currentObject.setXYZ(null, true);
this.currentObject.setMovableX((value).intValue());
}return;
}if ("ypos" === propertyName) {
if (this.currentObject != null) {
this.currentObject.setXYZ(null, true);
this.currentObject.setMovableY((value).intValue());
}return;
}if ("%xpos" === propertyName) {
if (this.currentObject != null) {
this.currentObject.setXYZ(null, true);
this.currentObject.setMovableXPercent((value).intValue());
}return;
}if ("%ypos" === propertyName) {
if (this.currentObject != null) {
this.currentObject.setXYZ(null, true);
this.currentObject.setMovableYPercent((value).intValue());
}return;
}if ("%zpos" === propertyName) {
if (this.currentObject != null) {
this.currentObject.setXYZ(null, true);
this.currentObject.setMovableZPercent((value).intValue());
}return;
}if ("xypos" === propertyName) {
if (this.currentObject != null) {
var pt = value;
this.currentObject.setXYZ(null, true);
if (pt.z == 3.4028235E38) {
this.currentObject.setMovableX(Clazz.floatToInt(pt.x));
this.currentObject.setMovableY(Clazz.floatToInt(pt.y));
} else {
this.currentObject.setMovableXPercent(Clazz.floatToInt(pt.x));
this.currentObject.setMovableYPercent(Clazz.floatToInt(pt.y));
}}return;
}if ("offset" === propertyName) {
if (this.currentObject != null) {
this.currentObject.pymolOffset = value;
}return;
}if ("align" === propertyName) {
if (this.currentObject != null) {
this.currentObject.pymolOffset = null;
}}this.setPropTS(propertyName, value, null);
}, "~S,~O,JU.BS");
Clazz.overrideMethod(c$, "getPropertyData", 
function(property, data){
if ("currentTarget" === property) {
return (this.currentObject != null && (data[0] = this.currentObject.target) != null);
}if (property === "%SCALE") {
data[0] = this.scaleObject;
return (data[0] != null);
}if (property === "checkID") {
var key = (data[0]).toUpperCase();
var isWild = JU.PT.isWild(key);
for (var t, $t = this.objects.values().iterator (); $t.hasNext()&& ((t = $t.next ()) || true);) {
var id = t.target;
if (id.equalsIgnoreCase(key) || isWild && JU.PT.isMatch(id.toUpperCase(), key, true, true)) {
data[1] = id;
return true;
}}
return false;
}return this.getPropShape(property, data);
}, "~S,~A");
Clazz.overrideMethod(c$, "getShapeDetail", 
function(){
var lst =  new java.util.Hashtable();
for (var e, $e = this.objects.entrySet().iterator (); $e.hasNext()&& ((e = $e.next ()) || true);) {
var info =  new java.util.Hashtable();
var t = e.getValue();
var name = e.getKey();
info.put("boxXY", t.boxXY);
if (t.xyz != null) info.put("xyz", t.xyz);
var o = t.image;
if (o == null) {
info.put("text", t.text == null ? "" : t.text);
} else {
info.put("imageFile", t.text);
info.put("imageWidth", Integer.$valueOf(this.vwr.apiPlatform.getImageWidth(o)));
info.put("imageHeight", Integer.$valueOf(this.vwr.apiPlatform.getImageHeight(o)));
}lst.put(name, info);
}
var lst2 =  new JU.Lst();
lst2.addLast(lst);
return lst2;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
