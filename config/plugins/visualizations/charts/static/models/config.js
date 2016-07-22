define( [], function() {
    return Backbone.Model.extend({
        defaults : {
            query_limit     : 1000,
            query_timeout   : 100
        }
    });
});