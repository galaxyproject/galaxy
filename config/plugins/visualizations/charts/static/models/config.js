// dependencies
define([], function() {

// model
return Backbone.Model.extend({
    // options
    defaults : {
        query_limit     : 500,
        query_timeout   : 100
    }
});

});