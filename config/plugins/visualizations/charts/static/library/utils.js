// dependencies
define([], function() {

// get
function get (url, success, error) {
    request('GET', url, {}, success, error);
};

// generic function to send json to url
function request (method, url, data, success, error) {

    // encode data into url
    if (method == 'GET' || method == 'DELETE') {
        url = url + "?" + $.param(data);
    }
    
    // prepare request
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('Cache-Control', 'no-cache');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onloadend = function() {
        var status = xhr.status;
        if (status == 200) {
            try {
                response = jQuery.parseJSON(xhr.responseText);
            } catch (e) {
                response = xhr.responseText;
            }
            success && success(response);
        } else {
            error && error(status);
        }
    };
    
    // make request
    if (method == 'GET' || method == 'DELETE') {
        xhr.send();
    } else {
        xhr.send(JSON.stringify(data));
    }
};

// merge
function merge (options, optionsDefault) {
    if (options)
        return _.defaults(options, optionsDefault);
    else
        return optionsDefault;
};

// get css value
function cssGetAttribute (classnames, name) {
    if (classnames.length == 0) {
       console.log('cssGetAttribute() : Requires a list of classnames');
    }

    // place dummy element
    var el = $('<div class="' + classnames[0] + '"></div>');
    var traverse_el = el;
    for (var i in classnames) {
        traverse_el.append('<div class="' + classnames[i] + '"></div>');
        traverse_el = traverse_el.find('.' + classnames[i]);
    }
      
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

// unique ide
function uuid(){
    return (new Date().getTime()).toString(36);
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
    cssLoadFile : cssLoadFile,
    cssGetAttribute : cssGetAttribute,
    get : get,
    merge : merge,
    request: request,
    uuid: uuid,
    wrap : wrap,
    time : time
};

});
