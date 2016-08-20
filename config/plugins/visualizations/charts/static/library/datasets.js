/** This class handles, formats and caches datasets. */
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.View.extend({
        initialize: function( app, options ){
            this.app = app;
        },

        /** Get dataset */
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

        /** Fills request dictionary with data from cache/response */
        request: function( options ) {
            var self = this;
            this.cache = this.cache || {};
            options.start = options.start || 0;

            // identify columns needed to fulfill request
            var column_list = [];
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
                this._fillFromCache( options );
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
                    console.debug( 'datasets::_fetch() - Fetching complete.' );
                    for ( var i in results ) {
                        var column = column_list[ i ];
                        var block_id = self._block_id( options, column );
                        self.cache[ block_id ] = results[ i ];
                    }
                    self._fillFromCache( options );
                }
            });

        },

        /** Fill data from cache */
        _fillFromCache: function( options ) {
            var result = Utils.clone( options );
            var start = options.start;
            console.debug( 'datasets::_fillFromCache() - Filling request from cache at ' + start + '.' );
            var limit = 0;
            for ( var i in result.groups ) {
                var group = result.groups[ i ];
                for ( var key in group.columns ) {
                    var column = group.columns[ key ];
                    var block_id = this._block_id( result, column.index );
                    var column_data = this.cache[ block_id ];
                    if ( column_data ) {
                        limit = Math.max( limit, column_data.length );
                    }
                }
            }
            if ( limit == 0 ) {
                console.debug( 'datasets::_fillFromCache() - Reached data range limit.' );
            }
            for ( var i in result.groups ) {
                var group = result.groups[ i ];
                group.values = [];
                for ( var j = 0; j < limit; j++ ) {
                    group.values[ j ] = { x : parseInt( j ) + start };
                }
            }
            for ( var i in result.groups ) {
                var group = result.groups[ i ];
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
                            var block_id = this._block_id( result, column.index );
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
            options.success( result );
        },

        /** Get block id */
        _block_id: function ( options, column ) {
            return options.id + '_' + options.start + '_' + column;
        },
    });
});