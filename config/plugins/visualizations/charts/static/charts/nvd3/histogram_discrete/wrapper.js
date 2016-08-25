define( [ 'plugin/charts/utilities/tabular-utilities', 'plugin/components/jobs', 'plugin/charts/nvd3/common/wrapper' ], function( Utilities, Jobs, NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            Jobs.request( app, Utilities.buildJobDictionary( 'histogramdiscrete', app.chart ), function( dataset ) {
                var request_dictionary = Utilities.buildRequestDictionary( app.chart, dataset.id );
                var index = 1;
                var tmp_dict = { id : request_dictionary.id, groups : [] };
                _.each( request_dictionary.groups, function( group ) {
                    tmp_dict.groups.push({
                        key     : group.key,
                        columns : { x: { index : 0, is_label : true }, y: { index : index++ } }
                    });
                });
                options.request_dictionary = tmp_dict;
                options.type = 'multiBarChart';
                options.makeConfig = function( nvd3_model ) {
                    nvd3_model.options( { showControls: true } );
                };
                new NVD3( app, options );
            }, function() { options.process.reject() } );
        }
    });
});