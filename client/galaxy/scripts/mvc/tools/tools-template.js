// dependencies
define([], function() {

// tool form templates
return {
    help: function(content) {
        return  '<div class="toolHelp">' +
                    '<div class="toolHelpBody">' +
                        content +
                    '</div>' +
                '</div>';
    },
    
    citations: function() {
        return  '<div id="citations"></div>';
    },
    
    message: function(options) {
        return  '<div class="donemessagelarge">' +
                    '<p>' + options.text + '</p>' +
                '</div>';
    }
};

});