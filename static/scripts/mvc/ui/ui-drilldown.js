// dependencies
define(['utils/utils', 'mvc/ui/ui-options'], function(Utils, Options) {

/**
 *  This class creates/wraps a drill down element.
 */
var View = Options.BaseIcons.extend({
    // initialize
    initialize: function(options) {
        options.type     = options.display || 'checkbox';
        options.multiple = (options.display == 'checkbox');
        Options.BaseIcons.prototype.initialize.call(this, options);
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
                    var $button = $('<span class="ui-drilldown-button form-toggle icon-button toggle-expand"/>');

                    // add expand group
                    var $buttongroup = $('<div/>');
                    $buttongroup.append($button);
                    $buttongroup.append(self._templateOption({
                        label: level.name,
                        value: level.value
                    }));
                    $group.append($buttongroup);

                    // add sub group
                    var $subgroup = $('<div style="display: none; margin-left: 25px;"/>');
                    iterate($subgroup, level.options);
                    $group.append($subgroup);

                    // attach click event to collapse/expand hierarchy
                    attachEvents($button, $subgroup);
                } else {
                    $group.append(self._templateOption({
                        label: level.name,
                        value: level.value
                    }));
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
        return '<div class="ui-options-list drilldown-container" id="' + options.id + '"/>';
    }
});

return {
    View: View
}

});
