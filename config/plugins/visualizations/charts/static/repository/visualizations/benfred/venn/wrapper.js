define( [ 'visualizations/utilities/tabular-datasets', 'plugins/benfred/venn', 'style!css!plugins/benfred/venn.css' ], function( Datasets, Venn ) {
    return Backbone.View.extend({
        _combinations: function( current, remaining, results ) {
            var self = this;
            _.each( remaining, function( value, index ) {
                var new_current = current.slice();
                var new_remaining = remaining.slice();
                new_remaining.splice( 0, index + 1 );
                new_current.push( value );
                results.push( new_current );
                self._combinations( new_current, new_remaining, results );
            });
        },

        initialize: function( options ) {
            var self = this;
            var separator = '_';
            Datasets.request({
                dataset_id      : options.chart.get( 'dataset_id' ),
                dataset_groups  : options.chart.groups,
                success         : function( result ) {
                    var group_keys   = [];
                    var group_values = [];
                    var all_values   = {};
                    var set_size     = {};
                    var group_ids    = [];
                    _.each( result, function( group, i ) {
                        var group_index = {};
                        _.each( group.values, function( d ) {
                            all_values[ d.observation ] = group_index[ d.observation ] = true;
                        });
                        group_keys.push( group.key );
                        group_values.push( group_index );
                        group_ids.push( i );
                    });
                    var combos = [];
                    self._combinations( [], group_ids, combos );
                    var sets = [];
                    _.each( combos, function( c ) {
                        var size = 0;
                        for ( var value in all_values ) {
                            var found = 0;
                            _.each( c, function( group_id ) {
                                if ( group_values[ group_id ][ value ] ) {
                                    found++;
                                }
                            });
                            if ( found == c.length ) {
                                size++;
                            }
                        }
                        if ( size > 0 ) {
                            var set_labels = [];
                            _.each( c, function( id ) {
                                set_labels.push( group_keys[ id ]);
                            });
                            sets.push( { sets: set_labels, size: size } );
                        }
                    });
                    var svg = d3.select( '#' + options.targets[ 0 ] ).datum( sets ).call( Venn.VennDiagram() );
                    var tooltip = null;
                    svg.selectAll( 'g' )
                       .on( 'mouseover', function( d, i ) {
                            Venn.sortAreas( svg, d );
                            tooltip = d3.select( 'body' ).append( 'div' ).attr( 'class', 'venntooltip' );
                            tooltip.transition().duration( 400 ).style( 'opacity', .9 );
                            tooltip.text(d.size );
                            var selection = d3.select( this ).transition( 'tooltip' ).duration( 400 );
                            selection.select( 'path' )
                                     .style( 'stroke-width', 3 )
                                     .style( 'fill-opacity', d.sets.length == 1 ? .4 : .1 )
                                     .style( 'stroke-opacity', 1 );
                       })
                       .on( 'mousemove', function() {
                            tooltip.style( 'left', ( d3.event.pageX ) + 'px')
                                   .style( 'top', ( d3.event.pageY - 28 ) + 'px');
                       })
                       .on( 'mouseout', function( d, i ) {
                            tooltip.remove();
                       });
                    options.chart.state( 'ok', 'Venn diagram drawn.' );
                    options.process.resolve();
                }
            });
        }
    });
});