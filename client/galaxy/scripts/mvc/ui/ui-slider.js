// dependencies
define(['utils/utils'], function(Utils) {

// plugin
var View = Backbone.View.extend({
    // options
    optionsDefault: {
        value   : '',
        min     : 1,
        max     : 100,
        step    : 1
    },
    
    // initialize
    initialize : function(options) {
        // link this
        var self = this;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // backup slider
        this.$slider = this.$el.find('#slider');
        
        // backup integer field
        this.$text = this.$el.find('#text');
        
        // load slider plugin
        this.$slider.slider(this.options);
        
        // add text field event
        this.$text.on('change', function () {
           self.value($(this).val());
        });
        
        // add text field event
        this.$text.on('keydown', function (event) {
            var v = event.which;
            if (!(v == 13 || v == 8 || v == 37 || v == 39 || v == 189 || (v >= 48 && v <= 57)
                || (self.options.step != 1 && $(this).val().indexOf('.') == -1) && v == 190)) {
                event.preventDefault();
            }
        });
        
        // add slider event
        this.$slider.on('slide', function (event, ui) {
           self.value(ui.value);
        });
    },
    
    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            // limit
            new_val = Math.max(Math.min(new_val, this.options.max), this.options.min);
            
            // trigger on change event
            if (this.options.onchange) {
                this.options.onchange(new_val);
            }
        
            // set values
            this.$slider.slider('value', new_val);
            this.$text.val(new_val);
        }
        
        // return current value
        return this.$text.val();
    },
    
    // element
    _template: function(options) {
        return  '<div id="' + options.id + '" class="ui-form-slider">' +
                    '<input id="text" type="text" class="ui-form-slider-text"/>' +
                    '<div id="slider" class="ui-form-slider-element"/>' +
                '</div>';
    }
});

return {
    View : View
};

});
