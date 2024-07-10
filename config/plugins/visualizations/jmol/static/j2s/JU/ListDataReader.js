Clazz.declarePackage("JU");
Clazz.load(["JU.DataReader"], "JU.ListDataReader", null, function(){
var c$ = Clazz.decorateAsClass(function(){
this.data = null;
this.pt = 0;
this.len = 0;
Clazz.instantialize(this, arguments);}, JU, "ListDataReader", JU.DataReader);
Clazz.overrideMethod(c$, "setData", 
function(data){
this.data = data;
this.len = this.data.size();
return this;
}, "~O");
Clazz.defineMethod(c$, "read", 
function(buf, off, len){
return this.readBuf(buf, off, len);
}, "~A,~N,~N");
Clazz.defineMethod(c$, "readLine", 
function(){
return (this.pt < this.len ? this.data.get(this.pt++) : null);
});
Clazz.defineMethod(c$, "mark", 
function(ptr){
this.ptMark = this.pt;
}, "~N");
Clazz.overrideMethod(c$, "reset", 
function(){
this.pt = this.ptMark;
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
