// dependencies
define(['plugin/charts/highcharts/common/wrapper'], function(HighchartsWrapper) {

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
        // draw chart
        var hc = new HighchartsWrapper(this.app, this.options);
        hc.draw(process_id, 'heatmap', chart, request_dictionary, function(model) {
            model.colorAxis = {
                minColor                    : '#00FF99',
                maxColor                    : '#000066'
            }
        });
    }
});

});