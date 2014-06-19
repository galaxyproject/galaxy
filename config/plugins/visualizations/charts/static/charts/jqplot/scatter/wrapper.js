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
    draw : function(process_id, chart, request_dictionary, canvas_list) {
        var plot = new Plot(this.app, this.options);
        plot.draw({
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
            canvas_list         : canvas_list,
            makeConfig          : function(groups, plot_config){
                $.extend(true, plot_config, {
                    seriesDefaults: {
                        renderer: $.jqplot.LineRenderer,
                        showLine: false,
                        markerOptions : {
                            show    : true
                        }
                    }
                });
            }
        });
    }
});

});