Clazz.declarePackage("J.io");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.fm = null;
this.vwr = null;
this.aDOMNode = null;
this.atomSetCollection = null;
this.htParams = null;
Clazz.instantialize(this, arguments);}, J.io, "DOMReader", null);
Clazz.prepareFields (c$, function(){
this.aDOMNode =  new Array(1);
});
Clazz.makeConstructor(c$, 
function(){
});
Clazz.defineMethod(c$, "set", 
function(fileManager, vwr, DOMNode, htParams){
this.fm = fileManager;
this.vwr = vwr;
this.aDOMNode[0] = DOMNode;
this.htParams = htParams;
}, "JV.FileManager,JV.Viewer,~O,java.util.Map");
Clazz.defineMethod(c$, "run", 
function(){
var info = null;
{
}if (info != null) this.htParams.put("nameSpaceInfo", info);
this.vwr.zap(false, true, false);
this.atomSetCollection = this.vwr.getModelAdapter().getAtomSetCollectionFromDOM(this.aDOMNode, this.htParams);
if ((typeof(this.atomSetCollection)=='string')) return;
this.fm.setFileInfo( Clazz.newArray(-1, ["JSNode"]));
});
})();
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
