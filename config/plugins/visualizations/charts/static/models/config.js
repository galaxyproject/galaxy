// dependencies
define([], function() {

// model
return Backbone.Model.extend({
    // options
    defaults : {
        query_limit     : 10000,
        query_timeout   : 100
    }
});

});