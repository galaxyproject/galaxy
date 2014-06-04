// dependencies
define(['utils/utils', 'plugin/charts/highcharts/common/highcharts-config'], function(Utils, configmaker) {

// widget
return Backbone.View.extend(
{
    // highcharts series
    hc_series: {
        name                : '',
        data                : [],
        tooltip: {
            headerFormat    : '<em>{point.key}</em><br/>'
        }
    },

    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
    
    // render
    draw : function(process_id, hc_type, chart, request_dictionary, callback)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function() {
            // check if this chart has multiple panels
            if (self.options.canvas.length == 1) {
                // groups
                if (self._drawGroups(hc_type, chart, request_dictionary.groups, self.options.canvas[0], callback)) {
                    // set chart state
                    chart.state('ok', 'Chart drawn.');
                }
            } else {
                // loop through data groups
                var valid = true;
                for (var group_index in request_dictionary.groups) {
                    // get group
                    var group = request_dictionary.groups[group_index];
                    
                    // draw group
                    if (!self._drawGroups(hc_type, chart, [group], self.options.canvas[group_index], callback)) {
                        valid = false;
                        break;
                    }
                }
                
                // set chart state
                if (valid) {
                    chart.state('ok', 'Multi-panel chart drawn.');
                }
            }
            
            // unregister process
            chart.deferred.done(process_id);
        });
    },
    
    // draw all data into a single canvas
    _drawGroups: function(hc_type, chart, groups, canvas, callback) {
        // create configuration
        var hc_config = configmaker(chart);
        
        // make custom wrapper callback
        if (callback) {
            callback(hc_config);
        }
    
        // reset
        hc_config.series = [];
        
        // loop through data groups
        for (var key in groups) {
            // get group
            var group = groups[key];
            
            // reset data
            var data = [];
        
            // format chart data
            for (var value_index in group.values) {
                // parse data
                var point = [];
                for (var column_index in group.values[value_index]) {
                    point.push(group.values[value_index][column_index]);
                }
                
                // add to data
                data.push (point);
            }
            
            // highcharts series
            var hc_series = {
                name        : group.key,
                type        : hc_type,
                data        : data
            };
            
            // append series
            hc_config.series.push(hc_series);
        }
        
        // draw plot
        try {
            canvas.highcharts(hc_config);
            return true;
        } catch (err) {
            var regex = /\www\.highcharts\.com([^&]+)/;
            var match = err.match(regex);
            if (match.length > 0) {
                chart.state('failed', 'Highcharts error: <a target="_blank" href="http://' + match[0] + '">' + match[0] + '</a>');
            } else {
                chart.state('failed', err);
            }
            return false;
        }
    }
});

});