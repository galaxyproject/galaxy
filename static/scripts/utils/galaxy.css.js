/**
 * Galaxy CSS utilities
*/

// dependencies
define(["libs/underscore"], function(_) {

// get css value
function get_attribute (classname, name)
{
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
}
    
// load css
function load_file (url)
{
    // check if css is already available
    if (!$('link[href^="' + url + '"]').length)
        $('<link href="' + url + '" rel="stylesheet">').appendTo('head');
};

// return
return {
    load_file   : load_file,
    get_attribute : get_attribute
};

});
