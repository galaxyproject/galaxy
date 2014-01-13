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
            self.chart_3d = nv.models.pieChart()
                .x(function(d) { return d.key })
                .y(function(d) { return d.y })
                .showLabels(true);
                
            d3.select(self.options.svg_id)
                .datum(data)
                .transition().duration(1200)
                .call(self.chart_3d);

            nv.utils.windowResize(self.chart_3d.update);
            
            return self.chart_3d;
        });
    }
});

});