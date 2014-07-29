// dependencies
define(['plugin/charts/tools', 'plugin/charts/others/heatmap/heatmap-plugin'], function(Tools, HeatMap) {

// widget
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        // define render function
        options.render = function(canvas_id, groups) {
            new HeatMap(app, {
                chart       : options.chart,
                canvas_id   : canvas_id,
                groups      : groups
            });
            return true;
        };
        
        // call panel helper
        Tools.panelHelper(app, options);
    }
});

});