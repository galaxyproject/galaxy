define( [ 'visualizations/utilities/tabular-utilities', 'utilities/jobs', 'visualizations/others/heatmap/heatmap-plugin' ], function( Utilities, Jobs, HeatMap ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            Jobs.request( options.chart, Utilities.buildJobDictionary( options.chart, 'heatmap' ), function( dataset ) {
                var index = 0;
                var dataset_groups = new Backbone.Collection();
                options.chart.groups.each( function( group, index ) {
                    dataset_groups.add({
                        __data_columns: {
                            x : { is_label   : true },
                            y : { is_label   : true },
                            z : { is_numeric : true }
                        },
                        x     : index++,
                        y     : index++,
                        z     : index++,
                        key   : group.get( 'key' )
                    });
                });
                options.dataset_id = dataset.id;
                options.dataset_groups = dataset_groups;
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