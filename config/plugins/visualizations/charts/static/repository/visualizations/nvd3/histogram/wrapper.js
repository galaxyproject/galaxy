define( [ 'visualizations/utilities/tabular-utilities', 'utilities/jobs', 'visualizations/nvd3/common/wrapper' ], function( Utilities, Jobs, NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            Jobs.request( options.chart, Utilities.buildJobDictionary( options.chart, 'histogram' ), function( dataset ) {
                var dataset_groups = new Backbone.Collection();
                options.chart.groups.each( function( group, index ) {
                    dataset_groups.add({
                        __data_columns: { x: { is_numeric: true }, y: { is_numeric: true } },
                        x     : 0,
                        y     : index + 1,
                        key   : group.get( 'key' )
                    });
                });
                options.dataset_id = dataset.id;
                options.dataset_groups = dataset_groups;
                options.type = 'multiBarChart';
                options.makeConfig = function( nvd3_model ) {
                    nvd3_model.options( { showControls: true } );
                };
                new NVD3( options );
            }, function() { options.process.reject() } );
        }
    });
});