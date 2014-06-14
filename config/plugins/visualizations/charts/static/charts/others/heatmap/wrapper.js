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
        // backup chart
        this.chart = chart;
        
        // distribute data groups on svgs and handle process
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
        // categories
        this.categories = Tools.makeUniqueCategories(groups);
        
        // collect parameters
        this.canvas_id  = canvas_id;
        this.data       = groups[0].values;
        this.color_set  = ['#ffffd9','#edf8b1','#c7e9b4','#7fcdbb','#41b6c4','#1d91c0','#225ea8','#253494','#081d58'];
        
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
        
        // create axis
        this.xAxis = d3.svg.axis().scale(this.xScale).orient('bottom');
        this.yAxis = d3.svg.axis().scale(this.yScale).orient('left');
        
        // set ticks
        this.xAxis.tickValues(d3.range(this.xScale.domain()[0], this.xScale.domain()[1], 1));
        this.yAxis.tickValues(d3.range(this.yScale.domain()[0], this.yScale.domain()[1], 1));
        
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
            svg         : d3.select('#' + this.canvas_id),
            discrete    : true
        });
        
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
        // set range
        //
        this.xScale.range([0, width]);
        this.yScale.range([height, 0]);
        this.zScale.range(color_set);

        //
        // draw boxes
        //
        // get box properties
        var rowCount = this.yScale.domain()[1] - this.yScale.domain()[0],
            colCount = this.xScale.domain()[1] - this.xScale.domain()[0],
            boxWidth = Math.max(1, Math.floor(width / colCount)),
            boxHeight = Math.max(1, Math.floor(height / rowCount));
        
        // box location
        function _locator(d) {
            return 'translate(' + self.xScale(d.x) + ',' + self.yScale(d.y) + ')';
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
        this.gxAxis = svg.append('g')
            .attr('class', 'x axis')
            .style('stroke-width', 0)
            .attr('transform', 'translate(0,' + (height + margin.top + boxHeight) + ')')
            .call(this.xAxis);
            
        // draw y axis
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
    _handleError: function(chart, err) {
        chart.state('failed', err);
    }
});

});