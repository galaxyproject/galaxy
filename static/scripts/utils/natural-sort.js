define([],function(){function a(a,b){var c=/(-?[0-9\.]+)/g,d=a.toString().toLowerCase()||"",e=b.toString().toLowerCase()||"",f=String.fromCharCode(0),g=d.replace(c,f+"$1"+f).split(f),h=e.replace(c,f+"$1"+f).split(f),i=new Date(d).getTime(),j=i?new Date(e).getTime():null;if(j){if(i<j)return-1;if(i>j)return 1}for(var k,l,m=0,n=Math.max(g.length,h.length);m<n;m++){if(k=parseFloat(g[m])||g[m],l=parseFloat(h[m])||h[m],k<l)return-1;if(k>l)return 1}return 0}return a});
//# sourceMappingURL=../../maps/utils/natural-sort.js.map