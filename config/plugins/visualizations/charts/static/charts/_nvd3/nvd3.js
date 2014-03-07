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
    draw : function(nvd3_model, chart, request_dictionary, callback)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function(data) {
            nv.addGraph(function() {
                
                nvd3_model.yAxis.tickFormat(d3.format('.1f'))
                                    .axisLabel(chart.settings.get('y_axis_label', 'Frequency'))
                                    .axisLabelDistance(30);
                
                nvd3_model.xAxis.tickFormat(d3.format('.2f'))
                                    .axisLabel(chart.settings.get('x_axis_label', 'Breaks'));
                
                if (callback) {
                    callback(nvd3_model);
                }
                
                self.options.svg.datum(data)
                                .call(nvd3_model);
     
                nv.utils.windowResize(nvd3_model.update);
                
                // set chart state
                chart.set('state', 'ok');
            });
        });
    }
});

});