define( [ 'plugin/charts/jqplot/common/wrapper' ], function( Plot ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            new Plot( options );
        }
    });
});