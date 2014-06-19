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
        // backup chart
        this.chart = chart;
        
        // distribute data groups on svgs and handle process
        var self = this;
        var plot = Tools.panelHelper({
            app                 : this.app,
            canvas_list         : canvas_list,
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
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