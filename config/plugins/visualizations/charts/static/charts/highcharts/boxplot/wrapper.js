// dependencies
define(['plugin/charts/highcharts/common/highcharts-config'], function(configmaker) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary)
    {
        // configure request
        var index = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            group.columns = null;
            group.columns = {
                x: {
                    index: index++
                }
            }
        }
        
        // hide legend
        chart.settings.set('legend_enabled', 'false')
        
        // create configuration
        this.hc_config = configmaker(chart.settings);
        
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function() {
            
            // reset data/categories
            var data = [];
            var categories = [];
            
            // loop through data groups
            for (var key in request_dictionary.groups) {
                // get group
                var group = request_dictionary.groups[key];
                
                // add category
                categories.push(group.key);
                
                // format chart data
                var point = [];
                for (var key in group.values) {
                    point.push(group.values[key].x);
                }
                
                // add to data
                data.push (point);
            }
            
            // categories
            self.hc_config.xAxis.categories = categories;
                
            // update data
            self.hc_config.series.push({
                type    : 'boxplot',
                data    : data
            });
        
            // draw plot
            self.options.canvas[0].highcharts(self.hc_config);
            
            // set chart state
            chart.state('ok', 'Box plot drawn.');
                
            // unregister process
            chart.deferred.done(process_id);
        });
    }
});

});