// dependencies
define([], function() {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    refresh : function(data)
    {
        // add graph to screen
        var self = this;
        nv.addGraph(function() {
            self.d3_chart = nv.models.multiBarChart();
                
            self.d3_chart.xAxis.tickFormat(d3.format('.2f'))
            self.d3_chart.yAxis.tickFormat(d3.format('.1f'))
            
            d3.select(self.options.svg_id)
                .datum(data)
                .call(self.d3_chart);
 
            nv.utils.windowResize(self.d3_chart.update);
        });
    }
});

});