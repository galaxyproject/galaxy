// dependencies
define(['plugin/charts/tools'], function(Tools) {

/**
 *  This is the common wrapper for nvd3 based visualizations.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        // get parameters
        this.options = options;
        
        // define render function
        var self = this;
        options.render = function(canvas_id, groups) {
            return self.render(canvas_id, groups)
        };
        
        // call panel helper
        Tools.panelHelper(app, options);
    },
    
    // render
    render : function(canvas_id, groups) {
        var chart       = this.options.chart;
        var type        = this.options.type;
        var makeConfig  = this.options.makeConfig;
    
        // create nvd3 model
        var d3chart = nv.models[type]()
        
        // request data
        var self = this;
        nv.addGraph(function() {
            try {
                // x axis label
                d3chart.xAxis.axisLabel(chart.settings.get('x_axis_label'));
                
                // y axis label
                d3chart.yAxis.axisLabel(chart.settings.get('y_axis_label'))
                             .axisLabelDistance(30);
                
                // controls
                d3chart.options({showControls: false});
                
                // legend
                if (d3chart.showLegend) {
                    d3chart.showLegend(chart.settings.get('show_legend') == 'true');
                }
                
                // make categories
                self._makeAxes(d3chart, groups, chart.settings);
                
                // custom callback
                if (makeConfig) {
                    makeConfig(d3chart);
                }
                
                // hide controls if in multi-viewer mode
                if (chart.settings.get('use_panels') === 'true') {
                    d3chart.options({showControls: false});
                }
        
                // hide min/max values
                d3chart.xAxis.showMaxMin(false);
                d3chart.yAxis.showMaxMin(chart.definition.showmaxmin);
                
                // draw chart
                if ($('#' + canvas_id).length == 0) {
                    return;
                }
                var canvas = d3.select('#' + canvas_id);
                    canvas.datum(groups)
                      .call(d3chart);
                    
                // add zoom/pan handler
                if (chart.definition.zoomable && chart.definition.zoomable != 'native') {
                    // clip edges
                    if (d3chart.clipEdge) {
                        d3chart.clipEdge(true);
                    }
        
                    // add zoom
                    Tools.addZoom({
                        xAxis  : d3chart.xAxis,
                        yAxis  : d3chart.yAxis,
                        yDomain: d3chart.yDomain,
                        xDomain: d3chart.xDomain,
                        redraw : function() { d3chart.update() },
                        svg    : canvas
                    });
                }

                // refresh on window resize
                nv.utils.windowResize(d3chart.update);
            } catch (err) {
                self._handleError(chart, err);
            }
        });
        
        // return
        return true;
    },
    
    // create axes formatting
    _makeAxes: function(d3chart, groups, settings) {
        // result
        var categories = Tools.makeCategories(groups);
                    
        // make axes
        function makeTickFormat (id) {
            Tools.makeTickFormat({
                categories  : categories.array[id],
                type        : settings.get(id + '_axis_type'),
                precision   : settings.get(id + '_axis_precision'),
                formatter   : function(formatter) {
                    if (formatter) {
                        d3chart[id + 'Axis'].tickFormat(function(value) {
                           return formatter(value);
                        });
                    }
                }
            });
        };
        makeTickFormat('x');
        makeTickFormat('y');
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});