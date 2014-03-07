// dependencies
define([], function() {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
    
    // draw
    draw: function(chart, request_dictionary) {
        
        // update request dataset id
        request_dictionary.id = chart.get('dataset_id_job');
        
        // configure request
        var index = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            group.columns = {
                x: index++,
                y: index++
            }
        }
        
        // send request
        var self = this;
        this.app.datasets.request(request_dictionary, function(data) {
            // set chart state
            chart.set('state', 'ok');
            
            // draw graph
            nv.addGraph(function() {
                self.d3_chart = nv.models.multiBarChart();
                    
                self.d3_chart.xAxis.tickFormat(d3.format('.2f'))
                                   .axisLabel('Breaks');
                
                self.d3_chart.yAxis.tickFormat(d3.format('.3f'))
                                   .axisLabel('Frequency')
                                   .axisLabelDistance(30);
                
                self.options.svg.datum(data)
                                .call(self.d3_chart);
     
                nv.utils.windowResize(self.d3_chart.update);
            });
        });
    }
});

});