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
        var chart           = this.options.chart;
        var makeCategories  = this.options.makeCategories;
        var makeSeries      = this.options.makeSeries;
        var makeConfig      = this.options.makeConfig;
        
        // create configuration
        var plot_config = configmaker(chart);
        var plot_data = [];
        
        // draw plot
        try {
            // make custom categories call
            this._makeAxes(plot_config, groups, chart.settings);
            
            // make custom series call
            if (makeSeries) {
                plot_data = makeSeries(groups);
            } else {
                plot_data = Tools.makeSeries(groups);
            }
    
            // make custom config call
            if (makeConfig) {
                makeConfig(plot_config, groups);
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
            var self = this;
            $(window).on('resize', function () {
                drawGraph();
            });
        
            return true;
        } catch (err) {
            this._handleError(chart, err);
            return false;
        }
    },
    
    // create axes formatting
    _makeAxes: function(plot_config, groups, settings) {
        // result
        var makeCategories = this.options.makeCategories;
        var categories;
        if (makeCategories) {
            categories = makeCategories(groups, plot_config);
        } else {
            categories = Tools.makeCategories(groups);
        }
                
        // make axis
        function makeAxis (id) {
            var axis        = plot_config.axes[id + 'axis'].tickOptions;
            var type        = settings.get(id + '_axis_type');
            var tick        = settings.get(id + '_axis_tick');
            var is_category = categories.array[id];
            
            // hide axis
            if (type == 'hide') {
                axis.formatter = function(format, value) { return '' };
                return;
            }
            
            // format values/labels
            if (type == 'auto') {
                if (is_category) {
                    axis.formatter = function(format, value) {
                        return categories.array[id][value] || '';
                    };
                }
            } else {
                var formatter = d3.format(tick + type);
                if (is_category) {
                    axis.formatter = function(format, value) {
                        return formatter(categories.array[id][value]);
                    };
                } else {
                    axis.formatter = function(format, value) {
                        return formatter(value);
                    }
                }
            }
        };
    
        // make axes
        makeAxis('x');
        makeAxis('y');
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});