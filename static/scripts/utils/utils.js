/**
 * Galaxy utilities comprises small functions, which at this point
 * do not require their own classes/files
*/

// dependencies
define(["libs/underscore"], function(_) {

// generic function to recieve json from url
function jsonFromUrl (url, successHandler, errorHandler) {
    
    // open url
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    
    // configure request
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('Cache-Control', 'no-cache');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    
    // on completion
    xhr.onloadend = function() {
        var status = xhr.status;
        if (status == 200) {
            try
            {
                response = jQuery.parseJSON(xhr.responseText);
            } catch (e) {
                response = xhr.responseText;
            }
            successHandler && successHandler(response);
        } else {
            errorHandler && errorHandler(status);
        }
    };
      
    // submit request
    xhr.send();
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
    return (new Date().getTime()).toString(36);
};

// return
return {
    cssLoadFile   : cssLoadFile,
    cssGetAttribute : cssGetAttribute,
    jsonFromUrl : jsonFromUrl,
    merge : merge,
    bytesToString: bytesToString,
    uuid: uuid
};

});
