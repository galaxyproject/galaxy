define( [], function() {
    return Backbone.Model.extend({
        defaults : {
            query_limit     : 10000,
            query_timeout   : 100
        }
    });
});