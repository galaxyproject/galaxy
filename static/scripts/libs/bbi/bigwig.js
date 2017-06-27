define(["libs/bbi/spans","libs/bbi/jszlib","libs/bbi/jquery-ajax-native"],function(a,b){"use strict";function c(){}function d(a){a&&(this.id=a)}function e(a,b){return a[b+3]<<24|a[b+2]<<16|a[b+1]<<8|a[b]}function f(a,b,c){Math.pow(10,6);return $.ajax({type:"GET",dataType:"native",url:a,timeout:5e3,beforeSend:function(a){a.setRequestHeader("Range","bytes="+b+"-"+(b+(c-1)))},xhrFields:{responseType:"arraybuffer"}})}function g(a,b){var c=a[b]+a[b+1]*x+a[b+2]*y+a[b+3]*z+a[b+4]*A;return c}function h(){}function i(a,b,c,d){this.bwg=a,this.cirTreeOffset=b,this.cirTreeLength=c,this.isSummary=d}function j(a){var b=$.Deferred(),c=new h;return c.url=a,c.zoom=null,$.when(f(c.url,0,512)).then(function(a){if(!a)return b.resolve(null,"Couldn't fetch file");var d=a,e=new Uint8Array(d),f=new Int16Array(d),h=new Int32Array(d),i=e[0]+x*e[1]+y*e[2]+z*e[3];if(i==q)c.type="bigwig";else{if(i!=s)return i==r||i==t?b.resolve(null,"Currently don't support big-endian BBI files"):b.resolve(null,"Not a supported format, magic=0x"+i.toString(16));c.type="bigbed"}c.version=f[2],c.numZoomLevels=f[3],c.chromTreeOffset=g(e,8),c.unzoomedDataOffset=g(e,16),c.unzoomedIndexOffset=g(e,24),c.fieldCount=f[16],c.definedFieldCount=f[17],c.asOffset=g(e,36),c.totalSummaryOffset=g(e,44),c.uncompressBufSize=h[13],c.extHeaderOffset=g(e,56),c.zoomLevels=[];for(var j=0;j<c.numZoomLevels;++j){var k=h[6*j+16],l=g(e,24*j+72),m=g(e,24*j+80);c.zoomLevels.push({reduction:k,dataOffset:l,indexOffset:m})}$.when(c.readChromTree()).then(function(){c.getAutoSQL(function(a){return c.schema=a,b.resolve(c)})})}),b}function k(a,b,c,d,e){this.bbi=a,this.type=b,this.fieldCount=c,this.offset=d,this.field=e}var l=a.Range,m=a.union,n=a.intersection,o=b.inflateBuffer,p=b.arrayCopy,q=2291137574,r=654086024,s=2273964779,t=3958540679,u=1,v=2,w=3,x=256,y=65536,z=16777216,A=4294967296,B=new RegExp("^[0-9]+,[0-9]+,[0-9]+");return h.prototype.readChromTree=function(){var a=this;this.chromsToIDs={},this.idsToChroms={},this.maxID=0;var b=this.unzoomedDataOffset,c=b-this.chromTreeOffset&3;return b=b+4-c,$.when(f(this.url,this.chromTreeOffset,b-this.chromTreeOffset)).then(function(b){var c=new Uint8Array(b),d=new Int16Array(b),e=new Int32Array(b),f=(e[0],e[1],e[2]),h=(e[3],g(c,16),32),i=function(b){var e=c[b],h=d[b/2+1];b+=4;for(var j=0;h>j;++j)if(0===e){b+=f;var k=g(c,b);b+=8,k-=a.chromTreeOffset,i(k)}else{for(var l="",m=0;f>m;++m){var n=c[b++];0!==n&&(l+=String.fromCharCode(n))}{var o=c[b+3]<<24|c[b+2]<<16|c[b+1]<<8|c[b+0];c[b+7]<<24|c[b+6]<<16|c[b+5]<<8|c[b+4]}b+=8,a.chromsToIDs[l]=o,0===l.indexOf("chr")&&(a.chromsToIDs[l.substr(3)]=o),a.idsToChroms[o]=l,a.maxID=Math.max(a.maxID,o)}};i(h)})},i.prototype.readWigData=function(a,b,c){var d,e=this.bwg.chromsToIDs[a];return d=void 0===e?[]:this.readWigDataById(e,b,c)},i.prototype.readWigDataById=function(a,b,c){var d=this,e=$.Deferred();if(!this.cirHeader)return $.when(f(d.bwg.url,this.cirTreeOffset,48)).then(function(f){d.cirHeader=f;var g=new Int32Array(d.cirHeader);d.cirBlockSize=g[1],$.when(d.readWigDataById(a,b,c)).then(function(a){e.resolve(a)})}),e;var h=[],i=0,j=(Date.now(),function(d,e,f){return(0>a||d==a)&&c>=e&&f>=b}),k=function(a,b){if(d.bwg.instrument&&console.log("level="+b+"; offset="+a+"; time="+(0|Date.now())),i+=a.length,1==a.length&&a[0]-d.cirTreeOffset==48&&d.cachedCirRoot)return o(d.cachedCirRoot,0,b),--i,void(0===i&&$.when(d.fetchFeatures(j,h)).then(function(a){e.resolve(a)}));for(var c,f=4+32*d.cirBlockSize,g=0;g<a.length;++g){var k=new l(a[g],a[g]+f);c=c?m(c,k):k}for(var p=c.ranges(),q=0;q<p.length;++q){var r=p[q];n(a,r,b)}},n=function(a,b,c){b.max()-b.min();$.when(f(d.bwg.url,b.min(),b.max()-b.min())).then(function(f){for(var g=0;g<a.length;++g)b.contains(a[g])&&(o(f,a[g]-b.min(),c),a[g]-d.cirTreeOffset==48&&a[g]-b.min()===0&&(d.cachedCirRoot=f),--i,0===i&&$.when(d.fetchFeatures(j,h)).then(function(a){e.resolve(a)}))})},o=function(d,e,f){var i=new Uint8Array(d),j=new Int16Array(d),l=new Int32Array(d),m=i[e],n=j[e/2+1];if(e+=4,0!==m)for(var o=0;n>o;++o){var p=e/4,q=l[p],r=l[p+1],s=l[p+2],t=l[p+3],u=g(i,e+16),v=g(i,e+24);(0>a||a>q||q==a&&c>=r)&&(0>a||s>a||s==a&&t>=b)&&h.push({offset:u,size:v}),e+=32}else{for(var w=[],o=0;n>o;++o){var p=e/4,q=l[p],r=l[p+1],s=l[p+2],t=l[p+3],u=g(i,e+16);(0>a||a>q||q==a&&c>=r)&&(0>a||s>a||s==a&&t>=b)&&w.push(u),e+=24}w.length>0&&k(w,f+1)}};return k([d.cirTreeOffset+48],1),e},i.prototype.fetchFeatures=function(a,b){var d=this,e=$.Deferred();if(b.sort(function(a,b){return(0|a.offset)-(0|b.offset)}),0===b.length)return[];var g=[],h=function(a,b,e,f){f||(f={});var h=new c;h._chromId=a,h.segment=d.bwg.idsToChroms[a],h.min=b,h.max=e,h.type=d.bwg.type;for(var i in f)h[i]=f[i];g.push(h)},i=function(){if(0===b.length){{Date.now()}return e.resolve(g)}var c=b[0];if(c.data)d.parseFeatures(c.data,h,a),b.splice(0,1),i();else{for(var j=c.offset,k=c.size,l=1;l<b.length&&b[l].offset==j+k;)k+=b[l].size,++l;$.when(f(d.bwg.url,j,k)).then(function(a){for(var c=0,e=0;k>c;){var f,g=b[e];if(d.bwg.uncompressBufSize>0)f=o(a,c+2,g.size-2);else{var h=new Uint8Array(g.size);p(new Uint8Array(a,c,g.size),0,h,0,g.size),f=h.buffer}g.data=f,c+=g.size,++e}i()})}};return i(),e},i.prototype.parseFeatures=function(a,b,c){var e=new Uint8Array(a);if(this.isSummary)for(var f=new Int16Array(a),g=new Int32Array(a),h=new Float32Array(a),i=a.byteLength/32,j=0;i>j;++j){{var k=g[8*j],o=g[8*j+1],p=g[8*j+2],q=g[8*j+3],r=(h[8*j+4],h[8*j+5]),s=h[8*j+6];h[8*j+7]}if(c(k,o+1,p)){var t={type:"bigwig",score:s/q,maxScore:r};"bigbed"==this.bwg.type&&(t.type="density"),b(k,o+1,p,t)}}else if("bigwig"==this.bwg.type){var f=new Int16Array(a),g=new Int32Array(a),h=new Float32Array(a),k=g[0],x=g[1],y=(g[2],g[3]),z=g[4],A=e[20],i=f[11];if(A==w)for(var j=0;i>j;++j){var C=h[j+6],D=x+j*y+1,E=x+j*y+z;c(k,D,E)&&b(k,D,E,{score:C})}else if(A==v)for(var j=0;i>j;++j){var o=g[2*j+6]+1,p=o+z-1,C=h[2*j+7];c(k,o,p)&&b(k,o,p,{score:C})}else if(A==u)for(var j=0;i>j;++j){var o=g[3*j+6]+1,p=g[3*j+7],C=h[3*j+8];o>p&&(o=p),c(k,o,p)&&b(k,o,p,{score:C})}else console.log("Currently not handling bwgType="+A)}else{if("bigbed"!=this.bwg.type)throw Error("Don't know what to do with "+this.bwg.type);for(var F=0,G=this.bwg.definedFieldCount,H=this.bwg.schema;F<e.length;){var k=e[F+3]<<24|e[F+2]<<16|e[F+1]<<8|e[F+0],o=e[F+7]<<24|e[F+6]<<16|e[F+5]<<8|e[F+4],p=e[F+11]<<24|e[F+10]<<16|e[F+9]<<8|e[F+8];F+=12;for(var I="";;){var J=e[F++];if(0==J)break;I+=String.fromCharCode(J)}var K,L={};if(K=I.length>0?I.split("	"):[],K.length>0&&G>3&&(L.label=K[0]),K.length>1&&G>4){var C=parseInt(K[1]);isNaN(C)||(L.score=C)}if(K.length>2&&G>5&&(L.orientation=K[2]),K.length>5&&G>8){var M=K[5];B.test(M)&&(L.itemRgb="rgb("+M+")")}if(K.length>G-3&&H)for(var N=G-3;N<K.length;++N)L[H.fields[N+3].name]=K[N];if(c(k,o+1,p,K))if(12>G)b(k,o+1,p,L);else{var O=0|K[3],P=0|K[4],Q=0|K[6],R=K[7].split(","),S=K[8].split(",");if(L.exonFrames){var T=L.exonFrames.split(",");L.exonFrames=void 0}L.type="transcript";var U=new d;for(var V in L)U[V]=L[V];if(U.id=K[0],U.segment=this.bwg.idsToChroms[k],U.min=o+1,U.max=p,U.notes=[],L.groups=[U],K.length>9){var W=L.geneName||K[9],X=W;K.length>10&&(X=K[10]),L.geneName2&&(X=L.geneName2);var Y=$.extend({},U);Y.id=W,Y.label=X,Y.type="gene",L.groups.push(Y)}for(var Z=[],_=0;Q>_;++_){var aa=(0|S[_])+o,ba=aa+(0|R[_]),ca=new l(aa,ba);Z.push(ca)}for(var da=m(Z),ea=da.ranges(),fa=0;fa<ea.length;++fa){var ga=ea[fa];b(k,ga.min()+1,ga.max(),L)}if(P>O){var ha="+"==L.orientation?new l(O,P+3):new l(O-3,P),ia=n(da,ha);if(ia){L.type="translation";for(var ja=ia.ranges(),ka=0,la=0;ja[0].min()>ea[la].max();)la++;for(var fa=0;fa<ja.length;++fa){var ma=fa;"-"==L.orientation&&(ma=ja.length-fa-1);var ga=ja[ma];if(L.readframe=ka,T){var na=parseInt(T[ma+la]);"number"==typeof na&&na>=0&&2>=na&&(L.readframe=na,L.readframeExplicit=!0)}var oa=ga.max()-ga.min();ka=(ka+oa)%3,b(k,ga.min()+1,ga.max(),L)}}}}}}},i.prototype.getFirstAdjacent=function(a,b,c,d){var e=this.bwg.chromsToIDs[a];return void 0===e?d([]):void this.getFirstAdjacentById(e,b,c,d)},i.prototype.getFirstAdjacentById=function(a,b,c,d){var e=this;if(!this.cirHeader)return void this.bwg.data.slice(this.cirTreeOffset,48).fetch(function(f){e.cirHeader=f;var g=new Int32Array(e.cirHeader);e.cirBlockSize=g[1],e.getFirstAdjacentById(a,b,c,d)});var f=null,h=-1,i=-1,j=0,k=(Date.now(),function(a,b){j+=a.length;for(var c,d=4+32*e.cirBlockSize,f=0;f<a.length;++f){var g=new l(a[f],a[f]+d);c=c?m(c,g):g}for(var h=c.ranges(),i=0;i<h.length;++i){var k=h[i];n(a,k,b)}}),n=function(g,h,i){h.max()-h.min();e.bwg.data.slice(h.min(),h.max()-h.min()).fetch(function(k){for(var l=0;l<g.length;++l)if(h.contains(g[l])&&(o(k,g[l]-h.min(),i),--j,0==j)){if(!f)return c>0&&(0!=a||b>0)?e.getFirstAdjacentById(0,0,c,d):0>c&&(a!=e.bwg.maxID||1e9>b)?e.getFirstAdjacentById(e.bwg.maxID,1e9,c,d):d([]);e.fetchFeatures(function(d,e,f){return 0>c&&(a>d||b>f)||c>0&&(d>a||e>b)},[f],function(a){for(var b=null,e=-1,f=-1,g=0;g<a.length;++g){var h=a[g],i=h._chromId,j=h.min,k=h.max;(null==b||0>c&&(i>e||k>f)||c>0&&(e>i||f>j))&&(b=h,f=0>c?k:j,e=i)}return d(null!=b?[b]:[])})}})},o=function(d,j,l){var m=new Uint8Array(d),n=new Int16Array(d),o=new Int32Array(d),p=m[j],q=n[j/2+1];if(j+=4,0!=p)for(var r=0;q>r;++r){var s=j/4,t=o[s],u=o[s+1],v=o[s+2],w=o[s+3],x=g(m,j+16),y=g(m,j+24);(0>c&&(a>t||t==a&&b>=u)||c>0&&(v>a||v==a&&w>=b))&&(/_random/.exec(e.bwg.idsToChroms[t])||(null==f||0>c&&(v>h||v==h&&w>i)||c>0&&(h>t||t==h&&i>u))&&(f={offset:x,size:y},i=0>c?w:u,h=0>c?v:t)),j+=32}else{for(var z=-1,A=-1,B=-1,r=0;q>r;++r){var s=j/4,t=o[s],u=o[s+1],v=o[s+2],w=o[s+3],x=o[s+4]<<32|o[s+5];(0>c&&(a>t||t==a&&b>=u)&&v>=a||c>0&&(v>a||v==a&&w>=b)&&a>=t)&&(0>z||w>A)&&(z=x,A=0>c?w:u,B=0>c?v:t),j+=24}z>=0&&k([z],l+1)}};k([e.cirTreeOffset+48],1)},h.prototype.readWigData=function(a,b,c){var d;if(null==this.zoom){var e=25e3,f=c-b;if(e>=f||0===this.zoomLevels.length)d=this.getUnzoomedView(),this.zoom=-1;else for(var g=0;g<this.zoomLevels.length;g++)if(g==this.zoomLevels.length-1||f/this.zoomLevels[g].reduction<e){d=this.getZoomedView(g),this.zoom=g;break}}else this.zoom-=1,d=-1==this.zoom?this.getUnzoomedView():this.getZoomedView(this.zoom);return d.readWigData(a,b,c)},h.prototype.getUnzoomedView=function(){if(!this.unzoomedView){var a=4e3,b=this.zoomLevels[0];b&&(a=this.zoomLevels[0].dataOffset-this.unzoomedIndexOffset),this.unzoomedView=new i(this,this.unzoomedIndexOffset,a,!1)}return this.unzoomedView},h.prototype.getZoomedView=function(a){var b=this.zoomLevels[a];return b.view||(b.view=new i(this,b.indexOffset,4e3,!0)),b.view},h.prototype._tsFetch=function(a,b,c,d,e){var f=this;if(!(a>=this.zoomLevels.length-1)){var g;return g=0>a?this.getUnzoomedView():this.getZoomedView(a),g.readWigDataById(b,c,d,e)}if(this.topLevelReductionCache){for(var h=[],i=this.topLevelReductionCache,j=0;j<i.length;++j)i[j]._chromId==b&&h.push(i[j]);return e(h)}this.getZoomedView(this.zoomLevels.length-1).readWigDataById(-1,0,3e8,function(g){return f.topLevelReductionCache=g,f._tsFetch(a,b,c,d,e)})},h.prototype.thresholdSearch=function(a,b,c,d,e){function f(){if(0==i.length)return e(null);i.sort(function(a,b){var d=a.zoom-b.zoom;return 0!=d?d:(d=a.chrOrd-b.chrOrd,0!=d?d:a.min-b.min*c)});var a=i.splice(0,1)[0];g._tsFetch(a.zoom,a.chr,a.min,a.max,function(g){var h=c>0?0:3e8;a.fromRef&&(h=b);for(var j=0;j<g.length;++j){var k,l=g[j];if(k=void 0!=l.maxScore?l.maxScore:l.score,c>0){if(k>d)if(a.zoom<0){if(l.min>h)return e(l)}else l.max>h&&i.push({chr:a.chr,chrOrd:a.chrOrd,zoom:a.zoom-2,min:l.min,max:l.max,fromRef:a.fromRef})}else if(k>d)if(a.zoom<0){if(l.max<h)return e(l)}else l.min<h&&i.push({chr:a.chr,chrOrd:a.chrOrd,zoom:a.zoom-2,min:l.min,max:l.max,fromRef:a.fromRef})}f()})}c=0>c?-1:1;for(var g=this,h=this.chromsToIDs[a],i=[{chrOrd:0,chr:h,zoom:g.zoomLevels.length-4,min:0,max:3e8,fromRef:!0}],j=1;j<=this.maxID+1;++j){var k=(h+c*j)%(this.maxID+1);0>k&&(k+=this.maxID+1),i.push({chrOrd:j,chr:k,zoom:g.zoomLevels.length-1,min:0,max:3e8})}f()},h.prototype.getAutoSQL=function(a){return this.asOffset?void $.when(f(this.url,this.asOffset,2048)).then(function(b){for(var c=new Uint8Array(b),d="",e=0;e<c.length&&0!=c[e];++e)d+=String.fromCharCode(c[e]);var f=/(\w+)\s+(\w+)\s+("([^"]+)")?\s+\(\s*/,g=/([\w\[\]]+)\s+(\w+)\s*;\s*("([^"]+)")?\s*/g,h=f.exec(d);if(h){var i={declType:h[1],name:h[2],comment:h[4],fields:[]};d=d.substring(h[0]);for(var j=g.exec(d);null!=j;j=g.exec(d))i.fields.push({type:j[1],name:j[2],comment:j[4]});return a(i)}}):a(null)},h.prototype.getExtraIndices=function(a){var b=this;return this.version<4||0==this.extHeaderOffset||"bigbed"!=this.type?a(null):void this.data.slice(this.extHeaderOffset,64).fetch(function(c){if(!c)return a(null,"Couldn't fetch extension header");var d=new Uint8Array(c),e=new Int16Array(c),f=(new Int32Array(c),e[0],e[1]),h=g(d,4);return 0==f?a(null):void b.data.slice(h,20*f).fetch(function(c){if(!c)return a(null,"Couldn't fetch index info");for(var d=new Uint8Array(c),e=new Int16Array(c),h=(new Int32Array(c),[]),i=0;f>i;++i){var j=e[10*i],l=e[10*i+1],m=g(d,20*i+4),n=e[10*i+8],o=new k(b,j,l,m,n);h.push(o)}a(h)})})},k.prototype.lookup=function(a,b){var c=this;this.bbi.data.slice(this.offset,32).fetch(function(d){function f(d){c.bbi.data.slice(d,4+j*(k+l)).fetch(function(d){var h=new Uint8Array(d),i=new Uint16Array(d),j=(new Uint32Array(d),h[0]),m=i[1],n=4;if(0!=j){for(var o=0;m>o;++o){for(var p="",q=0;k>q;++q){var r=h[n++];0!=r&&(p+=String.fromCharCode(r))}if(p==a){var s=g(h,n),t=e(h,n+8);return c.bbi.getUnzoomedView().fetchFeatures(function(b,d,e,f){return f&&f.length>c.field-3?f[c.field-3]==a:void 0},[{offset:s,size:t}],b)}n+=l}return b([])}for(var u=null,o=0;m>o;++o){for(var p="",q=0;k>q;++q){var r=h[n++];0!=r&&(p+=String.fromCharCode(r))}var v=g(h,n);if(n+=8,a.localeCompare(p)<0&&u)return void f(u);u=v}f(u)})}var h=new Uint8Array(d),i=(new Int16Array(d),new Int32Array(d)),j=(i[0],i[1]),k=i[2],l=i[3],m=(g(h,16),32);f(c.offset+m)})},{makeBwg:j}});
//# sourceMappingURL=../../../maps/libs/bbi/bigwig.js.map