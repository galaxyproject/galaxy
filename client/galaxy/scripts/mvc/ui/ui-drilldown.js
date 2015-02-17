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
        this.initial = true;
    },

    // set expand states for initial value
    value: function (new_val) {
        var val = Options.BaseIcons.prototype.value.call(this, new_val);
        if (this.initial && val !== null && this.header_index) {
            this.initial = false;
            var values = val;
            if (!$.isArray(values)) {
                values = [values];
            }
            for (var i in values) {
                var list = this.header_index[values[i]];
                for (var j in list) {
                    this._setState(list[j], true);
                }
            }
        }
        return val;
    },

    /** Expand/collapse a sub group
    */
    _setState: function (header_id, is_expanded) {
        var $button = this.$('#button-' + header_id);
        var $subgroup = this.$('#subgroup-' + header_id);
        $button.data('is_expanded', is_expanded);
        if (is_expanded) {
            $subgroup.fadeIn('fast')
            $button.removeClass('toggle-expand');
            $button.addClass('toggle');
        } else {
            $subgroup.hide();
            $button.removeClass('toggle');
            $button.addClass('toggle-expand');
        }
    },

    /** Template to create options tree
    */
    _templateOptions: function(options) {
        // link this
        var self = this;

        // link data
        this.header_index = {};
        
        // attach event handler
        function attach($el, header_id) {
            var $button = $el.find('#button-' + header_id);
            $button.on('click', function() {
                self._setState(header_id, !$button.data('is_expanded'));
            });
        }

        // recursive function which iterates through options
        function iterate ($tmpl, options, header) {
            header = header || [];
            for (i in options) {
                // current option level in hierarchy
                var level = options[i];

                // check for options
                var has_options = level.options.length > 0;

                // copy current header list
                var new_header = header.slice(0);

                // keep track of header list
                self.header_index[level.value] = new_header.slice(0);

                // build template
                var $group = $('<div/>');
                if (has_options) {
                    // create button and subgroup
                    var header_id = Utils.uuid();
                    var $button = $('<span id="button-' + header_id + '" class="ui-drilldown-button form-toggle icon-button toggle-expand"/>');
                    var $subgroup = $('<div id="subgroup-' + header_id + '" style="display: none; margin-left: 25px;"/>');

                    // keep track of button and subgroup
                    new_header.push(header_id);

                    // create expandable header section
                    var $buttongroup = $('<div/>');
                    $buttongroup.append($button);
                    $buttongroup.append(self._templateOption({
                        label: level.name,
                        value: level.value
                    }));
                    $group.append($buttongroup);
                    iterate($subgroup, level.options, new_header);
                    $group.append($subgroup);

                    // attach expand/collapse events
                    attach($group, header_id);
                } else {
                    // append child options
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

        // return template
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
