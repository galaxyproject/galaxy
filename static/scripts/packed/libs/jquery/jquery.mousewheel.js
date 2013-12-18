/* Copyright (c) 2013 Brandon Aaron (http://brandonaaron.net)
 * Licensed under the MIT License (LICENSE.txt).
 *
 * Thanks to: http://adomas.org/javascript-mouse-wheel/ for some pointers.
 * Thanks to: Mathias Bank(http://www.mathias-bank.de) for a scope bug fix.
 * Thanks to: Seamus Leahy for adding deltaX and deltaY
 *
 * Version: 3.1.3
 *
 * Requires: 1.2.2+
 */
(function(a){a(jQuery)}(function(e){var d=["wheel","mousewheel","DOMMouseScroll","MozMousePixelScroll"];var g="onwheel" in document||document.documentMode>=9?["wheel"]:["mousewheel","DomMouseScroll","MozMousePixelScroll"];var f,a;if(e.event.fixHooks){for(var b=d.length;b;){e.event.fixHooks[d[--b]]=e.event.mouseHooks}}e.event.special.mousewheel={setup:function(){if(this.addEventListener){for(var h=g.length;h;){this.addEventListener(g[--h],c,false)}}else{this.onmousewheel=c}},teardown:function(){if(this.removeEventListener){for(var h=g.length;h;){this.removeEventListener(g[--h],c,false)}}else{this.onmousewheel=null}}};e.fn.extend({mousewheel:function(h){return h?this.bind("mousewheel",h):this.trigger("mousewheel")},unmousewheel:function(h){return this.unbind("mousewheel",h)}});function c(h){var i=h||window.event,n=[].slice.call(arguments,1),p=0,k=0,j=0,m=0,l=0,o;h=e.event.fix(i);h.type="mousewheel";if(i.wheelDelta){p=i.wheelDelta}if(i.detail){p=i.detail*-1}if(i.deltaY){j=i.deltaY*-1;p=j}if(i.deltaX){k=i.deltaX;p=k*-1}if(i.wheelDeltaY!==undefined){j=i.wheelDeltaY}if(i.wheelDeltaX!==undefined){k=i.wheelDeltaX*-1}m=Math.abs(p);if(!f||m<f){f=m}l=Math.max(Math.abs(j),Math.abs(k));if(!a||l<a){a=l}o=p>0?"floor":"ceil";p=Math[o](p/f);k=Math[o](k/a);j=Math[o](j/a);n.unshift(h,p,k,j);return(e.event.dispatch||e.event.handle).apply(this,n)}}));