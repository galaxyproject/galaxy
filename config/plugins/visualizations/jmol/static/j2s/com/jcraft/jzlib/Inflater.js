Clazz.declarePackage("com.jcraft.jzlib");
Clazz.load(["com.jcraft.jzlib.ZStream"], "com.jcraft.jzlib.Inflater", ["com.jcraft.jzlib.Inflate"], function(){
var c$ = Clazz.declareType(com.jcraft.jzlib, "Inflater", com.jcraft.jzlib.ZStream);
Clazz.defineMethod(c$, "init", 
function(w, nowrap){
this.setAdler32();
if (w == 0) w = 15;
this.istate =  new com.jcraft.jzlib.Inflate(this);
this.istate.inflateInit(nowrap ? -w : w);
return this;
}, "~N,~B");
Clazz.overrideMethod(c$, "inflate", 
function(f){
if (this.istate == null) return -2;
var ret = this.istate.inflate(f);
return ret;
}, "~N");
Clazz.overrideMethod(c$, "end", 
function(){
if (this.istate == null) return -2;
var ret = this.istate.inflateEnd();
return ret;
});
Clazz.defineMethod(c$, "sync", 
function(){
if (this.istate == null) return -2;
return this.istate.inflateSync();
});
Clazz.defineMethod(c$, "syncPoint", 
function(){
if (this.istate == null) return -2;
return this.istate.inflateSyncPoint();
});
Clazz.defineMethod(c$, "setDictionary", 
function(dictionary, dictLength){
if (this.istate == null) return -2;
return this.istate.inflateSetDictionary(dictionary, dictLength);
}, "~A,~N");
Clazz.overrideMethod(c$, "finished", 
function(){
return this.istate.mode == 12;
});
Clazz.defineMethod(c$, "reset", 
function(){
this.avail_in = 0;
if (this.istate != null) this.istate.reset();
});
});
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
