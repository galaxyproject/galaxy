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
            canvas_list         : this.options.canvas_list,
            chart               : this.options.chart,
            request_dictionary  : this.options.request_dictionary,
            render              : function(canvas_id, groups) {
                                    return self.render(canvas_id, groups)
                                }
        });
    },
    
    // draw all data into a single canvas
    render: function(canvas_id, groups) {
        // get parameters
        var chart               = this.options.chart;
        var makeCategories      = this.options.makeCategories;
        var makeSeries          = this.options.makeSeries;
        var makeSeriesLabels    = this.options.makeSeriesLabels;
        var makeConfig          = this.options.makeConfig;
        
        // create configuration
        var plot_config = configmaker(chart);
        var plot_data = [];
        
        // draw plot
        try {
            // make custom categories call
            this._makeAxes(groups, plot_config, chart.settings);
            
            // make custom series call
            if (makeSeriesLabels) {
                plot_config.series = makeSeriesLabels(groups, plot_config);
            } else {
                plot_config.series = this._makeSeriesLabels(groups);
            }
    
            // make custom series call
            if (makeSeries) {
                plot_data = makeSeries(groups, plot_config);
            } else {
                plot_data = Tools.makeSeries(groups);
            }
    
            // make custom config call
            if (makeConfig) {
                makeConfig(groups, plot_config);
            }
            
            // check chart state
            if (chart.get('state') == 'failed') {
                return false;
            }
            
            // draw graph with default options, overwriting with passed options
            function drawGraph (opts) {
                var canvas = $('#' + canvas_id);
                if(canvas.length == 0) {
                    return;
                }
                canvas.empty();
                var plot_cnf = _.extend(_.clone(plot_config), opts || {});
                return plot = $.jqplot(canvas_id, plot_data, plot_cnf);
            }
  
            // draw plot
            var plot = drawGraph();
            
            // catch window resize event
            $(window).on('resize', function () {
                drawGraph();
            });
        
            return true;
        } catch (err) {
            this._handleError(chart, err);
            return false;
        }
    },
    
    // make series labels
    _makeSeriesLabels: function(groups, plot_config) {
        var series = [];
        for (var group_index in groups) {
            series.push({
                label: groups[group_index].key
            });
        }
        return series;
    },
    
    // create axes formatting
    _makeAxes: function(groups, plot_config, settings) {
        // result
        var makeCategories = this.options.makeCategories;
        var categories;
        if (makeCategories) {
            categories = makeCategories(groups, plot_config);
        } else {
            categories = Tools.makeCategories(groups);
        }
                
        // make axes
        function makeAxis (id) {
            Tools.makeAxis({
                categories  : categories.array[id],
                type        : settings.get(id + '_axis_type'),
                precision   : settings.get(id + '_axis_precision'),
                formatter   : function(formatter) {
                    if (formatter) {
                        plot_config.axes[id + 'axis'].tickOptions.formatter = function(format, value) {
                           return formatter(value);
                        };
                    }
                }
            });
        };
        makeAxis('x');
        makeAxis('y');
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});