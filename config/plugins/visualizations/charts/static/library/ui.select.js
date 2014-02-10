// dependencies
define(['library/utils'], function(Utils) {

// plugin
return Backbone.View.extend(
{
    // options
    optionsDefault: {
        id      : '',
        cls     : '',
        empty   : 'No data available'
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        // add change event
        var self = this;
        if (this.options.onchange) {
            this.$el.on('change', function() { self.options.onchange(self.value()); });
        }
        
        // refresh
        this._refresh();
    },
    
    // value
    value : function (new_value) {
        // get current id/value
        var before = this.$el.val();
        
        // check if new_value is defined
        if (new_value !== undefined) {
            this.$el.val(new_value);
        }
        
        // get current id/value
        var after = this.$el.val();
        if(after === undefined) {
            return null;
        } else {
            // fire onchange
            if ((after != before && this.options.onchange) || this.$el.find('option').length == 1) {
                this.options.onchange(after);
            }
            
            // return current value
            return after;
        }
    },
    
    // label
    label : function () {
        return this.$el.find('option:selected').text();
    },
    
    // disabled
    disabled: function() {
        return this.$el.is(':disabled');
    },

    // enable
    enable: function() {
        this.$el.prop('disabled', false);
    },
        
    // disable
    disable: function() {
        this.$el.prop('disabled', true);
    },
    
    // add
    add: function(options) {
        // add options
        $(this.el).append(this._templateOption(options));
        
        // refresh
        this._refresh();
    },
    
    // remove
    remove: function(value) {
        // remove option
        $(this.el).find('option[value=' + value + ']').remove();
        $(this.el).trigger('change');
        
        // refresh
        this._refresh();
    },
    
    // render
    update: function(options) {
        // selected
        var selected = this.$el.val();

        // remove all options
        $(this.el).find('option').remove();

        // add new options
        for (var key in options.data) {
            $(this.el).append(this._templateOption(options.data[key]));
        }
        
        // add selected value
        if (this._exists(selected))
            $(this.el).val(selected);
        
        // refresh
        this._refresh();
    },
    
    // refresh
    _refresh: function() {
        // remove placeholder
        $(this.el).find('option[value=null]').remove();
        
        // count remaining entries
        var remaining = $(this.el).find('option').length;
        if (remaining == 0) {
            // append placeholder
            $(this.el).append(this._templateOption({value : 'null', label : this.options.empty}));
            this.disable();
        } else {
            this.enable();
        }
    },
    
    // exists
    _exists: function(value) {
        // check if selected value exists
        return 0 != $(this.el).find('option[value=' + value + ']').length;
    },
    
    // option
    _templateOption: function(options) {
        return '<option value="' + options.value + '">' + options.label + '</option>';
    },
    
    // element
    _template: function(options) {
        var tmpl =  '<select id="' + options.id + '" class="select ' + options.cls + ' ' + options.id + '">';
        for (key in options.data) {
            // options
            var item = options.data[key];
            
            // identify selected value
            var tag = '';
            if (item.value == options.selected || item.value == '') {
                tag = 'selected';
            }
            
            // add template string
            tmpl +=     '<option value="' + item.value + '" ' + tag + '>' + item.label + '</option>';
        }
        tmpl +=     '</select>';
        return tmpl;
    }
});

});
