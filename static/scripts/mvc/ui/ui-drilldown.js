// dependencies
define(['utils/utils', 'mvc/ui/ui-options'], function(Utils, Options) {

/**
 *  This class creates/wraps a drill down element.
 */
var View = Options.Base.extend({
    // initialize
    initialize: function(options) {
        this.display = options.display || 'checkbox';
        options.multiple = (this.display == 'checkbox');
        Options.Base.prototype.initialize.call(this, options);
    },
    
    /** Template for input field
    */
    _templateOption: function(name, value, selected) {
        return  '<div>' +
                    '<input name="' + this.options.id + '" class="ui-option" type="' + this.display + '" value="' + value + '">' +
                        Utils.sanitize(name) +
                '<div/>';
    },
    
    /** Template to create options tree
    */
    _templateOptions: function(options) {
        // link this
        var self = this;
        
        // attach show/hide event
        function attachEvents($button, $subgroup) {
            function setVisibility (visible) {
                if (visible) {
                    $subgroup.fadeIn('fast')
                    $button.removeClass('toggle-expand');
                    $button.addClass('toggle');
                    $button.is_expanded = true;
                } else {
                    $subgroup.hide();
                    $button.removeClass('toggle');
                    $button.addClass('toggle-expand');
                    $button.is_expanded = false;
                }
            };
            $button.on('click', function() {
                 setVisibility(!$button.is_expanded);
            });
        }
        
        // recursive function which iterates through options
        function iterate ($tmpl, options) {
            for (i in options) {
                // current option level in hierarchy
                var level = options[i];
                
                // check for options
                var has_options = level.options.length > 0;
                
                // build template
                var $group = $('<div/>');
                if (has_options) {
                    // create button and add flag
                    var $button = $('<span class="ui-drilldown-button form-toggle icon-button toggle-expand" style="position: relative; top: 2px;"/>');
                    
                    // add expand group
                    var $buttongroup = $('<div/>');
                    $buttongroup.append($button);
                    $buttongroup.append(self._templateOption(level.name, level.value));
                    $group.append($buttongroup);
                    
                    // add sub group
                    var $subgroup = $('<div style="display: none; margin-left: 25px;"/>');
                    iterate($subgroup, level.options);
                    $group.append($subgroup);
                    
                    // attach click event to collapse/expand hierarchy
                    attachEvents($button, $subgroup);
                } else {
                    $group.append(self._templateOption(level.name, level.value));
                }
                $tmpl.append($group);
            }
        }
        
        // iterate through options and create dom
        var $tmpl = $('<div/>');
        iterate($tmpl, options);
        return $tmpl;
    },
    
    /** Template for drill down view
    */
    _template: function(options) {
        return '<div class="ui-options drilldown-container" id="' + options.id + '"/>';
    }
});

return {
    View: View
}

});
