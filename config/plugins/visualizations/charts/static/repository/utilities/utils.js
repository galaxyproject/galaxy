/** Useful helper functions */
define( [], function() {

    /** Clone */
    function clone( obj ) {
        return JSON.parse( JSON.stringify( obj ) || null );
    };

    /**
     * Check if a string is a json string
     * @param{String}   text - Content to be validated
     */
    function isJSON(text) {
        return /^[\],:{}\s]*$/.test(text.replace(/\\["\\\/bfnrtu]/g, '@').
            replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, ']').
            replace(/(?:^|:|,)(?:\s*\[)+/g, ''));
    };

    /**
     * Request handler for GET
     * @param{String}   url     - Url request is made to
     * @param{Function} success - Callback on success
     * @param{Function} error   - Callback on error
     * @param{Boolean}  cache   - Use cached data if available
     */
    function get (options) {
        top.__utils__get__ = top.__utils__get__ || {};
        var cache_key = JSON.stringify( options );
        if (options.cache && top.__utils__get__[cache_key]) {
            options.success && options.success(top.__utils__get__[cache_key]);
            window.console.debug('utils.js::get() - Fetching from cache [' + options.url + '].');
        } else {
            request({
                url     : options.url,
                data    : options.data,
                success : function(response) {
                    top.__utils__get__[cache_key] = response;
                    options.success && options.success(response);
                },
                error : function(response) {
                    options.error && options.error(response);
                }
            });
        }
    };

    /**
     * Request handler
     * @param{String}   method  - Request method ['GET', 'POST', 'DELETE', 'PUT']
     * @param{String}   url     - Url request is made to
     * @param{Object}   data    - Data send to url
     * @param{Function} success - Callback on success
     * @param{Function} error   - Callback on error
     */
    function request (options) {
        var ajaxConfig = {
            contentType : 'application/json',
            type        : options.type || 'GET',
            data        : options.data || {},
            url         : options.url
        }
        if ( ajaxConfig.type == 'GET' || ajaxConfig.type == 'DELETE' ) {
            if ( !$.isEmptyObject(ajaxConfig.data) ) {
                ajaxConfig.url += ajaxConfig.url.indexOf('?') == -1 ? '?' : '&';
                ajaxConfig.url += $.param(ajaxConfig.data, true);
            }
            ajaxConfig.data = null;
        } else {
            ajaxConfig.dataType = 'json';
            ajaxConfig.url      = ajaxConfig.url;
            ajaxConfig.data     = JSON.stringify( ajaxConfig.data );
        }
        $.ajax( ajaxConfig ).done( function( response ) {
            if ( typeof response === 'string' && isJSON( response ) ) {
                try {
                    response = response.replace( 'Infinity,', '"Infinity",' );
                    response = jQuery.parseJSON( response );
                } catch ( e ) {
                    console.debug( e );
                }
            }
            options.success && options.success( response );
        }).fail( function( response ) {
            var response_text = null;
            try {
                response_text = jQuery.parseJSON( response.responseText );
            } catch (e) {
                response_text = response.responseText;
            }
            options.error && options.error( response_text, response );
        }).always( function() {
            options.complete && options.complete();
        });
    };

    /**
     * Safely merge to dictionaries
     * @param{Object}   options         - Target dictionary
     * @param{Object}   optionsDefault  - Source dictionary
     */
    function merge (options, optionsDefault) {
        if (options) {
            return _.defaults(options, optionsDefault);
        } else {
            return optionsDefault;
        }
    };

    /** Create a unique id */
    function uid(){
        top.__utils__uid__ = top.__utils__uid__ || 0;
        return 'uid-' + top.__utils__uid__++;
    };

    return {
        get     : get,
        merge   : merge,
        uid     : uid,
        request : request,
        clone   : clone,
        isJSON  : isJSON
    };
});