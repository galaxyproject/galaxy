// dependencies
define(['plugin/charts/jqplot/common/plot-config', 'plugin/charts/tools'], function(configmaker, Tools) {

// widget
return Backbone.View.extend(
{
    // plot series
    plot_series: {
        name                : '',
        data                : [],
        tooltip: {
            headerFormat    : '<em>{point.key}</em><br/>'
        }
    },
    
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary, callback) {
        var self = this;
        var plot = new Tools.panelHelper({
            app                 : this.app,
            process_id          : process_id,
            canvas              : this.options.canvas,
            chart               : chart,
            request_dictionary  : request_dictionary,
            render              : function(groups, canvas) {
                                    return self.render(chart, groups, canvas, callback)
                                }
        });
    },
    
    // draw all data into a single canvas
    render: function(chart, groups, el_canvas, callback) {
        // create configuration
        var plot_config = configmaker(chart);
        var plot_data = []
        
        // identify categories
        this._makeCategories(chart, groups, plot_config, true);
        
        // loop through data groups
        for (var key in groups) {
            // get group
            var group = groups[key];
            
            // reset data
            var data = Tools.makeSeries(group, ['x', 'y']);
            
            // append series
            plot_data.push(data);
        }
        
        // draw plot
        try {
            // canvas
            var canvas = el_canvas[0];
            
            // make custom wrapper callback
            if (callback) {
                callback(plot_config);
            }
        
            // Draw graph with default options, overwriting with passed options
            function drawGraph (opts) {
                el_canvas.empty();
                var plot_cnf = _.extend(_.clone(plot_config), opts || {});
                return plot = $.jqplot('canvas', plot_data, plot_cnf);
            }
  
            // draw plot
            var plot = drawGraph();
            
            // catch window resize event
            var self = this;
            $(window).resize(function () {
                drawGraph();
            });
        
            return true;
        } catch (err) {
            this._handleError(chart, err);
            return false;
        }
    },
    
    // create categories
    _makeCategories: function(chart, groups, plot_config) {
        // result
        var result = Tools.makeCategories(chart, groups);
        
        /*/ add categories to plot configuration
        for (var key in result.array) {
            var axis = key + 'axis';
            if (plot_config.axes[axis]) {
                plot_config.axes[axis].ticks = result.array[key];
            }
        }*/
        
        // add x tick formatter
        function axisTickFormatter (axis_char, plot_axis, axis_type, axis_tick) {
            /*if (axis_type != 'auto' && axis_type !== undefined) {
                plot_axis.tickOptions.formatter = function(format, value) {
                    if (axis_type == 'hide') {
                        return '';
                    }
                    var format = d3.format(axis_tick + axis_type);
                    return format(v);
                }
            } else {*/
                if (chart.definition.columns[axis_char].is_label) {
                    plot_axis.tickOptions.formatter = function(format, value) {
                        if (value == parseInt(value)) {
                            if (result.array[axis_char] !== undefined) {
                                return result.array[axis_char][value];
                            } else {
                                return '';
                            }
                        } else {
                            return '';
                        }
                    }
                }
            //}
        }
        axisTickFormatter ('x', plot_config.axes.xaxis, chart.settings.get('x_axis_type'), chart.settings.get('x_axis_tick'));
        axisTickFormatter ('y', plot_config.axes.yaxis, chart.settings.get('y_axis_type'), chart.settings.get('y_axis_tick'));
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});