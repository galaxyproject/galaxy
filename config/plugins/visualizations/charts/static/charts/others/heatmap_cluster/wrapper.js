// dependencies
define(['plugin/charts/tools', 'plugin/charts/others/heatmap/heatmap-plugin'], function(Tools, HeatMap) {

// widget
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary, canvas_list) {
        // configure request
        var index = 0;
        var tmp_dict = {
            id      : request_dictionary.id,
            groups  : []
        };
        
        // configure groups
        for (var group_index in request_dictionary.groups) {
            var group = request_dictionary.groups[group_index];
            tmp_dict.groups.push({
                key     : group.key,
                columns : {
                    x: {
                        index       : index++,
                        is_label    : true
                    },
                    y: {
                        index       : index++,
                        is_label    : true
                    },
                    z: {
                        index       : index++
                    }
                }
            });
        }
        
        // backup chart
        this.chart = chart;
        
        // distribute data groups on svgs and handle process
        var self = this;
        var plot = Tools.panelHelper({
            app                 : this.app,
            canvas_list         : canvas_list,
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : tmp_dict,
            render              : function(canvas_id, groups) {
                                    this.heatmap = new HeatMap(app, {
                                        chart       : chart,
                                        canvas_id   : canvas_id,
                                        groups      : groups
                                    });
                                    return true;
                                  }
        });
    }
});

});