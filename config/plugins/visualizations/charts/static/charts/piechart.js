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
    refresh : function()
    {
        // add graph to screen
        var self = this;
        nv.addGraph(function(data) {
            self.chart_3d = nv.models.pieChart()
                .x(function(d) { return d.key })
                .y(function(d) { return d.y })
                .color(d3.scale.category10().range())
                .height(250)
                .width(250);
                
            d3.select(self.options.svg_id)
                .datum(self._data())
                .transition().duration(1200)
                .attr('height', 250)
                .attr('width', 250)
                .call(self.chart_3d);

            nv.utils.windowResize(self.chart_3d.update);
        });
    },
    
    _data : function() {
        return [
        {
            key: "Cumulative Return",
            values: [
            {
                key : "CDS / Options" ,
                y   : 29.765957771107
            },
            {
                key : "Options" ,
                y   : 19.765957771107
            },
            {
                key : "Other" ,
                y   : 12.765957771107
            }]
        }];
    }
});

});