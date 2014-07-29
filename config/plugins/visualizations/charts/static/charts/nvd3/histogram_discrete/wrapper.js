// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        // link request
        var request_dictionary = options.request_dictionary;
        
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
        
        // setup chart wrapper
        options.type = 'multiBarChart';
        options.request_dictionary = tmp_dict;
        options.makeConfig = function(nvd3_model) {
            nvd3_model.options({showControls: true});
        };
        new NVD3(app, options);
    }
});

});