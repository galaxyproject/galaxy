// dependencies
define(['utils/utils'], function(Utils) {

// plugin
return Backbone.View.extend({

    // default options
    optionsDefault: {
        icons : ['fa fa-square-o', 'fa fa-minus-square-o', 'fa fa-check-square-o'],
        value : 0
    },

    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement($('<div/>'));

        // set initial value
        this.value(this.options.value);

        // add event handler
        var self = this;
        this.$el.on('click', function() {
            self.current = (!self.current && 2) || 0;
            self.value(self.current);
            self.options.onclick && self.options.onclick();
        });
    },

    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            this.current = new_val;
            this.$el.removeClass()
                    .addClass('ui-checkbutton')
                    .addClass(this.options.icons[new_val]);
            this.options.onchange && this.options.onchange(new_val);
        }
        return this.current;
    }
});
});