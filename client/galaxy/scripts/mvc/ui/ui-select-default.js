/**
 *  This class creates/wraps a default html select field as backbone class.
 */
define(['utils/utils', 'mvc/ui/ui-buttons'], function(Utils, Buttons) {
var View = Backbone.View.extend({
    // options
    optionsDefault: {
        id          : Utils.uid(),
        cls         : 'ui-select',
        error_text  : 'No options available',
        empty_text  : 'Nothing selected',
        visible     : true,
        wait        : false,
        multiple    : false,
        searchable  : true,
        optional    : false
    },

    // initialize
    initialize: function(options) {
        // link this
        var self = this;

        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement(this._template(this.options));

        // link elements
        this.$select = this.$el.find('.select');
        this.$icon_dropdown = this.$el.find('.icon-dropdown');

        // allow regular multi-select field to be resized
        var minHeight = null;
        this.$('.icon-resize').on('mousedown', function(event) {
            var currentY = event.pageY;
            var currentHeight = self.$select.height();
            minHeight = minHeight || currentHeight;
            $('#dd-helper').show().on('mousemove', function(event) {
                self.$select.height(Math.max(currentHeight + (event.pageY - currentY), minHeight));
            }).on('mouseup mouseleave', function() {
                $('#dd-helper').hide().off();
            });
        });

        // multiple select fields have an additional button and other custom properties
        if (this.options.multiple) {
            // create select all button
            if (this.options.searchable) {
                this.all_button = new Buttons.ButtonCheck({
                    onclick: function() {
                        var new_value = [];
                        if (self.all_button.value() !== 0) {
                            new_value = self._availableOptions();
                        }
                        self.value(new_value);
                        self.trigger('change');
                    }
                });
                this.$el.prepend(this.all_button.$el);
            } else {
                this.$el.addClass('ui-select-multiple');
            }
            this.$select.prop('multiple', true);
            this.$icon_dropdown.remove();
        }

        // update initial options
        this.update(this.options.data);

        // set initial value
        if (this.options.value !== undefined) {
            this.value(this.options.value);
        }

        // show/hide
        if (!this.options.visible) {
            this.hide();
        }

        // wait
        if (this.options.wait) {
            this.wait();
        } else {
            this.show();
        }

        // add change event. fires only on user activity
        this.$select.on('change', function() {
            self.trigger('change');
        });

        // add change event. fires on trigger
        this.on('change', function() {
            self.options.onchange && self.options.onchange(this.value());
        });
    },

    /** Return/Set current selection
    */
    value: function (new_value) {
        // set new value
        if (new_value !== undefined) {
            if (new_value === null) {
                new_value = '__null__';
            }
            if (this.exists(new_value) || this.options.multiple) {
                this.$select.val(new_value);
                if (this.$select.select2) {
                    this.$select.select2('val', new_value);
                }
            }
        }
        // get current value
        var current = this._getValue();
        if (this.all_button) {
            this.all_button.value($.isArray(current) && current.length || 0, this._size());
        }
        return current;
    },

    /** Return the first select option
    */
    first: function() {
        var options = this.$select.find('option').first();
        if (options.length > 0) {
            return options.val();
        } else {
            return null;
        }
    },

    /** Return the label/text of the current selection
    */
    text: function () {
        return this.$select.find('option:selected').text();
    },

    /** Show the select field
    */
    show: function() {
        this.unwait();
        this.$select.show();
        this.$el.show();
    },

    /** Hide the select field
    */
    hide: function() {
        this.$el.hide();
    },

    /** Show a spinner indicating that the select options are currently loaded
    */
    wait: function() {
        this.$icon_dropdown.removeClass();
        this.$icon_dropdown.addClass('icon-dropdown fa fa-spinner fa-spin');
    },

    /** Hide spinner indicating that the request has been completed
    */
    unwait: function() {
        this.$icon_dropdown.removeClass();
        this.$icon_dropdown.addClass('icon-dropdown fa fa-caret-down');
    },

    /** Returns true if the field is disabled
    */
    disabled: function() {
        return this.$select.is(':disabled');
    },

    /** Enable the select field
    */
    enable: function() {
        this.$select.prop('disabled', false);
    },

    /** Disable the select field
    */
    disable: function() {
        this.$select.prop('disabled', true);
    },

    /** Update all available options at once
    */
    update: function(options) {
        // backup current value
        var current = this._getValue();

        // remove all options
        this.$select.find('option').remove();

        // add optional field
        if (!this.options.multiple && this.options.optional) {
            this.$select.append(this._templateOption({value : '__null__', label : this.options.empty_text}));
        }

        // add new options
        for (var key in options) {
            this.$select.append(this._templateOption(options[key]));
        }

        // count remaining entries
        if (this._size() == 0) {
            // disable select field
            this.disable();

            // create placeholder
            this.$select.append(this._templateOption({value : '__null__', label : this.options.error_text}));
        } else {
            // enable select field
            this.enable();
        }

        // update to searchable field (in this case select2)
        if (this.options.searchable) {
            this.$select.select2('destroy');
            this.$select.select2({ closeOnSelect: !this.options.multiple });
            this.$( '.select2-container .select2-search input' ).off( 'blur' );
        }

        // set previous value
        this.value(current);

        // check if any value was set
        if (this._getValue() === null && !(this.options.multiple && this.options.optional)) {
            this.value(this.first());
        }
    },

    /** Set the custom onchange callback function
    */
    setOnChange: function(callback) {
        this.options.onchange = callback;
    },

    /** Check if a value is an existing option
    */
    exists: function(value) {
        return this.$select.find('option[value="' + value + '"]').length > 0;
    },

    /** Get current value from dom
    */
    _getValue: function() {
        var val = this.$select.val();
        if (!Utils.validate(val)) {
            return null;
        }
        return val;
    },

    /** Returns all currently available options
    */
    _availableOptions: function() {
        var available = [];
        this.$select.find('option').each(function(i, e){
            available.push($(e).attr('value'));
        });
        return available;
    },

    /** Number of available options
    */
    _size: function() {
        return this.$select.find('option').length;
    },

    /** Template for select options
    */
    _templateOption: function(options) {
        return '<option value="' + options.value + '">' + options.label + '</option>';
    },

    /** Template for select view
    */
    _template: function(options) {
        return  '<div id="' + options.id + '" class="' + options.cls + '">' +
                    '<select id="' + options.id + '_select" class="select"/>' +
                    '<div class="icon-dropdown"/>' +
                    '<div class="icon-resize">' +
                         '<i class="fa fa-angle-double-right fa-rotate-45"/>' +
                    '</div>' +
                '</div>';
    }
});

return {
    View: View
}

});
