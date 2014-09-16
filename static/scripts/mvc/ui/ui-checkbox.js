// dependencies
define(['utils/utils'], function(Utils) {

// plugin
var View = Backbone.View.extend({
    // options
    optionsDefault: {
        value           : '',
        visible         : true,
        cls             : '',
        data            : [],
        id              : Utils.uuid()
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }
        
        // set initial value
        if (this.options.value) {
            this.value(this.options.value);
        }
        
        // current value
        this.current = this.options.value;
        
        // onchange event handler. fires on user activity.
        var self = this;
        this.$el.find('input').on('change', function() {        
            self.value(self._getValue());
        });
    },
    
    // value
    value : function (new_val) {
        // get current value
        var before = this.current;
        
        // set new value
        if (new_val !== undefined) {
            this.$el.find('label').removeClass('active');
            this.$el.find('[value="' + new_val + '"]').closest('label').addClass('active');
            this.current = new_val;
        }

        // check value
        var after = this.current;
        if (after != before && this.options.onchange) {
            this.options.onchange(this.current);
        }

        // get and return value
        return this.current;
    },
    
    // get value
    _getValue: function() {
        var selected = this.$el.find(':checked');
        var value = null;
        if (selected.length > 0) {
            value = selected.val();
        }
        return value;
    },
    
    // element
    _template: function(options) {
        var tmpl =  '<div class="ui-checkbox">';
        for (key in options.data) {
            var pair = options.data[key];
            tmpl +=     '<input type="checkbox" name="' + options.id + '" value="' + pair.value + '" selected>' + pair.label + '<br>';
        }
        tmpl +=     '</div>';
        return tmpl;
    }
});

return {
    View : View
};

});
