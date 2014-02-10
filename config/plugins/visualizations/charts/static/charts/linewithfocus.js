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
            self.chart_3d = nv.models.lineWithFocusChart();

            self.chart_3d.xAxis
                .tickFormat(d3.format(',f'));

            self.chart_3d.yAxis
                .tickFormat(d3.format(',.2f'));
            
            d3.select(self.options.svg_id)
                .datum(data)
                .call(self.chart_3d);

            nv.utils.windowResize(self.chart_3d.update);
        });
    }
});

});