// dependencies
define(['library/utils'], function(Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
        this.chart      = options.chart;
    },
            
    // render
    refresh : function(data)
    {
        // add graph to screen
        var self = this;
        nv.addGraph(function() {
            // check data
            var valid = true;
            var length = 0;
            for (var key in data) {
                // evalute length
                if (length == 0) {
                    length = data[key].values.length;
                } else {
                    if (length != data[key].values.length) {
                        valid = false;
                        break;
                    }
                }
            }
            if (!valid) {
                return;
            }
            
            // make plot
            self.d3_chart = nv.models.stackedAreaChart()
                .x(function(d) {
                    return d.x
                })
                .y(function(d) {
                    return d.y
                })
                .clipEdge(true);
            
            self.d3_chart.xAxis.tickFormat(function() { return ''; });
            
            d3.select(self.options.svg_id)
                .datum(data)
                .call(self.d3_chart);
 
            nv.utils.windowResize(self.d3_chart.update);
        });
    }
});

});