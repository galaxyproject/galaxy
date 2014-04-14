// dependencies
define(['utils/utils'], function(Utils) {

// plugin
var View = Backbone.View.extend(
{
    // options
    optionsDefault: {
        id      : '',
        cls     : '',
        empty   : 'No data available',
        visible : true,
        wait    : false
    },
    
    // value
    selected : null,
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        // link elements
        this.$select = this.$el.find('#select');
        this.$icon = this.$el.find('#icon');
        
        // initial value
        this.selected = this.options.value;
        
        // add change event
        var self = this;
        if (this.options.onchange) {
            this.$select.on('change', function() {
                self.value(self.$select.val());
            });
        }
        
        // refresh
        this._refresh();
        
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
    },
    
    // value
    value : function (new_value) {
        
        // get current id/value
        var before = this.selected;
        
        // check if new_value is defined
        if (new_value !== undefined) {
            this.selected = new_value;
            this.$select.val(new_value);
        }
        
        // get current id/value
        var after = this.selected;
        if(after) {
            // fire onchange
            if ((after != before && this.options.onchange)) {
                this.options.onchange(after);
            }
        }
        
        // return
        return after;
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
        // remove all options
        this.$select.find('option').remove();

        // add new options
        for (var key in options) {
            this.$select.append(this._templateOption(options[key]));
        }
        
        // select first option if nothing else is selected
        if (!this.selected && options.length > 0) {
            this.value(options[0].value);
        }
        
        // refresh
        this._refresh();
    },
    
    // refresh
    _refresh: function() {
        // remove placeholder
        this.$select.find('option[value=null]').remove();
        
        // count remaining entries
        var remaining = this.$select.find('option').length;
        if (remaining == 0) {
            // append placeholder
            this.$select.append(this._templateOption({value : 'null', label : this.options.empty}));
            this.disable();
        } else {
            // enable select field
            this.enable();
            
            // update selected value
            if (this.selected) {
                this.$select.val(this.selected);
            }
        }
    },
    
    // exists
    _exists: function(value) {
        // check if selected value exists
        return 0 != this.$select.find('option[value=' + value + ']').length;
    },
    
    // option
    _templateOption: function(options) {
        return '<option value="' + options.value + '">' + options.label + '</option>';
    },
    
    // element
    _template: function(options) {
        var tmpl =  '<div id="' + options.id + '" class="styled-select">' +
                        '<div class="button">' +
                            '<i id="icon"/>' +
                        '</div>' +
                        '<select id="select" class="select ' + options.cls + ' ' + options.id + '">';
        for (key in options.data) {
            // options
            var item = options.data[key];
            
            // identify selected value
            var tag = '';
            if (item.value == options.value || item.value == '') {
                tag = 'selected';
            }
            
            // add template string
            tmpl +=         '<option value="' + item.value + '" ' + tag + '>' + item.label + '</option>';
        }
        tmpl +=         '</select>' +
                    '</div>';
        return tmpl;
    }
});

return {
    View: View
}

});
