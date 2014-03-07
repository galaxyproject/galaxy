// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(chart, request_dictionary)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function(data) {
            nv.addGraph(function() {
                self.d3_chart = nv.models.scatterChart()
                    .showDistX(true)
                    .showDistY(true)
                    .color(d3.scale.category10().range());
                    
                self.d3_chart.xAxis.tickFormat(d3.format('.02f'))
                self.d3_chart.yAxis.tickFormat(d3.format('.02f'))
                
                self.options.svg.datum(data)
                                .call(self.d3_chart);
     
                nv.utils.windowResize(self.d3_chart.update);
                
                // set chart state
                chart.set('state', 'ok');
            });
        });
    }
});

});