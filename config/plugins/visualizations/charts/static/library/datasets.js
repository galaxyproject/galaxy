/** This class handles, formats and caches datasets. */
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Collection.extend({
        initialize: function( app, options ){
            this.app = app;
            this.list = {};
            this.cache = {};
            this.options = options;
        },

        /** Request handler */
        request: function( request_dictionary ) {
            if ( request_dictionary.groups ) {
                this._get_blocks( request_dictionary );
            } else {
                this._get_dataset( request_dictionary.id, request_dictionary.success, request_dictionary.error )
            }
        },

        /** Multiple request handler */
        _get_blocks: function( request_dictionary ) {
            var self        = this;
            var success     = request_dictionary.success;
            var progress    = request_dictionary.progress;
            var query_size  = this.app.config.get( 'query_limit' );
            var query_start = request_dictionary.start || 0;
            var query_end   = query_start + request_dictionary.query_limit || query_start + this.app.config.get( 'query_limit' );
            var query_range = Math.abs( query_end - query_start );
            if ( query_range <= 0 ) {
                console.debug( 'FAILED - Datasets::request() - Invalid query range.' );
                return;
            }
            var query_number = Math.ceil( query_range / query_size ) || 1;
            var query_dictionary_template = $.extend( true, {}, request_dictionary );
            var query_counter = 0;

            function fetch_blocks ( query ) {
                self._get(query, function() {
                    var done = false;
                    for ( var group_index in request_dictionary.groups ) {
                        destination_group = request_dictionary.groups[ group_index ];
                        source_group = query.groups[ group_index ];
                        if ( !destination_group.values ) {
                            destination_group.values = [];
                        }
                        destination_group.values = destination_group.values.concat( source_group.values );
                        if ( source_group.values.length == 0 ) {
                            done = true;
                            break;
                        }
                    }
                    if ( ++query_counter < query_number && !done ) {
                        if ( progress ) {
                            progress( parseInt( ( query_counter / query_number ) * 100 ) );
                        }
                        var start = query.start + query_size;
                        query = $.extend( true, query_dictionary_template, { start: start } );
                        fetch_blocks( query );
                    } else {
                        success();
                    }
                });
            };
            var query = $.extend(true, query_dictionary_template, {start: query_start});
            this._get_dataset( request_dictionary.id, function() { fetch_blocks( query ) } );
        },

        /** Get dataset */
        _get_dataset: function( id, success, error ) {
            var self = this;
            var dataset = this.list[ id ];
            if ( dataset ) {
                success( dataset );
                return;
            }
            Utils.request({
                type    : 'GET',
                url     : config.root + 'api/datasets/' + id,
                success : function( dataset ) {
                    switch ( dataset.state ) {
                        case 'error':
                            error && error( dataset );
                            break;
                        default:
                            self.list[ id ] = dataset;
                            success( dataset );
                    }
                }
            });
        },

        /** Get block id */
        _block_id: function ( options, column ) {
            return options.id + '_' + options.start + '_' + options.start + this.app.config.get( 'query_limit' ) + '_' + column;
        },

        /** Fills request dictionary with data from cache/response */
        _get: function( request_dictionary, callback ) {
            var self = this;
            var column_list = [];
            var column_map  = {};
            var column_count = 0;
            request_dictionary.start = request_dictionary.start || 0;
            for ( var i in request_dictionary.groups ) {
                var group = request_dictionary.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ].index;
                    var block_id = this._block_id( request_dictionary, column );
                    if ( this.cache[ block_id ] || column === 'auto' || column === 'zero' ) {
                        continue;
                    }
                    if ( !column_map[ column ] && column !== undefined ) {
                        column_map[ column ] = column_count;
                        column_list.push( column );
                        column_count++;
                    }
                }
            }
            if ( column_list.length == 0 ) {
                this._fill_from_cache( request_dictionary );
                callback( request_dictionary );
                return;
            }
            var dataset_request = {
                dataset_id  : request_dictionary.id,
                start       : request_dictionary.start,
                columns     : column_list
            }
            this._fetch(dataset_request, function( results ) {
                for ( var i in results ) {
                    var column = column_list[ i ];
                    var block_id = self._block_id( request_dictionary, column );
                    self.cache[ block_id ] = results[ i ];
                }
                self._fill_from_cache( request_dictionary );
                callback( request_dictionary );
            });
        },

        /** Fill data from cache */
        _fill_from_cache: function( request_dictionary ) {
            var start = request_dictionary.start;
            console.debug( 'Datasets::_fill_from_cache() - Filling request from cache at ' + start + '.' );
            var limit = 0;
            for ( var i in request_dictionary.groups ) {
                var group = request_dictionary.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ];
                    var block_id = this._block_id( request_dictionary, column.index );
                    var column_data = this.cache[ block_id ];
                    if ( column_data ) {
                        limit = Math.max( limit, column_data.length );
                    }
                }
            }
            if ( limit == 0 ) {
                console.debug( 'Datasets::_fill_from_cache() - Reached data range limit.' );
            }
            for ( var i in request_dictionary.groups ) {
                var group = request_dictionary.groups[ i ];
                group.values = [];
                for ( var j = 0; j < limit; j++ ) {
                    group.values[ j ] = { x : parseInt( j ) + start };
                }
            }
            for ( var i in request_dictionary.groups ) {
                var group = request_dictionary.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ];
                    switch ( column.index ) {
                        case 'auto':
                            for ( var j = 0; j < limit; j++ ) {
                                var value = group.values[ j ];
                                value[ key ] = parseInt( j ) + start;
                            }
                            break;
                        case 'zero':
                            for ( var j = 0; j < limit; j++ ) {
                                var value = group.values[ j ];
                                value[ key ] = 0;
                            }
                            break;
                        default:
                            var block_id = this._block_id( request_dictionary, column.index );
                            var column_data = this.cache[ block_id ];
                            for ( var j = 0; j < limit; j++ ) {
                                var value = group.values[ j ];
                                var v = column_data[ j ];
                                if ( isNaN( v ) && !column.is_label && !column.is_text ) {
                                    v = 0;
                                }
                                value[ key ] = v;
                            }
                    }
                }
            }
        },

        /** Fetch data columns into dataset object */
        _fetch: function(dataset_request, callback) {
            var self        = this;
            var offset      = dataset_request.start ? dataset_request.start : 0;
            var limit       = this.app.config.get('query_limit');
            var n_columns   = 0;
            if ( dataset_request.columns ) {
                n_columns = dataset_request.columns.length;
                console.debug( 'Datasets::_fetch() - Fetching ' + n_columns + ' column(s) at ' + offset + '.' );
            }
            if (n_columns == 0) {
                console.debug( 'Datasets::_fetch() - No columns requested' );
            }
            var column_string = '';
            for ( var i in dataset_request.columns ) {
                column_string += dataset_request.columns[ i ] + ',';
            }
            column_string = column_string.substring( 0, column_string.length - 1 );
            Utils.request({
                type    : 'GET',
                url     : config.root + 'api/datasets/' + dataset_request.dataset_id,
                data    : {
                    data_type   : 'raw_data',
                    provider    : 'dataset-column',
                    limit       : limit,
                    offset      : offset,
                    indeces     : column_string
                },
                success : function( response ) {
                    var result = new Array( n_columns );
                    for ( var i = 0; i < n_columns; i++ ) {
                        result[ i ] = [];
                    }
                    for ( var i in response.data ) {
                        var row = response.data[ i ];
                        for ( var j in row ) {
                            var v = row[ j ];
                            if ( v !== undefined && v != 2147483647 ) {
                                result[ j ].push( v );
                            }
                        }
                    }
                    console.debug( 'Datasets::_fetch() - Fetching complete.' );
                    callback( result );
                }
            });
        }
    });
});