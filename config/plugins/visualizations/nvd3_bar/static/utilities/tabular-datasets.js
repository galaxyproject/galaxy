/** This class handles, formats and caches datasets. */
define( [ 'utilities/utils' ], function( Utils ) {
    /** Fills request dictionary with data from cache/response */
    var _cache = {};
    var request = function( options ) {
        var groups      = options.dataset_groups;
        var dataset_id  = options.dataset_id;
        // identify columns needed to fulfill request
        var column_list = [];
        groups.each( function( group ) {
            _.each( group.get( '__data_columns' ), function( column_def, column_name ) {
                var column = group.get( column_name );
                var block_id = _block_id( dataset_id, column );
                if ( column_list.indexOf( column ) === -1 && !_cache[ block_id ] && column != 'auto' && column != 'zero' && column !== undefined ) {
                    column_list.push( column );
                }
            });
        });
        if ( column_list.length == 0 ) {
            _fillFromCache( options );
            return;
        }
        // Fetch data columns into dataset object
        Utils.get({
            url     : Galaxy.root + 'api/datasets/' + dataset_id,
            data    : {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                indeces     : column_list.toString()
            },
            success : function( response ) {
                var results = new Array( column_list.length );
                for ( var i = 0; i < results.length; i++ ) {
                    results[ i ] = [];
                }
                for ( var i in response.data ) {
                    var row = response.data[ i ];
                    for ( var j in row ) {
                        var v = row[ j ];
                        if ( v !== undefined && v != 2147483647 ) {
                            results[ j ].push( v );
                        }
                    }
                }
                console.debug( 'tabular-datasets::_fetch() - Fetching complete.' );
                for ( var i in results ) {
                    var column = column_list[ i ];
                    var block_id = _block_id( dataset_id, column );
                    _cache[ block_id ] = results[ i ];
                }
                _fillFromCache( options );
            }
        });
    };

    /** Fill data from cache */
    var _fillFromCache = function( options ) {
        var groups      = options.dataset_groups;
        var dataset_id  = options.dataset_id;
        console.debug( 'tabular-datasets::_fillFromCache() - Filling request from cache.' );
        var limit = 0;
        groups.each( function( group ) {
            _.each( group.get( '__data_columns' ), function( column_def, column_name ) {
                var column = group.get( column_name );
                var block_id = _block_id( dataset_id, column );
                var column_data = _cache[ block_id ];
                if ( column_data ) {
                    limit = Math.max( limit, column_data.length );
                }
            });
        });
        if ( limit == 0 ) {
            console.debug( 'tabular-datasets::_fillFromCache() - No data available.' );
        }
        var results = [];
        groups.each( function( group, group_index ) {
            var dict = Utils.merge( { key: ( group_index ) + ':' + group.get( 'key' ), values: [] }, group.attributes );
            for ( var j = 0; j < limit; j++ ) {
                dict.values[ j ] = { x : parseInt( j ) };
            }
            results.push( dict );
        });
        groups.each( function( group, group_index ) {
            var values = results[ group_index ].values;
            _.each( group.get( '__data_columns' ), function( column_def, column_name ) {
                var column = group.get( column_name );
                switch ( column ) {
                    case 'auto':
                        for ( var j = 0; j < limit; j++ ) {
                            values[ j ][ column_name ] = parseInt( j );
                        }
                        break;
                    case 'zero':
                        for ( var j = 0; j < limit; j++ ) {
                            values[ j ][ column_name ] = 0;
                        }
                        break;
                    default:
                        var block_id = _block_id( dataset_id, column );
                        var column_data = _cache[ block_id ];
                        for ( var j = 0; j < limit; j++ ) {
                            var value = values[ j ];
                            var v = column_data[ j ];
                            if ( isNaN( v ) && !column_def.is_label ) {
                                v = 0;
                            }
                            value[ column_name ] = v;
                        }
                }
            });
        });
        options.success( results );
    };

    /** Get block id */
    var _block_id = function ( dataset_id, column ) {
        return dataset_id + '_' + '_' + column;
    };

    return { request: request };
});