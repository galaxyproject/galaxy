/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
*/

// dependencies
define(["libs/underscore"], function(_) {

/* request handler for GET
    param{string}   url
    param{function} success
    param{function} error
    param{boolean}  cache
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

/* request handler
    param{string}   method
    param{string}   url
    param{object}   data
    param{function} success
    param{function} error
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
        ajaxConfig.url      = ajaxConfig.url + $.param(ajaxConfig.data);
        ajaxConfig.data     = null;
    } else {
        ajaxConfig.dataType = 'json';
        ajaxConfig.url      = ajaxConfig.url;
        ajaxConfig.data     = JSON.stringify(ajaxConfig.data);
    }

    // make request
    $.ajax(ajaxConfig)
    .done(function(response) {
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

// get css value
function cssGetAttribute (classname, name) {
    // place dummy element
    var el = $('<div class="' + classname + '"></div>');
       
    // required append
    el.appendTo(':eq(0)');
    
    // get value
    var value = el.css(name);
    
    // remove element
    el.remove();
        
    // return css value
    return value;
};
    
// load css
function cssLoadFile (url) {
    // check if css is already available
    if (!$('link[href^="' + url + '"]').length)
        $('<link href="' + galaxy_config.root + url + '" rel="stylesheet">').appendTo('head');
};

// merge
function merge (options, optionsDefault) {
    if (options)
        return _.defaults(options, optionsDefault);
    else
        return optionsDefault;
};

// to string
function bytesToString (size, normal_font) {
    // identify unit
    var unit = "";
    if (size >= 100000000000)   { size = size / 100000000000; unit = 'TB'; } else
    if (size >= 100000000)      { size = size / 100000000; unit = 'GB'; } else
    if (size >= 100000)         { size = size / 100000; unit = 'MB'; } else
    if (size >= 100)            { size = size / 100; unit = 'KB'; } else
    if (size >  0)              { size = size * 10; unit = 'b'; } else
        return '<strong>-</strong>';
                                
    // return formatted string
    var rounded = (Math.round(size) / 10);
    if (normal_font) {
       return  rounded + ' ' + unit;
    } else {
        return '<strong>' + rounded + '</strong> ' + unit;
    }
};

// unique ide
function uuid(){
    return 'x' + Math.random().toString(36).substring(2, 9);
};

// wrap
function wrap($el) {
    var wrapper = $('<p></p>');
    wrapper.append($el);
    return wrapper;
};

// time
function time() {
    // get date object
    var d = new Date();
    
    // format items
    var hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
    var minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes()
    
    // format final stamp
    var datetime = d.getDate() + "/"
                + (d.getMonth() + 1)  + "/"
                + d.getFullYear() + ", "
                + hours + ":"
                + minutes;
    return datetime;
};

// return
return {
    cssLoadFile   : cssLoadFile,
    cssGetAttribute : cssGetAttribute,
    get : get,
    merge : merge,
    bytesToString: bytesToString,
    uuid: uuid,
    time: time,
    wrap: wrap,
    request: request
};

});
