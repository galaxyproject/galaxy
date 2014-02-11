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
            self.d3_chart = nv.models.multiBarHorizontalChart();
            
            self.d3_chart.xAxis.tickFormat(function() { return ''; });
            
            d3.select(self.options.svg_id)
                .datum(data)
                .call(self.d3_chart);
 
            nv.utils.windowResize(self.d3_chart.update);
        });
    }
});

});