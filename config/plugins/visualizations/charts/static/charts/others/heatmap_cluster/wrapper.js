define( [ 'plugin/charts/utilities/tabular-utilities', 'plugin/components/jobs', 'plugin/charts/others/heatmap/heatmap-plugin' ], function( Utilities, Jobs, HeatMap ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            Jobs.request( options.chart, Utilities.buildJobDictionary( 'heatmap', options.chart ), function( dataset ) {
                var request_dictionary = Utilities.buildRequestDictionary( options.chart, dataset.id );
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
                    new HeatMap({
                        chart       : options.chart,
                        canvas_id   : canvas_id,
                        groups      : groups
                    });
                    return true;
                };
                Utilities.panelHelper( options );
            }, function() { options.process.reject() } );
        }
    });
});