define( [ 'visualizations/utilities/tabular-utilities', 'visualizations/others/heatmap/heatmap-plugin' ], function( Utilities, HeatMap ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            options.render = function( canvas_id, groups ) {
                new HeatMap({
                    chart       : options.chart,
                    canvas_id   : canvas_id,
                    groups      : groups
                });
                return true;
            };
            Utilities.panelHelper( options );
        }
    });
});