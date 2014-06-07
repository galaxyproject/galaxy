// dependencies
define(['utils/utils'], function(Utils) {

// render
function panelHelper (options)
{
    // require parameters
    var process_id          = options.process_id;
    var chart               = options.chart;
    var request_dictionary  = options.request_dictionary;
    var render              = options.render;
    var canvas              = options.canvas;
    var app                 = options.app;
    
    // request data
    var self = this;
    app.datasets.request(request_dictionary, function() {
        try {
            // check if this chart has multiple panels
            if (!chart.definition.use_panels && chart.settings.get('use_panels') !== 'true') {
                // draw all groups into a single panel
                if (render(chart, request_dictionary.groups, canvas[0])) {
                    chart.state('ok', 'Chart drawn.');
                }
            } else {
                // draw groups in separate panels
                var valid = true;
                for (var group_index in request_dictionary.groups) {
                    var group = request_dictionary.groups[group_index];
                    if (!render(chart, [group], canvas[group_index])) {
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
        } catch (err) {
            // log
            console.debug('FAILED: Tools::draw() - ' + err);
        
            // set chart state
            chart.state('failed', err);
            
            // unregister process
            chart.deferred.done(process_id);
        }
    });
};

// series maker
function makeSeries(group) {
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
    
    // return
    return data;
};

// category maker
function makeCategories(chart, groups) {
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
                    categories[key][value] = counter[key];
                    array[key].push([counter[key], value]);
                    counter[key]++;
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
    
    // return dictionary
    return {
        categories  : categories,
        array       : array,
        counter     : counter
    }
};
    
// return
return {
    panelHelper     : panelHelper,
    makeCategories  : makeCategories,
    makeSeries      : makeSeries
}

});