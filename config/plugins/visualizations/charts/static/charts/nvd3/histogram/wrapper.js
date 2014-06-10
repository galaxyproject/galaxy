// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

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
        
        // link this
        var self = this;
        
        // load nvd3
        var nvd3 = new NVD3(this.app, this.options);
        nvd3.draw({
            type                : 'multiBarChart',
            process_id          : process_id,
            chart               : chart,
            request_dictionary  : request_dictionary,
            makeConfig          : function(nvd3_model) {
                nvd3_model.options({showControls: true});
            }
        });
    }
});

});