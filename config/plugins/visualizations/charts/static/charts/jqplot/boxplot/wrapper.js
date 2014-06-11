// dependencies
define(['plugin/charts/jqplot/common/wrapper', 'plugin/charts/tools'], function(Plot, Tools) {

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
                    index       : index++
                }
            }
        }
        
        var plot = new Plot(this.app, this.options);
        plot.draw({
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
            makeConfig          : function(plot_config, groups){
                var boundary = Tools.getDomains(groups, 'x');
                $.extend(true, plot_config, {
                    seriesDefaults: {
                        renderer: $.jqplot.OHLCRenderer,
                        rendererOptions : {
                            candleStick     : true,
                            fillUpBody      : true,
                            fillDownBody    : true
                        }
                    },
                    axes : {
                        xaxis: {
                            pad: 1.2
                        },
                        yaxis: {
                            min: boundary.x.min,
                            max: boundary.x.max
                        }
                    }
                });
            },
            makeSeries          : function (groups) {
                /* example data
                var catOHLC = [
                    [0, 138.7, 139.68, 135.18, 135.4],
                    [1, 143.46, 144.66, 139.79, 140.02],
                    [2, 140.67, 143.56, 132.88, 142.44],
                    [3, 136.01, 139.5, 134.53, 139.48]
                ];
                return [catOHLC];
                */
                
                // plot data
                var plot_data = [];
                
                // check group length
                if (groups.length == 0 || groups[0].values.length < 5) {
                    chart.state('failed', 'Boxplot data could not be found.');
                    return [plot_data];
                }
                
                // loop through data groups
                for (var group_index in request_dictionary.groups) {
                    // get group
                    var group = request_dictionary.groups[group_index];
                  
                    // format chart data
                    var point = [];
                    point.push(parseInt(group_index));
                    var indeces = [2, 4, 0, 1];
                    for (var key in indeces) {
                        point.push(group.values[indeces[key]].x);
                    }
                  
                    // add to data
                    plot_data.push (point);
                }
                
                // return
                return [plot_data];
            }
        });
    }
});

});