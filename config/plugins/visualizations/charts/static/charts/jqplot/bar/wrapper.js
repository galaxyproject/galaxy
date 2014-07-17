// dependencies
define(['plugin/charts/jqplot/common/wrapper'], function(Plot) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
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