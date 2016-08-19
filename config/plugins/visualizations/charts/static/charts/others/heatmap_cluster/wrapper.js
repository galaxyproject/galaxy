define( [ 'plugin/charts/utilities', 'plugin/charts/others/heatmap/heatmap-plugin' ], function( Utilities, HeatMap ) {
    return Backbone.View.extend({
        initialize: function(app, options) {
            var request_dictionary = Utilities.tabularRequestDictionary( options.chart );
            var index = 0;
            var tmp_dict = { id : request_dictionary.id, groups : [] };
            for ( var group_index in request_dictionary.groups ) {
                var group = request_dictionary.groups[ group_index ];
                tmp_dict.groups.push({
                    key     : group.key,
                    columns : {
                        x: {
                            index       : index++,
                            is_label    : true
                        },
                        y: {
                            index       : index++,
                            is_label    : true
                        },
                        z: {
                            index       : index++
                        }
                    }
                });
            }
            options.request_dictionary = tmp_dict;
            options.render = function( canvas_id, groups ) {
                new HeatMap( app, {
                    chart       : options.chart,
                    canvas_id   : canvas_id,
                    groups      : groups
                });
                return true;
            };
            Utilities.panelHelper( app, options );
        }
    });
});