// dependencies
define(['plugin/charts/highcharts/common/wrapper'], function(Highcharts) {

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
        var index = 1;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            group.columns = {
                x: {
                    index: 0
                },
                y: {
                    index: index++
                }
            }
        }
        
        var hc = new Highcharts(this.app, this.options);
        hc.draw(process_id, 'column', chart, request_dictionary);
    }
});

});