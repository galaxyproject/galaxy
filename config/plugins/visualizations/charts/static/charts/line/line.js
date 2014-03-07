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
                self.chart_3d = nv.models.lineChart();

                self.chart_3d.xAxis
                    .tickFormat(d3.format(',f'));

                self.chart_3d.yAxis
                    .tickFormat(d3.format(',.2f'));
                
                self.options.svg.datum(data)
                                .call(self.chart_3d);

                nv.utils.windowResize(self.chart_3d.update);
                
                // set chart state
                chart.set('state', 'ok');
            });
        });
    }
});

});