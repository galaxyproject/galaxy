// dependencies
define(['plugin/charts/tools'], function(Tools) {

// widget
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary) {
        var self = this;
        var plot = Tools.panelHelper({
            app                 : this.app,
            canvas_list         : this.options.canvas_list,
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
            render              : function(canvas_id, groups) {
                                    return self.render(canvas_id, groups)
                                  }
        });
    },
    
    // render
    render : function(canvas_id, groups) {
        // collect parameters
        this.canvas_id  = canvas_id;
        this.data       = groups[0].values;
        this.color_set  = ['#ffffd9','#edf8b1','#c7e9b4','#7fcdbb','#41b6c4','#1d91c0','#225ea8','#253494','#081d58'];
        
        // result
        var categories = Tools.makeUniqueCategories(groups);
    
        // get limits
        this.xMax = d3.max(this.data, function(d) { return d.x; });
        this.yMax = d3.max(this.data, function(d) { return d.y; });
        this.zMax = d3.max(this.data, function(d) { return d.z; });
        
        //
        // domains/scales
        //
        this.xScale = d3.scale.linear().domain([0, this.xMax]);
        this.yScale = d3.scale.linear().domain([0, this.yMax]);
        this.zScale = d3.scale.ordinal().domain([0, this.zMax]);
            
        // refresh on window resize
        var self = this;
        $(window).on('resize', function () {
            self.redraw();
        });
        
        // draw
        this.redraw();
                    
        // add zoom
        this._addZoom();
        
        // return
        return true;
    },
        
    // redraw
    redraw: function() {
        // get parameters
        var chart       = this.options.chart;
        var type        = this.options.type;
        var data        = this.data;
        var color_set   = this.color_set;
        var self        = this;
        
        // get/reset container
        var container = $('#' + this.canvas_id);
        container.empty();
        
        // set margin and heights
        var margin = {top: 20, right: 90, bottom: 90, left: 100},
        width = parseInt(container.width()) - margin.left - margin.right,
        height = parseInt(container.height()) - margin.top - margin.bottom;
        
        //
        // create svg
        //
        var svg = d3.select('#' + this.canvas_id)
            .append('svg')
                .attr('width', width + margin.left + margin.right)
                .attr('height', height + margin.top + margin.bottom)
            .append('g')
                .attr('class', 'heatmap')
                .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
        
        //
        // set range
        //
        this.xScale.range([0, width]);
        this.yScale.range([height, 0]);
        this.zScale.range(color_set);

        // get domain
        var xDomain = this.xScale.domain();
        var yDomain = this.yScale.domain();
        
        //
        // draw boxes
        //
        // get box properties
        var rowCount = this.yScale.domain()[1] - this.yScale.domain()[0],
            colCount = this.xScale.domain()[1] - this.xScale.domain()[0],
            boxWidth = Math.max(1, Math.min(Math.floor(width / colCount), 20)),
            boxHeight = Math.max(1, Math.min(Math.floor(height / rowCount), 20));
        
        // box location
        function _locator(d) {
            return 'translate(' + self.xScale(d.x) + ',' + self.yScale(d.y) + ')';
        };

        // box color
        function _color (d) {
            return self.zScale(d.z);
        };
        
        // clip path
        var clip = svg.append('clipPath')
            .attr('id', 'clip')
            .append('rect')
            .attr('x', 0)
            .attr('y', boxHeight)
            .attr('width', width)
            .attr('height', height);

        // create chart area
        var chartBody = svg.append('g')
            .attr('clip-path', 'url(#clip)');
            
        // add boxes to chart area
        var boxes = chartBody.selectAll('g.box-group').data(data, function(d, i) {
            return d.x + '\0' + d.y;
        });
        var gEnter = boxes.enter().append('g')
            .attr('class', 'box-group');
        gEnter.append('rect')
            .attr('class','heat-box')
            .attr('fill', 'red');
        boxes.selectAll('rect')
            .attr('rx', 2)
            .attr('ry', 2)
            .attr('fill', _color)
            .attr('width', boxWidth)
            .attr('height', boxHeight)
            .attr('transform', _locator);
        boxes.exit().remove();

        // draw x axis
        this.xAxis = d3.svg.axis().scale(this.xScale).orient('bottom');
        this.xAxis.tickValues(d3.range(xDomain[0], xDomain[1], 1));
        this.gxAxis = svg.append('g')
            .attr('class', 'x axis')
            .style('stroke-width', 0)
            .attr('transform', 'translate(0,' + (height + margin.top + boxHeight) + ')')
            .call(this.xAxis);
            
        // draw y axis
        this.yAxis = d3.svg.axis().scale(this.yScale).orient('left');
        this.yAxis.tickValues(d3.range(yDomain[0], yDomain[1], 1));
        this.gyAxis = svg.append('g')
            .attr('class', 'y axis')
            .style('stroke-width', 0)
            .call(this.yAxis);
        
        // fix text
        var xFontSize = Math.min(boxWidth, 12);
        this.gxAxis.selectAll('text')
            .style({'font-family': 'Courier New', 'font-size': xFontSize + 'px'})
            .attr('transform', 'rotate(-90)')
            .attr('y', (boxWidth-xFontSize)/2);

        // fix text
        var yFontSize = Math.min(boxHeight, 12);
        this.gyAxis.selectAll('text')
            .style({'font-family': 'Courier New', 'font-size': yFontSize + 'px'})
            .attr('y', -boxHeight/2 + boxHeight);
    },
    
    // add zoom handler
    _addZoom: function() {
        // link this
        var self = this;
        
        // min/max boundaries
        var x_boundary = this.xScale.domain().slice();
        var y_boundary = this.yScale.domain().slice();
        
        // create d3 zoom handler
        var d3zoom = d3.behavior.zoom();
        
        // fix domain
        function fixDomain(domain, boundary) {
            domain[0] = parseInt(domain[0]);
            domain[1] = parseInt(domain[1]);
            domain[0] = Math.max(domain[0], boundary[0]);
            domain[1] = Math.max(0, Math.min(domain[1], boundary[1]));
            return domain;
        };
        
        // zoom event handler
        function zoomed() {
            var yDomain = fixDomain(self.yScale.domain(), y_boundary);
            if (Math.abs(yDomain[1]-yDomain[0]) > 30) {
                self.yScale.domain(yDomain);
                self.gyAxis.call(self.yAxis);
            }
            var xDomain = fixDomain(self.xScale.domain(), x_boundary);
            if (Math.abs(xDomain[1]-xDomain[0]) > 30) {
                self.xScale.domain(xDomain);
                self.gxAxis.call(self.xAxis);
            }
            self.redraw();
        };

        // zoom event handler
        function unzoomed() {
            self.xScale.domain(x_boundary);
            self.yScale.domain(y_boundary);
            self.redraw();
            d3zoom.scale(1);
            d3zoom.translate([0,0]);
        };
        
        // initialize wrapper
        d3zoom.x(this.xScale)
              .y(this.yScale)
              .scaleExtent([1, 10])
              .on('zoom', zoomed);
              
        // clip edges
        //svg.clipEdge(true);
              
        // add handler
        var svg = d3.select('#' + this.canvas_id);
        svg.call(d3zoom).on('dblclick.zoom', unzoomed);
    },

    // create axes formatting
    _makeAxes: function(d3chart, settings) {
        // make axes
        function makeAxis (id) {
            Tools.makeAxis({
                categories  : categories.array[id],
                type        : settings.get(id + '_axis_type'),
                precision   : settings.get(id + '_axis_precision'),
                formatter   : function(formatter) {
                    if (formatter) {
                        d3chart[id + 'Axis']().tickFormat(function(value) {
                           return formatter(value);
                        });
                    }
                }
            });
        };
        //makeAxis('x');
        //makeAxis('y');
    },
    
    // handle error
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});