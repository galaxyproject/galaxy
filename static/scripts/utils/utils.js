/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
*/

// dependencies
define(["libs/underscore"], function(_) {

// generic function to recieve json from url
function get (url, success, error) {
    request('GET', url, {}, success, error);
};

// generic function to send json to url
function request (method, url, data, success, error) {

    // encode data into url
    if (method == 'GET' || method == 'DELETE') {
        if (url.indexOf('?') == -1) {
            url += '?';
        } else {
            url += '&';
        }
        url += $.param(data)
    }
    
    // prepare request
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('Cache-Control', 'no-cache');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onloadend = function() {
        // get status
        var status = xhr.status;
       
        // read response
        try {
            response = jQuery.parseJSON(xhr.responseText);
        } catch (e) {
            response = xhr.responseText;
        }
   
        // parse response
        if (status == 200) {
            success && success(response);
        } else {
            error && error(response);
        }
    };
    
    // make request
    if (method == 'GET' || method == 'DELETE') {
        xhr.send();
    } else {
        xhr.send(JSON.stringify(data));
    }
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
