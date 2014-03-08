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
                
                if (chart.settings.get('x_axis_type') == 'hide') {
                    nvd3_model.xAxis.tickFormat(function() { return '' });
                } else {
                    var tick = chart.settings.get('x_axis_tick') + chart.settings.get('x_axis_type');
                    nvd3_model.xAxis.tickFormat(d3.format(tick));
                }
                
                nvd3_model.xAxis.axisLabel(chart.settings.get('x_axis_label'));
                
                if (chart.settings.get('y_axis_type') == 'hide') {
                    nvd3_model.yAxis.tickFormat(function() { return '' });
                } else {
                    var tick = chart.settings.get('y_axis_tick') + chart.settings.get('y_axis_type');
                    nvd3_model.yAxis.tickFormat(d3.format(tick));
                }
                
                nvd3_model.yAxis.axisLabel(chart.settings.get('y_axis_label'))
                                .axisLabelDistance(30);
                
                if (chart.groups.length == 1) {
                    nvd3_model.options({ showControls: false });
                }
                
                //nvd3_model.useInteractiveGuideline(true);
                
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