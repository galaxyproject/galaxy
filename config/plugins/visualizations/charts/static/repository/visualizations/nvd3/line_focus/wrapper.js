define( [ 'visualizations/nvd3/common/wrapper' ], function( NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            options.type = 'lineWithFocusChart';
            new NVD3( options );
        }
    });
});