// dependencies
define(['utils/utils', 'plugin/charts/heatmap/heatmap-plugin'], function(Utils, HeatmapPlugin) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function() {
            
            // loop through data groups
            for (var group_index in request_dictionary.groups) {
                // get group
                var group = request_dictionary.groups[group_index];
            
                // draw plot
                var heatmap = new HeatmapPlugin({
                    'data'  : group.values,
                    'div'   : self.options.canvas[group_index]
                });
            }
            
            // set chart state
            chart.state('ok', 'Heat map drawn.');
                
            // unregister process
            chart.deferred.done(process_id);
        });
    }
});

});