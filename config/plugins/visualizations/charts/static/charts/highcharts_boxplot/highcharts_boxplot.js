// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.View.extend(
{
    // highcharts configuration
    hc_config : {
        chart: {
	        type: 'boxplot'
	    },
	    
	    title: {
	        text: ''
	    },
	    
	    legend: {
	        enabled: false
	    },
        
        credits: {
            enabled: false
        },
        
        plotOptions: {
            series: {
                animation: false
            }
        },
        
        xAxis: {
            categories: [],
            title: {
                text: ''
            }
        },
        
        yAxis: {
            title: {
                text: ''
            }
        },
    
        series: [{
            name: 'Details:',
            data: [],
            tooltip: {
                headerFormat: '<em>{point.key}</em><br/>'
            }
        }]
	},

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
        
        // set axis labels
        this.hc_config.xAxis.title.text = chart.settings.get('x_axis_label');
        this.hc_config.yAxis.title.text = chart.settings.get('y_axis_label');
        
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
            self.hc_config.series[0].data = data;
        
            // draw plot
            self.options.canvas.highcharts(self.hc_config);
            
            // set chart state
            chart.state('ok', 'Box plot drawn.');
                
            // unregister process
            chart.deferred.done(process_id);
        });
    }
});

});