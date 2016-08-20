define( [ 'plugin/charts/utilities', 'plugin/library/jobs', 'plugin/charts/nvd3/common/wrapper' ], function( Utilities, Jobs, NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            Jobs.request( app, 'histogram', function( dataset ) {
                var request_dictionary = Utilities.tabularRequestDictionary( app.chart, dataset.id );
                var index = 1;
                for ( var i in request_dictionary.groups ) {
                    var group = request_dictionary.groups[ i ];
                    group.columns = {
                        x: {
                            index       : 0,
                            is_numeric  : true
                        },
                        y: {
                            index       : index++
                        }
                    }
                }
                options.request_dictionary = request_dictionary;
                options.type = 'multiBarChart';
                options.makeConfig = function( nvd3_model ) {
                    nvd3_model.options( { showControls: true } );
                };
                new NVD3( app, options );
            }, function() {
                process.reject();
            });
        }
    });
});