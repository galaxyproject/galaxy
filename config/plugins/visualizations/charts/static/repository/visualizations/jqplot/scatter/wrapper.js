define( [ 'visualizations/jqplot/common/wrapper' ], function( Plot ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            options.makeConfig = function( groups, plot_config ) {
                $.extend( true, plot_config, {
                    seriesDefaults: {
                        renderer: $.jqplot.LineRenderer,
                        showLine: false,
                        markerOptions : {
                            show    : true
                        }
                    }
                });
            };
            new Plot( options );
        }
    });
});