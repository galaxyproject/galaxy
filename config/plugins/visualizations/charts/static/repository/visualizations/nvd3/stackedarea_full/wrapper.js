define( [ 'visualizations/nvd3/common/wrapper' ], function( NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            options.type = 'stackedAreaChart';
            options.makeConfig = function( nvd3_model ) {
                nvd3_model.style( 'expand' );
            };
            new NVD3( options );
        }
    });
});