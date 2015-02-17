// dependencies
define(['utils/utils', 'mvc/ui/ui-button-check'], function(Utils, ButtonCheck) {

/** Base class for options based ui elements **/
var Base = Backbone.View.extend({
    // initialize
    initialize: function(options) {
        // options
        this.optionsDefault = {
            visible     : true,
            data        : [],
            id          : Utils.uuid(),
            error_text  : 'No data available.',
            wait_text   : 'Please wait...',
            multiple    : false
        };

        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement('<div class="ui-options"/>');

        // create elements
        this.$message   = $('<div/>');
        this.$options   = $(this._template(options));
        this.$menu      = $('<div class="ui-options-menu"/>');

        // append
        this.$el.append(this.$message);
        this.$el.append(this.$menu);
        this.$el.append(this.$options);

        // add select/unselect all button
        if (this.options.multiple) {
            this.select_button = new ButtonCheck({
                onclick: function() {
                    self.$('input').prop('checked', self.select_button.value() !== 0);
                    self._change();
                }
            });
            this.$menu.addClass('ui-margin-bottom');
            this.$menu.append(this.select_button.$el);
            this.$menu.append('Select/Unselect all');
        }

        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }

        // initialize data
        this.update(this.options.data);

        // set initial value
        if (this.options.value !== undefined) {
            this.value(this.options.value);
        }

        // add change event. fires on trigger
        var self = this;
        this.on('change', function() {
            self._change();
        });
    },

    /** Update options
    */
    update: function(options) {
        // backup current value
        var current = this._getValue();

        // remove all options
        this.$options.empty();

        // add new options using single option templates or full template
        if (this._templateOptions) {
            // rebuild options using full template
            this.$options.append(this._templateOptions(options));
        } else {
            // rebuild options using single option templates
            for (var key in options) {
                var $option = $(this._templateOption(options[key]));
                $option.addClass('ui-option');
                $option.tooltip({title: options[key].tooltip, placement: 'bottom'});
                this.$options.append($option);
            }
        }

        // add change events
        var self = this;
        this.$('input').on('change', function() {
            self.value(self._getValue());
            self._change();
        });

        // set previous value
        this.value(current);
    },

    /** Return/Set current value
    */
    value: function (new_value) {
        // set new value if available
        if (new_value !== undefined) {
            // reset selection
            this.$('input').prop('checked', false);

            // set value
            if (new_value !== null) {
                // check if its an array
                if (!(new_value instanceof Array)) {
                    new_value = [new_value];
                }

                // update to new selection
                for (var i in new_value) {
                    this.$('input[value="' + new_value[i] + '"]').first().prop('checked', true);
                }
            };
        }

        // refresh
        this._refresh();

        // get and return value
        return this._getValue();
    },

    /** Check if selected value exists (or any if multiple)
    */
    exists: function(value) {
        if (value !== undefined) {
            if (!(value instanceof Array)) {
                value = [value];
            }
            for (var i in value) {
                if (this.$('input[value="' + value[i] + '"]').length > 0) {
                    return true;
                }
            }
        }
        return false;
    },

    /** Return first available option
    */
    first: function() {
        var options = this.$('input').first();
        if (options.length > 0) {
            return options.val();
        } else {
            return null;
        }
    },

    /** Wait message during request processing
    */
    wait: function() {
        if (this._size() == 0) {
            this._messageShow(this.options.wait_text, 'info');
            this.$options.hide();
            this.$menu.hide();
        }
    },

    /** Hide wait message
    */
    unwait: function() {
        this._refresh();
    },

    /** Trigger custom onchange callback function
    */
    _change: function() {
        if (this.options.onchange) {
            this.options.onchange(this._getValue());
        }
    },

    /** Refresh options view
    */
    _refresh: function() {
        // show/hide messages
        if (this._size() == 0) {
            this._messageShow(this.options.error_text, 'danger');
            this.$options.hide();
            this.$menu.hide();
        } else {
            this._messageHide();
            this.$options.css('display', 'inline-block');
            this.$menu.show();
        }
        // refresh select/unselect button
        if (this.select_button) {
            var total = this._size();
            var value = this._getValue();
            if (!(value instanceof Array)) {
                this.select_button.value(0);
            } else {
                if (value.length !== total) {
                    this.select_button.value(1);
                } else {
                    this.select_button.value(2);
                }
            }
        }
    },

    /** Return current selection
    */
    _getValue: function() {
        // track values in array
        var selected = [];
        this.$(':checked').each(function() {
            selected.push($(this).val());
        });
        
        // get selected elements
        if (!Utils.validate(selected)) {
            return null;
        }
        
        // return multiple or single value
        if (this.options.multiple) {
            return selected;
        } else {
            return selected[0];
        }
    },

    /** Returns the number of options
    */
    _size: function() {
        return this.$('.ui-option').length;
    },

    /** Show message instead if options
    */
    _messageShow: function(text, status) {
        this.$message.show();
        this.$message.removeClass();
        this.$message.addClass('ui-message alert alert-' + status);
        this.$message.html(text);
    },

    /** Hide message
    */
    _messageHide: function() {
        this.$message.hide();
    },

    /** Main template function
    */
    _template: function() {
        return '<div class="ui-options-list"/>';
    }
});

/** Iconized **/
var BaseIcons = Base.extend({
    _templateOption: function(pair) {
        var id = Utils.uuid();
        return  '<div class="ui-option">' +
                    '<input id="' + id + '" type="' + this.options.type + '" name="' + this.options.id + '" value="' + pair.value + '"/>' +
                    '<label class="ui-options-label" for="' + id + '">' + pair.label + '</label>' +
                '</div>';
    }
});

/** Radio button field **/
var Radio = {};
Radio.View = BaseIcons.extend({
    initialize: function(options) {
        options.type = 'radio';
        BaseIcons.prototype.initialize.call(this, options);
    }
});

/** Checkbox options field **/
var Checkbox = {};
Checkbox.View = BaseIcons.extend({
    initialize: function(options) {
        options.multiple = true;
        options.type = 'checkbox';
        BaseIcons.prototype.initialize.call(this, options);
    }
});

/** Radio button options field styled as classic buttons **/
var RadioButton = {};
RadioButton.View = Base.extend({
    // initialize
    initialize: function(options) {
        Base.prototype.initialize.call(this, options);
    },

    /** Return/Set current value
    */
    value: function (new_value) {
        // set new value
        if (new_value !== undefined) {
            this.$('input').prop('checked', false);
            this.$('label').removeClass('active');
            this.$('[value="' + new_value + '"]').prop('checked', true).closest('label').addClass('active');
        }

        // get and return value
        return this._getValue();
    },

    /** Template for a single option
    */
    _templateOption: function(pair) {
        var cls = 'fa ' + pair.icon;
        if (!pair.label) {
            cls += ' no-padding';
        }
        var tmpl =  '<label class="btn btn-default">';
        if (pair.icon) {
            tmpl +=     '<i class="' + cls + '"/>';
        }
        tmpl +=         '<input type="radio" name="' + this.options.id + '" value="' + pair.value + '"/>';
        if (pair.label) {
            tmpl +=         pair.label;
        }
        tmpl +=     '</label>';
        return tmpl;
    },

    /** Main template function
    */
    _template: function() {
        return '<div class="btn-group ui-radiobutton" data-toggle="buttons"/>';
    }
});

return {
    Base        : Base,
    BaseIcons   : BaseIcons,
    Radio       : Radio,
    RadioButton : RadioButton,
    Checkbox    : Checkbox
};

});
