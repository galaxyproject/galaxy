define( [ 'plugin/charts/utilities/tabular-utilities', 'plugin/components/jobs', 'plugin/charts/nvd3/common/wrapper' ], function( Utilities, Jobs, NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            Jobs.request( options.chart, Utilities.buildJobDictionary( 'histogram', options.chart ), function( dataset ) {
                options.request_dictionary = Utilities.buildRequestDictionary( options.chart, dataset.id );
                var index = 1;
                _.each( options.request_dictionary.groups, function( group ) {
                    group.columns = { x : { index : 0, is_numeric : true }, y : { index : index++ } }
                });
                options.type = 'multiBarChart';
                options.makeConfig = function( nvd3_model ) {
                    nvd3_model.options( { showControls: true } );
                };
                new NVD3( options );
            }, function() { options.process.reject() } );
        }
    });
});