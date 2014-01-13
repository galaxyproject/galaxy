// dependencies
define(['library/utils'], function(Utils) {


// model
return Backbone.Model.extend(
{
    // defaults
    defaults : {
    },
    
    // initialize
    initialize: function(options)
    {
    },
    
    // reset
    reset: function()
    {
        this.clear().set(this.defaults);
    }
});

});