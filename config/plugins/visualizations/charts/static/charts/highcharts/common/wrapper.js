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
            if (!chart.definition.use_panels) {
                // draw all groups into a single panel
                if (self._drawGroups(hc_type, chart, request_dictionary.groups, self.options.canvas[0], callback)) {
                    chart.state('ok', 'Chart drawn.');
                }
            } else {
                // draw groups in separate panels
                var valid = true;
                for (var group_index in request_dictionary.groups) {
                    var group = request_dictionary.groups[group_index];
                    if (!self._drawGroups(hc_type, chart, [group], self.options.canvas[group_index], callback)) {
                        valid = false;
                        break;
                    }
                }
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
        
        // fix title
        if (!chart.definition.use_panels) {
            hc_config.title.text = chart.get('title');
        }
        
        // identify categories
        this._makeCategories(chart, groups, hc_config);
        
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
        
        // make custom wrapper callback
        if (callback) {
            callback(hc_config);
        }

        // draw plot
        try {
            canvas.highcharts(hc_config);
            return true;
        } catch (err) {
            this._handleError(chart, err);
            return false;
        }
    },
    
    // create categories
    _makeCategories: function(chart, groups, hc_config) {
        // hashkeys, arrays and counter for labeled columns
        var categories  = {};
        var array       = {};
        var counter     = {};
        
        // identify label columns
        var chart_definition = groups[0];
        for (var key in chart_definition.columns) {
            var column_def = chart_definition.columns[key];
            if (column_def.is_label) {
                categories[key] = {};
                array[key]      = [];
                counter[key]    = 0;
            }
        }
        
        // index all values contained in label columns (for all groups)
        for (var i in groups) {
            var group = groups[i];
            for (var j in group.values) {
                var value_dict = group.values[j];
                for (var key in categories) {
                    var value = String(value_dict[key]);
                    if (categories[key][value] === undefined) {
                        categories[key][value] = counter[key]++;
                        array[key].push(value);
                    }
                }
            }
        }

        // convert group values into category indeces
        for (var i in groups) {
            var group = groups[i];
            for (var j in group.values) {
                var value_dict = group.values[j];
                for (var key in categories) {
                    var value = String(value_dict[key]);
                    value_dict[key] = categories[key][value]
                }
            }
        }
        console.log(array);
        // add categories to highcharts configuration
        for (var key in array) {
            var axis = key + 'Axis';
            if (hc_config[axis]) {
                hc_config[axis].categories = array[key];
            }
        }
    },
    
    // handle error
    _handleError: function(chart, err) {
        var regex = /\www\.highcharts\.com([^&]+)/;
        var match = err.match(regex);
        if (match.length > 0) {
            chart.state('failed', 'Highcharts error: <a target="_blank" href="http://' + match[0] + '">' + match[0] + '</a>');
        } else {
            chart.state('failed', err);
        }
    }
});

});