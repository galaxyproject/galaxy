/**
 * Screenshot creator
*/

// dependencies
define(["libs/underscore"], function(_) {

    // screenshot
    function create ($el, screenshot_url, name) {
        if ($el.find('svg').length > 0) {
            _fromSVG ($el, screenshot_url, name);
        } else {
            _fromCanvas ($el);
        }
    };
    
    // from jqplot
    function _fromCanvas ($el) {
        $el.find('#canvas').jqplotSaveImage({});
    };
    
    // from svg
    function _fromSVG ($el, screenshot_url, name) {
        var serializer = new XMLSerializer();
        var xmlString = '';
        var self = this;
        var height = 0;
        var width  = 0;
        $el.find('svg').each(function() {
            // get svg element
            var $svg = $(this);
            
            // inline all styles
            _inline($svg);
            
            // get height/width
            height = parseInt($svg.css('height'));
            width = parseInt($svg.css('width'));
            
            // configure svg
            $svg.attr({
                version : '1.1',
                xmlns   : 'http://www.w3.org/2000/svg',
                width   : width,
                height  : height
            });
            
            // hide input fields
            $svg.find('.highcharts-button').hide();
            
            // create xml string
            xmlString += serializer.serializeToString(this);
            
            // show input fields
            $svg.find('.highcharts-button').show();
        });
       
        // do the post
        _post($el, screenshot_url, {
            filename    : name || 'chart',
            type        : 'application/pdf',
            height      : height,
            width       : width,
            scale       : 2,
            svg         : xmlString
        });
        
        // return string
        return xmlString;
    };
    
    // css inliner
    function _inline ($target) {
        for (var sheet_id in document.styleSheets) {
            var sheet = document.styleSheets[sheet_id];
            var rules = sheet.cssRules;
            if (rules) {
                for (var idx = 0, len = rules.length; idx < len; idx++) {
                    try {
                        $target.find(rules[idx].selectorText).each(function (i, elem) {
                            elem.style.cssText += rules[idx].style.cssText;
                        });
                    } catch(err) {
                    }
                }
            }
        }
    };
    
    // post operator
    function _post ($el, url, data) {
        // create the form
        var form = $el.find('#viewport-form');
        if (form.length === 0) {
            form = $('<form>', {
                id      : 'viewport-form',
                method  : 'post',
                action  : url,
                display : 'none'
            });
            $el.append(form);
        }

        // reset form
        form.empty();

        // add the data
        for (name in data) {
            var input = $('<input/>', {
                type    : 'hidden',
                name    : name,
                value   : data[name]
            });
            form.append(input);
        }
        
        // submit
        try {
            form.submit();
        } catch(err) {
            console.log(err);
        }
    };

// return
return {
    create: create
};

});
