// dependencies
define([], function() {

// model
return Backbone.Model.extend({
    // options
    defaults : {
        key     : 'Data label',
        date    : ''
    },
    
    // reset
    reset: function(){
        this.clear({silent: true}).set(this.defaults);
        this.trigger('reset', this);
    }
});

});