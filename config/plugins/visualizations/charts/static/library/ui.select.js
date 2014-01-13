// dependencies
define(['library/utils'], function(Utils) {


// plugin
return Backbone.View.extend(
{
    // options
    optionsDefault: {
        id  : '',
        cls : ''
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this.template(this.options));
        
        // add change event
        var self = this;
        if (this.options.onchange) {
            this.$el.on('change', function() { self.options.onchange(self.value()) });
        }
    },
    
    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            this.$el.val(new_val);
        }
        return this.$el.val();
    },
    
    // label
    label : function () {
        return this.$el.find('option:selected').text();
    },
    
    // disabled
    disabled: function() {
        return this.$el.is(':disabled');
    },
    
    // render
    update: function(options) {
        // selected
        var selected = this.$el.val();

        // remove all options
        $(this.el).find('option').remove();

        // add new options
        for (var key in options.data) {
            $(this.el).append(this.templateOption(options.data[key]));
        }
        
        // check if selected value exists
        var exists = 0 != $(this.el).find('option[value=' + selected + ']').length;
        
        // add selected value
        if (exists)
            $(this.el).val(selected);
    },
    
    // update from url
    updateUrl : function(options, callback) {
        // get json
        var self = this;
        Utils.get(options.url, function(json) {
            // write data into array
            var data = [];
            for (key in json) {
                data.push({label: json[key].name, value: json[key].id});
            }

            // check if disabled. do not update disabled select elements.
            if (!self.disabled()) {
                self.update({data: data});
            }
            
            // callback
            if (callback) {
                callback();
            }
        });
    },
    
    // option
    templateOption: function(options) {
        return '<option value="' + options.value + '">' + options.label + '</option>';
    },
    
    // element
    template: function(options) {
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
