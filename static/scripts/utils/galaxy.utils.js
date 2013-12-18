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

// return
return {
    cssLoadFile   : cssLoadFile,
    cssGetAttribute : cssGetAttribute,
    jsonFromUrl : jsonFromUrl
};

});
