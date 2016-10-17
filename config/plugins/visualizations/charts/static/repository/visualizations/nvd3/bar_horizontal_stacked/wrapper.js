define( [ 'visualizations/nvd3/common/wrapper' ], function( NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            options.type = 'multiBarHorizontalChart';
            options.makeConfig = function( nvd3_model ) {
                nvd3_model.stacked( true );
            };
            new NVD3( options );
        }
    });
});