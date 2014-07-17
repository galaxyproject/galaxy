// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        // get parameters
        var request_dictionary = options.request_dictionary;
        var chart = options.chart;
        var canvas_list = options.canvas_list;
        var process_id = options.process_id;
        
        // setup handler
        var self = this;
        request_dictionary.success = function() {
            // loop through data groups
            for (var group_index in request_dictionary.groups) {
                // get group
                var group = request_dictionary.groups[group_index];
            
                // draw group
                self._drawGroup(chart, group, canvas_list[group_index]);
            }
            
            // set chart state
            chart.state('ok', 'Pie chart has been drawn.');
        
            // unregister process
            app.deferred.done(process_id);
        }
        
        // request data
        app.datasets.request(request_dictionary);
    },
    
    // draw group
    _drawGroup: function(chart, group, canvas_id) {
        try {
            // get canvas
            var canvas = d3.select('#' + canvas_id);
            
            // add title
            var title = canvas.append('text');
      
            // configure title attributes
            this._fixTitle(chart, canvas, title, group.key);
      
            // format chart data
            var pie_data = [];
            for (var key in group.values) {
                var value = group.values[key];
                pie_data.push ({
                    y : value.y,
                    x : value.label
                });
            }

            // add graph to screen
            var self = this;
            nv.addGraph(function() {
                // legend
                var legend_visible = true;
                if (chart.settings.get('show_legend') == 'false') {
                    legend_visible = false;
                }
                
                // legend
                var label_outside = true;
                if (chart.settings.get('label_outside') == 'false') {
                    label_outside = false;
                }
                
                // label type
                var label_type = chart.settings.get('label_type');
                
                // ratio
                var donut_ratio = parseFloat(chart.settings.get('donut_ratio'))
                
                // create chart model
                var chart_3d = nv.models.pieChart()
                    .donut(true)
                    .labelThreshold(.05)
                    .showLegend(legend_visible)
                    .labelType(label_type)
                    .donutRatio(donut_ratio)
                    .donutLabelsOutside(label_outside);
                
                // add data to canvas
                canvas.datum(pie_data)
                      .call(chart_3d);
                
                // add resize trigger
                nv.utils.windowResize(function() {
                    // update chart
                    chart_3d.update();
                    
                    // fix title
                    self._fixTitle(chart, canvas, title, group.key);
                });
            });
        } catch (err) {
            console.log(err);
        }
    },
    
    // fix title
    _fixTitle: function(chart, canvas, title_element, title_text) {
        // update title
        var width = parseInt(canvas.style('width'));
        var height = parseInt(canvas.style('height'));
        
        // add title
        title_element.attr('x', width / 2)
                     .attr('y', height - 10)
                     .attr('text-anchor', 'middle')
                     .text(title_text);
    }
});

});