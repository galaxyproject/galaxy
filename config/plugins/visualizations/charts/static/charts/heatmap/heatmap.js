// dependencies
define(['utils/utils', 'plugin/charts/heatmap/heatmap-plugin'], function(Utils, Plugin) {

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
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function() {
            
            console.log(request_dictionary.groups);
            
            // draw plot
            new Plugin({
                'data'  : request_dictionary.groups[0].values,
                'div'   : self.options.canvas[0]
            });
            
            // set chart state
            chart.state('ok', 'Heat map drawn.');
                
            // unregister process
            chart.deferred.done(process_id);
        });
    }
});

});