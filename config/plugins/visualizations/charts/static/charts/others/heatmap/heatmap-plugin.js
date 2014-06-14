// dependencies
define(['plugin/charts/tools', 'utils/utils'], function(Tools, Utils) {

// widget
return Backbone.View.extend({
    
    // options
    optionsDefault: {
        font_size           : 12,
        font_family         : 'Verdana',
        font_style          : {
            'font-weight'   : 'normal',
            'font-family'   : 'Verdana'
        },
        background_color    : '#FFFFF8',
        debug_color         : '#FFFFFF',
        color_set           : ['#ffffd9','#edf8b1','#c7e9b4','#7fcdbb','#41b6c4','#1d91c0','#225ea8','#253494','#081d58']
    },
    
    // initialize
    initialize: function(app, options) {
        this.app    = app;
        this.chart  = options.chart;
        this.options = Utils.merge (this.optionsDefault, options);
    },
            
    // render
    render : function(canvas_id, groups) {
        // categories
        this.categories = Tools.makeUniqueCategories(groups);
        
        // collect parameters
        this.canvas_id  = canvas_id;
        this.data       = groups[0].values;
        
        //
        // domains/scales
        //
        this.xScale = d3.scale.linear().domain([0, this.categories.array.x.length]);
        this.yScale = d3.scale.linear().domain([0, this.categories.array.y.length]);
        
        // color scale
        this.zMax = d3.max(this.data, function(d) { return d.z; });
        this.zScale = d3.scale.quantize().domain([0, this.zMax]);
        this.zScale.range(this.options.color_set);
        
        // create axis
        this.xAxis = d3.svg.axis().scale(this.xScale).orient('bottom');
        this.yAxis = d3.svg.axis().scale(this.yScale).orient('left');
        
        // make categories
        this._makeTickFormat('x');
        this._makeTickFormat('y');
                
        // refresh on window resize
        var self = this;
        $(window).on('resize', function () {
            self.redraw();
        });
        
        // draw
        this.redraw();
                    
        // add zoom
        Tools.addZoom({
            xAxis       : this.xAxis,
            yAxis       : this.yAxis,
            redraw      : function() { self.redraw() },
            svg         : d3.select('#' + this.canvas_id)
        });
        
        // return
        return true;
    },
        
    // redraw
    redraw: function() {
        // get parameters
        var chart       = this.chart;
        var data        = this.data;
        var self        = this;
        
        // get/reset container
        var container = $('#' + this.canvas_id);
        container.empty();
        
        // get domain
        var xDomain = this.xScale.domain();
        var yDomain = this.yScale.domain();
        
        // set ticks
        var xTickStart = Math.ceil(xDomain[0]);
        var xTickEnd   = Math.floor(xDomain[1]);
        var yTickStart = Math.ceil(yDomain[0]);
        var yTickEnd   = Math.floor(yDomain[1]);
        this.xAxis.tickValues(d3.range(xTickStart, xTickEnd, 1));
        this.yAxis.tickValues(d3.range(yTickStart, yTickEnd, 1));
        
        // set margin and heights
        var margin = {top: 40, right: 20, bottom: 70, left: 70},
        width = parseInt(container.width()) - margin.left - margin.right,
        height = parseInt(container.height()) - margin.top - margin.bottom;
        
        // default font size
        var font_size = this.options.font_size;
        
        //
        // set range
        //
        this.xScale.range([0, width]);
        this.yScale.range([height, 0]);

        //
        // draw boxes
        //
        // get box properties
        var rowCount = yDomain[1] - yDomain[0],
            colCount = xDomain[1] - xDomain[0],
            boxWidth = Math.max(1, Math.floor(width / colCount)),
            boxHeight = Math.max(1, Math.floor(height / rowCount));
        
        // box location
        function _locator(d) {
            return 'translate(' + self.xScale(d.x) + ',' + self.yScale(d.y+1) + ')';
        };

        // box color
        function _color (d) {
            return self.zScale(d.z);
        };
        
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
        
        // set background color
        var gBackground = svg.append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', this.options.background_color);

        // clip path
        var clip = svg.append('clipPath')
            .attr('id', 'clip')
            .append('rect')
            .attr('x', 0)
            .attr('y', 0)
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
            .attr('rx', 1)
            .attr('ry', 1)
            .attr('fill', _color)
            .attr('width', boxWidth)
            .attr('height', boxHeight)
            .attr('transform', _locator);
        boxes.exit().remove();

        // draw x axis
        this.gxAxis = svg.append('g')
            .attr('class', 'x axis')
            .style('stroke-width', 1)
            .attr('transform', 'translate(0,' + height + ')')
            .call(this.xAxis);
        
        // draw y axis
        this.gyAxis = svg.append('g')
            .attr('class', 'y axis')
            .style('stroke-width', 1)
            .call(this.yAxis);
        
        // fix text
        var xFontSize = Math.min(boxWidth, font_size);
        this.gxAxis.selectAll('text')
            .style(this.options.font_style)
            .style({'font-size': xFontSize + 'px'})
            .attr('transform', function(d) {
                var y = -this.getBBox().height - 10;
                var x = -xFontSize + boxWidth/2;
                return 'rotate(-90)translate(' + y + ',' + x + ')';
            });
    
        // fix text
        var yFontSize = Math.min(boxHeight, font_size);
        this.gyAxis.selectAll('text')
            .style(this.options.font_style)
            .style({'font-size': yFontSize + 'px'})
            .attr('y', -boxHeight/2);
        
        // set background color
        var gBackgroundBottom = svg.append('rect')
            .attr('width', width)
            .attr('height', font_size + 3)
            .attr('y', height + margin.bottom - font_size - 3)
            .attr('fill', this.options.debug_color);
            
        // axis label
        this.gxLabel = svg.append('text')
            .attr('class', 'x label')
            .style(this.options.font_style)
            .text(this.chart.settings.get('x_axis_label'))
            .attr('transform', function(d) {
                var y = height + margin.bottom - font_size/3;
                var x = (width - this.getBBox().width)/2;
                return 'translate(' + x + ',' + y + ')';
            });
        
        // set background color
        var gBackgroundLeft = svg.append('rect')
            .attr('width', font_size)
            .attr('height', height)
            .attr('x', -margin.left)
            .attr('fill', this.options.debug_color);
        
        // axis label
        this.gyLabel = svg.append('text')
            .attr('class', 'y label')
            .style(this.options.font_style)
            .text(this.chart.settings.get('y_axis_label'))
            .attr('transform', function(d) {
                var x = -margin.left + font_size-2;
                var y = -(height + this.getBBox().width)/2;
                return 'rotate(-90)translate(' + y + ',' + x + ')';
            });
            
        // chart title
        this.gxLabel = svg.append('text')
            .attr('class', 'title')
            .style(this.options.font_style)
            .style({'font-size' : 1.5*font_size})
            .text(this.chart.get('title'))
            .attr('transform', function(d) {
                var y = -margin.top/2;
                var x = (width - this.getBBox().width)/2;
                return 'translate(' + x + ',' + y + ')';
            });
    },
    
    // create axes formatting
    _makeTickFormat: function(id) {
        var settings = this.chart.settings;
        var self = this;
        Tools.makeTickFormat({
            categories  : self.categories.array[id],
            type        : settings.get(id + '_axis_type'),
            precision   : settings.get(id + '_axis_precision'),
            formatter   : function(formatter) {
                if (formatter) {
                    self[id + 'Axis'].tickFormat(function(value) {
                       return formatter(value);
                    });
                }
            }
        });
    },
    
    // handle error
    _handleError: function(err) {
        this.chart.state('failed', err);
    }
});

});