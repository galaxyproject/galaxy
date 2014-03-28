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
    draw : function(process_id, nvd3_model, chart, request_dictionary, callback)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function(data) {
            nv.addGraph(function() {
                // x axis
                if (chart.settings.get('x_axis_type') == 'hide') {
                    nvd3_model.xAxis.tickFormat(function() { return '' });
                } else {
                    var tick = chart.settings.get('x_axis_tick') + chart.settings.get('x_axis_type');
                    nvd3_model.xAxis.tickFormat(d3.format(tick));
                }
                
                // x axis label
                nvd3_model.xAxis.axisLabel(chart.settings.get('x_axis_label'));
                
                // y axis
                if (chart.settings.get('y_axis_type') == 'hide') {
                    nvd3_model.yAxis.tickFormat(function() { return '' });
                } else {
                    var tick = chart.settings.get('y_axis_tick') + chart.settings.get('y_axis_type');
                    nvd3_model.yAxis.tickFormat(d3.format(tick));
                }
                
                // y axis label
                nvd3_model.yAxis.axisLabel(chart.settings.get('y_axis_label'))
                                .axisLabelDistance(30);
                
                // controls
                if (chart.groups.length == 1) {
                    nvd3_model.options({ showControls: false });
                }
                
                // legend
                var legend_visible = true;
                if (chart.settings.get('show_legend') == 'false') {
                    legend_visible = false;
                }
                nvd3_model.showLegend(legend_visible);
                
                // custom callback
                if (callback) {
                    callback(nvd3_model);
                }
                
                // parse data to svg
                self.options.svg.datum(data)
                                .call(nvd3_model);
     
                // refresh on window resize
                nv.utils.windowResize(nvd3_model.update);
                
                // set chart state
                chart.state('ok', 'Chart has been drawn.');
                
                // unregister process
                chart.deferred.done(process_id);
            });
        });
    }
});

});