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
    draw : function(options) {
        _.extend(this.options, options);
        var self = this;
        var plot = new Tools.panelHelper({
            app                 : this.app,
            process_id          : this.options.process_id,
            canvas              : this.options.canvas,
            chart               : this.options.chart,
            request_dictionary  : this.options.request_dictionary,
            render              : function(groups, canvas) {
                                    return self.render(groups, canvas)
                                }
        });
    },
    
    // draw all data into a single canvas
    render: function(groups, el_canvas) {
        // set chart settings
        var chart       = this.options.chart;
        var makeConfig  = this.options.makeConfig;
        var makeSeries  = this.options.makeSeries;
        
        // create configuration
        var plot_config = configmaker(chart);
        var plot_data = []
        
        // identify categories
        this._makeCategories(chart, groups, plot_config, true);
        
        // reset data
        if (makeSeries) {
            plot_data = makeSeries(groups);
        } else {
            plot_data = Tools.makeSeries(groups);
        }
        
        // draw plot
        try {
            // canvas
            var canvas = el_canvas[0];
            
            // make custom wrapper callback
            if (makeConfig) {
                makeConfig(plot_config);
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
        
        // check length
        if (groups.length == 0) {
            return;
        }
        
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
            // get chart definition from first group
            var chart_definition = groups[0];
            
            /*if (axis_type != 'auto' && axis_type !== undefined) {
                plot_axis.tickOptions.formatter = function(format, value) {
                    if (axis_type == 'hide') {
                        return '';
                    }
                    var format = d3.format(axis_tick + axis_type);
                    return format(v);
                }
            } else {*/
                if (chart_definition.columns[axis_char] && chart_definition.columns[axis_char].is_label) {
                    plot_axis.tickOptions.formatter = function(format, value) {
                        if (result.array[axis_char] !== undefined &&
                            result.array[axis_char][value] !== undefined) {
                            return result.array[axis_char][value];
                        } else {
                            return '';
                        }
                    }
                }
            //}
        }
        //axisTickFormatter ('x', plot_config.axes.xaxis, chart.settings.get('x_axis_type'), chart.settings.get('x_axis_tick'));
        //axisTickFormatter ('y', plot_config.axes.yaxis, chart.settings.get('y_axis_type'), chart.settings.get('y_axis_tick'));
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});