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
            canvas_list         : this.options.canvas_list,
            chart               : this.options.chart,
            request_dictionary  : this.options.request_dictionary,
            render              : function(canvas_id, groups) {
                                    return self.render(canvas_id, groups)
                                }
        });
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
        // clip edges
        if (nvd3_model.clipEdge) {
            nvd3_model.clipEdge(true);
        }
        
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
        
        // min/max boundaries
        var x_boundary = nvd3_model.xScale().domain().slice();
        var y_boundary = nvd3_model.yScale().domain().slice();
        
        // create d3 zoom handler
        var d3zoom = d3.behavior.zoom();
        
        // fix domain
        function fixDomain(domain, boundary) {
            domain[0] = Math.max(domain[0], boundary[0]);
            domain[1] = Math.min(domain[1], boundary[1]);
            return domain;
        };
        
        // zoom event handler
        function zoomed() {
            if (zoom_mode == 'axis') {
                nvd3_model.xDomain(fixDomain(x.domain(), x_boundary));
                nvd3_model.yDomain(fixDomain(y.domain(), y_boundary));
                nvd3_model.update();
            } else {
                var translate = d3.event.translate;
                svg.select('.nvd3').attr("transform", "translate(" + translate + ")  scale(" + d3.event.scale + ")");
            }
        };

        // zoom event handler
        function unzoomed() {
            if (zoom_mode == 'axis') {
                nvd3_model.xDomain(x_boundary);
                nvd3_model.yDomain(y_boundary);
                nvd3_model.update();
                d3zoom.scale(1);
                d3zoom.translate([0,0]);
            } else {
                var translate = d3.event.translate;
                svg.select('.nvd3').attr("transform", "translate([0,0]) scale(1)");
            }
        };

        // initialize wrapper
        d3zoom.x(x)
              .y(y)
              .scaleExtent([1, 10])
              .on("zoom", zoomed);
            
        // add handler
        svg.call(d3zoom).on("dblclick.zoom", unzoomed);
    },

    // create axes formatting
    _makeAxes: function(d3chart, groups, settings) {
        // result
        var categories = Tools.makeCategories(groups);
        
        // make axis
        function makeAxis (id) {
            var axis        = d3chart[id + 'Axis'];
            var type        = settings.get(id + '_axis_type');
            var tick        = settings.get(id + '_axis_tick');
            var is_category = categories.array[id];
            
            // hide axis
            if (type == 'hide') {
                axis.tickFormat(function() { return '' });
                return;
            }
            
            // format values/labels
            if (type == 'auto') {
                if (is_category) {
                    axis.tickFormat(function(value) {
                        return categories.array[id][value]
                    });
                }
            } else {
                var formatter = d3.format(tick + type);
                if (is_category) {
                    axis.tickFormat(function(value) {
                        return formatter(categories.array[id][value]);
                    });
                } else {
                    axis.tickFormat(formatter);
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