/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
*/

// dependencies
define([], function() {

/** Traverse through json
*/
function deepeach(dict, callback) {
    for (var i in dict) {
        var d = dict[i];
        if (d && typeof(d) == "object") {
            callback(d);
            deepeach(d, callback);
        }
    }
}

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
 * Sanitize/escape a string
 * @param{String}   content - Content to be sanitized
 */
function sanitize(content) {
    return $('<div/>').text(content).html();
};

/**
 * Validate atomic values or list of values
 * usually used for selectable options
 * @param{String}   value - Value or list to be validated
 */
function validate (value) {
    if (!(value instanceof Array)) {
        value = [value];
    }
    if (value.length === 0) {
        return false;
    }
    for (var i in value) {
        if (['__null__', '__undefined__', null, undefined].indexOf(value[i]) > -1) {
            return false;
        }
    }
    return true;
};

/**
 * Convert list to pretty string
 * @param{String}   lst - List of strings to be converted in human readable list sentence
 */
function textify(lst) {
    var lst = lst.toString();
    if (lst) {
        lst = lst.replace(/,/g, ', ');
        var pos = lst.lastIndexOf(', ');
        if (pos != -1) {
            lst = lst.substr(0, pos) + ' or ' + lst.substr(pos+1);
        }
        return lst;
    }
    return '';
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
    if (options.cache && top.__utils__get__[options.url]) {
        options.success && options.success(top.__utils__get__[options.url]);
        console.debug('utils.js::get() - Fetching from cache [' + options.url + '].');
    } else {
        request({
            url     : options.url,
            data    : options.data,
            success : function(response) {
                top.__utils__get__[options.url] = response;
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
    // prepare ajax
    var ajaxConfig = {
        contentType : 'application/json',
        type        : options.type || 'GET',
        data        : options.data || {},
        url         : options.url
    }

    // encode data into url
    if (ajaxConfig.type == 'GET' || ajaxConfig.type == 'DELETE') {
        if (ajaxConfig.url.indexOf('?') == -1) {
            ajaxConfig.url += '?';
        } else {
            ajaxConfig.url += '&';
        }
        ajaxConfig.url      = ajaxConfig.url + $.param(ajaxConfig.data, true);
        ajaxConfig.data     = null;
    } else {
        ajaxConfig.dataType = 'json';
        ajaxConfig.url      = ajaxConfig.url;
        ajaxConfig.data     = JSON.stringify(ajaxConfig.data);
    }

    // make request
    $.ajax(ajaxConfig)
    .done(function(response) {
        if (typeof response === 'string') {
            try {
                response = response.replace('Infinity,', '"Infinity",');
                response = jQuery.parseJSON(response);
            } catch (e) {
                console.debug(e);
            }
        }
        options.success && options.success(response);
    })
    .fail(function(response) {
        var response_text = null;
        try {
            response_text = jQuery.parseJSON(response.responseText);
        } catch (e) {
            response_text = response.responseText;
        }
        options.error && options.error(response_text, response);
    });
};

/**
 * Read a property value from CSS
 * @param{String}   classname   - CSS class
 * @param{String}   name        - CSS property
 */
function cssGetAttribute (classname, name) {
    var el = $('<div class="' + classname + '"></div>');
    el.appendTo(':eq(0)');
    var value = el.css(name);
    el.remove();
    return value;
};

/**
 * Load a CSS file
 * @param{String}   url - Url of CSS file
 */
function cssLoadFile (url) {
    if (!$('link[href^="' + url + '"]').length) {
        $('<link href="' + galaxy_config.root + url + '" rel="stylesheet">').appendTo('head');
    }
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


/**
 * Round floaing point 'number' to 'numPlaces' number of decimal places.
 * @param{Object}   number      a floaing point number
 * @param{Object}   numPlaces   number of decimal places
 */
function roundToDecimalPlaces( number, numPlaces ){
    var placesMultiplier = 1;
    for( var i=0; i<numPlaces; i++ ){
        placesMultiplier *= 10;
    }
    return Math.round( number * placesMultiplier ) / placesMultiplier;
}

// calculate on import
var kb = 1024,
    mb = kb * kb,
    gb = mb * kb,
    tb = gb * kb;
/**
 * Format byte size to string with units
 * @param{Integer}   size           - Size in bytes
 * @param{Boolean}   normal_font    - Switches font between normal and bold
 */
function bytesToString (size, normal_font, numberPlaces) {
    numberPlaces = numberPlaces !== undefined? numberPlaces: 1;
    // identify unit
    var unit = "";
    if (size >= tb){ size = size / tb; unit = 'TB'; } else
    if (size >= gb){ size = size / gb; unit = 'GB'; } else
    if (size >= mb){ size = size / mb; unit = 'MB'; } else
    if (size >= kb){ size = size / kb; unit = 'KB'; } else
    if (size >  0){ unit = 'b'; }
    else { return normal_font? '0 b': '<strong>-</strong>'; }
    // return formatted string
    var rounded = unit == 'b'? size: roundToDecimalPlaces( size, numberPlaces );
    if (normal_font) {
       return  rounded + ' ' + unit;
    } else {
        return '<strong>' + rounded + '</strong> ' + unit;
    }
};

/**
 * Create a unique id
 */
function uid(){
    top.__utils__uid__ = top.__utils__uid__ || 0;
    return 'uid-' + top.__utils__uid__++;
};

/**
 * Create a time stamp
 */
function time() {
    var d = new Date();
    var hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
    var minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes()
    return datetime = d.getDate() + "/"
                + (d.getMonth() + 1)  + "/"
                + d.getFullYear() + ", "
                + hours + ":"
                + minutes;
}

/**
 * Output message to Galaxy logger
 */
var emit = {};
[ 'log', 'debug', 'info', 'warn', 'error', 'metric' ].map(function( i ) {
    emit[ i ] = function( data ) {
        Galaxy.logger.emit( i, arguments[ 0 ], Array.prototype.slice.call( arguments, 1 ) );
    };
});

return {
    cssLoadFile: cssLoadFile,
    cssGetAttribute: cssGetAttribute,
    get: get,
    merge: merge,
    bytesToString: bytesToString,
    uid: uid,
    time: time,
    request: request,
    sanitize: sanitize,
    textify: textify,
    validate: validate,
    deepeach: deepeach,
    isJSON: isJSON,
    emit: emit
};

});
