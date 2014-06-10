// dependencies
define(['plugin/charts/jqplot/common/wrapper'], function(Plot) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, chart, request_dictionary) {
        // configure request
        var index = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            group.columns = null;
            group.columns = {
                x: {
                    index: index++,
                    is_numeric: true
                }
            }
        }
        
        var plot = new Plot(this.app, this.options);
        plot.draw({
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
            makeConfig          : function(plot_config){
                $.extend(true, plot_config, {
                    seriesDefaults: {
                        renderer: $.jqplot.OHLCRenderer,
                        rendererOptions : {
                            candleStick : true
                        }
                    }
                });
            },
            makeSeries          : function (groups) {
                // plot data
                var plot_data = [];
                
                // check group length
                if (groups.length == 0 && groups[0].values.length == 0) {
                    return;
                }
                
                 // reset data/categories
                var data = [];
                
                /*/ loop through data groups
                for (var key in request_dictionary.groups) {
                    // get group
                    var group = request_dictionary.groups[key];
                    
                    // format chart data
                    var point = [];
                    point.push(group.key);
                    for (var key in [0, 1, 3, 4]) {
                        point.push(group.values[key].x);
                    }
                    
                    // add to data
                    data.push (point);
                }*/
                
                /*/ loop through data groups
                for (var key in groups) {
                    var group = groups[key];
                    var point = [];
                    for (var value_index in group.values) {
                        point.push(group.values[value_index].x);
                    }
                    plot_data.push (point);
                }
                
                // return
                return [plot_data];

                var catOHLC = [[1, 138.7, 139.68, 135.18, 135.4],
                    [2, 143.46, 144.66, 139.79, 140.02],
                    [3, 140.67, 143.56, 132.88, 142.44],
                    [4, 136.01, 139.5, 134.53, 139.48],
                    [5, 443.82, 144.56, 136.04, 136.97],
                    [6, 136.47, 146.4, 136, 144.67],
                    [7, 124.76, 135.9, 124.55, 135.81],
                    [8, 223.73, 129.31, 121.57, 122.5]];
                return [catOHLC];*/
            }
        });
    }
});

});