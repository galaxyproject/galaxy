Clazz.declarePackage("J.appletjs");
Clazz.load(["JU.GenericApplet"], "J.appletjs.Jmol", ["java.util.Hashtable"], function(){
var c$ = Clazz.declareType(J.appletjs, "Jmol", JU.GenericApplet);
Clazz.makeConstructor(c$, 
function(vwrOptions){
Clazz.superConstructor (this, J.appletjs.Jmol, []);
this.htParams =  new java.util.Hashtable();
if (vwrOptions == null) vwrOptions =  new java.util.Hashtable();
this.vwrOptions = vwrOptions;
for (var entry, $entry = vwrOptions.entrySet().iterator (); $entry.hasNext()&& ((entry = $entry.next ()) || true);) this.htParams.put(entry.getKey().toLowerCase(), entry.getValue());

this.documentBase = "" + vwrOptions.get("documentBase");
this.codeBase = "" + vwrOptions.get("codePath");
JU.GenericApplet.isJS = true;
this.init(this);
}, "java.util.Map");
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
