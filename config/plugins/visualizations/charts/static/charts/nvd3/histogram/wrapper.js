define( [ 'plugin/charts/nvd3/common/wrapper' ], function( NVD3 ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            var request_dictionary = options.request_dictionary;
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
            options.type = 'multiBarChart';
            options.makeConfig = function( nvd3_model ) {
                nvd3_model.options( { showControls: true } );
            };
            new NVD3( app, options );
        }
    });
});