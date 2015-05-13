// dependencies
define(['utils/utils'], function(Utils) {

// plugin
return Backbone.View.extend({

    // default options
    optionsDefault: {
        icons : ['fa fa-square-o', 'fa fa-minus-square-o', 'fa fa-check-square-o'],
        value : 0,
        title : 'Select/Unselect all'
    },

    // initialize
    initialize: function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement(this._template());
        this.$title = this.$('.title');
        this.$icon  = this.$('.icon');

        // set initial value
        this.value(this.options.value);

        // set title
        this.$title.html(this.options.title);

        // add event handler
        var self = this;
        this.$el.on('click', function() {
            self.current = (self.current === 0 && 2) || 0;
            self.value(self.current);
            self.options.onclick && self.options.onclick();
        });
    },

    /* Sets a new value and/or returns the current value.
    * @param{Integer}   new_val - Set a new value 0=unchecked, 1=partial and 2=checked.
    * OR:
    * @param{Integer}   new_val - Number of selected options.
    * @param{Integer}   total   - Total number of available options.
    */
    value: function (new_val, total) {
        if (new_val !== undefined) {
            if (total) {
                if (new_val !== 0) {
                    if (new_val !== total) {
                        new_val = 1;
                    } else {
                        new_val = 2;
                    }
                }
            }
            this.current = new_val;
            this.$icon.removeClass()
                      .addClass('icon')
                      .addClass(this.options.icons[new_val]);
            this.options.onchange && this.options.onchange(new_val);
        }
        return this.current;
    },

    /** Template containing the check button and the title
    */
    _template: function() {
        return  '<div class="ui-button-check" >' +
                    '<span class="icon"/>' +
                    '<span class="title"/>' +
                '</div>';
    }
});
});