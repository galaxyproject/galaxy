/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *//* This is a compiled version of Dojo, designed for deployment and not for development. If would like to modify or work with Dojo, please visit http://dojotoolkit.org for more information and to get the 'source' version of this file. */var dj_global=this;
function dj_undef(_1,_2){
if(!_2){
_2=dj_global;
}
return (typeof _2[_1]=="undefined");
}
if(dj_undef("djConfig")){
var djConfig={};
}
var dojo;
if(dj_undef("dojo")){
dojo={};
}
dojo.version={major:0,minor:1,patch:0,flag:"+",revision:Number("$Rev: 1885 $".match(/[0-9]+/)[0]),toString:function(){
with(dojo.version){
return major+"."+minor+"."+patch+flag+" ("+revision+")";
}
}};
dojo.evalObjPath=function(_3,_4){
if(typeof _3!="string"){
return dj_global;
}
if(_3.indexOf(".")==-1){
if(dj_undef(_3,dj_global)){
dj_global[_3]={};
}
return dj_global[_3];
}
var _5=_3.split(/\./);
var _6=dj_global;
for(var i=0;i<_5.length;++i){
if(!_4){
_6=_6[_5[i]];
if((typeof _6=="undefined")||(!_6)){
return _6;
}
}else{
if(dj_undef(_5[i],_6)){
_6[_5[i]]={};
}
_6=_6[_5[i]];
}
}
return _6;
};
dojo.errorToString=function(_8){
return ((!dj_undef("message",_8))?_8.message:(dj_undef("description",_8)?_8:_8.description));
};
dojo.raise=function(_9,_10){
if(_10){
_9=_9+": "+dojo.errorToString(_10);
}
var he=dojo.hostenv;
if(dj_undef("hostenv",dojo)&&dj_undef("println",dojo)){
dojo.hostenv.println("FATAL: "+_9);
}
throw Error(_9);
};
dj_throw=dj_rethrow=function(m,e){
dojo.deprecated("dj_throw and dj_rethrow deprecated, use dojo.raise instead");
dojo.raise(m,e);
};
dojo.debug=function(){
if(!djConfig.isDebug){
return;
}
var _14=arguments;
if(dj_undef("println",dojo.hostenv)){
dojo.raise("dojo.debug not available (yet?)");
}
var _15=dj_global["jum"]&&!dj_global["jum"].isBrowser;
var s=[(_15?"":"DEBUG: ")];
for(var i=0;i<_14.length;++i){
if(!false&&_14[i] instanceof Error){
var msg="["+_14[i].name+": "+dojo.errorToString(_14[i])+(_14[i].fileName?", file: "+_14[i].fileName:"")+(_14[i].lineNumber?", line: "+_14[i].lineNumber:"")+"]";
}else{
var msg=_14[i];
}
s.push(msg);
}
if(_15){
jum.debug(s.join(" "));
}else{
dojo.hostenv.println(s.join(" "));
}
};
var dj_debug=dojo.debug;
function dj_eval(s){
return dj_global.eval?dj_global.eval(s):eval(s);
}
dj_unimplemented=dojo.unimplemented=function(_18,_19){
var _20="'"+_18+"' not implemented";
if((typeof _19!="undefined")&&(_19)){
_20+=" "+_19;
}
dojo.raise(_20);
};
dj_deprecated=dojo.deprecated=function(_21,_22){
var _23="DEPRECATED: "+_21;
if((typeof _22!="undefined")&&(_22)){
_23+=" "+_22;
}
dojo.debug(_23);
};
dojo.inherits=function(_24,_25){
if(typeof _25!="function"){
dojo.raise("superclass: "+_25+" borken");
}
_24.prototype=new _25();
_24.prototype.constructor=_24;
_24.superclass=_25.prototype;
_24["super"]=_25.prototype;
};
dj_inherits=function(_26,_27){
dojo.deprecated("dj_inherits deprecated, use dojo.inherits instead");
dojo.inherits(_26,_27);
};
dojo.render=(function(){
function vscaffold(_28,_29){
var tmp={capable:false,support:{builtin:false,plugin:false},prefixes:_28};
for(var x in _29){
tmp[x]=false;
}
return tmp;
}
return {name:"",ver:dojo.version,os:{win:false,linux:false,osx:false},html:vscaffold(["html"],["ie","opera","khtml","safari","moz"]),svg:vscaffold(["svg"],["corel","adobe","batik"]),swf:vscaffold(["Swf","Flash","Mm"],["mm"]),swt:vscaffold(["Swt"],["ibm"])};
})();
dojo.hostenv=(function(){
var _32={isDebug:false,baseScriptUri:"",baseRelativePath:"",libraryScriptUri:"",iePreventClobber:false,ieClobberMinimal:true,preventBackButtonFix:true,searchIds:[],parseWidgets:true};
if(typeof djConfig=="undefined"){
djConfig=_32;
}else{
for(var _33 in _32){
if(typeof djConfig[_33]=="undefined"){
djConfig[_33]=_32[_33];
}
}
}
var djc=djConfig;
function _def(obj,_36,def){
return (dj_undef(_36,obj)?def:obj[_36]);
}
return {name_:"(unset)",version_:"(unset)",pkgFileName:"__package__",loading_modules_:{},loaded_modules_:{},addedToLoadingCount:[],removedFromLoadingCount:[],inFlightCount:0,modulePrefixes_:{dojo:{name:"dojo",value:"src"}},setModulePrefix:function(_38,_39){
this.modulePrefixes_[_38]={name:_38,value:_39};
},getModulePrefix:function(_40){
var mp=this.modulePrefixes_;
if((mp[_40])&&(mp[_40]["name"])){
return mp[_40].value;
}
return _40;
},getTextStack:[],loadUriStack:[],loadedUris:[],post_load_:false,modulesLoadedListeners:[],getName:function(){
return this.name_;
},getVersion:function(){
return this.version_;
},getText:function(uri){
dojo.unimplemented("getText","uri="+uri);
},getLibraryScriptUri:function(){
dojo.unimplemented("getLibraryScriptUri","");
}};
})();
dojo.hostenv.getBaseScriptUri=function(){
if(djConfig.baseScriptUri.length){
return djConfig.baseScriptUri;
}
var uri=new String(djConfig.libraryScriptUri||djConfig.baseRelativePath);
if(!uri){
dojo.raise("Nothing returned by getLibraryScriptUri(): "+uri);
}
var _43=uri.lastIndexOf("/");
djConfig.baseScriptUri=djConfig.baseRelativePath;
return djConfig.baseScriptUri;
};
dojo.hostenv.setBaseScriptUri=function(uri){
djConfig.baseScriptUri=uri;
};
dojo.hostenv.loadPath=function(_44,_45,cb){
if((_44.charAt(0)=="/")||(_44.match(/^\w+:/))){
dojo.raise("relpath '"+_44+"'; must be relative");
}
var uri=this.getBaseScriptUri()+_44;
try{
return ((!_45)?this.loadUri(uri,cb):this.loadUriAndCheck(uri,_45,cb));
}
catch(e){
dojo.debug(e);
return false;
}
};
dojo.hostenv.loadUri=function(uri,cb){
if(dojo.hostenv.loadedUris[uri]){
return;
}
var _47=this.getText(uri,null,true);
if(_47==null){
return 0;
}
var _48=dj_eval(_47);
return 1;
};
dojo.hostenv.getDepsForEval=function(_49){
if(!_49){
_49="";
}
var _50=[];
var tmp;
var _51=[/dojo.hostenv.loadModule\(.*?\)/mg,/dojo.hostenv.require\(.*?\)/mg,/dojo.require\(.*?\)/mg,/dojo.requireIf\(.*?\)/mg,/dojo.hostenv.conditionalLoadModule\([\w\W]*?\)/mg];
for(var i=0;i<_51.length;i++){
tmp=_49.match(_51[i]);
if(tmp){
for(var x=0;x<tmp.length;x++){
_50.push(tmp[x]);
}
}
}
return _50;
};
dojo.hostenv.loadUriAndCheck=function(uri,_52,cb){
var ok=true;
try{
ok=this.loadUri(uri,cb);
}
catch(e){
dojo.debug("failed loading ",uri," with error: ",e);
}
return ((ok)&&(this.findModule(_52,false)))?true:false;
};
dojo.loaded=function(){
};
dojo.hostenv.loaded=function(){
this.post_load_=true;
var mll=this.modulesLoadedListeners;
for(var x=0;x<mll.length;x++){
mll[x]();
}
dojo.loaded();
};
dojo.addOnLoad=function(obj,_55){
if(arguments.length==1){
dojo.hostenv.modulesLoadedListeners.push(obj);
}else{
if(arguments.length>1){
dojo.hostenv.modulesLoadedListeners.push(function(){
obj[_55]();
});
}
}
};
dojo.hostenv.modulesLoaded=function(){
if(this.post_load_){
return;
}
if((this.loadUriStack.length==0)&&(this.getTextStack.length==0)){
if(this.inFlightCount>0){
dojo.debug("files still in flight!");
return;
}
if(typeof setTimeout=="object"){
setTimeout("dojo.hostenv.loaded();",0);
}else{
dojo.hostenv.loaded();
}
}
};
dojo.hostenv.moduleLoaded=function(_56){
var _57=dojo.evalObjPath((_56.split(".").slice(0,-1)).join("."));
this.loaded_modules_[(new String(_56)).toLowerCase()]=_57;
};
dojo.hostenv.loadModule=function(_58,_59,_60){
var _61=this.findModule(_58,false);
if(_61){
return _61;
}
if(dj_undef(_58,this.loading_modules_)){
this.addedToLoadingCount.push(_58);
}
this.loading_modules_[_58]=1;
var _62=_58.replace(/\./g,"/")+".js";
var _63=_58.split(".");
var _64=_58.split(".");
for(var i=_63.length-1;i>0;i--){
var _65=_63.slice(0,i).join(".");
var _66=this.getModulePrefix(_65);
if(_66!=_65){
_63.splice(0,i,_66);
break;
}
}
var _67=_63[_63.length-1];
if(_67=="*"){
_58=(_64.slice(0,-1)).join(".");
while(_63.length){
_63.pop();
_63.push(this.pkgFileName);
_62=_63.join("/")+".js";
if(_62.charAt(0)=="/"){
_62=_62.slice(1);
}
ok=this.loadPath(_62,((!_60)?_58:null));
if(ok){
break;
}
_63.pop();
}
}else{
_62=_63.join("/")+".js";
_58=_64.join(".");
var ok=this.loadPath(_62,((!_60)?_58:null));
if((!ok)&&(!_59)){
_63.pop();
while(_63.length){
_62=_63.join("/")+".js";
ok=this.loadPath(_62,((!_60)?_58:null));
if(ok){
break;
}
_63.pop();
_62=_63.join("/")+"/"+this.pkgFileName+".js";
if(_62.charAt(0)=="/"){
_62=_62.slice(1);
}
ok=this.loadPath(_62,((!_60)?_58:null));
if(ok){
break;
}
}
}
if((!ok)&&(!_60)){
dojo.raise("Could not load '"+_58+"'; last tried '"+_62+"'");
}
}
if(!_60){
_61=this.findModule(_58,false);
if(!_61){
dojo.raise("symbol '"+_58+"' is not defined after loading '"+_62+"'");
}
}
return _61;
};
dojo.hostenv.startPackage=function(_68){
var _69=_68.split(/\./);
if(_69[_69.length-1]=="*"){
_69.pop();
}
return dojo.evalObjPath(_69.join("."),true);
};
dojo.hostenv.findModule=function(_70,_71){
if(this.loaded_modules_[(new String(_70)).toLowerCase()]){
return this.loaded_modules_[_70];
}
var _72=dojo.evalObjPath(_70);
if((typeof _72!=="undefined")&&(_72)){
return _72;
}
if(_71){
dojo.raise("no loaded module named '"+_70+"'");
}
return null;
};
if(typeof window=="undefined"){
dojo.raise("no window object");
}
(function(){
if(((djConfig["baseScriptUri"]=="")||(djConfig["baseRelativePath"]==""))&&(document&&document.getElementsByTagName)){
var _73=document.getElementsByTagName("script");
var _74=/(__package__|dojo)\.js$/i;
for(var i=0;i<_73.length;i++){
var src=_73[i].getAttribute("src");
if(_74.test(src)){
var _76=src.replace(_74,"");
if(djConfig["baseScriptUri"]==""){
djConfig["baseScriptUri"]=_76;
}
if(djConfig["baseRelativePath"]==""){
djConfig["baseRelativePath"]=_76;
}
break;
}
}
}
var dr=dojo.render;
var drh=dojo.render.html;
var dua=drh.UA=navigator.userAgent;
var dav=drh.AV=navigator.appVersion;
var t=true;
var f=false;
drh.capable=t;
drh.support.builtin=t;
dr.ver=parseFloat(drh.AV);
dr.os.mac=dav.indexOf("Macintosh")>=0;
dr.os.win=dav.indexOf("Windows")>=0;
dr.os.linux=dav.indexOf("X11")>=0;
drh.opera=dua.indexOf("Opera")>=0;
drh.khtml=(dav.indexOf("Konqueror")>=0)||(dav.indexOf("Safari")>=0);
drh.safari=dav.indexOf("Safari")>=0;
var _83=dua.indexOf("Gecko");
drh.mozilla=drh.moz=(_83>=0)&&(!drh.khtml);
if(drh.mozilla){
drh.geckoVersion=dua.substring(_83+6,_83+14);
}
drh.ie=(document.all)&&(!drh.opera);
drh.ie50=drh.ie&&dav.indexOf("MSIE 5.0")>=0;
drh.ie55=drh.ie&&dav.indexOf("MSIE 5.5")>=0;
drh.ie60=drh.ie&&dav.indexOf("MSIE 6.0")>=0;
dr.svg.capable=f;
dr.svg.support.plugin=f;
dr.svg.support.builtin=f;
dr.svg.adobe=f;
if(document.createElementNS&&drh.moz&&parseFloat(dua.substring(dua.lastIndexOf("/")+1,dua.length))>1){
dr.svg.capable=t;
dr.svg.support.builtin=t;
dr.svg.support.plugin=f;
dr.svg.adobe=f;
}else{
if(navigator.mimeTypes&&navigator.mimeTypes.length>0){
var _84=navigator.mimeTypes["image/svg+xml"]||navigator.mimeTypes["image/svg"]||navigator.mimeTypes["image/svg-xml"];
if(_84){
dr.svg.capable=t;
dr.svg.support.plugin=t;
dr.svg.adobe=_84&&_84.enabledPlugin&&_84.enabledPlugin.description&&(_84.enabledPlugin.description.indexOf("Adobe")>-1);
}
}else{
if(drh.ie&&dr.os.win){
var _84=f;
try{
var _85=new ActiveXObject("Adobe.SVGCtl");
_84=t;
}
catch(e){
}
if(_84){
dr.svg.capable=t;
dr.svg.support.plugin=t;
dr.svg.adobe=t;
}
}else{
dr.svg.capable=f;
dr.svg.support.plugin=f;
dr.svg.adobe=f;
}
}
}
})();
dojo.hostenv.startPackage("dojo.hostenv");
dojo.hostenv.name_="browser";
dojo.hostenv.searchIds=[];
var DJ_XMLHTTP_PROGIDS=["Msxml2.XMLHTTP","Microsoft.XMLHTTP","Msxml2.XMLHTTP.4.0"];
dojo.hostenv.getXmlhttpObject=function(){
var _86=null;
var _87=null;
try{
_86=new XMLHttpRequest();
}
catch(e){
}
if(!_86){
for(var i=0;i<3;++i){
var _88=DJ_XMLHTTP_PROGIDS[i];
try{
_86=new ActiveXObject(_88);
}
catch(e){
_87=e;
}
if(_86){
DJ_XMLHTTP_PROGIDS=[_88];
break;
}
}
}
if(!_86){
return dojo.raise("XMLHTTP not available",_87);
}
return _86;
};
dojo.hostenv.getText=function(uri,_89,_90){
var _91=this.getXmlhttpObject();
if(_89){
_91.onreadystatechange=function(){
if((4==_91.readyState)&&(_91["status"])){
if(_91.status==200){
dojo.debug("LOADED URI: "+uri);
_89(_91.responseText);
}
}
};
}
_91.open("GET",uri,_89?true:false);
_91.send(null);
if(_89){
return null;
}
return _91.responseText;
};
function dj_last_script_src(){
var _92=window.document.getElementsByTagName("script");
if(_92.length<1){
dojo.raise("No script elements in window.document, so can't figure out my script src");
}
var _93=_92[_92.length-1];
var src=_93.src;
if(!src){
dojo.raise("Last script element (out of "+_92.length+") has no src");
}
return src;
}
if(!dojo.hostenv["library_script_uri_"]){
dojo.hostenv.library_script_uri_=dj_last_script_src();
}
dojo.hostenv.defaultDebugContainerId="dojoDebug";
dojo.hostenv.println=function(_94){
try{
var _95=document.getElementById(djConfig.debugContainerId?djConfig.debugContainerId:dojo.hostenv.defaultDebugContainerId);
if(!_95){
_95=document.getElementsByTagName("body")[0]||document.body;
}
var div=document.createElement("div");
div.appendChild(document.createTextNode(_94));
_95.appendChild(div);
}
catch(e){
try{
document.write("<div>"+_94+"</div>");
}
catch(e2){
window.status=_94;
}
}
};
function dj_addNodeEvtHdlr(_97,_98,fp,_100){
var _101=_97["on"+_98]||function(){
};
_97["on"+_98]=function(){
fp.apply(_97,arguments);
_101.apply(_97,arguments);
};
return true;
}
dj_addNodeEvtHdlr(window,"load",function(){
if(dojo.render.html.ie){
dojo.hostenv.makeWidgets();
}
dojo.hostenv.modulesLoaded();
});
dojo.hostenv.makeWidgets=function(){
if((djConfig.parseWidgets)||(djConfig.searchIds.length>0)){
if(dojo.evalObjPath("dojo.widget.Parse")){
try{
var _102=new dojo.xml.Parse();
var sids=djConfig.searchIds;
if(sids.length>0){
for(var x=0;x<sids.length;x++){
if(!document.getElementById(sids[x])){
continue;
}
var frag=_102.parseElement(document.getElementById(sids[x]),null,true);
dojo.widget.getParser().createComponents(frag);
}
}else{
if(djConfig.parseWidgets){
var frag=_102.parseElement(document.getElementsByTagName("body")[0]||document.body,null,true);
dojo.widget.getParser().createComponents(frag);
}
}
}
catch(e){
dojo.debug("auto-build-widgets error:",e);
}
}
}
};
dojo.hostenv.modulesLoadedListeners.push(function(){
if(!dojo.render.html.ie){
dojo.hostenv.makeWidgets();
}
});
try{
if(!window["djConfig"]||!window.djConfig["preventBackButtonFix"]){
document.write("<iframe style='border: 0px; width: 1px; height: 1px; position: absolute; bottom: 0px; right: 0px; visibility: visible;' name='djhistory' id='djhistory' src='"+(dojo.hostenv.getBaseScriptUri()+"iframe_history.html")+"'></iframe>");
}
if(dojo.render.html.ie){
document.write("<style>v:*{ behavior:url(#default#VML); }</style>");
document.write("<xml:namespace ns=\"urn:schemas-microsoft-com:vml\" prefix=\"v\"/>");
}
}
catch(e){
}
dojo.hostenv.writeIncludes=function(){
};
dojo.hostenv.conditionalLoadModule=function(_105){
var _106=_105["common"]||[];
var _107=(_105[dojo.hostenv.name_])?_106.concat(_105[dojo.hostenv.name_]||[]):_106.concat(_105["default"]||[]);
for(var x=0;x<_107.length;x++){
var curr=_107[x];
if(curr.constructor==Array){
dojo.hostenv.loadModule.apply(dojo.hostenv,curr);
}else{
dojo.hostenv.loadModule(curr);
}
}
};
dojo.hostenv.require=dojo.hostenv.loadModule;
dojo.require=function(){
dojo.hostenv.loadModule.apply(dojo.hostenv,arguments);
};
dojo.requireIf=function(){
if((arguments[0]=="common")||(dojo.render[arguments[0]].capable)){
var args=[];
for(var i=1;i<arguments.length;i++){
args.push(arguments[i]);
}
dojo.require.apply(dojo,args);
}
};
dojo.conditionalRequire=dojo.requireIf;
dojo.kwCompoundRequire=function(){
dojo.hostenv.conditionalLoadModule.apply(dojo.hostenv,arguments);
};
dojo.hostenv.provide=dojo.hostenv.startPackage;
dojo.provide=function(){
return dojo.hostenv.startPackage.apply(dojo.hostenv,arguments);
};
dojo.profile={start:function(){
},end:function(){
},dump:function(){
}};
dojo.provide("dojo.lang");
dojo.provide("dojo.lang.Lang");
dojo.lang.mixin=function(obj,_110){
var tobj={};
for(var x in _110){
if(typeof tobj[x]=="undefined"){
obj[x]=_110[x];
}
}
return obj;
};
dojo.lang.extend=function(ctor,_113){
this.mixin(ctor.prototype,_113);
};
dojo.lang.extendPrototype=function(obj,_114){
this.extend(obj.constructor,_114);
};
dojo.lang.hitch=function(obj,meth){
return function(){
return obj[meth].apply(obj,arguments);
};
};
dojo.lang.setTimeout=function(func,_117){
var _118=window,argsStart=2;
if(typeof _117=="function"){
_118=func;
func=_117;
_117=arguments[2];
argsStart++;
}
var args=[];
for(var i=argsStart;i<arguments.length;i++){
args.push(arguments[i]);
}
return setTimeout(function(){
func.apply(_118,args);
},_117);
};
dojo.lang.isObject=function(wh){
return typeof wh=="object"||dojo.lang.isArray(wh)||dojo.lang.isFunction(wh);
};
dojo.lang.isArray=function(wh){
return (wh instanceof Array||typeof wh=="array");
};
dojo.lang.isFunction=function(wh){
return (wh instanceof Function||typeof wh=="function");
};
dojo.lang.isString=function(wh){
return (wh instanceof String||typeof wh=="string");
};
dojo.lang.isNumber=function(wh){
return (wh instanceof Number||typeof wh=="number");
};
dojo.lang.isBoolean=function(wh){
return (wh instanceof Boolean||typeof wh=="boolean");
};
dojo.lang.isUndefined=function(wh){
return ((wh==undefined)&&(typeof wh=="undefined"));
};
dojo.lang.isAlien=function(wh){
return !dojo.lang.isFunction()&&/\{\s*\[native code\]\s*\}/.test(String(wh));
};
dojo.lang.find=function(arr,val,_122){
if(_122){
for(var i=0;i<arr.length;++i){
if(arr[i]===val){
return i;
}
}
}else{
for(var i=0;i<arr.length;++i){
if(arr[i]==val){
return i;
}
}
}
return -1;
};
dojo.lang.inArray=function(arr,val){
if((!arr||arr.constructor!=Array)&&(val&&val.constructor==Array)){
var a=arr;
arr=val;
val=a;
}
return dojo.lang.find(arr,val)>-1;
};
dojo.lang.getNameInObj=function(ns,item){
if(!ns){
ns=dj_global;
}
for(var x in ns){
if(ns[x]===item){
return new String(x);
}
}
return null;
};
dojo.lang.has=function(obj,name){
return (typeof obj[name]!=="undefined");
};
dojo.lang.isEmpty=function(obj){
var tmp={};
var _127=0;
for(var x in obj){
if(obj[x]&&(!tmp[x])){
_127++;
break;
}
}
return (_127==0);
};
dojo.lang.forEach=function(arr,_128,_129){
var il=arr.length;
for(var i=0;i<((_129)?il:arr.length);i++){
if(_128(arr[i])=="break"){
break;
}
}
};
dojo.lang.map=function(arr,obj,_131){
if((typeof obj=="function")&&(!_131)){
_131=obj;
obj=dj_global;
}
for(var i=0;i<arr.length;++i){
_131.call(obj,arr[i]);
}
};
dojo.lang.tryThese=function(){
for(var x=0;x<arguments.length;x++){
try{
if(typeof arguments[x]=="function"){
var ret=(arguments[x]());
if(ret){
return ret;
}
}
}
catch(e){
dojo.debug(e);
}
}
};
dojo.lang.delayThese=function(farr,cb,_134,_135){
if(!farr.length){
if(typeof _135=="function"){
_135();
}
return;
}
if((typeof _134=="undefined")&&(typeof cb=="number")){
_134=cb;
cb=function(){
};
}else{
if(!cb){
cb=function(){
};
if(!_134){
_134=0;
}
}
}
setTimeout(function(){
(farr.shift())();
cb();
dojo.lang.delayThese(farr,cb,_134,_135);
},_134);
};
dojo.lang.shallowCopy=function(obj){
var ret={},key;
for(key in obj){
if(dojo.lang.isUndefined(ret[key])){
ret[key]=obj[key];
}
}
return ret;
};
dojo.provide("dojo.string");
dojo.require("dojo.lang");
dojo.string.trim=function(_136){
if(arguments.length==0){
_136=this;
}
if(typeof _136!="string"){
return _136;
}
if(!_136.length){
return _136;
}
return _136.replace(/^\s*/,"").replace(/\s*$/,"");
};
dojo.string.paramString=function(str,_138,_139){
if(typeof str!="string"){
_138=str;
_139=_138;
str=this;
}
for(var name in _138){
var re=new RegExp("\\%\\{"+name+"\\}","g");
str=str.replace(re,_138[name]);
}
if(_139){
str=str.replace(/%\{([^\}\s]+)\}/g,"");
}
return str;
};
dojo.string.capitalize=function(str){
if(typeof str!="string"||str==null){
return "";
}
if(arguments.length==0){
str=this;
}
var _141=str.split(" ");
var _142="";
var len=_141.length;
for(var i=0;i<len;i++){
var word=_141[i];
word=word.charAt(0).toUpperCase()+word.substring(1,word.length);
_142+=word;
if(i<len-1){
_142+=" ";
}
}
return new String(_142);
};
dojo.string.isBlank=function(str){
if(!dojo.lang.isString(str)){
return true;
}
return (dojo.string.trim(str).length==0);
};
dojo.string.encodeAscii=function(str){
if(!dojo.lang.isString(str)){
return str;
}
var ret="";
var _145=escape(str);
var _146,re=/%u([0-9A-F]{4})/i;
while((_146=_145.match(re))){
var num=Number("0x"+_146[1]);
var _148=escape("&#"+num+";");
ret+=_145.substring(0,_146.index)+_148;
_145=_145.substring(_146.index+_146[0].length);
}
ret+=_145.replace(/\+/g,"%2B");
return ret;
};
dojo.string.summary=function(str,len){
if(!len||str.length<len){
return str;
}else{
return str.substring(0,len)+"...";
}
};
dojo.provide("dojo.io.IO");
dojo.require("dojo.string");
dojo.io.transports=[];
dojo.io.hdlrFuncNames=["load","error"];
dojo.io.Request=function(url,_150,_151,_152){
if((arguments.length==1)&&(arguments[0].constructor==Object)){
this.fromKwArgs(arguments[0]);
}else{
this.url=url;
if(arguments.length>=2){
this.mimetype=_150;
}
if(arguments.length>=3){
this.transport=_151;
}
if(arguments.length>=4){
this.changeUrl=_152;
}
}
};
dojo.lang.extend(dojo.io.Request,{url:"",mimetype:"text/plain",method:"GET",content:undefined,transport:undefined,changeUrl:undefined,formNode:undefined,sync:false,bindSuccess:false,useCache:false,load:function(type,data,evt){
},error:function(type,_156){
},fromKwArgs:function(_157){
if(_157["url"]){
_157.url=_157.url.toString();
}
if(!_157["method"]&&_157["formNode"]&&_157["formNode"].method){
_157.method=_157["formNode"].method;
}
if(!_157["handle"]&&_157["handler"]){
_157.handle=_157.handler;
}
if(!_157["load"]&&_157["loaded"]){
_157.load=_157.loaded;
}
if(!_157["changeUrl"]&&_157["changeURL"]){
_157.changeUrl=_157.changeURL;
}
if(!_157["encoding"]){
if(!dojo.lang.isUndefined(djConfig["bindEncoding"])){
_157.encoding=djConfig.bindEncoding;
}else{
_157.encoding="";
}
}
var _158=dojo.lang.isFunction;
for(var x=0;x<dojo.io.hdlrFuncNames.length;x++){
var fn=dojo.io.hdlrFuncNames[x];
if(_158(_157[fn])){
continue;
}
if(_158(_157["handle"])){
_157[fn]=_157.handle;
}
}
dojo.lang.mixin(this,_157);
}});
dojo.io.Error=function(msg,type,num){
this.message=msg;
this.type=type||"unknown";
this.number=num||0;
};
dojo.io.transports.addTransport=function(name){
this.push(name);
this[name]=dojo.io[name];
};
dojo.io.bind=function(_160){
if(!(_160 instanceof dojo.io.Request)){
try{
_160=new dojo.io.Request(_160);
}
catch(e){
dojo.debug(e);
}
}
var _161="";
if(_160["transport"]){
_161=_160["transport"];
if(!this[_161]){
return _160;
}
}else{
for(var x=0;x<dojo.io.transports.length;x++){
var tmp=dojo.io.transports[x];
if((this[tmp])&&(this[tmp].canHandle(_160))){
_161=tmp;
}
}
if(_161==""){
return _160;
}
}
this[_161].bind(_160);
_160.bindSuccess=true;
return _160;
};
dojo.io.argsFromMap=function(map,_163){
var _164=new Object();
var _165="";
var enc=/utf/i.test(_163||"")?encodeURIComponent:dojo.string.encodeAscii;
for(var x in map){
if(!_164[x]){
_165+=enc(x)+"="+enc(map[x])+"&";
}
}
return _165;
};
dojo.provide("dojo.dom");
dojo.dom.ELEMENT_NODE=1;
dojo.dom.ATTRIBUTE_NODE=2;
dojo.dom.TEXT_NODE=3;
dojo.dom.CDATA_SECTION_NODE=4;
dojo.dom.ENTITY_REFERENCE_NODE=5;
dojo.dom.ENTITY_NODE=6;
dojo.dom.PROCESSING_INSTRUCTION_NODE=7;
dojo.dom.COMMENT_NODE=8;
dojo.dom.DOCUMENT_NODE=9;
dojo.dom.DOCUMENT_TYPE_NODE=10;
dojo.dom.DOCUMENT_FRAGMENT_NODE=11;
dojo.dom.NOTATION_NODE=12;
dojo.dom.dojoml="http://www.dojotoolkit.org/2004/dojoml";
dojo.dom.xmlns={svg:"http://www.w3.org/2000/svg",smil:"http://www.w3.org/2001/SMIL20/",mml:"http://www.w3.org/1998/Math/MathML",cml:"http://www.xml-cml.org",xlink:"http://www.w3.org/1999/xlink",xhtml:"http://www.w3.org/1999/xhtml",xul:"http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul",xbl:"http://www.mozilla.org/xbl",fo:"http://www.w3.org/1999/XSL/Format",xsl:"http://www.w3.org/1999/XSL/Transform",xslt:"http://www.w3.org/1999/XSL/Transform",xi:"http://www.w3.org/2001/XInclude",xforms:"http://www.w3.org/2002/01/xforms",saxon:"http://icl.com/saxon",xalan:"http://xml.apache.org/xslt",xsd:"http://www.w3.org/2001/XMLSchema",dt:"http://www.w3.org/2001/XMLSchema-datatypes",xsi:"http://www.w3.org/2001/XMLSchema-instance",rdf:"http://www.w3.org/1999/02/22-rdf-syntax-ns#",rdfs:"http://www.w3.org/2000/01/rdf-schema#",dc:"http://purl.org/dc/elements/1.1/",dcq:"http://purl.org/dc/qualifiers/1.0","soap-env":"http://schemas.xmlsoap.org/soap/envelope/",wsdl:"http://schemas.xmlsoap.org/wsdl/",AdobeExtensions:"http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/"};
dojo.dom.getTagName=function(node){
var _168=node.tagName;
if(_168.substr(0,5).toLowerCase()!="dojo:"){
if(_168.substr(0,4).toLowerCase()=="dojo"){
return "dojo:"+_168.substring(4).toLowerCase();
}
var djt=node.getAttribute("dojoType")||node.getAttribute("dojotype");
if(djt){
return "dojo:"+djt.toLowerCase();
}
if((node.getAttributeNS)&&(node.getAttributeNS(this.dojoml,"type"))){
return "dojo:"+node.getAttributeNS(this.dojoml,"type").toLowerCase();
}
try{
djt=node.getAttribute("dojo:type");
}
catch(e){
}
if(djt){
return "dojo:"+djt.toLowerCase();
}
if((!dj_global["djConfig"])||(!djConfig["ignoreClassNames"])){
var _170=node.className||node.getAttribute("class");
if((_170)&&(_170.indexOf("dojo-")!=-1)){
var _171=_170.split(" ");
for(var x=0;x<_171.length;x++){
if((_171[x].length>5)&&(_171[x].indexOf("dojo-")>=0)){
return "dojo:"+_171[x].substr(5).toLowerCase();
}
}
}
}
}
return _168.toLowerCase();
};
dojo.dom.getUniqueId=function(){
do{
var id="dj_unique_"+(++arguments.callee._idIncrement);
}while(document.getElementById(id));
return id;
};
dojo.dom.getUniqueId._idIncrement=0;
dojo.dom.getFirstChildElement=function(_173){
var node=_173.firstChild;
while(node&&node.nodeType!=dojo.dom.ELEMENT_NODE){
node=node.nextSibling;
}
return node;
};
dojo.dom.getLastChildElement=function(_174){
var node=_174.lastChild;
while(node&&node.nodeType!=dojo.dom.ELEMENT_NODE){
node=node.previousSibling;
}
return node;
};
dojo.dom.getNextSiblingElement=function(node){
if(!node){
return null;
}
do{
node=node.nextSibling;
}while(node&&node.nodeType!=dojo.dom.ELEMENT_NODE);
return node;
};
dojo.dom.getPreviousSiblingElement=function(node){
if(!node){
return null;
}
do{
node=node.previousSibling;
}while(node&&node.nodeType!=dojo.dom.ELEMENT_NODE);
return node;
};
dojo.dom.moveChildren=function(_175,_176,trim){
var _178=0;
if(trim){
while(_175.hasChildNodes()&&_175.firstChild.nodeType==dojo.dom.TEXT_NODE){
_175.removeChild(_175.firstChild);
}
while(_175.hasChildNodes()&&_175.lastChild.nodeType==dojo.dom.TEXT_NODE){
_175.removeChild(_175.lastChild);
}
}
while(_175.hasChildNodes()){
_176.appendChild(_175.firstChild);
_178++;
}
return _178;
};
dojo.dom.copyChildren=function(_179,_180,trim){
var _181=_179.cloneNode(true);
return this.moveChildren(_181,_180,trim);
};
dojo.dom.removeChildren=function(node){
var _182=node.childNodes.length;
while(node.hasChildNodes()){
node.removeChild(node.firstChild);
}
return _182;
};
dojo.dom.replaceChildren=function(node,_183){
dojo.dom.removeChildren(node);
node.appendChild(_183);
};
dojo.dom.removeNode=function(node){
if(node&&node.parentNode){
return node.parentNode.removeChild(node);
}
};
dojo.dom.getAncestors=function(node){
var _184=[];
while(node){
_184.push(node);
node=node.parentNode;
}
return _184;
};
dojo.dom.isDescendantOf=function(node,_185,_186){
if(_186&&node){
node=node.parentNode;
}
while(node){
if(node==_185){
return true;
}
node=node.parentNode;
}
return false;
};
dojo.dom.innerXML=function(node){
if(node.innerXML){
return node.innerXML;
}else{
if(typeof XMLSerializer!="undefined"){
return (new XMLSerializer()).serializeToString(node);
}
}
};
dojo.dom.createDocumentFromText=function(str,_187){
if(!_187){
_187="text/xml";
}
if(typeof DOMParser!="undefined"){
var _188=new DOMParser();
return _188.parseFromString(str,_187);
}else{
if(typeof ActiveXObject!="undefined"){
var _189=new ActiveXObject("Microsoft.XMLDOM");
if(_189){
_189.async=false;
_189.loadXML(str);
return _189;
}else{
dojo.debug("toXml didn't work?");
}
}else{
if(document.createElement){
var tmp=document.createElement("xml");
tmp.innerHTML=str;
if(document.implementation&&document.implementation.createDocument){
var _190=document.implementation.createDocument("foo","",null);
for(var i=0;i<tmp.childNodes.length;i++){
_190.importNode(tmp.childNodes.item(i),true);
}
return _190;
}
return tmp.document&&tmp.document.firstChild?tmp.document.firstChild:tmp;
}
}
}
return null;
};
dojo.dom.insertBefore=function(node,ref,_192){
if(_192!=true&&(node===ref||node.nextSibling===ref)){
return false;
}
var _193=ref.parentNode;
_193.insertBefore(node,ref);
return true;
};
dojo.dom.insertAfter=function(node,ref,_194){
var pn=ref.parentNode;
if(ref==pn.lastChild){
if((_194!=true)&&(node===ref)){
return false;
}
pn.appendChild(node);
}else{
return this.insertBefore(node,ref.nextSibling,_194);
}
return true;
};
dojo.dom.insertAtPosition=function(node,ref,_196){
switch(_196.toLowerCase()){
case "before":
dojo.dom.insertBefore(node,ref);
break;
case "after":
dojo.dom.insertAfter(node,ref);
break;
case "first":
if(ref.firstChild){
dojo.dom.insertBefore(node,ref.firstChild);
}else{
ref.appendChild(node);
}
break;
default:
ref.appendChild(node);
break;
}
};
dojo.dom.insertAtIndex=function(node,_197,_198){
var _199=_197.childNodes;
var _200=false;
if((dojo.lang.isNumber(_198))&&(_198>=_199.length)){
_197.appendChild(node);
return;
}
for(var i=0;i<_199.length;i++){
if((_199.item(i)["getAttribute"])&&(parseInt(_199.item(i).getAttribute("dojoinsertionindex"))>_198)){
dojo.dom.insertBefore(node,_199.item(i));
_200=true;
break;
}
}
if(!_200){
dojo.dom.insertBefore(node,_197);
}
};
dojo.dom.textContent=function(node,text){
if(text){
dojo.dom.replaceChildren(node,document.createTextNode(text));
return text;
}else{
var _202="";
if(node==null){
return _202;
}
for(var i=0;i<node.childNodes.length;i++){
switch(node.childNodes[i].nodeType){
case 1:
case 5:
_202+=dojo.dom.textContent(node.childNodes[i]);
break;
case 3:
case 2:
case 4:
_202+=node.childNodes[i].nodeValue;
break;
default:
break;
}
}
return _202;
}
};
dojo.dom.collectionToArray=function(_203){
var _204=new Array(_203.length);
for(var i=0;i<_203.length;i++){
_204[i]=_203[i];
}
return _204;
};
dojo.provide("dojo.io.BrowserIO");
dojo.require("dojo.io");
dojo.require("dojo.lang");
dojo.require("dojo.dom");
try{
if((!djConfig.preventBackButtonFix)&&(!dojo.hostenv.post_load_)){
document.write("<iframe style='border: 0px; width: 1px; height: 1px; position: absolute; bottom: 0px; right: 0px; visibility: visible;' name='djhistory' id='djhistory' src='"+(dojo.hostenv.getBaseScriptUri()+"iframe_history.html")+"'></iframe>");
}
}
catch(e){
}
dojo.io.checkChildrenForFile=function(node){
var _205=false;
var _206=node.getElementsByTagName("input");
dojo.lang.forEach(_206,function(_207){
if(_205){
return;
}
if(_207.getAttribute("type")=="file"){
_205=true;
}
});
return _205;
};
dojo.io.formHasFile=function(_208){
return dojo.io.checkChildrenForFile(_208);
};
dojo.io.encodeForm=function(_209,_210){
if((!_209)||(!_209.tagName)||(!_209.tagName.toLowerCase()=="form")){
dojo.raise("Attempted to encode a non-form element.");
}
var enc=/utf/i.test(_210||"")?encodeURIComponent:dojo.string.encodeAscii;
var _211=[];
for(var i=0;i<_209.elements.length;i++){
var elm=_209.elements[i];
if(elm.disabled||elm.tagName.toLowerCase()=="fieldset"){
continue;
}
var name=enc(elm.name);
var type=elm.type.toLowerCase();
if(type=="select-multiple"){
for(var j=0;j<elm.options.length;j++){
if(elm.options[j].selected){
_211.push(name+"="+enc(elm.options[j].value));
}
}
}else{
if(dojo.lang.inArray(type,["radio","checkbox"])){
if(elm.checked){
_211.push(name+"="+enc(elm.value));
}
}else{
if(!dojo.lang.inArray(type,["file","submit","reset","button"])){
_211.push(name+"="+enc(elm.value));
}
}
}
}
var _214=_209.getElementsByTagName("input");
for(var i=0;i<_214.length;i++){
var _215=_214[i];
if(_215.type.toLowerCase()=="image"&&_215.form==_209){
var name=enc(_215.name);
_211.push(name+"="+enc(_215.value));
_211.push(name+".x=0");
_211.push(name+".y=0");
}
}
return _211.join("&")+"&";
};
dojo.io.setIFrameSrc=function(_216,src,_217){
try{
var r=dojo.render.html;
if(!_217){
if(r.safari){
_216.location=src;
}else{
frames[_216.name].location=src;
}
}else{
var idoc=(r.moz)?_216.contentWindow:_216;
idoc.location.replace(src);
dojo.debug(_216.contentWindow.location);
}
}
catch(e){
dojo.debug("setIFrameSrc: "+e);
}
};
dojo.io.XMLHTTPTransport=new function(){
var _220=this;
this.initialHref=window.location.href;
this.initialHash=window.location.hash;
this.moveForward=false;
var _221={};
this.useCache=false;
this.historyStack=[];
this.forwardStack=[];
this.historyIframe=null;
this.bookmarkAnchor=null;
this.locationTimer=null;
function getCacheKey(url,_222,_223){
return url+"|"+_222+"|"+_223.toLowerCase();
}
function addToCache(url,_224,_225,http){
_221[getCacheKey(url,_224,_225)]=http;
}
function getFromCache(url,_227,_228){
return _221[getCacheKey(url,_227,_228)];
}
this.clearCache=function(){
_221={};
};
function doLoad(_229,http,url,_230,_231){
if((http.status==200)||(location.protocol=="file:"&&http.status==0)){
var ret;
if(_229.method.toLowerCase()=="head"){
var _232=http.getAllResponseHeaders();
ret={};
ret.toString=function(){
return _232;
};
var _233=_232.split(/[\r\n]+/g);
for(var i=0;i<_233.length;i++){
var pair=_233[i].match(/^([^:]+)\s*:\s*(.+)$/i);
if(pair){
ret[pair[1]]=pair[2];
}
}
}else{
if(_229.mimetype=="text/javascript"){
try{
ret=dj_eval(http.responseText);
}
catch(e){
dojo.debug(e);
ret=false;
}
}else{
if((_229.mimetype=="application/xml")||(_229.mimetype=="text/xml")){
ret=http.responseXML;
if(!ret||typeof ret=="string"){
ret=dojo.dom.createDocumentFromText(http.responseText);
}
}else{
ret=http.responseText;
}
}
}
if(_231){
addToCache(url,_230,_229.method,http);
}
if(typeof _229.load=="function"){
_229.load("load",ret,http);
}
}else{
var _235=new dojo.io.Error("XMLHttpTransport Error: "+http.status+" "+http.statusText);
if(typeof _229.error=="function"){
_229.error("error",_235,http);
}
}
}
function setHeaders(http,_236){
if(_236["headers"]){
for(var _237 in _236["headers"]){
if(_237.toLowerCase()=="content-type"&&!_236["contentType"]){
_236["contentType"]=_236["headers"][_237];
}else{
http.setRequestHeader(_237,_236["headers"][_237]);
}
}
}
}
this.addToHistory=function(args){
var _238=args["back"]||args["backButton"]||args["handle"];
var hash=null;
if(!this.historyIframe){
this.historyIframe=window.frames["djhistory"];
}
if(!this.bookmarkAnchor){
this.bookmarkAnchor=document.createElement("a");
(document.body||document.getElementsByTagName("body")[0]).appendChild(this.bookmarkAnchor);
this.bookmarkAnchor.style.display="none";
}
if((!args["changeUrl"])||(dojo.render.html.ie)){
var url=dojo.hostenv.getBaseScriptUri()+"iframe_history.html?"+(new Date()).getTime();
this.moveForward=true;
dojo.io.setIFrameSrc(this.historyIframe,url,false);
}
if(args["changeUrl"]){
hash="#"+((args["changeUrl"]!==true)?args["changeUrl"]:(new Date()).getTime());
setTimeout("window.location.href = '"+hash+"';",1);
this.bookmarkAnchor.href=hash;
if(dojo.render.html.ie){
var _240=_238;
var lh=null;
var hsl=this.historyStack.length-1;
if(hsl>=0){
while(!this.historyStack[hsl]["urlHash"]){
hsl--;
}
lh=this.historyStack[hsl]["urlHash"];
}
if(lh){
_238=function(){
if(window.location.hash!=""){
setTimeout("window.location.href = '"+lh+"';",1);
}
_240();
};
}
this.forwardStack=[];
var _243=args["forward"]||args["forwardButton"];
var tfw=function(){
if(window.location.hash!=""){
window.location.href=hash;
}
if(_243){
_243();
}
};
if(args["forward"]){
args.forward=tfw;
}else{
if(args["forwardButton"]){
args.forwardButton=tfw;
}
}
}else{
if(dojo.render.html.moz){
if(!this.locationTimer){
this.locationTimer=setInterval("dojo.io.XMLHTTPTransport.checkLocation();",200);
}
}
}
}
this.historyStack.push({"url":url,"callback":_238,"kwArgs":args,"urlHash":hash});
};
this.checkLocation=function(){
var hsl=this.historyStack.length;
if((window.location.hash==this.initialHash)||(window.location.href==this.initialHref)&&(hsl==1)){
this.handleBackButton();
return;
}
if(this.forwardStack.length>0){
if(this.forwardStack[this.forwardStack.length-1].urlHash==window.location.hash){
this.handleForwardButton();
return;
}
}
if((hsl>=2)&&(this.historyStack[hsl-2])){
if(this.historyStack[hsl-2].urlHash==window.location.hash){
this.handleBackButton();
return;
}
}
};
this.iframeLoaded=function(evt,_245){
var isp=_245.href.split("?");
if(isp.length<2){
if(this.historyStack.length==1){
this.handleBackButton();
}
return;
}
var _247=isp[1];
if(this.moveForward){
this.moveForward=false;
return;
}
var last=this.historyStack.pop();
if(!last){
if(this.forwardStack.length>0){
var next=this.forwardStack[this.forwardStack.length-1];
if(_247==next.url.split("?")[1]){
this.handleForwardButton();
}
}
return;
}
this.historyStack.push(last);
if(this.historyStack.length>=2){
if(isp[1]==this.historyStack[this.historyStack.length-2].url.split("?")[1]){
this.handleBackButton();
}
}else{
this.handleBackButton();
}
};
this.handleBackButton=function(){
var last=this.historyStack.pop();
if(!last){
return;
}
if(last["callback"]){
last.callback();
}else{
if(last.kwArgs["backButton"]){
last.kwArgs["backButton"]();
}else{
if(last.kwArgs["back"]){
last.kwArgs["back"]();
}else{
if(last.kwArgs["handle"]){
last.kwArgs.handle("back");
}
}
}
}
this.forwardStack.push(last);
};
this.handleForwardButton=function(){
var last=this.forwardStack.pop();
if(!last){
return;
}
if(last.kwArgs["forward"]){
last.kwArgs.forward();
}else{
if(last.kwArgs["forwardButton"]){
last.kwArgs.forwardButton();
}else{
if(last.kwArgs["handle"]){
last.kwArgs.handle("forward");
}
}
}
this.historyStack.push(last);
};
this.inFlight=[];
this.inFlightTimer=null;
this.startWatchingInFlight=function(){
if(!this.inFlightTimer){
this.inFlightTimer=setInterval("dojo.io.XMLHTTPTransport.watchInFlight();",10);
}
};
this.watchInFlight=function(){
for(var x=this.inFlight.length-1;x>=0;x--){
var tif=this.inFlight[x];
if(!tif){
this.inFlight.splice(x,1);
continue;
}
if(4==tif.http.readyState){
this.inFlight.splice(x,1);
doLoad(tif.req,tif.http,tif.url,tif.query,tif.useCache);
if(this.inFlight.length==0){
clearInterval(this.inFlightTimer);
this.inFlightTimer=null;
}
}
}
};
var _251=dojo.hostenv.getXmlhttpObject()?true:false;
this.canHandle=function(_252){
return _251&&dojo.lang.inArray(_252["mimetype"],["text/plain","text/html","application/xml","text/xml","text/javascript"])&&dojo.lang.inArray(_252["method"].toLowerCase(),["post","get","head"])&&!(_252["formNode"]&&dojo.io.formHasFile(_252["formNode"]));
};
this.bind=function(_253){
if(!_253["url"]){
if(!_253["formNode"]&&(_253["backButton"]||_253["back"]||_253["changeUrl"]||_253["watchForURL"])&&(!djConfig.preventBackButtonFix)){
this.addToHistory(_253);
return true;
}
}
var url=_253.url;
var _254="";
if(_253["formNode"]){
var ta=_253.formNode.getAttribute("action");
if((ta)&&(!_253["url"])){
url=ta;
}
var tp=_253.formNode.getAttribute("method");
if((tp)&&(!_253["method"])){
_253.method=tp;
}
_254+=dojo.io.encodeForm(_253.formNode,_253.encoding);
}
if(!_253["method"]){
_253.method="get";
}
if(_253["content"]){
_254+=dojo.io.argsFromMap(_253.content,_253.encoding);
}
if(_253["postContent"]&&_253.method.toLowerCase()=="post"){
_254=_253.postContent;
}
if(_253["backButton"]||_253["back"]||_253["changeUrl"]){
this.addToHistory(_253);
}
var _257=_253["sync"]?false:true;
var _258=_253["useCache"]==true||(this.useCache==true&&_253["useCache"]!=false);
if(_258){
var _259=getFromCache(url,_254,_253.method);
if(_259){
doLoad(_253,_259,url,_254,false);
return;
}
}
var http=dojo.hostenv.getXmlhttpObject();
var _260=false;
if(_257){
this.inFlight.push({"req":_253,"http":http,"url":url,"query":_254,"useCache":_258});
this.startWatchingInFlight();
}
if(_253.method.toLowerCase()=="post"){
http.open("POST",url,_257);
setHeaders(http,_253);
http.setRequestHeader("Content-Type",_253["contentType"]||"application/x-www-form-urlencoded");
http.send(_254);
}else{
var _261=url;
if(_254!=""){
_261+=(url.indexOf("?")>-1?"&":"?")+_254;
}
http.open(_253.method.toUpperCase(),_261,_257);
setHeaders(http,_253);
http.send(null);
}
if(!_257){
doLoad(_253,http,url,_254,_258);
}
return;
};
dojo.io.transports.addTransport("XMLHTTPTransport");
};
dojo.require("dojo.lang");
dojo.provide("dojo.event");
dojo.event=new function(){
var _262=0;
this.anon={};
this.canTimeout=dojo.lang.isFunction(dj_global["setTimeout"])||dojo.lang.isAlien(dj_global["setTimeout"]);
this.nameAnonFunc=function(_263,_264){
var nso=(_264||this.anon);
if((dj_global["djConfig"])&&(djConfig["slowAnonFuncLookups"]==true)){
for(var x in nso){
if(nso[x]===_263){
dojo.debug(x);
return x;
}
}
}
var ret="__"+_262++;
while(typeof nso[ret]!="undefined"){
ret="__"+_262++;
}
nso[ret]=_263;
return ret;
};
this.createFunctionPair=function(obj,cb){
var ret=[];
if(typeof obj=="function"){
ret[1]=dojo.event.nameAnonFunc(obj,dj_global);
ret[0]=dj_global;
return ret;
}else{
if((typeof obj=="object")&&(typeof cb=="string")){
return [obj,cb];
}else{
if((typeof obj=="object")&&(typeof cb=="function")){
ret[1]=dojo.event.nameAnonFunc(cb,obj);
ret[0]=obj;
return ret;
}
}
}
return null;
};
this.matchSignature=function(args,_266){
var end=Math.min(args.length,_266.length);
for(var x=0;x<end;x++){
if(compareTypes){
if((typeof args[x]).toLowerCase()!=(typeof _266[x])){
return false;
}
}else{
if((typeof args[x]).toLowerCase()!=_266[x].toLowerCase()){
return false;
}
}
}
return true;
};
this.matchSignatureSets=function(args){
for(var x=1;x<arguments.length;x++){
if(this.matchSignature(args,arguments[x])){
return true;
}
}
return false;
};
function interpolateArgs(args){
var ao={srcObj:dj_global,srcFunc:null,adviceObj:dj_global,adviceFunc:null,aroundObj:null,aroundFunc:null,adviceType:(args.length>2)?args[0]:"after",precedence:"last",once:false,delay:null,rate:0};
switch(args.length){
case 0:
return;
case 1:
return;
case 2:
ao.srcFunc=args[0];
ao.adviceFunc=args[1];
break;
case 3:
if((typeof args[0]=="object")&&(typeof args[1]=="string")&&(typeof args[2]=="string")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
}else{
if((typeof args[1]=="string")&&(typeof args[2]=="string")){
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
}else{
if((typeof args[0]=="object")&&(typeof args[1]=="string")&&(typeof args[2]=="function")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
var _269=dojo.event.nameAnonFunc(args[2],ao.adviceObj);
ao.adviceObj[_269]=args[2];
ao.adviceFunc=_269;
}else{
if((typeof args[0]=="function")&&(typeof args[1]=="object")&&(typeof args[2]=="string")){
ao.adviceType="after";
ao.srcObj=dj_global;
var _269=dojo.event.nameAnonFunc(args[0],ao.srcObj);
ao.srcObj[_269]=args[0];
ao.srcFunc=_269;
ao.adviceObj=args[1];
ao.adviceFunc=args[2];
}
}
}
}
break;
case 4:
if((typeof args[0]=="object")&&(typeof args[2]=="object")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
ao.adviceObj=args[2];
ao.adviceFunc=args[3];
}else{
if((typeof args[1]).toLowerCase()=="object"){
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=dj_global;
ao.adviceFunc=args[3];
}else{
if((typeof args[2]).toLowerCase()=="object"){
ao.srcObj=dj_global;
ao.srcFunc=args[1];
ao.adviceObj=args[2];
ao.adviceFunc=args[3];
}else{
ao.srcObj=ao.adviceObj=ao.aroundObj=dj_global;
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
ao.aroundFunc=args[3];
}
}
}
break;
case 6:
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=args[3];
ao.adviceFunc=args[4];
ao.aroundFunc=args[5];
ao.aroundObj=dj_global;
break;
default:
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=args[3];
ao.adviceFunc=args[4];
ao.aroundObj=args[5];
ao.aroundFunc=args[6];
ao.once=args[7];
ao.delay=args[8];
ao.rate=args[9];
break;
}
if((typeof ao.srcFunc).toLowerCase()!="string"){
ao.srcFunc=dojo.lang.getNameInObj(ao.srcObj,ao.srcFunc);
}
if((typeof ao.adviceFunc).toLowerCase()!="string"){
ao.adviceFunc=dojo.lang.getNameInObj(ao.adviceObj,ao.adviceFunc);
}
if((ao.aroundObj)&&((typeof ao.aroundFunc).toLowerCase()!="string")){
ao.aroundFunc=dojo.lang.getNameInObj(ao.aroundObj,ao.aroundFunc);
}
if(!ao.srcObj){
dojo.raise("bad srcObj for srcFunc: "+ao.srcFunc);
}
if(!ao.adviceObj){
dojo.raise("bad adviceObj for adviceFunc: "+ao.adviceFunc);
}
return ao;
}
this.connect=function(){
var ao=interpolateArgs(arguments);
var mjp=dojo.event.MethodJoinPoint.getForMethod(ao.srcObj,ao.srcFunc);
if(ao.adviceFunc){
var mjp2=dojo.event.MethodJoinPoint.getForMethod(ao.adviceObj,ao.adviceFunc);
}
mjp.kwAddAdvice(ao);
return mjp;
};
this.connectBefore=function(){
var args=["before"];
for(var i=0;i<arguments.length;i++){
args.push(arguments[i]);
}
return this.connect.apply(this,args);
};
this.connectAround=function(){
var args=["around"];
for(var i=0;i<arguments.length;i++){
args.push(arguments[i]);
}
return this.connect.apply(this,args);
};
this.kwConnectImpl_=function(_272,_273){
var fn=(_273)?"disconnect":"connect";
if(typeof _272["srcFunc"]=="function"){
_272.srcObj=_272["srcObj"]||dj_global;
var _274=dojo.event.nameAnonFunc(_272.srcFunc,_272.srcObj);
_272.srcFunc=_274;
}
if(typeof _272["adviceFunc"]=="function"){
_272.adviceObj=_272["adviceObj"]||dj_global;
var _274=dojo.event.nameAnonFunc(_272.adviceFunc,_272.adviceObj);
_272.adviceFunc=_274;
}
return dojo.event[fn]((_272["type"]||_272["adviceType"]||"after"),_272["srcObj"]||dj_global,_272["srcFunc"],_272["adviceObj"]||_272["targetObj"]||dj_global,_272["adviceFunc"]||_272["targetFunc"],_272["aroundObj"],_272["aroundFunc"],_272["once"],_272["delay"],_272["rate"]);
};
this.kwConnect=function(_275){
return this.kwConnectImpl_(_275,false);
};
this.disconnect=function(){
var ao=interpolateArgs(arguments);
if(!ao.adviceFunc){
return;
}
var mjp=dojo.event.MethodJoinPoint.getForMethod(ao.srcObj,ao.srcFunc);
return mjp.removeAdvice(ao.adviceObj,ao.adviceFunc,ao.adviceType,ao.once);
};
this.kwDisconnect=function(_276){
return this.kwConnectImpl_(_276,true);
};
};
dojo.event.MethodInvocation=function(_277,obj,args){
this.jp_=_277;
this.object=obj;
this.args=[];
for(var x=0;x<args.length;x++){
this.args[x]=args[x];
}
this.around_index=-1;
};
dojo.event.MethodInvocation.prototype.proceed=function(){
this.around_index++;
if(this.around_index>=this.jp_.around.length){
return this.jp_.object[this.jp_.methodname].apply(this.jp_.object,this.args);
}else{
var ti=this.jp_.around[this.around_index];
var mobj=ti[0]||dj_global;
var meth=ti[1];
return mobj[meth].call(mobj,this);
}
};
dojo.event.MethodJoinPoint=function(obj,_280){
this.object=obj||dj_global;
this.methodname=_280;
this.methodfunc=this.object[_280];
this.before=[];
this.after=[];
this.around=[];
};
dojo.event.MethodJoinPoint.getForMethod=function(obj,_281){
if(!obj){
obj=dj_global;
}
if(!obj[_281]){
obj[_281]=function(){
};
}else{
if((!dojo.lang.isFunction(obj[_281]))&&(!dojo.lang.isAlien(obj[_281]))){
return null;
}
}
var _282=_281+"$joinpoint";
var _283=_281+"$joinpoint$method";
var _284=obj[_282];
if(!_284){
var _285=false;
if(dojo.event["browser"]){
if((obj["attachEvent"])||(obj["nodeType"])||(obj["addEventListener"])){
_285=true;
dojo.event.browser.addClobberNodeAttrs(obj,[_282,_283,_281]);
}
}
obj[_283]=obj[_281];
_284=obj[_282]=new dojo.event.MethodJoinPoint(obj,_283);
obj[_281]=function(){
var args=[];
if((_285)&&(!arguments.length)&&(window.event)){
args.push(dojo.event.browser.fixEvent(window.event));
}else{
for(var x=0;x<arguments.length;x++){
if((x==0)&&(_285)&&(dojo.event.browser.isEvent(arguments[x]))){
args.push(dojo.event.browser.fixEvent(arguments[x]));
}else{
args.push(arguments[x]);
}
}
}
return _284.run.apply(_284,args);
};
}
return _284;
};
dojo.event.MethodJoinPoint.prototype.unintercept=function(){
this.object[this.methodname]=this.methodfunc;
};
dojo.event.MethodJoinPoint.prototype.run=function(){
var obj=this.object||dj_global;
var args=arguments;
var _286=[];
for(var x=0;x<args.length;x++){
_286[x]=args[x];
}
var _287=function(marr){
if(!marr){
dojo.debug("Null argument to unrollAdvice()");
return;
}
var _289=marr[0]||dj_global;
var _290=marr[1];
if(!_289[_290]){
throw new Error("function \""+_290+"\" does not exist on \""+_289+"\"");
}
var _291=marr[2]||dj_global;
var _292=marr[3];
var _293;
var to={args:[],jp_:this,object:obj,proceed:function(){
return _289[_290].apply(_289,to.args);
}};
to.args=_286;
var _295=parseInt(marr[4]);
var _296=((!isNaN(_295))&&(marr[4]!==null)&&(typeof marr[4]!="undefined"));
if(marr[5]){
var rate=parseInt(marr[5]);
var cur=new Date();
var _299=false;
if((marr["last"])&&((cur-marr.last)<=rate)){
if(dojo.event.canTimeout){
if(marr["delayTimer"]){
clearTimeout(marr.delayTimer);
}
var tod=parseInt(rate*2);
var mcpy=dojo.lang.shallowCopy(marr);
marr.delayTimer=setTimeout(function(){
mcpy[5]=0;
_287(mcpy);
},tod);
}
return;
}else{
marr.last=cur;
}
}
if(_292){
_291[_292].call(_291,to);
}else{
if((_296)&&((dojo.render.html)||(dojo.render.svg))){
dj_global["setTimeout"](function(){
_289[_290].apply(_289,args);
},_295);
}else{
_289[_290].apply(_289,args);
}
}
};
if(this.before.length>0){
dojo.lang.forEach(this.before,_287,true);
}
var _302;
if(this.around.length>0){
var mi=new dojo.event.MethodInvocation(this,obj,args);
_302=mi.proceed();
}else{
if(this.methodfunc){
_302=this.object[this.methodname].apply(this.object,args);
}
}
if(this.after.length>0){
dojo.lang.forEach(this.after,_287,true);
}
return (this.methodfunc)?_302:null;
};
dojo.event.MethodJoinPoint.prototype.getArr=function(kind){
var arr=this.after;
if((typeof kind=="string")&&(kind.indexOf("before")!=-1)){
arr=this.before;
}else{
if(kind=="around"){
arr=this.around;
}
}
return arr;
};
dojo.event.MethodJoinPoint.prototype.kwAddAdvice=function(args){
this.addAdvice(args["adviceObj"],args["adviceFunc"],args["aroundObj"],args["aroundFunc"],args["adviceType"],args["precedence"],args["once"],args["delay"],args["rate"]);
};
dojo.event.MethodJoinPoint.prototype.addAdvice=function(_305,_306,_307,_308,_309,_310,once,_312,rate){
var arr=this.getArr(_309);
if(!arr){
dojo.raise("bad this: "+this);
}
var ao=[_305,_306,_307,_308,_312,rate];
if(once){
if(this.hasAdvice(_305,_306,_309,arr)>=0){
return;
}
}
if(_310=="first"){
arr.unshift(ao);
}else{
arr.push(ao);
}
};
dojo.event.MethodJoinPoint.prototype.hasAdvice=function(_313,_314,_315,arr){
if(!arr){
arr=this.getArr(_315);
}
var ind=-1;
for(var x=0;x<arr.length;x++){
if((arr[x][0]==_313)&&(arr[x][1]==_314)){
ind=x;
}
}
return ind;
};
dojo.event.MethodJoinPoint.prototype.removeAdvice=function(_317,_318,_319,once){
var arr=this.getArr(_319);
var ind=this.hasAdvice(_317,_318,_319,arr);
if(ind==-1){
return false;
}
while(ind!=-1){
arr.splice(ind,1);
if(once){
break;
}
ind=this.hasAdvice(_317,_318,_319,arr);
}
return true;
};
dojo.require("dojo.event");
dojo.provide("dojo.event.topic");
dojo.event.topic=new function(){
this.topics={};
this.getTopic=function(_320){
if(!this.topics[_320]){
this.topics[_320]=new this.TopicImpl(_320);
}
return this.topics[_320];
};
this.registerPublisher=function(_321,obj,_322){
var _321=this.getTopic(_321);
_321.registerPublisher(obj,_322);
};
this.subscribe=function(_323,obj,_324){
var _323=this.getTopic(_323);
_323.subscribe(obj,_324);
};
this.unsubscribe=function(_325,obj,_326){
var _325=this.getTopic(_325);
_325.unsubscribe(obj,_326);
};
this.publish=function(_327,_328){
var _327=this.getTopic(_327);
var args=[];
if((arguments.length==2)&&(_328.length)&&(typeof _328!="string")){
args=_328;
}else{
var args=[];
for(var x=1;x<arguments.length;x++){
args.push(arguments[x]);
}
}
_327.sendMessage.apply(_327,args);
};
};
dojo.event.topic.TopicImpl=function(_329){
this.topicName=_329;
var self=this;
self.subscribe=function(_331,_332){
dojo.event.connect("before",self,"sendMessage",_331,_332);
};
self.unsubscribe=function(_333,_334){
dojo.event.disconnect("before",self,"sendMessage",_333,_334);
};
self.registerPublisher=function(_335,_336){
dojo.event.connect(_335,_336,self,"sendMessage");
};
self.sendMessage=function(_337){
};
};
dojo.provide("dojo.event.browser");
dojo.require("dojo.event");
dojo_ie_clobber=new function(){
this.clobberArr=["data","onload","onmousedown","onmouseup","onmouseover","onmouseout","onmousemove","onclick","ondblclick","onfocus","onblur","onkeypress","onkeydown","onkeyup","onsubmit","onreset","onselect","onchange","onselectstart","ondragstart","oncontextmenu"];
this.exclusions=[];
this.clobberList={};
this.clobberNodes=[];
this.addClobberAttr=function(type){
if(dojo.render.html.ie){
if(this.clobberList[type]!="set"){
this.clobberArr.push(type);
this.clobberList[type]="set";
}
}
};
this.addExclusionID=function(id){
this.exclusions.push(id);
};
if(dojo.render.html.ie){
for(var x=0;x<this.clobberArr.length;x++){
this.clobberList[this.clobberArr[x]]="set";
}
}
function nukeProp(node,prop){
try{
node[prop]=null;
}
catch(e){
}
try{
delete node[prop];
}
catch(e){
}
try{
node.removeAttribute(prop);
}
catch(e){
}
}
this.clobber=function(_339){
for(var x=0;x<this.exclusions.length;x++){
try{
var tn=document.getElementById(this.exclusions[x]);
tn.parentNode.removeChild(tn);
}
catch(e){
}
}
var na;
var tna;
if(_339){
tna=_339.getElementsByTagName("*");
na=[_339];
for(var x=0;x<tna.length;x++){
if(!djConfig.ieClobberMinimal){
na.push(tna[x]);
}else{
if(tna[x]["__doClobber__"]){
na.push(tna[x]);
}
}
}
}else{
try{
window.onload=null;
}
catch(e){
}
na=(this.clobberNodes.length)?this.clobberNodes:document.all;
}
tna=null;
var _343={};
for(var i=na.length-1;i>=0;i=i-1){
var el=na[i];
if(djConfig.ieClobberMinimal){
if(el["__clobberAttrs__"]){
for(var j=0;j<el.__clobberAttrs__.length;j++){
nukeProp(el,el.__clobberAttrs__[j]);
}
nukeProp(el,"__clobberAttrs__");
nukeProp(el,"__doClobber__");
}
}else{
for(var p=this.clobberArr.length-1;p>=0;p=p-1){
var ta=this.clobberArr[p];
nukeProp(el,ta);
}
}
}
na=null;
};
};
if((dojo.render.html.ie)&&((!dojo.hostenv.ie_prevent_clobber_)||(djConfig.ieClobberMinimal))){
window.onunload=function(){
dojo_ie_clobber.clobber();
try{
if((dojo["widget"])&&(dojo.widget["manager"])){
dojo.widget.manager.destroyAll();
}
}
catch(e){
}
try{
window.onload=null;
}
catch(e){
}
try{
window.onunload=null;
}
catch(e){
}
dojo_ie_clobber.clobberNodes=[];
};
}
dojo.event.browser=new function(){
var _346=0;
this.clean=function(node){
if(dojo.render.html.ie){
dojo_ie_clobber.clobber(node);
}
};
this.addClobberAttr=function(type){
dojo_ie_clobber.addClobberAttr(type);
};
this.addClobberAttrs=function(){
for(var x=0;x<arguments.length;x++){
this.addClobberAttr(arguments[x]);
}
};
this.addClobberNode=function(node){
if(djConfig.ieClobberMinimal){
if(!node["__doClobber__"]){
node.__doClobber__=true;
dojo_ie_clobber.clobberNodes.push(node);
node.__clobberAttrs__=[];
}
}
};
this.addClobberNodeAttrs=function(node,_347){
this.addClobberNode(node);
if(djConfig.ieClobberMinimal){
for(var x=0;x<_347.length;x++){
node.__clobberAttrs__.push(_347[x]);
}
}else{
this.addClobberAttrs.apply(this,_347);
}
};
this.removeListener=function(node,_348,fp,_349){
if(!_349){
var _349=false;
}
_348=_348.toLowerCase();
if(_348.substr(0,2)=="on"){
_348=_348.substr(2);
}
if(node.removeEventListener){
node.removeEventListener(_348,fp,_349);
}
};
this.addListener=function(node,_350,fp,_351,_352){
if(!node){
return;
}
if(!_351){
var _351=false;
}
_350=_350.toLowerCase();
if(_350.substr(0,2)!="on"){
_350="on"+_350;
}
if(!_352){
var _353=function(evt){
if(!evt){
evt=window.event;
}
var ret=fp(dojo.event.browser.fixEvent(evt));
if(_351){
dojo.event.browser.stopEvent(evt);
}
return ret;
};
}else{
_353=fp;
}
if(node.addEventListener){
node.addEventListener(_350.substr(2),_353,_351);
return _353;
}else{
if(typeof node[_350]=="function"){
var _354=node[_350];
node[_350]=function(e){
_354(e);
return _353(e);
};
}else{
node[_350]=_353;
}
if(dojo.render.html.ie){
this.addClobberNodeAttrs(node,[_350]);
}
return _353;
}
};
this.isEvent=function(obj){
return (typeof Event!="undefined")&&(obj.eventPhase);
};
this.fixEvent=function(evt){
if((!evt)&&(window["event"])){
var evt=window.event;
}
if((evt["type"])&&(evt["type"].indexOf("key")==0)){
var keys={KEY_BACKSPACE:8,KEY_TAB:9,KEY_ENTER:13,KEY_SHIFT:16,KEY_CTRL:17,KEY_ALT:18,KEY_PAUSE:19,KEY_CAPS_LOCK:20,KEY_ESCAPE:27,KEY_SPACE:32,KEY_PAGE_UP:33,KEY_PAGE_DOWN:34,KEY_END:35,KEY_HOME:36,KEY_LEFT_ARROW:37,KEY_UP_ARROW:38,KEY_RIGHT_ARROW:39,KEY_DOWN_ARROW:40,KEY_INSERT:45,KEY_DELETE:46,KEY_LEFT_WINDOW:91,KEY_RIGHT_WINDOW:92,KEY_SELECT:93,KEY_F1:112,KEY_F2:113,KEY_F3:114,KEY_F4:115,KEY_F5:116,KEY_F6:117,KEY_F7:118,KEY_F8:119,KEY_F9:120,KEY_F10:121,KEY_F11:122,KEY_F12:123,KEY_NUM_LOCK:144,KEY_SCROLL_LOCK:145};
evt.keys=[];
for(var key in keys){
evt[key]=keys[key];
evt.keys[keys[key]]=key;
}
if(dojo.render.html.ie&&evt["type"]=="keypress"){
evt.charCode=evt.keyCode;
}
}
if(dojo.render.html.ie){
if(!evt.target){
evt.target=evt.srcElement;
}
if(!evt.currentTarget){
evt.currentTarget=evt.srcElement;
}
if(!evt.layerX){
evt.layerX=evt.offsetX;
}
if(!evt.layerY){
evt.layerY=evt.offsetY;
}
if(evt.fromElement){
evt.relatedTarget=evt.fromElement;
}
if(evt.toElement){
evt.relatedTarget=evt.toElement;
}
evt.callListener=function(_357,_358){
if(typeof _357!="function"){
dojo.raise("listener not a function: "+_357);
}
evt.currentTarget=_358;
var ret=_357.call(_358,evt);
return ret;
};
evt.stopPropagation=function(){
evt.cancelBubble=true;
};
evt.preventDefault=function(){
evt.returnValue=false;
};
}
return evt;
};
this.stopEvent=function(ev){
if(window.event){
ev.returnValue=false;
ev.cancelBubble=true;
}else{
ev.preventDefault();
ev.stopPropagation();
}
};
};
dojo.hostenv.conditionalLoadModule({common:["dojo.event","dojo.event.topic"],browser:["dojo.event.browser"]});
dojo.hostenv.moduleLoaded("dojo.event.*");
dojo.provide("dojo.alg.Alg");
dojo.require("dojo.lang");
dj_deprecated("dojo.alg.Alg is deprecated, use dojo.lang instead");
dojo.alg.find=function(arr,val){
return dojo.lang.find(arr,val);
};
dojo.alg.inArray=function(arr,val){
return dojo.lang.inArray(arr,val);
};
dojo.alg.inArr=dojo.alg.inArray;
dojo.alg.getNameInObj=function(ns,item){
return dojo.lang.getNameInObj(ns,item);
};
dojo.alg.has=function(obj,name){
return dojo.lang.has(obj,name);
};
dojo.alg.forEach=function(arr,_360,_361){
return dojo.lang.forEach(arr,_360,_361);
};
dojo.alg.for_each=dojo.alg.forEach;
dojo.alg.map=function(arr,obj,_362){
return dojo.lang.map(arr,obj,_362);
};
dojo.alg.tryThese=function(){
return dojo.lang.tryThese.apply(dojo.lang,arguments);
};
dojo.alg.delayThese=function(farr,cb,_363,_364){
return dojo.lang.delayThese.apply(dojo.lang,arguments);
};
dojo.alg.for_each_call=dojo.alg.map;
dojo.require("dojo.alg.Alg",false,true);
dojo.hostenv.moduleLoaded("dojo.alg.*");
dojo.provide("dojo.uri.Uri");
dojo.uri=new function(){
this.joinPath=function(){
var arr=[];
for(var i=0;i<arguments.length;i++){
arr.push(arguments[i]);
}
return arr.join("/").replace(/\/{2,}/g,"/").replace(/((https*|ftps*):)/i,"$1/");
};
this.dojoUri=function(uri){
return new dojo.uri.Uri(dojo.hostenv.getBaseScriptUri(),uri);
};
this.Uri=function(){
var uri=arguments[0];
for(var i=1;i<arguments.length;i++){
if(!arguments[i]){
continue;
}
var _365=new dojo.uri.Uri(arguments[i].toString());
var _366=new dojo.uri.Uri(uri.toString());
if(_365.path==""&&_365.scheme==null&&_365.authority==null&&_365.query==null){
if(_365.fragment!=null){
_366.fragment=_365.fragment;
}
_365=_366;
}else{
if(_365.scheme==null){
_365.scheme=_366.scheme;
if(_365.authority==null){
_365.authority=_366.authority;
if(_365.path.charAt(0)!="/"){
var path=_366.path.substring(0,_366.path.lastIndexOf("/")+1)+_365.path;
var segs=path.split("/");
for(var j=0;j<segs.length;j++){
if(segs[j]=="."){
if(j==segs.length-1){
segs[j]="";
}else{
segs.splice(j,1);
j--;
}
}else{
if(j>0&&!(j==1&&segs[0]=="")&&segs[j]==".."&&segs[j-1]!=".."){
if(j==segs.length-1){
segs.splice(j,1);
segs[j-1]="";
}else{
segs.splice(j-1,2);
j-=2;
}
}
}
}
_365.path=segs.join("/");
}
}
}
}
uri="";
if(_365.scheme!=null){
uri+=_365.scheme+":";
}
if(_365.authority!=null){
uri+="//"+_365.authority;
}
uri+=_365.path;
if(_365.query!=null){
uri+="?"+_365.query;
}
if(_365.fragment!=null){
uri+="#"+_365.fragment;
}
}
this.uri=uri.toString();
var _369="^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\\?([^#]*))?(#(.*))?$";
var r=this.uri.match(new RegExp(_369));
this.scheme=r[2]||(r[1]?"":null);
this.authority=r[4]||(r[3]?"":null);
this.path=r[5];
this.query=r[7]||(r[6]?"":null);
this.fragment=r[9]||(r[8]?"":null);
if(this.authority!=null){
_369="^((([^:]+:)?([^@]+))@)?([^:]*)(:([0-9]+))?$";
r=this.authority.match(new RegExp(_369));
this.user=r[3]||null;
this.password=r[4]||null;
this.host=r[5];
this.port=r[7]||null;
}
this.toString=function(){
return this.uri;
};
};
};
dojo.provide("dojo.math");
dojo.math.degToRad=function(x){
return (x*Math.PI)/180;
};
dojo.math.radToDeg=function(x){
return (x*180)/Math.PI;
};
dojo.math.factorial=function(n){
if(n<1){
return 0;
}
var _371=1;
for(var i=1;i<=n;i++){
_371*=i;
}
return _371;
};
dojo.math.permutations=function(n,k){
if(n==0||k==0){
return 1;
}
return (dojo.math.factorial(n)/dojo.math.factorial(n-k));
};
dojo.math.combinations=function(n,r){
if(n==0||r==0){
return 1;
}
return (dojo.math.factorial(n)/(dojo.math.factorial(n-r)*dojo.math.factorial(r)));
};
dojo.math.bernstein=function(t,n,i){
return (dojo.math.combinations(n,i)*Math.pow(t,i)*Math.pow(1-t,n-i));
};
dojo.math.gaussianRandom=function(){
var k=2;
do{
var i=2*Math.random()-1;
var j=2*Math.random()-1;
k=i*i+j*j;
}while(k>=1);
k=Math.sqrt((-2*Math.log(k))/k);
return i*k;
};
dojo.math.mean=function(){
var _373=dojo.lang.isArray(arguments[0])?arguments[0]:arguments;
var mean=0;
for(var i=0;i<_373.length;i++){
mean+=_373[i];
}
return mean/_373.length;
};
dojo.math.round=function(_375,_376){
if(!_376){
var _377=1;
}else{
var _377=Math.pow(10,_376);
}
return Math.round(_375*_377)/_377;
};
dojo.math.sd=function(){
var _378=dojo.lang.isArray(arguments[0])?arguments[0]:arguments;
return Math.sqrt(dojo.math.variance(_378));
};
dojo.math.variance=function(){
var _379=dojo.lang.isArray(arguments[0])?arguments[0]:arguments;
var mean=0,squares=0;
for(var i=0;i<_379.length;i++){
mean+=_379[i];
squares+=Math.pow(_379[i],2);
}
return (squares/_379.length)-Math.pow(mean/_379.length,2);
};
dojo.provide("dojo.graphics.color");
dojo.require("dojo.lang");
dojo.require("dojo.math");
dojo.graphics.color.Color=function(r,g,b,a){
if(dojo.lang.isArray(r)){
this.r=r[0];
this.g=r[1];
this.b=r[2];
this.a=r[3]||1;
}else{
if(dojo.lang.isString(r)){
var rgb=dojo.graphics.color.extractRGB(r);
this.r=rgb[0];
this.g=rgb[1];
this.b=rgb[2];
this.a=g||1;
}else{
if(r instanceof dojo.graphics.color.Color){
this.r=r.r;
this.b=r.b;
this.g=r.g;
this.a=r.a;
}else{
this.r=r;
this.g=g;
this.b=b;
this.a=a;
}
}
}
};
dojo.graphics.color.Color.prototype.toRgb=function(_383){
if(_383){
return this.toRgba();
}else{
return [this.r,this.g,this.b];
}
};
dojo.graphics.color.Color.prototype.toRgba=function(){
return [this.r,this.g,this.b,this.a];
};
dojo.graphics.color.Color.prototype.toHex=function(){
return dojo.graphics.color.rgb2hex(this.toRgb());
};
dojo.graphics.color.Color.prototype.toCss=function(){
return "rgb("+this.toRgb().join()+")";
};
dojo.graphics.color.Color.prototype.toString=function(){
return this.toHex();
};
dojo.graphics.color.Color.prototype.toHsv=function(){
return dojo.graphics.color.rgb2hsv(this.toRgb());
};
dojo.graphics.color.Color.prototype.toHsl=function(){
return dojo.graphics.color.rgb2hsl(this.toRgb());
};
dojo.graphics.color.Color.prototype.blend=function(_384,_385){
return dojo.graphics.color.blend(this.toRgb(),new Color(_384).toRgb(),_385);
};
dojo.graphics.color.named={white:[255,255,255],black:[0,0,0],red:[255,0,0],green:[0,255,0],blue:[0,0,255],navy:[0,0,128],gray:[128,128,128],silver:[192,192,192]};
dojo.graphics.color.blend=function(a,b,_386){
if(typeof a=="string"){
return dojo.graphics.color.blendHex(a,b,_386);
}
if(!_386){
_386=0;
}else{
if(_386>1){
_386=1;
}else{
if(_386<-1){
_386=-1;
}
}
}
var c=new Array(3);
for(var i=0;i<3;i++){
var half=Math.abs(a[i]-b[i])/2;
c[i]=Math.floor(Math.min(a[i],b[i])+half+(half*_386));
}
return c;
};
dojo.graphics.color.blendHex=function(a,b,_389){
return dojo.graphics.color.rgb2hex(dojo.graphics.color.blend(dojo.graphics.color.hex2rgb(a),dojo.graphics.color.hex2rgb(b),_389));
};
dojo.graphics.color.extractRGB=function(_390){
var hex="0123456789abcdef";
_390=_390.toLowerCase();
if(_390.indexOf("rgb")==0){
dojo.debug("e1");
var _392=_390.match(/rgba*\((\d+), *(\d+), *(\d+)/i);
var ret=_392.splice(1,3);
return ret;
}else{
var _393=dojo.graphics.color.hex2rgb(_390);
if(_393){
return _393;
}else{
return dojo.graphics.color.named[_390]||[255,255,255];
}
}
};
dojo.graphics.color.hex2rgb=function(hex){
var _394="0123456789ABCDEF";
var rgb=new Array(3);
if(hex.indexOf("#")==0){
hex=hex.substring(1);
}
hex=hex.toUpperCase();
if(hex.replace(new RegExp("["+_394+"]","g"),"")!=""){
return null;
}
if(hex.length==3){
rgb[0]=hex.charAt(0)+hex.charAt(0);
rgb[1]=hex.charAt(1)+hex.charAt(1);
rgb[2]=hex.charAt(2)+hex.charAt(2);
}else{
rgb[0]=hex.substring(0,2);
rgb[1]=hex.substring(2,4);
rgb[2]=hex.substring(4);
}
for(var i=0;i<rgb.length;i++){
rgb[i]=_394.indexOf(rgb[i].charAt(0))*16+_394.indexOf(rgb[i].charAt(1));
}
return rgb;
};
dojo.graphics.color.rgb2hex=function(r,g,b){
if(dojo.lang.isArray(r)){
g=r[1]||"00";
b=r[2]||"00";
r=r[0]||"00";
}
r="00"+r.toString(16);
g="00"+g.toString(16);
b="00"+b.toString(16);
return ["#",r.substr(-2,2),g.substr(-2,2),b.substr(-2,2)].join("");
};
dojo.graphics.color.rgb2hsv=function(r,g,b){
if(dojo.lang.isArray(r)){
b=r[2]||0;
g=r[1]||0;
r=r[0]||0;
}
var h=null;
var s=null;
var v=null;
var min=Math.min(r,g,b);
v=Math.max(r,g,b);
var _398=v-min;
s=(v==0)?0:_398/v;
if(s==0){
h=0;
}else{
if(r==v){
h=60*(g-b)/_398;
}else{
if(g==v){
h=120+60*(b-r)/_398;
}else{
if(b==v){
h=240+60*(r-g)/_398;
}
}
}
if(h<0){
h+=360;
}
}
h=(h==0)?360:Math.ceil((h/360)*255);
s=Math.ceil(s*255);
return [h,s,v];
};
dojo.graphics.color.hsv2rgb=function(h,s,v){
if(dojo.lang.isArray(h)){
v=h[2]||0;
s=h[1]||0;
h=h[0]||0;
}
h=(h/255)*360;
if(h==360){
h=0;
}
s=s/255;
v=v/255;
var r=null;
var g=null;
var b=null;
if(s==0){
r=v;
g=v;
b=v;
}else{
var _399=h/60;
var i=Math.floor(_399);
var f=_399-i;
var p=v*(1-s);
var q=v*(1-(s*f));
var t=v*(1-(s*(1-f)));
switch(i){
case 0:
r=v;
g=t;
b=p;
break;
case 1:
r=q;
g=v;
b=p;
break;
case 2:
r=p;
g=v;
b=t;
break;
case 3:
r=p;
g=q;
b=v;
break;
case 4:
r=t;
g=p;
b=v;
break;
case 5:
r=v;
g=p;
b=q;
break;
}
}
r=Math.ceil(r*255);
g=Math.ceil(g*255);
b=Math.ceil(b*255);
return [r,g,b];
};
dojo.graphics.color.rgb2hsl=function(r,g,b){
if(dojo.lang.isArray(r)){
b=r[2]||0;
g=r[1]||0;
r=r[0]||0;
}
r/=255;
g/=255;
b/=255;
var h=null;
var s=null;
var l=null;
var min=Math.min(r,g,b);
var max=Math.max(r,g,b);
var _403=max-min;
l=(min+max)/2;
s=0;
if((l>0)&&(l<1)){
s=_403/((l<0.5)?(2*l):(2-2*l));
}
h=0;
if(_403>0){
if((max==r)&&(max!=g)){
h+=(g-b)/_403;
}
if((max==g)&&(max!=b)){
h+=(2+(b-r)/_403);
}
if((max==b)&&(max!=r)){
h+=(4+(r-g)/_403);
}
h*=60;
}
h=(h==0)?360:Math.ceil((h/360)*255);
s=Math.ceil(s*255);
l=Math.ceil(l*255);
return [h,s,l];
};
dojo.graphics.color.hsl2rgb=function(h,s,l){
if(dojo.lang.isArray(h)){
l=h[2]||0;
s=h[1]||0;
h=h[0]||0;
}
h=(h/255)*360;
if(h==360){
h=0;
}
s=s/255;
l=l/255;
while(h<0){
h+=360;
}
while(h>360){
h-=360;
}
if(h<120){
r=(120-h)/60;
g=h/60;
b=0;
}else{
if(h<240){
r=0;
g=(240-h)/60;
b=(h-120)/60;
}else{
r=(h-240)/60;
g=0;
b=(360-h)/60;
}
}
r=Math.min(r,1);
g=Math.min(g,1);
b=Math.min(b,1);
r=2*s*r+(1-s);
g=2*s*g+(1-s);
b=2*s*b+(1-s);
if(l<0.5){
r=l*r;
g=l*g;
b=l*b;
}else{
r=(1-l)*r+2*l-1;
g=(1-l)*g+2*l-1;
b=(1-l)*b+2*l-1;
}
r=Math.ceil(r*255);
g=Math.ceil(g*255);
b=Math.ceil(b*255);
return [r,g,b];
};
dojo.provide("dojo.style");
dojo.require("dojo.dom");
dojo.require("dojo.uri.Uri");
dojo.require("dojo.graphics.color");
dojo.style.boxSizing={marginBox:"margin-box",borderBox:"border-box",paddingBox:"padding-box",contentBox:"content-box"};
dojo.style.getBoxSizing=function(node){
if(dojo.render.html.ie||dojo.render.html.opera){
var cm=document["compatMode"];
if(cm=="BackCompat"||cm=="QuirksMode"){
return dojo.style.boxSizing.borderBox;
}else{
return dojo.style.boxSizing.contentBox;
}
}else{
if(arguments.length==0){
node=document.documentElement;
}
var _405=dojo.style.getStyle(node,"-moz-box-sizing");
if(!_405){
_405=dojo.style.getStyle(node,"box-sizing");
}
return (_405?_405:dojo.style.boxSizing.contentBox);
}
};
dojo.style.isBorderBox=function(node){
return (dojo.style.getBoxSizing(node)==dojo.style.boxSizing.borderBox);
};
dojo.style.getUnitValue=function(_406,_407,_408){
var _409={value:0,units:"px"};
var s=dojo.style.getComputedStyle(_406,_407);
if(s==""||(s=="auto"&&_408)){
return _409;
}
if(dojo.lang.isUndefined(s)){
_409.value=NaN;
}else{
var _410=s.match(/([\d.]+)([a-z%]*)/i);
if(!_410){
_409.value=NaN;
}else{
_409.value=Number(_410[1]);
_409.units=_410[2].toLowerCase();
}
}
return _409;
};
dojo.style.getPixelValue=function(_411,_412,_413){
var _414=dojo.style.getUnitValue(_411,_412,_413);
if(isNaN(_414.value)||(_414.value&&_414.units!="px")){
return NaN;
}
return _414.value;
};
dojo.style.getNumericStyle=dojo.style.getPixelValue;
dojo.style.isPositionAbsolute=function(node){
return (dojo.style.getComputedStyle(node,"position")=="absolute");
};
dojo.style.getMarginWidth=function(node){
var _415=dojo.style.isPositionAbsolute(node);
var left=dojo.style.getPixelValue(node,"margin-left",_415);
var _417=dojo.style.getPixelValue(node,"margin-right",_415);
return left+_417;
};
dojo.style.getBorderWidth=function(node){
var left=(dojo.style.getStyle(node,"border-left-style")=="none"?0:dojo.style.getPixelValue(node,"border-left-width"));
var _418=(dojo.style.getStyle(node,"border-right-style")=="none"?0:dojo.style.getPixelValue(node,"border-right-width"));
return left+_418;
};
dojo.style.getPaddingWidth=function(node){
var left=dojo.style.getPixelValue(node,"padding-left",true);
var _419=dojo.style.getPixelValue(node,"padding-right",true);
return left+_419;
};
dojo.style.getContentWidth=function(node){
return node.offsetWidth-dojo.style.getPaddingWidth(node)-dojo.style.getBorderWidth(node);
};
dojo.style.getInnerWidth=function(node){
return node.offsetWidth;
};
dojo.style.getOuterWidth=function(node){
return dojo.style.getInnerWidth(node)+dojo.style.getMarginWidth(node);
};
dojo.style.setOuterWidth=function(node,_420){
if(!dojo.style.isBorderBox(node)){
_420-=dojo.style.getPaddingWidth(node)+dojo.style.getBorderWidth(node);
}
_420-=dojo.style.getMarginWidth(node);
if(!isNaN(_420)&&_420>0){
node.style.width=_420+"px";
return true;
}else{
return false;
}
};
dojo.style.getContentBoxWidth=dojo.style.getContentWidth;
dojo.style.getBorderBoxWidth=dojo.style.getInnerWidth;
dojo.style.getMarginBoxWidth=dojo.style.getOuterWidth;
dojo.style.setMarginBoxWidth=dojo.style.setOuterWidth;
dojo.style.getMarginHeight=function(node){
var _421=dojo.style.isPositionAbsolute(node);
var top=dojo.style.getPixelValue(node,"margin-top",_421);
var _423=dojo.style.getPixelValue(node,"margin-bottom",_421);
return top+_423;
};
dojo.style.getBorderHeight=function(node){
var top=(dojo.style.getStyle(node,"border-top-style")=="none"?0:dojo.style.getPixelValue(node,"border-top-width"));
var _424=(dojo.style.getStyle(node,"border-bottom-style")=="none"?0:dojo.style.getPixelValue(node,"border-bottom-width"));
return top+_424;
};
dojo.style.getPaddingHeight=function(node){
var top=dojo.style.getPixelValue(node,"padding-top",true);
var _425=dojo.style.getPixelValue(node,"padding-bottom",true);
return top+_425;
};
dojo.style.getContentHeight=function(node){
return node.offsetHeight-dojo.style.getPaddingHeight(node)-dojo.style.getBorderHeight(node);
};
dojo.style.getInnerHeight=function(node){
return node.offsetHeight;
};
dojo.style.getOuterHeight=function(node){
return dojo.style.getInnerHeight(node)+dojo.style.getMarginHeight(node);
};
dojo.style.setOuterHeight=function(node,_426){
if(!dojo.style.isBorderBox(node)){
_426-=dojo.style.getPaddingHeight(node)+dojo.style.getBorderHeight(node);
}
_426-=dojo.style.getMarginHeight(node);
if(!isNaN(_426)&&_426>0){
node.style.height=_426+"px";
return true;
}else{
return false;
}
};
dojo.style.getContentBoxHeight=dojo.style.getContentHeight;
dojo.style.getBorderBoxHeight=dojo.style.getInnerHeight;
dojo.style.getMarginBoxHeight=dojo.style.getOuterHeight;
dojo.style.setMarginBoxHeight=dojo.style.setOuterHeight;
dojo.style.getTotalOffset=function(node,type,_427){
var _428=(type=="top")?"offsetTop":"offsetLeft";
var _429=(type=="top")?"scrollTop":"scrollLeft";
var alt=(type=="top")?"y":"x";
var ret=0;
if(node["offsetParent"]){
if(_427){
ret-=dojo.style.sumAncestorProperties(node,_429);
}
do{
ret+=node[_428];
node=node.offsetParent;
}while(node!=document.getElementsByTagName("body")[0].parentNode&&node!=null);
}else{
if(node[alt]){
ret+=node[alt];
}
}
return ret;
};
dojo.style.sumAncestorProperties=function(node,prop){
if(!node){
return 0;
}
var _431=0;
while(node){
var val=node[prop];
if(val){
_431+=val-0;
}
node=node.parentNode;
}
return _431;
};
dojo.style.totalOffsetLeft=function(node,_432){
return dojo.style.getTotalOffset(node,"left",_432);
};
dojo.style.getAbsoluteX=dojo.style.totalOffsetLeft;
dojo.style.totalOffsetTop=function(node,_433){
return dojo.style.getTotalOffset(node,"top",_433);
};
dojo.style.getAbsoluteY=dojo.style.totalOffsetTop;
dojo.style.styleSheet=null;
dojo.style.insertCssRule=function(_434,_435,_436){
if(!dojo.style.styleSheet){
if(document.createStyleSheet){
dojo.style.styleSheet=document.createStyleSheet();
}else{
if(document.styleSheets[0]){
dojo.style.styleSheet=document.styleSheets[0];
}else{
return null;
}
}
}
if(arguments.length<3){
if(dojo.style.styleSheet.cssRules){
_436=dojo.style.styleSheet.cssRules.length;
}else{
if(dojo.style.styleSheet.rules){
_436=dojo.style.styleSheet.rules.length;
}else{
return null;
}
}
}
if(dojo.style.styleSheet.insertRule){
var rule=_434+" { "+_435+" }";
return dojo.style.styleSheet.insertRule(rule,_436);
}else{
if(dojo.style.styleSheet.addRule){
return dojo.style.styleSheet.addRule(_434,_435,_436);
}else{
return null;
}
}
};
dojo.style.removeCssRule=function(_438){
if(!dojo.style.styleSheet){
dojo.debug("no stylesheet defined for removing rules");
return false;
}
if(dojo.render.html.ie){
if(!_438){
_438=dojo.style.styleSheet.rules.length;
dojo.style.styleSheet.removeRule(_438);
}
}else{
if(document.styleSheets[0]){
if(!_438){
_438=dojo.style.styleSheet.cssRules.length;
}
dojo.style.styleSheet.deleteRule(_438);
}
}
return true;
};
dojo.style.insertCssFile=function(URI,doc,_441){
if(!URI){
return;
}
if(!doc){
doc=document;
}
if(doc.baseURI){
URI=new dojo.uri.Uri(doc.baseURI,URI);
}
if(_441&&doc.styleSheets){
var loc=location.href.split("#")[0].substring(0,location.href.indexOf(location.pathname));
for(var i=0;i<doc.styleSheets.length;i++){
if(doc.styleSheets[i].href&&URI.toString()==new dojo.uri.Uri(doc.styleSheets[i].href.toString())){
return;
}
}
}
var file=doc.createElement("link");
file.setAttribute("type","text/css");
file.setAttribute("rel","stylesheet");
file.setAttribute("href",URI);
var head=doc.getElementsByTagName("head")[0];
if(head){
head.appendChild(file);
}
};
dojo.style.getBackgroundColor=function(node){
var _445;
do{
_445=dojo.style.getStyle(node,"background-color");
if(_445.toLowerCase()=="rgba(0, 0, 0, 0)"){
_445="transparent";
}
if(node==document.getElementsByTagName("body")[0]){
node=null;
break;
}
node=node.parentNode;
}while(node&&dojo.lang.inArray(_445,["transparent",""]));
if(_445=="transparent"){
_445=[255,255,255,0];
}else{
_445=dojo.graphics.color.extractRGB(_445);
}
return _445;
};
dojo.style.getComputedStyle=function(_446,_447,_448){
var _449=_448;
if(_446.style.getPropertyValue){
_449=_446.style.getPropertyValue(_447);
}
if(!_449){
if(document.defaultView){
_449=document.defaultView.getComputedStyle(_446,"").getPropertyValue(_447);
}else{
if(_446.currentStyle){
_449=_446.currentStyle[dojo.style.toCamelCase(_447)];
}
}
}
return _449;
};
dojo.style.getStyle=function(_450,_451){
var _452=dojo.style.toCamelCase(_451);
var _453=_450.style[_452];
return (_453?_453:dojo.style.getComputedStyle(_450,_451,_453));
};
dojo.style.toCamelCase=function(_454){
var arr=_454.split("-"),cc=arr[0];
for(var i=1;i<arr.length;i++){
cc+=arr[i].charAt(0).toUpperCase()+arr[i].substring(1);
}
return cc;
};
dojo.style.toSelectorCase=function(_455){
return _455.replace(/([A-Z])/g,"-$1").toLowerCase();
};
dojo.style.setOpacity=function setOpacity(node,_456,_457){
var h=dojo.render.html;
if(!_457){
if(_456>=1){
if(h.ie){
dojo.style.clearOpacity(node);
return;
}else{
_456=0.999999;
}
}else{
if(_456<0){
_456=0;
}
}
}
if(h.ie){
if(node.nodeName.toLowerCase()=="tr"){
var tds=node.getElementsByTagName("td");
for(var x=0;x<tds.length;x++){
tds[x].style.filter="Alpha(Opacity="+_456*100+")";
}
}
node.style.filter="Alpha(Opacity="+_456*100+")";
}else{
if(h.moz){
node.style.opacity=_456;
node.style.MozOpacity=_456;
}else{
if(h.safari){
node.style.opacity=_456;
node.style.KhtmlOpacity=_456;
}else{
node.style.opacity=_456;
}
}
}
};
dojo.style.getOpacity=function getOpacity(node){
if(dojo.render.html.ie){
var opac=(node.filters&&node.filters.alpha&&typeof node.filters.alpha.opacity=="number"?node.filters.alpha.opacity:100)/100;
}else{
var opac=node.style.opacity||node.style.MozOpacity||node.style.KhtmlOpacity||1;
}
return opac>=0.999999?1:Number(opac);
};
dojo.style.clearOpacity=function clearOpacity(node){
var h=dojo.render.html;
if(h.ie){
if(node.filters&&node.filters.alpha){
node.style.filter="";
}
}else{
if(h.moz){
node.style.opacity=1;
node.style.MozOpacity=1;
}else{
if(h.safari){
node.style.opacity=1;
node.style.KhtmlOpacity=1;
}else{
node.style.opacity=1;
}
}
}
};
dojo.provide("dojo.html");
dojo.require("dojo.dom");
dojo.require("dojo.style");
dojo.require("dojo.string");
dojo.lang.mixin(dojo.html,dojo.dom);
dojo.lang.mixin(dojo.html,dojo.style);
dojo.html.clearSelection=function(){
try{
if(window.getSelection){
window.getSelection().removeAllRanges();
}else{
if(document.selection&&document.selection.clear){
document.selection.clear();
}
}
}
catch(e){
dojo.debug(e);
}
};
dojo.html.disableSelection=function(_460){
if(arguments.length==0){
_460=dojo.html.body();
}
if(dojo.render.html.mozilla){
_460.style.MozUserSelect="none";
}else{
if(dojo.render.html.safari){
_460.style.KhtmlUserSelect="none";
}else{
if(dojo.render.html.ie){
_460.unselectable="on";
}
}
}
};
dojo.html.enableSelection=function(_461){
if(arguments.length==0){
_461=dojo.html.body();
}
if(dojo.render.html.mozilla){
_461.style.MozUserSelect="";
}else{
if(dojo.render.html.safari){
_461.style.KhtmlUserSelect="";
}else{
if(dojo.render.html.ie){
_461.unselectable="off";
}
}
}
};
dojo.html.selectElement=function(_462){
if(document.selection&&dojo.html.body().createTextRange){
var _463=dojo.html.body().createTextRange();
_463.moveToElementText(_462);
_463.select();
}else{
if(window.getSelection){
var _464=window.getSelection();
if(_464.selectAllChildren){
_464.selectAllChildren(_462);
}
}
}
};
dojo.html.isSelectionCollapsed=function(){
if(document.selection){
return document.selection.createRange().text=="";
}else{
if(window.getSelection){
var _465=window.getSelection();
if(dojo.lang.isString(_465)){
return _465=="";
}else{
return _465.isCollapsed;
}
}
}
};
dojo.html.getEventTarget=function(evt){
if((window["event"])&&(window.event["srcElement"])){
return window.event.srcElement;
}else{
if((evt)&&(evt.target)){
return evt.target;
}
}
};
dojo.html.getScrollTop=function(){
return document.documentElement.scrollTop||dojo.html.body().scrollTop||0;
};
dojo.html.getScrollLeft=function(){
return document.documentElement.scrollLeft||dojo.html.body().scrollLeft||0;
};
dojo.html.getDocumentWidth=function(){
var _466=document.documentElement;
var _467=_466?_466.clientWidth:0;
var body=dojo.html.body();
var _469=body?body.clientWidth:0;
if(dojo.lang.isNumber(window.innerWidth)){
return window.innerWidth;
}else{
if(_467&&_469){
return Math.min(_467,_469);
}else{
return _467||_469||0;
}
}
};
dojo.html.getDocumentHeight=function(){
var _470=document.documentElement;
var _471=_470?_470.clientHeight:0;
var body=dojo.html.body();
var _472=body?body.clientHeight:0;
if(dojo.lang.isNumber(window.innerHeight)){
return window.innerHeight;
}else{
if(_471&&_472){
return Math.min(_471,_472);
}else{
return _471||_472||0;
}
}
};
dojo.html.getDocumentSize=function(){
return [dojo.html.getDocumentWidth(),dojo.html.getDocumentHeight()];
};
dojo.html.getParentOfType=function(node,type){
var _473=node;
type=type.toLowerCase();
while(_473.nodeName.toLowerCase()!=type){
if((!_473)||(_473==(document["body"]||document["documentElement"]))){
return null;
}
_473=_473.parentNode;
}
return _473;
};
dojo.html.getAttribute=function(node,attr){
if((!node)||(!node.getAttribute)){
return null;
}
var ta=typeof attr=="string"?attr:new String(attr);
var v=node.getAttribute(ta.toUpperCase());
if((v)&&(typeof v=="string")&&(v!="")){
return v;
}
if(v&&typeof v=="object"&&v.value){
return v.value;
}
if((node.getAttributeNode)&&(node.getAttributeNode(ta))){
return (node.getAttributeNode(ta)).value;
}else{
if(node.getAttribute(ta)){
return node.getAttribute(ta);
}else{
if(node.getAttribute(ta.toLowerCase())){
return node.getAttribute(ta.toLowerCase());
}
}
}
return null;
};
dojo.html.hasAttribute=function(node,attr){
var v=dojo.html.getAttribute(node,attr);
return v?true:false;
};
dojo.html.getClass=function(node){
if(node.className){
return node.className;
}else{
if(dojo.html.hasAttribute(node,"class")){
return dojo.html.getAttribute(node,"class");
}
}
return "";
};
dojo.html.hasClass=function(node,_475){
var _476=dojo.html.getClass(node).split(/\s+/g);
for(var x=0;x<_476.length;x++){
if(_475==_476[x]){
return true;
}
}
return false;
};
dojo.html.prependClass=function(node,_477){
if(!node){
return null;
}
if(dojo.html.hasAttribute(node,"class")||node.className){
_477+=" "+(node.className||dojo.html.getAttribute(node,"class"));
}
return dojo.html.setClass(node,_477);
};
dojo.html.addClass=function(node,_478){
if(!node){
throw new Error("addClass: node does not exist");
}
if(dojo.html.hasAttribute(node,"class")||node.className){
_478=(node.className||dojo.html.getAttribute(node,"class"))+" "+_478;
}
return dojo.html.setClass(node,_478);
};
dojo.html.setClass=function(node,_479){
if(!node){
return false;
}
var cs=new String(_479);
try{
if(typeof node.className=="string"){
node.className=cs;
}else{
if(node.setAttribute){
node.setAttribute("class",_479);
node.className=cs;
}else{
return false;
}
}
}
catch(e){
dojo.debug("__util__.setClass() failed",e);
}
return true;
};
dojo.html.removeClass=function(node,_481){
if(!node){
return false;
}
var _481=dojo.string.trim(new String(_481));
try{
var cs=String(node.className).split(" ");
var nca=[];
for(var i=0;i<cs.length;i++){
if(cs[i]!=_481){
nca.push(cs[i]);
}
}
node.className=nca.join(" ");
}
catch(e){
dojo.debug("__util__.removeClass() failed",e);
}
return true;
};
dojo.html.classMatchType={ContainsAll:0,ContainsAny:1,IsOnly:2};
dojo.html.getElementsByClass=function(_483,_484,_485,_486){
if(!_484){
_484=document;
}
var _487=_483.split(/\s+/g);
var _488=[];
if(_486!=1&&_486!=2){
_486=0;
}
if(false&&document.evaluate){
var _489="//"+(_485||"*")+"[contains(";
if(_486!=dojo.html.classMatchType.ContainsAny){
_489+="concat(' ',@class,' '), ' "+_487.join(" ') and contains(concat(' ',@class,' '), ' ")+" ')]";
}else{
_489+="concat(' ',@class,' '), ' "+_487.join(" ')) or contains(concat(' ',@class,' '), ' ")+" ')]";
}
var _490=document.evaluate(_489,_484,null,XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,null);
outer:
for(var node=null,i=0;node=_490.snapshotItem(i);i++){
if(_486!=dojo.html.classMatchType.IsOnly){
_488.push(node);
}else{
if(!dojo.html.getClass(node)){
continue outer;
}
var _491=dojo.html.getClass(node).split(/\s+/g);
var _492=new RegExp("(\\s|^)("+_487.join(")|(")+")(\\s|$)");
for(var j=0;j<_491.length;j++){
if(!_491[j].match(_492)){
continue outer;
}
}
_488.push(node);
}
}
}else{
if(!_485){
_485="*";
}
var _493=_484.getElementsByTagName(_485);
outer:
for(var i=0;i<_493.length;i++){
var node=_493[i];
if(!dojo.html.getClass(node)){
continue outer;
}
var _491=dojo.html.getClass(node).split(/\s+/g);
var _492=new RegExp("(\\s|^)(("+_487.join(")|(")+"))(\\s|$)");
var _494=0;
for(var j=0;j<_491.length;j++){
if(_492.test(_491[j])){
if(_486==dojo.html.classMatchType.ContainsAny){
_488.push(node);
continue outer;
}else{
_494++;
}
}else{
if(_486==dojo.html.classMatchType.IsOnly){
continue outer;
}
}
}
if(_494==_487.length){
if(_486==dojo.html.classMatchType.IsOnly&&_494==_491.length){
_488.push(node);
}else{
if(_486==dojo.html.classMatchType.ContainsAll){
_488.push(node);
}
}
}
}
}
return _488;
};
dojo.html.gravity=function(node,e){
var _495=e.pageX||e.clientX+dojo.html.body().scrollLeft;
var _496=e.pageY||e.clientY+dojo.html.body().scrollTop;
with(dojo.html){
var _497=getAbsoluteX(node)+(getInnerWidth(node)/2);
var _498=getAbsoluteY(node)+(getInnerHeight(node)/2);
}
with(dojo.html.gravity){
return ((_495<_497?WEST:EAST)|(_496<_498?NORTH:SOUTH));
}
};
dojo.html.gravity.NORTH=1;
dojo.html.gravity.SOUTH=1<<1;
dojo.html.gravity.EAST=1<<2;
dojo.html.gravity.WEST=1<<3;
dojo.html.overElement=function(_499,e){
var _500=e.pageX||e.clientX+dojo.html.body().scrollLeft;
var _501=e.pageY||e.clientY+dojo.html.body().scrollTop;
with(dojo.html){
var top=getAbsoluteY(_499);
var _502=top+getInnerHeight(_499);
var left=getAbsoluteX(_499);
var _503=left+getInnerWidth(_499);
}
return (_500>=left&&_500<=_503&&_501>=top&&_501<=_502);
};
dojo.html.renderedTextContent=function(node){
var _504="";
if(node==null){
return _504;
}
for(var i=0;i<node.childNodes.length;i++){
switch(node.childNodes[i].nodeType){
case 1:
case 5:
switch(dojo.style.getStyle(node.childNodes[i],"display")){
case "block":
case "list-item":
case "run-in":
case "table":
case "table-row-group":
case "table-header-group":
case "table-footer-group":
case "table-row":
case "table-column-group":
case "table-column":
case "table-cell":
case "table-caption":
_504+="\n";
_504+=dojo.html.renderedTextContent(node.childNodes[i]);
_504+="\n";
break;
case "none":
break;
default:
_504+=dojo.html.renderedTextContent(node.childNodes[i]);
break;
}
break;
case 3:
case 2:
case 4:
var text=node.childNodes[i].nodeValue;
switch(dojo.style.getStyle(node,"text-transform")){
case "capitalize":
text=dojo.string.capitalize(text);
break;
case "uppercase":
text=text.toUpperCase();
break;
case "lowercase":
text=text.toLowerCase();
break;
default:
break;
}
switch(dojo.style.getStyle(node,"text-transform")){
case "nowrap":
break;
case "pre-wrap":
break;
case "pre-line":
break;
case "pre":
break;
default:
text=text.replace(/\s+/," ");
if(/\s$/.test(_504)){
text.replace(/^\s/,"");
}
break;
}
_504+=text;
break;
default:
break;
}
}
return _504;
};
dojo.html.setActiveStyleSheet=function(_505){
var i,a,main;
for(i=0;(a=document.getElementsByTagName("link")[i]);i++){
if(a.getAttribute("rel").indexOf("style")!=-1&&a.getAttribute("title")){
a.disabled=true;
if(a.getAttribute("title")==_505){
a.disabled=false;
}
}
}
};
dojo.html.getActiveStyleSheet=function(){
var i,a;
for(i=0;(a=document.getElementsByTagName("link")[i]);i++){
if(a.getAttribute("rel").indexOf("style")!=-1&&a.getAttribute("title")&&!a.disabled){
return a.getAttribute("title");
}
}
return null;
};
dojo.html.getPreferredStyleSheet=function(){
var i,a;
for(i=0;(a=document.getElementsByTagName("link")[i]);i++){
if(a.getAttribute("rel").indexOf("style")!=-1&&a.getAttribute("rel").indexOf("alt")==-1&&a.getAttribute("title")){
return a.getAttribute("title");
}
}
return null;
};
dojo.html.body=function(){
return document.body||document.getElementsByTagName("body")[0];
};
dojo.html.createNodesFromText=function(txt,wrap){
var tn=document.createElement("div");
tn.style.visibility="hidden";
document.body.appendChild(tn);
tn.innerHTML=txt;
tn.normalize();
if(wrap){
var ret=[];
var fc=tn.firstChild;
ret[0]=((fc.nodeValue==" ")||(fc.nodeValue=="\t"))?fc.nextSibling:fc;
document.body.removeChild(tn);
return ret;
}
var _509=[];
for(var x=0;x<tn.childNodes.length;x++){
_509.push(tn.childNodes[x].cloneNode(true));
}
tn.style.display="none";
document.body.removeChild(tn);
return _509;
};
if(!dojo.evalObjPath("dojo.dom.createNodesFromText")){
dojo.dom.createNodesFromText=function(){
dojo.deprecated("dojo.dom.createNodesFromText","use dojo.html.createNodesFromText instead");
return dojo.html.createNodesFromText.apply(dojo.html,arguments);
};
}
dojo.provide("dojo.math.curves");
dojo.require("dojo.math");
dojo.math.curves={Line:function(_510,end){
this.start=_510;
this.end=end;
this.dimensions=_510.length;
for(var i=0;i<_510.length;i++){
_510[i]=Number(_510[i]);
}
for(var i=0;i<end.length;i++){
end[i]=Number(end[i]);
}
this.getValue=function(n){
var _511=new Array(this.dimensions);
for(var i=0;i<this.dimensions;i++){
_511[i]=((this.end[i]-this.start[i])*n)+this.start[i];
}
return _511;
};
return this;
},Bezier:function(pnts){
this.getValue=function(step){
if(step>=1){
return this.p[this.p.length-1];
}
if(step<=0){
return this.p[0];
}
var _514=new Array(this.p[0].length);
for(var k=0;j<this.p[0].length;k++){
_514[k]=0;
}
for(var j=0;j<this.p[0].length;j++){
var C=0;
var D=0;
for(var i=0;i<this.p.length;i++){
C+=this.p[i][j]*this.p[this.p.length-1][0]*dojo.math.bernstein(step,this.p.length,i);
}
for(var l=0;l<this.p.length;l++){
D+=this.p[this.p.length-1][0]*dojo.math.bernstein(step,this.p.length,l);
}
_514[j]=C/D;
}
return _514;
};
this.p=pnts;
return this;
},CatmullRom:function(pnts,c){
this.getValue=function(step){
var _517=step*(this.p.length-1);
var node=Math.floor(_517);
var _518=_517-node;
var i0=node-1;
if(i0<0){
i0=0;
}
var i=node;
var i1=node+1;
if(i1>=this.p.length){
i1=this.p.length-1;
}
var i2=node+2;
if(i2>=this.p.length){
i2=this.p.length-1;
}
var u=_518;
var u2=_518*_518;
var u3=_518*_518*_518;
var _525=new Array(this.p[0].length);
for(var k=0;k<this.p[0].length;k++){
var x1=(-this.c*this.p[i0][k])+((2-this.c)*this.p[i][k])+((this.c-2)*this.p[i1][k])+(this.c*this.p[i2][k]);
var x2=(2*this.c*this.p[i0][k])+((this.c-3)*this.p[i][k])+((3-2*this.c)*this.p[i1][k])+(-this.c*this.p[i2][k]);
var x3=(-this.c*this.p[i0][k])+(this.c*this.p[i1][k]);
var x4=this.p[i][k];
_525[k]=x1*u3+x2*u2+x3*u+x4;
}
return _525;
};
if(!c){
this.c=0.7;
}else{
this.c=c;
}
this.p=pnts;
return this;
},Arc:function(_530,end,ccw){
var _532=dojo.math.points.midpoint(_530,end);
var _533=dojo.math.points.translate(dojo.math.points.invert(_532),_530);
var rad=Math.sqrt(Math.pow(_533[0],2)+Math.pow(_533[1],2));
var _535=dojo.math.radToDeg(Math.atan(_533[1]/_533[0]));
if(_533[0]<0){
_535-=90;
}else{
_535+=90;
}
dojo.math.curves.CenteredArc.call(this,_532,rad,_535,_535+(ccw?-180:180));
},CenteredArc:function(_536,_537,_538,end){
this.center=_536;
this.radius=_537;
this.start=_538||0;
this.end=end;
this.getValue=function(n){
var _539=new Array(2);
var _540=dojo.math.degToRad(this.start+((this.end-this.start)*n));
_539[0]=this.center[0]+this.radius*Math.sin(_540);
_539[1]=this.center[1]-this.radius*Math.cos(_540);
return _539;
};
return this;
},Circle:function(_541,_542){
dojo.math.curves.CenteredArc.call(this,_541,_542,0,360);
return this;
},Path:function(){
var _543=[];
var _544=[];
var _545=[];
var _546=0;
this.add=function(_547,_548){
if(_548<0){
dojo.raise("dojo.math.curves.Path.add: weight cannot be less than 0");
}
_543.push(_547);
_544.push(_548);
_546+=_548;
computeRanges();
};
this.remove=function(_549){
for(var i=0;i<_543.length;i++){
if(_543[i]==_549){
_543.splice(i,1);
_546-=_544.splice(i,1)[0];
break;
}
}
computeRanges();
};
this.removeAll=function(){
_543=[];
_544=[];
_546=0;
};
this.getValue=function(n){
var _550=false,value=0;
for(var i=0;i<_545.length;i++){
var r=_545[i];
if(n>=r[0]&&n<r[1]){
var subN=(n-r[0])/r[2];
value=_543[i].getValue(subN);
_550=true;
break;
}
}
if(!_550){
value=_543[_543.length-1].getValue(1);
}
for(j=0;j<i;j++){
value=dojo.math.points.translate(value,_543[j].getValue(1));
}
return value;
};
function computeRanges(){
var _552=0;
for(var i=0;i<_544.length;i++){
var end=_552+_544[i]/_546;
var len=end-_552;
_545[i]=[_552,end,len];
_552=end;
}
}
return this;
}};
dojo.provide("dojo.animation");
dojo.provide("dojo.animation.Animation");
dojo.require("dojo.math");
dojo.require("dojo.math.curves");
dojo.animation={};
dojo.animation.Animation=function(_553,_554,_555,_556){
var _557=this;
this.curve=_553;
this.duration=_554;
this.repeatCount=_556||0;
this.animSequence_=null;
if(_555){
if(dojo.lang.isFunction(_555.getValue)){
this.accel=_555;
}else{
var i=0.35*_555+0.5;
this.accel=new dojo.math.curves.CatmullRom([[0],[i],[1]],0.45);
}
}
this.onBegin=null;
this.onAnimate=null;
this.onEnd=null;
this.onPlay=null;
this.onPause=null;
this.onStop=null;
this.handler=null;
var _558=null,endTime=null,lastFrame=null,timer=null,percent=0,active=false,paused=false;
this.play=function(_559){
if(_559){
clearTimeout(timer);
active=false;
paused=false;
percent=0;
}else{
if(active&&!paused){
return;
}
}
_558=new Date().valueOf();
if(paused){
_558-=(_557.duration*percent/100);
}
endTime=_558+_557.duration;
lastFrame=_558;
var e=new dojo.animation.AnimationEvent(_557,null,_557.curve.getValue(percent),_558,_558,endTime,_557.duration,percent,0);
active=true;
paused=false;
if(percent==0){
e.type="begin";
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onBegin=="function"){
_557.onBegin(e);
}
}
e.type="play";
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onPlay=="function"){
_557.onPlay(e);
}
if(this.animSequence_){
this.animSequence_.setCurrent(this);
}
cycle();
};
this.pause=function(){
clearTimeout(timer);
if(!active){
return;
}
paused=true;
var e=new dojo.animation.AnimationEvent(_557,"pause",_557.curve.getValue(percent),_558,new Date().valueOf(),endTime,_557.duration,percent,0);
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onPause=="function"){
_557.onPause(e);
}
};
this.playPause=function(){
if(!active||paused){
_557.play();
}else{
_557.pause();
}
};
this.gotoPercent=function(pct,_561){
clearTimeout(timer);
active=true;
paused=true;
percent=pct;
if(_561){
this.play();
}
};
this.stop=function(_562){
clearTimeout(timer);
var step=percent/100;
if(_562){
step=1;
}
var e=new dojo.animation.AnimationEvent(_557,"stop",_557.curve.getValue(step),_558,new Date().valueOf(),endTime,_557.duration,percent,Math.round(fps));
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onStop=="function"){
_557.onStop(e);
}
active=false;
paused=false;
};
this.status=function(){
if(active){
return paused?"paused":"playing";
}else{
return "stopped";
}
};
function cycle(){
clearTimeout(timer);
if(active){
var curr=new Date().valueOf();
var step=(curr-_558)/(endTime-_558);
fps=1000/(curr-lastFrame);
lastFrame=curr;
if(step>=1){
step=1;
percent=100;
}else{
percent=step*100;
}
if(_557.accel&&_557.accel.getValue){
step=_557.accel.getValue(step);
}
var e=new dojo.animation.AnimationEvent(_557,"animate",_557.curve.getValue(step),_558,curr,endTime,_557.duration,percent,Math.round(fps));
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onAnimate=="function"){
_557.onAnimate(e);
}
if(step<1){
timer=setTimeout(cycle,10);
}else{
e.type="end";
active=false;
if(typeof _557.handler=="function"){
_557.handler(e);
}
if(typeof _557.onEnd=="function"){
_557.onEnd(e);
}
if(_557.repeatCount>0){
_557.repeatCount--;
_557.play(true);
}else{
if(_557.repeatCount==-1){
_557.play(true);
}else{
if(_557.animSequence_){
_557.animSequence_.playNext();
}
}
}
}
}
}
};
dojo.animation.AnimationEvent=function(anim,type,_564,_565,_566,_567,dur,pct,fps){
this.type=type;
this.animation=anim;
this.coords=_564;
this.x=_564[0];
this.y=_564[1];
this.z=_564[2];
this.startTime=_565;
this.currentTime=_566;
this.endTime=_567;
this.duration=dur;
this.percent=pct;
this.fps=fps;
this.coordsAsInts=function(){
var _570=new Array(this.coords.length);
for(var i=0;i<this.coords.length;i++){
_570[i]=Math.round(this.coords[i]);
}
return _570;
};
return this;
};
dojo.animation.AnimationSequence=function(_571){
var _572=[];
var _573=-1;
this.repeatCount=_571||0;
this.onBegin=null;
this.onEnd=null;
this.onNext=null;
this.handler=null;
this.add=function(){
for(var i=0;i<arguments.length;i++){
_572.push(arguments[i]);
arguments[i].animSequence_=this;
}
};
this.remove=function(anim){
for(var i=0;i<_572.length;i++){
if(_572[i]==anim){
_572[i].animSequence_=null;
_572.splice(i,1);
break;
}
}
};
this.removeAll=function(){
for(var i=0;i<_572.length;i++){
_572[i].animSequence_=null;
}
_572=[];
_573=-1;
};
this.play=function(_574){
if(_572.length==0){
return;
}
if(_574||!_572[_573]){
_573=0;
}
if(_572[_573]){
if(_573==0){
var e={type:"begin",animation:_572[_573]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onBegin=="function"){
this.onBegin(e);
}
}
_572[_573].play(_574);
}
};
this.pause=function(){
if(_572[_573]){
_572[_573].pause();
}
};
this.playPause=function(){
if(_572.length==0){
return;
}
if(_573==-1){
_573=0;
}
if(_572[_573]){
_572[_573].playPause();
}
};
this.stop=function(){
if(_572[_573]){
_572[_573].stop();
}
};
this.status=function(){
if(_572[_573]){
return _572[_573].status();
}else{
return "stopped";
}
};
this.setCurrent=function(anim){
for(var i=0;i<_572.length;i++){
if(_572[i]==anim){
_573=i;
break;
}
}
};
this.playNext=function(){
if(_573==-1||_572.length==0){
return;
}
_573++;
if(_572[_573]){
var e={type:"next",animation:_572[_573]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onNext=="function"){
this.onNext(e);
}
_572[_573].play(true);
}else{
var e={type:"end",animation:_572[_572.length-1]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onEnd=="function"){
this.onEnd(e);
}
if(this.repeatCount>0){
_573=0;
this.repeatCount--;
_572[_573].play(true);
}else{
if(this.repeatCount==-1){
_573=0;
_572[_573].play(true);
}else{
_573=-1;
}
}
}
};
};
dojo.hostenv.conditionalLoadModule({common:["dojo.animation.Animation",false,false]});
dojo.hostenv.moduleLoaded("dojo.animation.*");
dojo.provide("dojo.fx.html");
dojo.require("dojo.html");
dojo.require("dojo.style");
dojo.require("dojo.lang");
dojo.require("dojo.animation.*");
dojo.require("dojo.event.*");
dojo.require("dojo.graphics.color");
dojo.fx.html.fadeOut=function(node,_575,_576){
return dojo.fx.html.fade(node,_575,dojo.style.getOpacity(node),0,_576);
};
dojo.fx.html.fadeIn=function(node,_577,_578){
return dojo.fx.html.fade(node,_577,dojo.style.getOpacity(node),1,_578);
};
dojo.fx.html.fadeHide=function(node,_579,_580){
if(!_579){
_579=150;
}
return dojo.fx.html.fadeOut(node,_579,function(node){
node.style.display="none";
if(typeof _580=="function"){
_580(node);
}
});
};
dojo.fx.html.fadeShow=function(node,_581,_582){
if(!_581){
_581=150;
}
node.style.display="block";
return dojo.fx.html.fade(node,_581,0,1,_582);
};
dojo.fx.html.fade=function(node,_583,_584,_585,_586){
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([_584],[_585]),_583,0);
dojo.event.connect(anim,"onAnimate",function(e){
dojo.style.setOpacity(node,e.x);
});
if(_586){
dojo.event.connect(anim,"onEnd",function(e){
_586(node,anim);
});
}
anim.play(true);
return anim;
};
dojo.fx.html.slideTo=function(node,_587,_588,_589){
return dojo.fx.html.slide(node,[node.offsetLeft,node.offsetTop],_587,_588,_589);
};
dojo.fx.html.slideBy=function(node,_590,_591,_592){
return dojo.fx.html.slideTo(node,[node.offsetLeft+_590[0],node.offsetTop+_590[1]],_591,_592);
};
dojo.fx.html.slide=function(node,_593,_594,_595,_596){
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_593,_594),_595,0);
dojo.event.connect(anim,"onAnimate",function(e){
with(node.style){
left=e.x+"px";
top=e.y+"px";
}
});
if(_596){
dojo.event.connect(anim,"onEnd",function(e){
_596(node,anim);
});
}
anim.play(true);
return anim;
};
dojo.fx.html.colorFadeIn=function(node,_597,_598,_599,_600){
var _601=dojo.html.getBackgroundColor(node);
var bg=dojo.style.getStyle(node,"background-color").toLowerCase();
var _603=bg=="transparent"||bg=="rgba(0, 0, 0, 0)";
while(_601.length>3){
_601.pop();
}
var rgb=new dojo.graphics.color.Color(_597).toRgb();
var anim=dojo.fx.html.colorFade(node,_597,_601,_598,_600,true);
dojo.event.connect(anim,"onEnd",function(e){
if(_603){
node.style.backgroundColor="transparent";
}
});
if(_599>0){
node.style.backgroundColor="rgb("+rgb.join(",")+")";
setTimeout(function(){
anim.play(true);
},_599);
}else{
anim.play(true);
}
return anim;
};
dojo.fx.html.highlight=dojo.fx.html.colorFadeIn;
dojo.fx.html.colorFadeFrom=dojo.fx.html.colorFadeIn;
dojo.fx.html.colorFadeOut=function(node,_604,_605,_606,_607){
var _608=new dojo.graphics.color.Color(dojo.html.getBackgroundColor(node)).toRgb();
var rgb=new dojo.graphics.color.Color(_604).toRgb();
var anim=dojo.fx.html.colorFade(node,_608,rgb,_605,_607,_606>0);
if(_606>0){
node.style.backgroundColor="rgb("+_608.join(",")+")";
setTimeout(function(){
anim.play(true);
},_606);
}
return anim;
};
dojo.fx.html.unhighlight=dojo.fx.html.colorFadeOut;
dojo.fx.html.colorFadeTo=dojo.fx.html.colorFadeOut;
dojo.fx.html.colorFade=function(node,_609,_610,_611,_612,_613){
var _614=new dojo.graphics.color.Color(_609).toRgb();
var _615=new dojo.graphics.color.Color(_610).toRgb();
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_614,_615),_611,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.backgroundColor="rgb("+e.coordsAsInts().join(",")+")";
});
if(_612){
dojo.event.connect(anim,"onEnd",function(e){
_612(node,anim);
});
}
if(!_613){
anim.play(true);
}
return anim;
};
dojo.fx.html.wipeIn=function(node,_616,_617,_618){
var _619=dojo.html.getStyle(node,"height");
var _620=dojo.lang.inArray(node.tagName.toLowerCase(),["tr","td","th"])?"":"block";
node.style.display=_620;
var _621=node.offsetHeight;
var anim=dojo.fx.html.wipeInToHeight(node,_616,_621,function(e){
node.style.height=_619||"auto";
if(_617){
_617(node,anim);
}
},_618);
};
dojo.fx.html.wipeInToHeight=function(node,_622,_623,_624,_625){
var _626=dojo.html.getStyle(node,"overflow");
node.style.display="none";
node.style.height=0;
if(_626=="visible"){
node.style.overflow="hidden";
}
var _627=dojo.lang.inArray(node.tagName.toLowerCase(),["tr","td","th"])?"":"block";
node.style.display=_627;
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([0],[_623]),_622,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.height=Math.round(e.x)+"px";
});
dojo.event.connect(anim,"onEnd",function(e){
if(_626!="visible"){
node.style.overflow=_626;
}
if(_624){
_624(node,anim);
}
});
if(!_625){
anim.play(true);
}
return anim;
};
dojo.fx.html.wipeOut=function(node,_628,_629,_630){
var _631=dojo.html.getStyle(node,"overflow");
var _632=dojo.html.getStyle(node,"height");
var _633=node.offsetHeight;
node.style.overflow="hidden";
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([_633],[0]),_628,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.height=Math.round(e.x)+"px";
});
dojo.event.connect(anim,"onEnd",function(e){
node.style.display="none";
node.style.overflow=_631;
node.style.height=_632||"auto";
if(_629){
_629(node,anim);
}
});
if(!_630){
anim.play(true);
}
return anim;
};
dojo.fx.html.explode=function(_634,_635,_636,_637){
var _638=[dojo.html.getAbsoluteX(_634),dojo.html.getAbsoluteY(_634),dojo.html.getInnerWidth(_634),dojo.html.getInnerHeight(_634)];
return dojo.fx.html.explodeFromBox(_638,_635,_636,_637);
};
dojo.fx.html.explodeFromBox=function(_639,_640,_641,_642){
var _643=document.createElement("div");
with(_643.style){
position="absolute";
border="1px solid black";
display="none";
}
dojo.html.body().appendChild(_643);
with(_640.style){
visibility="hidden";
display="block";
}
var _644=[dojo.html.getAbsoluteX(_640),dojo.html.getAbsoluteY(_640),dojo.html.getInnerWidth(_640),dojo.html.getInnerHeight(_640)];
with(_640.style){
display="none";
visibility="visible";
}
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_639,_644),_641,0);
dojo.event.connect(anim,"onBegin",function(e){
_643.style.display="block";
});
dojo.event.connect(anim,"onAnimate",function(e){
with(_643.style){
left=e.x+"px";
top=e.y+"px";
width=e.coords[2]+"px";
height=e.coords[3]+"px";
}
});
dojo.event.connect(anim,"onEnd",function(){
_640.style.display="block";
_643.parentNode.removeChild(_643);
if(_642){
_642(_640,anim);
}
});
anim.play();
return anim;
};
dojo.fx.html.implode=function(_645,_646,_647,_648){
var _649=[dojo.html.getAbsoluteX(_646),dojo.html.getAbsoluteY(_646),dojo.html.getInnerWidth(_646),dojo.html.getInnerHeight(_646)];
return dojo.fx.html.implodeToBox(_645,_649,_647,_648);
};
dojo.fx.html.implodeToBox=function(_650,_651,_652,_653){
var _654=document.createElement("div");
with(_654.style){
position="absolute";
border="1px solid black";
display="none";
}
dojo.html.body().appendChild(_654);
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([dojo.html.getAbsoluteX(_650),dojo.html.getAbsoluteY(_650),dojo.html.getInnerWidth(_650),dojo.html.getInnerHeight(_650)],_651),_652,0);
dojo.event.connect(anim,"onBegin",function(e){
_650.style.display="none";
_654.style.display="block";
});
dojo.event.connect(anim,"onAnimate",function(e){
with(_654.style){
left=e.x+"px";
top=e.y+"px";
width=e.coords[2]+"px";
height=e.coords[3]+"px";
}
});
dojo.event.connect(anim,"onEnd",function(){
_654.parentNode.removeChild(_654);
if(_653){
_653(_650,anim);
}
});
anim.play();
return anim;
};
dojo.fx.html.Exploder=function(_655,_656){
var _657=this;
this.waitToHide=500;
this.timeToShow=100;
this.waitToShow=200;
this.timeToHide=70;
this.autoShow=false;
this.autoHide=false;
var _658=null;
var _659=null;
var _660=null;
var _661=null;
var _662=null;
var _663=null;
this.showing=false;
this.onBeforeExplode=null;
this.onAfterExplode=null;
this.onBeforeImplode=null;
this.onAfterImplode=null;
this.onExploding=null;
this.onImploding=null;
this.timeShow=function(){
clearTimeout(_660);
_660=setTimeout(_657.show,_657.waitToShow);
};
this.show=function(){
clearTimeout(_660);
clearTimeout(_661);
if((_659&&_659.status()=="playing")||(_658&&_658.status()=="playing")||_657.showing){
return;
}
if(typeof _657.onBeforeExplode=="function"){
_657.onBeforeExplode(_655,_656);
}
_658=dojo.fx.html.explode(_655,_656,_657.timeToShow,function(e){
_657.showing=true;
if(typeof _657.onAfterExplode=="function"){
_657.onAfterExplode(_655,_656);
}
});
if(typeof _657.onExploding=="function"){
dojo.event.connect(_658,"onAnimate",this,"onExploding");
}
};
this.timeHide=function(){
clearTimeout(_660);
clearTimeout(_661);
if(_657.showing){
_661=setTimeout(_657.hide,_657.waitToHide);
}
};
this.hide=function(){
clearTimeout(_660);
clearTimeout(_661);
if(_658&&_658.status()=="playing"){
return;
}
_657.showing=false;
if(typeof _657.onBeforeImplode=="function"){
_657.onBeforeImplode(_655,_656);
}
_659=dojo.fx.html.implode(_656,_655,_657.timeToHide,function(e){
if(typeof _657.onAfterImplode=="function"){
_657.onAfterImplode(_655,_656);
}
});
if(typeof _657.onImploding=="function"){
dojo.event.connect(_659,"onAnimate",this,"onImploding");
}
};
dojo.event.connect(_655,"onclick",function(e){
if(_657.showing){
_657.hide();
}else{
_657.show();
}
});
dojo.event.connect(_655,"onmouseover",function(e){
if(_657.autoShow){
_657.timeShow();
}
});
dojo.event.connect(_655,"onmouseout",function(e){
if(_657.autoHide){
_657.timeHide();
}
});
dojo.event.connect(_656,"onmouseover",function(e){
clearTimeout(_661);
});
dojo.event.connect(_656,"onmouseout",function(e){
if(_657.autoHide){
_657.timeHide();
}
});
dojo.event.connect(document.documentElement||dojo.html.body(),"onclick",function(e){
if(_657.autoHide&&_657.showing&&!dojo.dom.isDescendantOf(e.target,_656)&&!dojo.dom.isDescendantOf(e.target,_655)){
_657.hide();
}
});
return this;
};
dojo.lang.mixin(dojo.fx,dojo.fx.html);
dojo.hostenv.conditionalLoadModule({browser:["dojo.fx.html"]});
dojo.hostenv.moduleLoaded("dojo.fx.*");
dojo.provide("dojo.graphics.htmlEffects");
dojo.require("dojo.fx.*");
dj_deprecated("dojo.graphics.htmlEffects is deprecated, use dojo.fx.html instead");
dojo.graphics.htmlEffects=dojo.fx.html;
dojo.hostenv.conditionalLoadModule({browser:["dojo.graphics.htmlEffects"]});
dojo.hostenv.moduleLoaded("dojo.graphics.*");

