// dependencies
define([], function() {

// model
return Backbone.Model.extend(
{
    // options
    defaults : {
        query_limit     : 1000,
        query_timeout   : 500
    }
});

});