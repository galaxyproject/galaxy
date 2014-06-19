// dependencies
define(['plugin/charts/jqplot/common/wrapper'], function(Plot) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        // link request
        var request_dictionary = options.request_dictionary;
        
        // configure request
        var index = 1;
        var tmp_dict = {
            id      : request_dictionary.id,
            groups  : []
        };
        
        // configure groups
        for (var group_index in request_dictionary.groups) {
            var group = request_dictionary.groups[group_index];
            tmp_dict.groups.push({
                key     : group.key,
                columns : {
                    x: {
                        index       : 0,
                        is_label    : true
                    },
                    y: {
                        index       : index++
                    }
                }
            });
        }
        
        // add new request dictionary
        options.request_dictionary = tmp_dict;

        // add config maker
        options.makeConfig = function(groups, plot_config){
            $.extend(true, plot_config, {
                seriesDefaults: {
                    renderer : $.jqplot.BarRenderer
                },
                axes: {
                    xaxis: {
                        min  : -1
                    },
                    yaxis: {
                        pad  : 1.2
                    }
                }
            });
        };
        new Plot(app, options);
    }
});

});