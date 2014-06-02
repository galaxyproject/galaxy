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
            var tmp_dict = {
                id      : request_dictionary.id,
                groups  : [{
                    key     : request_dictionary.groups[group_index].key,
                    columns : {
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
                }]
            };
            
            // target div
            var group_div = self.options.canvas[group_index];
            
            // draw group
            this._draw_group(group_index, group_div, chart, tmp_dict, function(group_index) {
                if (group_index == request_dictionary.groups.length - 1) {
                    // set chart state
                    chart.state('ok', 'Heat map drawn.');
            
                    // unregister process
                    chart.deferred.done(process_id);
                }
            });
        }
    },
    
    // draw group
    _draw_group: function(group_index, div, chart, request_dictionary, callback) {
        // link this
        var self = this;
        
        // request data
        this.app.datasets.request(request_dictionary, function() {
            
            // get group
            var group = request_dictionary.groups[0];
            
            // draw plot
            var heatmap = new HeatmapPlugin({
                'title'     : group.key,
                'colors'    : HeatmapParameters.colorSets[chart.settings.get('color_set')],
                'data'      : group.values,
                'div'       : div
            });
            
            // callback on completion
            callback (group_index);
        });
    }
});

});