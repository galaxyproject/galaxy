// dependencies
define(['utils/utils', 'plugin/charts/heatmap/heatmap-plugin', 'plugin/charts/heatmap/heatmap-parameters'],
function(Utils, HeatmapPlugin, HeatmapParameters) {

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
        // link this
        var self = this;
        
        // loop through data groups
        var index = 0;
        for (var group_index in request_dictionary.groups) {
            
            // configure request
            for (var i in request_dictionary.groups) {
                var group = request_dictionary.groups[i];
                group.columns = null;
                group.columns = {
                    row_label: {
                        index       : index++,
                        is_label    : true
                    },
                    col_label: {
                        index       : index++,
                        is_label    : true
                    },
                    value: {
                        index       : index++
                    }
                }
            }
        
            // request data
            this.app.datasets.request(request_dictionary, function() {
            
                // get group
                var group = request_dictionary.groups[group_index];
                var div = self.options.canvas[group_index];

                // draw plot
                var heatmap = new HeatmapPlugin({
                    'title'     : group.key,
                    'colors'    : HeatmapParameters.colorSets[chart.settings.get('color_set')],
                    'data'      : group.values,
                    'div'       : div
                });
                
                // check if done
                if (group_index == request_dictionary.groups.length - 1) {
                    // set chart state
                    chart.state('ok', 'Heat map drawn.');
                
                    // unregister process
                    chart.deferred.done(process_id);
                }
            });
        }
    }
});

});