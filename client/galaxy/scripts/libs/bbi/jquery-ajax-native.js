//     jQuery Ajax Native Plugin

//     (c) 2015 Tarik Zakaria Benmerar, Acigna Inc.
//      jQuery Ajax Native Plugin may be freely distributed under the MIT license.
(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['jquery'], factory);
    } else if (typeof exports === 'object') {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        module.exports = factory(require('jquery'));
    } else {
        // Browser globals (root is window)
        factory(root.jQuery);
    }
}(this, function ( $ ) {
    var ajaxSettings = $.ajaxSettings;
    ajaxSettings.responseFields.native = 'responseNative';
    ajaxSettings.converters[ '* native' ] = true;
    var support = {},
        xhrId = 0,
        xhrSuccessStatus = {
            // file protocol always yields status code 0, assume 200
            0: 200,
            // Support: IE9
            // #1450: sometimes IE returns 1223 when it should be 204
            1223: 204
        },
        xhrCallbacks = {},
        xhrSupported = jQuery.ajaxSettings.xhr();
    // Support: IE9
    // Open requests must be manually aborted on unload (#5280)
    if ( window.ActiveXObject ) {
        $( window ).on( "unload", function() {
            for ( var key in xhrCallbacks ) {
                xhrCallbacks[ key ]();
            }
        });
    }
    support.cors = !!xhrSupported && ( "withCredentials" in xhrSupported );
    support.ajax = xhrSupported = !!xhrSupported;

    //Native Data Type Ajax Transport
    $.ajaxTransport('native', function ( options ) {
        var callback;
        // Cross domain only allowed if supported through XMLHttpRequest
        if ( support.cors || xhrSupported && !options.crossDomain ) {
            return {
                send: function( headers, complete ) {
                    var i,
                        xhr = options.xhr(),
                        id = ++xhrId,
                        responses = {};

                    xhr.open( options.type, options.url, options.async, options.username, options.password );

                    // Apply custom fields if provided
                    if ( options.xhrFields ) {
                        for ( i in options.xhrFields ) {
                            xhr[ i ] = options.xhrFields[ i ];
                        }
                    }

                    // Override mime type if needed
                    if ( options.mimeType && xhr.overrideMimeType ) {
                        xhr.overrideMimeType( options.mimeType );
                    }

                    // X-Requested-With header
                    // For cross-domain requests, seeing as conditions for a preflight are
                    // akin to a jigsaw puzzle, we simply never set it to be sure.
                    // (it can always be set on a per-request basis or even using ajaxSetup)
                    // For same-domain requests, won't change header if already provided.
                    if ( !options.crossDomain && !headers["X-Requested-With"] ) {
                        headers["X-Requested-With"] = "XMLHttpRequest";
                    }

                    // Set headers
                    for ( i in headers ) {
                        xhr.setRequestHeader( i, headers[ i ] );
                    }

                    // Callback
                    callback = function( type ) {
                        return function() {
                            if ( callback ) {
                                delete xhrCallbacks[ id ];
                                callback = xhr.onload = xhr.onerror = null;

                                if ( type === "abort" ) {
                                    xhr.abort();
                                } else if ( type === "error" ) {
                                    complete(
                                        // file: protocol always yields status 0; see #8605, #14207
                                        xhr.status,
                                        xhr.statusText
                                    );
                                } else {
                                    // The native response associated with the responseType
                                    // Stored in the xhr.response attribute (XHR2 Spec)
                                    if ( xhr.response ) {
                                        responses.native = xhr.response;
                                    }

                                    complete(
                                        xhrSuccessStatus[ xhr.status ] || xhr.status,
                                        xhr.statusText,
                                        responses,
                                        xhr.getAllResponseHeaders()
                                    );
                                }
                            }
                        };
                    };

                    // Listen to events
                    xhr.onload = callback();
                    xhr.onerror = callback("error");

                    // Create the abort callback
                    callback = xhrCallbacks[ id ] = callback("abort");

                    try {
                        // Do send the request (this may raise an exception)
                        xhr.send( options.hasContent && options.data || null );
                    } catch ( e ) {
                        // #14683: Only rethrow if this hasn't been notified as an error yet
                        if ( callback ) {
                            throw e;
                        }
                    }
                },

                abort: function() {
                    if ( callback ) {
                        callback();
                    }
                }
            };
        }
    });


    //$.getNative wrapper
    $.getNative = function ( url, callback ) {
        return $.ajax({
            dataType: 'native',
            url: url,
            xhrFields: {
                responseType: 'arraybuffer'
            },
            success: callback
        });
    }
}));
