/**
    Perform feature inference and redirect if below some minimum (must have canvas, etc.)
    and polyfill for non-standard features.
 */

(function() {
    /* TODO: move to modernizr or something besides us doing this...
     * These are across all of our apps (reports, tool shed), but:
     *     these should be configurable via options because they all need different things.
     * So, analysis-polyfills.js, reports-polyfills.js (or analysis/polyfills)
     */
    'use strict';
    /*globals window, clearTimeout */

    // ------------------------------------------------------------------ polyfills
    // console protection needed in some versions of IE (at this point (IE>=9), shouldn't be needed)
    window.console = window.console || {
        log     : function(){},
        debug   : function(){},
        info    : function(){},
        warn    : function(){},
        error   : function(){},
        assert  : function(){}
    };

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

    // ------------------------------------------------------------------ can't/won't polyfill
    var features = [
        { name: 'canvas',           compatible: function(){ return window.CanvasRenderingContext2D; } },
        { name: 'sessionStorage',   compatible: function(){
            try {
                return window.sessionStorage.length >= 0;
            } catch( err ){}
            return false;
        }},
    ];
    // build a list of feature names for features that were not found
    var incompatibilities = features
        .filter( function( feature ){ return !feature.compatible(); })
        .map( function( feature ){ return feature.name; });

    // if there are needed features missing, follow the index link to the static incompat warning
    if( !!incompatibilities.length ){
        var root = document.querySelectorAll( 'link[rel="index"]' ).item( 0 );
        if( root ){
            window.location = root.href + 'static/incompatible-browser.html';
        }
        console.log( 'incompatible browser:\n' + incompatibilities.join( '\n' ) );
    }

})();
