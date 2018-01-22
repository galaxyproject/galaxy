define( [ 'visualizations/nvd3/common/wrapper' ], function( NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            options.type = 'multiBarChart';
            new NVD3( options );
        }
    });
});