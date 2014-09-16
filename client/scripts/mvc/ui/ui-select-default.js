// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class creates/wraps a default html select field as backbone class.
 */
var View = Backbone.View.extend({
    // options
    optionsDefault : {
        id          : '',
        cls         : '',
        empty       : 'No data available',
        visible     : true,
        wait        : false,
        multiple    : false
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        // link elements
        this.$select = this.$el.find('#select');
        this.$icon = this.$el.find('#icon');
        
        // configure multiple
        if (this.options.multiple) {
            this.$select.prop('multiple', true);
            this.$select.addClass('ui-select-multiple');
            this.$icon.remove();
        } else {
            this.$el.addClass('ui-select');
        }
        
        // refresh
        this.update(this.options.data);
        
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
        var self = this;
        this.$select.on('change', function() {
            self._change();
        });
        
        // add change event. fires on trigger
        this.on('change', function() {
            self._change();
        });
    },
    
    // value
    value : function (new_value) {
        if (new_value !== undefined) {
            this.$select.val(new_value);
        }
        return this.$select.val();
    },
    
    // first
    first: function() {
        var options = this.$select.find('option');
        if (options.length > 0) {
            return options.val();
        } else {
            return undefined;
        }
    },
    
    // label
    text : function () {
        return this.$select.find('option:selected').text();
    },
    
    // show
    show: function() {
        this.$icon.removeClass();
        this.$icon.addClass('fa fa-caret-down');
        this.$select.show();
        this.$el.show();
    },
    
    // hide
    hide: function() {
        this.$el.hide();
    },
    
    // wait
    wait: function() {
        this.$icon.removeClass();
        this.$icon.addClass('fa fa-spinner fa-spin');
        this.$select.hide();
    },
    
    // disabled
    disabled: function() {
        return this.$select.is(':disabled');
    },

    // enable
    enable: function() {
        this.$select.prop('disabled', false);
    },
        
    // disable
    disable: function() {
        this.$select.prop('disabled', true);
    },
    
    // add
    add: function(options) {
        // add options
        this.$select.append(this._templateOption(options));
        
        // refresh
        this._refresh();
    },
    
    // remove
    del: function(value) {
        // remove option
        this.$select.find('option[value=' + value + ']').remove();
        this.$select.trigger('change');
        
        // refresh
        this._refresh();
    },
    
    // render
    update: function(options) {
        // backup current value
        var current = this.$select.val();
        
        // remove all options
        this.$select.find('option').remove();

        // add new options
        for (var key in options) {
            this.$select.append(this._templateOption(options[key]));
        }
        
        // refresh
        this._refresh();
        
        // set previous value
        this.$select.val(current);
        
        // check if any value was set
        if (!this.$select.val()) {
            this.$select.val(this.first());
        }
    },
    
    // set on change event
    setOnChange: function(callback) {
        this.options.onchange = callback;
    },
    
    // check if selected value exists
    exists: function(value) {
        return this.$select.find('option[value="' + value + '"]').length > 0;
    },
    
    // change
    _change: function() {
        if (this.options.onchange) {
            this.options.onchange(this.$select.val());
        }
    },
    
    // refresh
    _refresh: function() {
        // remove placeholder
        this.$select.find('option[value=null]').remove();
        
        // count remaining entries
        var remaining = this.$select.find('option').length;
        if (remaining == 0) {
            // disable select field
            this.disable();
        
            // append placeholder
            this.$select.append(this._templateOption({value : 'null', label : this.options.empty}));
        } else {
            // enable select field
            this.enable();
        }
    },
    
    // template option
    _templateOption: function(options) {
        return '<option value="' + options.value + '">' + options.label + '</option>';
    },
    
    // template
    _template: function(options) {
        return  '<div id="' + options.id + '">' +
                    '<div class="button">' +
                        '<i id="icon"/>' +
                    '</div>' +
                    '<select id="select" class="select ' + options.cls + ' ' + options.id + '"></select>' +
                '</div>';
    }
});

return {
    View: View
}

});
