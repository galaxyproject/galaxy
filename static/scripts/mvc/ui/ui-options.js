// dependencies
define(['utils/utils'], function(Utils) {

/** Base class for options based ui elements **/
var OptionsBase = Backbone.View.extend({
    // initialize
    initialize: function(options) {
        // options
        this.optionsDefault = {
            value       : [],
            visible     : true,
            data        : [],
            id          : Utils.uuid(),
            errorText   : 'No data available.',
            waitText    : 'Please wait...'
        };
    
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    
        // create new element
        this.setElement('<div style="display: inline-block;"/>');
        
        // create elements
        this.$message = $('<div/>');
        this.$options = $(this._template(options));
        
        // append
        this.$el.append(this.$message);
        this.$el.append(this.$options);
        
        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }
        
        // initialize data
        this.update(this.options.data);
        
        // set initial value
        if (this.options.value) {
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
        this.$el.find('.ui-option').remove();

        // add new options
        for (var key in options) {
            // load option template
            var $option = $(this._templateOption(options[key]));
            $option.addClass('ui-option');
            
            // append to dom
            this.$options.append($option);
        }
        
        // add change events
        var self = this;
        this.$el.find('input').on('change', function() {
            self.value(self._getValue());
            self._change();
        });
        
        // refresh
        this._refresh();
        
        // set previous value
        this.value(current);
    },
    
    /** Check if selected value exists (or any if multiple)
    */
    exists: function(value) {
        if (typeof value === 'string') {
            value = [value];
        }
        for (var i in value) {
            if (this.$el.find('input[value="' + value[i] + '"]').length > 0) {
                return true;
            }
        }
        return false;
    },
    
    /** Return first available option
    */
    first: function() {
        var options = this.$el.find('input');
        if (options.length > 0) {
            return options.val();
        } else {
            return undefined;
        }
    },
    
    /** Validate the selected option/options
    */
    validate: function() {
        var current = this.value();
        if (!(current instanceof Array)) {
            current = [current];
        }
        for (var i in current) {
            if ([null, 'null', undefined].indexOf(current[i]) > -1) {
                return false;
            }
        }
        return true;
    },
    
    /** Wait message during request processing
    */
    wait: function() {
        if (this._size() == 0) {
            this._messageShow(this.options.waitText, 'info');
            this.$options.hide();
        }
    },
    
    /** Hide wait message
    */
    unwait: function() {
        this._messageHide();
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
        if (this._size() == 0) {
            this._messageShow(this.options.errorText, 'danger');
            this.$options.hide();
        } else {
            this._messageHide();
            this.$options.css('display', 'inline-block');
        }
    },
            
    /** Return current selection
    */
    _getValue: function() {
        // get selected values
        var selected = this.$el.find(':checked');
        if (selected.length == 0) {
            return 'null';
        }
        
        // return multiple or single value
        if (this.options.multiple) {
            var values = [];
            selected.each(function() {
                values.push($(this).val());
            });
            return values;
        } else {
            return selected.val();
        }
    },
    
    /** Returns the number of options
    */
    _size: function() {
        return this.$el.find('.ui-option').length;
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
    }
});

/** Radio button field **/
var Radio = {};
Radio.View = OptionsBase.extend({
    // initialize
    initialize: function(options) {
        OptionsBase.prototype.initialize.call(this, options);
    },
    
    /** Return/Set current value
    */
    value: function (new_val) {
        // check if its an array
        if (typeof new_val === 'string') {
            new_val = [new_val];
        }
        
        // set new value
        if (new_val !== undefined) {
            // reset selection
            this.$el.find('input').prop('checked', false);
            
            // update to new selection
            for (var i in new_val) {
                this.$el.find('input[value="' + new_val[i] + '"]').prop('checked', true);
            };
        }
        
        // get and return value
        return this._getValue();
    },
    
    /** Template for options
    */
    _templateOption: function(pair) {
        return  '<div>' +
                    '<input type="radio" name="' + this.options.id + '" value="' + pair.value + '"/>' + pair.label + '<br>' +
                '</div>';
    },
    
    /** Main template function
    */
    _template: function() {
        return '<div class="ui-options"/>';
    }
});

/** Checkbox options field **/
var Checkbox = {};
Checkbox.View = Radio.View.extend({
    // initialize
    initialize: function(options) {
        options.multiple = true;
        Radio.View.prototype.initialize.call(this, options);
    },
    
    /** Template for options
    */
    _templateOption: function(pair) {
        return  '<div>' +
                    '<input type="checkbox" name="' + this.options.id + '" value="' + pair.value + '"/>' + pair.label + '<br>' +
                '</div>';
    }
});

/** Radio button options field styled as classic buttons **/
var RadioButton = {};
RadioButton.View = OptionsBase.extend({
    // initialize
    initialize: function(options) {
        OptionsBase.prototype.initialize.call(this, options);
    },
    
    /** Return/Set current value
    */
    value: function (new_val) {
        // set new value
        if (new_val !== undefined) {
            this.$el.find('input').prop('checked', false);
            this.$el.find('label').removeClass('active');
            this.$el.find('[value="' + new_val + '"]').prop('checked', true).closest('label').addClass('active');
        }
        
        // get and return value
        return this._getValue();
    },
    
    /** Template for options
    */
    _templateOption: function(pair) {
        var tmpl =  '<label class="btn btn-default">';
        if (pair.icon) {
            tmpl +=     '<i class="fa ' + pair.icon + '"/>';
        }
        tmpl +=         '<input type="radio" name="' + this.options.id + '" value="' + pair.value + '">' + pair.label +
                    '</label>';
        return tmpl;
    },
    
    /** Main template function
    */
    _template: function() {
        return '<div class="btn-group ui-radiobutton" data-toggle="buttons"/>';
    }
});

return {
    Radio       : Radio,
    RadioButton : RadioButton,
    Checkbox    : Checkbox
};

});
