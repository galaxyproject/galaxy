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
        var index = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            group.columns = {
                x: {
                    index: index++
                },
                y: {
                    index: index++
                },
            }
        }
        
        // link this
        var self = this;
        
        // load nvd3
        var nvd3 = new NVD3(this.app, this.options);
        nvd3.draw(process_id, nv.models.multiBarChart(), chart, request_dictionary, function() {
            // ensure data consistency
            self._fix_partial_data(request_dictionary.groups);
        });
    },
    
    // the histogram module might generate partial data i.e. length(col1) = 10, length(col2) = 11, length(col3) = 12.
    // this function ensures that data is consistent, such that all columns have the same length.
    _fix_partial_data: function(groups) {
        // x-values
        var x_list = {};
        
        // identify all x values
        for (var i in groups) {
            var x_sub = this._identify_x_values(groups[i].values);
            x_list = _.extend(x_list, x_sub);
        }
        
        // identify all x values
        for (var i in groups) {
            var values = groups[i].values;
            var x_sub = this._identify_x_values(values);
            for (var x in x_list) {
                if (x_sub[x] === undefined) {
                    values.push({
                        x: parseFloat(x),
                        y: 0.0
                    });
                }
            }
            values.sort(function(a, b) {return a.x - b.x})
        }
    },
    
    // identify available x-values
    _identify_x_values: function(values) {
        var x_list = {};
        for (var j in values) {
            var x_value = values[j].x;
            if (x_value !== undefined && x_value !== null) {
                x_list[x_value] = true;
            }
        }
        return x_list;
    }
});

});