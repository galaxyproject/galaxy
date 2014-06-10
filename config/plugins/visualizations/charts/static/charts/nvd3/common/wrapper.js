// dependencies
define(['plugin/charts/tools'], function(Tools) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
    
    // render
    draw : function(options) {
        _.extend(this.options, options);
        var self = this;
        var plot = Tools.panelHelper({
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
    
    // render
    render : function(groups, canvas) {
        var chart       = this.options.chart;
        var type        = this.options.type;
        var makeConfig  = this.options.makeConfig;
    
        // create nvd3 model
        var d3chart = nv.models[type]()
        
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
                    d3chart.showLegend(chart.settings.get('show_legend') == 'true');
                }
                
                // custom callback
                if (makeConfig) {
                    makeConfig(d3chart);
                }
                
                // make categories
                self._makeCategories(chart, groups, d3chart);
                
                // hide min/max values
                d3chart.xAxis.showMaxMin(false);
                d3chart.yAxis.showMaxMin(chart.definition.showmaxmin);
                
                // draw chart
                canvas.datum(groups)
                      .call(d3chart);
                    
                // add zoom/pan handler
                var zoom_mode = chart.definition.zoomable;
                if (zoom_mode == 'axis' || zoom_mode == 'svg') {
                    self._addZoom(d3chart, canvas, zoom_mode);
                }

                // refresh on window resize
                nv.utils.windowResize(d3chart.update);
            } catch (err) {
                self._handleError(chart, err);
            }
        });
        
        return true;
    },
    
    // add zoom handler
    _addZoom: function(nvd3_model, svg, zoom_mode) {
        // get canvas dimensions
        var width = parseInt(svg.style('width'));
        var height = parseInt(svg.style('height'));
        
        // create x scales
        var x_domain = nvd3_model.xAxis.scale().domain();
        var x = d3.scale.linear()
            .domain(x_domain)
            .range([0, width]);
        
        // create y scale
        var y_domain = nvd3_model.yAxis.scale().domain();
        var y = d3.scale.linear()
            .domain(y_domain)
            .range([height, 0]);
            
        // zoom event handler
        function zoomed() {
            if (zoom_mode == 'axis') {
                nvd3_model.xDomain(x.domain());
                nvd3_model.yDomain(y.domain());
                nvd3_model.update();
            } else {
                var translate = d3.event.translate;
                svg.select('.nvd3').attr("transform", "translate(" + translate + ")  scale(" + d3.event.scale + ")");
            }
        }

        // clip edges
        if (nvd3_model.clipEdge) {
            nvd3_model.clipEdge(true);
        }
        
        // d3 zoom wrapper
        var d3zoom = d3.behavior.zoom()
            .x(x)
            .y(y)
            .scaleExtent([1, 10])
            .on("zoom", zoomed);
            
        // add handler
        svg.call(d3zoom);
    },

    // create categories
    _makeCategories: function(chart, groups, d3chart) {
        // result
        var result = Tools.makeCategories(chart, groups);
        
        // add categories to flot configuration
        for (var key in result.array) {
            var axis = key + 'Axis';
            if (d3chart[axis]) {
                var a = result.array[key];
                d3chart[axis].tickFormat(function(value) {
                    return a[value];
                });
            }
        }
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