// dependencies
define(['plugin/charts/nvd3/nvd3'], function(NVD3) {

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
        
        // draw
        var nvd3 = new NVD3(this.app, this.options);
        nvd3.draw(process_id, nv.models.multiBarChart(), chart, tmp_dict, function(nvd3_model) {
            nvd3_model.options({showControls: true});
        });
    }
});

});