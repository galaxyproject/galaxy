// dependencies
define(['utils/utils'], function(Utils) {

/** base class for options based ui elements **/
var OptionsBase = Backbone.View.extend({
    // settings
    settings : {
        multiple    : false
    },
    
    // options
    optionsDefault: {
        value       : [],
        visible     : true,
        data        : [],
        id          : Utils.uuid(),
        empty       : 'No data available'
    },

    // initialize
    initialize: function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    
        // create new element
        this.setElement(this._template(this.options));
        
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
    
    // update options
    update: function(options) {
        // backup current value
        var current = this._getValue();
        
        // remove all options
        this.$el.find('.ui-option').remove();

        // add new options
        for (var key in options) {
            this.$el.append(this._templateOption(options[key]));
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
    
    // check if selected value exists (or any if multiple)
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
    
    // first
    first: function() {
        var options = this.$el.find('input');
        if (options.length > 0) {
            return options.val();
        } else {
            return undefined;
        }
    },
    
    // change
    _change: function() {
        if (this.options.onchange) {
            this.options.onchange(this._getValue());
        }
    },
    
    // refresh
    _refresh: function() {
        // remove placeholder
        this.$el.find('.ui-error').remove();
        
        // count remaining options
        var remaining = this.$el.find('input').length;
        if (remaining == 0) {
            this.$el.append(this._templateEmpty());
        }
    },
            
    // get value
    _getValue: function() {
        // get selected values
        var selected = this.$el.find(':checked');
        if (selected.length == 0) {
            return null;
        }
        
        // return multiple or single value
        if (this.settings.multiple) {
            var values = [];
            selected.each(function() {
                values.push($(this).val());
            });
            return values;
        } else {
            return selected.val();
        }
    },

    // template for options
    _templateEmpty: function() {
        return  '<div class="ui-error">' + this.options.empty + '</div>';
    }
});

/** checkbox options field **/
var Checkbox = {};
Checkbox.View = OptionsBase.extend({
    // initialize
    initialize: function(options) {
        this.settings.multiple = true;
        OptionsBase.prototype.initialize.call(this, options);
    },
    
    // value
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
                this.$el.find('input[value=' + new_val[i] + ']').prop('checked', true);
            };
        }
        
        // get and return value
        return this._getValue();
    },
    
    // template for options
    _templateOption: function(pair) {
        return  '<div class="ui-option">' +
                    '<input type="checkbox" name="' + this.options.id + '" value="' + pair.value + '"/>' + pair.label + '<br>' +
                '</div>';
    },
    
    // template
    _template: function() {
        return '<div class="ui-checkbox"/>';
    }
});

/** radio button options field **/
var RadioButton = {};
RadioButton.View = OptionsBase.extend({
    // initialize
    initialize: function(options) {
        OptionsBase.prototype.initialize.call(this, options);
    },
    
    // value
    value: function (new_val) {
        // set new value
        if (new_val !== undefined) {
            this.$el.find('label').removeClass('active');
            this.$el.find('[value="' + new_val + '"]').closest('label').addClass('active');
        }
        
        // get and return value
        return this._getValue();
    },
    
    // template for options
    _templateOption: function(pair) {
        return  '<label class="btn btn-default">' +
                    '<input type="radio" name="' + this.options.id + '" value="' + pair.value + '">' + pair.label +
                '</label>';
    },
    
    // template
    _template: function() {
        return '<div class="btn-group ui-radiobutton" data-toggle="buttons"/>';
    }
});

return {
    Checkbox    : Checkbox,
    RadioButton : RadioButton
};

});
