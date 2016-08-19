define( [ 'plugin/charts/tools', 'plugin/charts/others/heatmap/heatmap-plugin' ], function( Tools, HeatMap ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            options.render = function( canvas_id, groups ) {
                new HeatMap( app, {
                    chart       : options.chart,
                    canvas_id   : canvas_id,
                    groups      : groups
                });
                return true;
            };
            Tools.panelHelper( app, options );
        }
    });
});