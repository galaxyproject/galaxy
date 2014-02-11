// dependencies
define([], function() {


// model
return Backbone.Model.extend(
{
    // options
    defaults : {
        query_limit     : 20,
        query_pace      : 1000,
        query_max       : 5
    }
});

});