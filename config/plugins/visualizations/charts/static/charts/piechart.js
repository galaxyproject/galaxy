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
        // loop through data groups
        for (var key in data) {
            // get group
            var group = data[key];
            
            // format chart data
            var pie_data = [];
            for (var key in group.values) {
                var value = group.values[key];
                pie_data.push ({
                    key : value.x,
                    y   : value.y
                });
            }
            
            // add graph to screen
            var self = this;
            nv.addGraph(function() {
                self.chart_3d = nv.models.pieChart()
                    .donut(true)
                    .showLegend(false);
                
                d3.select(self.options.svg_id)
                    .datum(pie_data)
                    .call(self.chart_3d);

                nv.utils.windowResize(self.chart_3d.update);
                
                return self.chart_3d;
            });
        }
    }
});

});