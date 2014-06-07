// dependencies
define(['plugin/charts/tools', 'plugin/plugins/nvd3/nv.d3'], function(Tools) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
    
    // render
    draw : function(type, process_id, chart, request_dictionary, callback) {
        var self = this;
        var plot = Tools.panelHelper({
            app                 : this.app,
            process_id          : process_id,
            canvas              : this.options.canvas,
            chart               : chart,
            request_dictionary  : request_dictionary,
            render              : function(chart, groups, canvas) {
                                    return self.render(type, chart, groups, canvas, callback)
                                }
        });
    },
    
    // render
    render : function(type, chart, groups, canvas, callback)
    {
        // create nvd3 model
        var d3chart = nv.models[type]();
        
        // request data
        var self = this;
        nv.addGraph(function() {
            try {
                // x axis
                self._axis(d3chart.xAxis, chart.settings.get('x_axis_type'), chart.settings.get('x_axis_tick'));
                
                // x axis label
                d3chart.xAxis.axisLabel(chart.settings.get('x_axis_label'));
                
                // y axis
                self._axis(d3chart.yAxis, chart.settings.get('y_axis_type'), chart.settings.get('y_axis_tick'));
                
                // y axis label
                d3chart.yAxis.axisLabel(chart.settings.get('y_axis_label'))
                                .axisLabelDistance(30);
                
                // controls
                d3chart.options({showControls: false});
                
                // legend
                if (d3chart.showLegend) {
                    var legend_visible = true;
                    if (chart.settings.get('show_legend') == 'false') {
                        legend_visible = false;
                    }
                    d3chart.showLegend(legend_visible);
                }
                
                // custom callback
                if (callback) {
                    callback(d3chart);
                }
                
                // parse data to canvas
                canvas.datum(groups)
                      .call(d3chart);
     
                
                // refresh on window resize
                nv.utils.windowResize(d3chart.update);
            } catch (err) {
                self._handleError(chart, err);
            }
        });
        
        return true;
    },
    
    // make axis
    _axis: function(axis, type, tick) {
        switch (type) {
            case 'hide':
                axis.tickFormat(function() { return '' });
                break;
            case 'auto':
                break;
            default:
                axis.tickFormat(d3.format(tick + type));
        }
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});