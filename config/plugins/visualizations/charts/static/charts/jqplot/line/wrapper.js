define( [ 'plugin/charts/jqplot/common/wrapper' ], function( Plot ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            new Plot( app, options );
        }
    });
});