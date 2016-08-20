/** This class handles, formats and caches datasets. */
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Collection.extend({
        initialize: function( app, options ){
            this.app = app;
            this.list = {};
            this.cache = {};
            this.options = options;
        },

        /** Get dataset metadata */
        get: function( options ) {
            var self = this;
            this.dataset_list = this.dataset_list || [];
            var dataset = this.dataset_list[ options.id ];
            if ( dataset ) {
                options.success( dataset );
            } else {
                Utils.request({
                    type    : 'GET',
                    url     : config.root + 'api/datasets/' + options.id,
                    success : function( dataset ) {
                        switch ( dataset.state ) {
                            case 'error':
                                options.error && options.error( dataset );
                                break;
                            default:
                                self.dataset_list[ options.id ] = dataset;
                                options.success( dataset );
                        }
                    }
                });
            }
        },

        /** Multiple request handler */
        request: function( options ) {
            var self        = this;
            var success     = options.success;
            var progress    = options.progress;
            var query_size  = this.app.config.get( 'query_limit' );
            var query_start = options.start || 0;
            var query_end   = query_start + options.query_limit || query_start + this.app.config.get( 'query_limit' );
            var query_range = Math.abs( query_end - query_start );
            if ( query_range <= 0 ) {
                console.debug( 'FAILED - Datasets::request() - Invalid query range.' );
                return;
            }
            var query_number = Math.ceil( query_range / query_size ) || 1;
            var query_dictionary_template = $.extend( true, {}, options );
            var query_counter = 0;


            // recursive caller to fill blocks
            function fetch_blocks ( query ) {
                self._get(query, function() {
                    var done = false;
                    for ( var group_index in options.groups ) {
                        destination_group = options.groups[ group_index ];
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
            fetch_blocks( $.extend(true, query_dictionary_template, {start: query_start}) );
        },

        /** Get block id */
        _block_id: function ( options, column ) {
            return options.id + '_' + options.start + '_' + options.start + this.app.config.get( 'query_limit' ) + '_' + column;
        },

        /** Fills request dictionary with data from cache/response */
        _get: function( options, callback ) {
            var self = this;
            var column_list = [];
            options.start = options.start || 0;

            // identify columns needed to fulfill request
            for ( var i in options.groups ) {
                var group = options.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ].index;
                    var block_id = this._block_id( options, column );
                    if ( column_list.indexOf( column ) === -1 && !this.cache[ block_id ] && column != 'auto' && column != 'zero' && column !== undefined ) {
                        column_list.push( column );
                    }
                }
            }
            if ( column_list.length == 0 ) {
                this._fill_from_cache( options );
                callback( options );
                return;
            }

            // Fetch data columns into dataset object
            Utils.request({
                type    : 'GET',
                url     : config.root + 'api/datasets/' + options.id,
                data    : {
                    data_type   : 'raw_data',
                    provider    : 'dataset-column',
                    limit       : self.app.config.get( 'query_limit' ),
                    offset      : options.start,
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
                    console.debug( 'Datasets::_fetch() - Fetching complete.' );
                    for ( var i in results ) {
                        var column = column_list[ i ];
                        var block_id = self._block_id( options, column );
                        self.cache[ block_id ] = results[ i ];
                    }
                    self._fill_from_cache( options );
                    callback( options );
                }
            });

        },

        /** Fill data from cache */
        _fill_from_cache: function( options ) {
            var start = options.start;
            console.debug( 'Datasets::_fill_from_cache() - Filling request from cache at ' + start + '.' );
            var limit = 0;
            for ( var i in options.groups ) {
                var group = options.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ];
                    var block_id = this._block_id( options, column.index );
                    var column_data = this.cache[ block_id ];
                    if ( column_data ) {
                        limit = Math.max( limit, column_data.length );
                    }
                }
            }
            if ( limit == 0 ) {
                console.debug( 'Datasets::_fill_from_cache() - Reached data range limit.' );
            }
            for ( var i in options.groups ) {
                var group = options.groups[ i ];
                group.values = [];
                for ( var j = 0; j < limit; j++ ) {
                    group.values[ j ] = { x : parseInt( j ) + start };
                }
            }
            for ( var i in options.groups ) {
                var group = options.groups[ i ];
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
                            var block_id = this._block_id( options, column.index );
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
        }
    });
});