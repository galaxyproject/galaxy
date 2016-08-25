define( [ 'plugin/charts/utilities/tabular-utilities', 'plugin/charts/utilities/tabular-datasets' ], function( Utilities, Datasets ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var chart = app.chart;
            var request_dictionary = Utilities.buildRequestDictionary( chart );
            var error = null;
            request_dictionary.success = function( result ) {
                var colors = d3.scale.category20();
                _.each( result.groups, function( group, group_index ) {
                    try {
                        var svg = d3.select( '#' + ( options.targets[ group_index ] || options.targets[ 0 ] ) );
                        var height = parseInt( svg.style( 'height' ) );
                        var width  = parseInt( svg.style( 'width' ) );
                        var maxValue = d3.max( group.values, function( d ) { return Math.max( d.x, d.y ) } );
                        svg.selectAll( 'bubbles' )
                            .data( group.values )
                            .enter().append( 'circle' )
                            .attr( 'r', function( d ) { return ( Math.abs( d.z ) * 20 ) / maxValue } )
                            .attr( 'cy', function( d, i ) { return height * d.y / maxValue } )
                            .attr( 'cx', function( d ) { return width * d.x / maxValue } )
                            .style( 'stroke', colors( group_index ) )
                            .style( 'fill', 'white' );
                    } catch ( err ) {
                        error = err;
                    }
                });
                if ( error ) {
                    chart.state( 'failed', error );
                } else {
                    chart.state( 'ok', 'Workshop chart has been drawn.' );
                }
                options.process.resolve();
            }
            Datasets.request( request_dictionary );
        }
    });
});