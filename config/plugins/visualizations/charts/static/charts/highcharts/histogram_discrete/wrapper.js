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
        var tmp_dict = {
            id      : request_dictionary.id,
            groups  : []
        };
        
        // configure groups
        var index = 0;
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
                        index       : ++index,
                        is_numeric  : true
                    }
                }
            });
        }
        
        // settings
        chart.settings.set('x_axis_categories', [])
    
        // draw chart
        var hc = new Highcharts(this.app, this.options);
        hc.draw(process_id, 'column', chart, tmp_dict);
    }
});

});