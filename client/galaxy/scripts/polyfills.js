/*
    Perform feature inference and redirect if below some minimum (must have canvas, etc.)
    and polyfill for non-standard features.
 */
(function() {
    'use strict';
    /*globals window, clearTimeout */

    // ------------------------------------------------------------------ can't/won't polyfill
    // TODO: move to modernizr or something besides us doing this...
    var incompatibilities = [
        { name: 'canvas',           compatible: function(){ return window.CanvasRenderingContext2D; } },
        { name: 'sessionStorage',   compatible: function(){
            try {
                return Number.isInteger( sessionStorage.length );
            } catch( err ){}
            return false;
        }},
    ];
    // build a list of feature names for features that were not found
    incompatibilities = incompatibilities
        .filter( function( feature ){ return !feature.compatible(); })
        .map( function( feature ){ return feature.name; });

    if( !!incompatibilities.length ){
        window.location.href = Galaxy.root + 'static/incompatible-browser.html';
        console.log( 'incompatible browser:\n' + incompatibilities.join( '\n' ) );
    }

    // ------------------------------------------------------------------ polyfills
    // phantomjs: does not have the native extend fn assign
    Object.assign = Object.assign || _.extend;

    // requestAnimationFrame polyfill
    var lastTime = 0;
    var vendors = ['ms', 'moz', 'webkit', 'o'];
    for(var x = 0; x < vendors.length && !window.requestAnimationFrame; ++x) {
        window.requestAnimationFrame = window[vendors[x]+'RequestAnimationFrame'];
        window.cancelRequestAnimationFrame = window[vendors[x]+
          'CancelRequestAnimationFrame'];
    }

    if (!window.requestAnimationFrame)
        window.requestAnimationFrame = function(callback, element) {
            var currTime = new Date().getTime();
            var timeToCall = Math.max(0, 16 - (currTime - lastTime));
            var id = window.setTimeout(function() { callback(currTime + timeToCall); },
              timeToCall);
            lastTime = currTime + timeToCall;
            return id;
        };

    if (!window.cancelAnimationFrame)
        window.cancelAnimationFrame = function(id) {
            clearTimeout(id);
    };

})();
