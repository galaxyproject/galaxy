define( [ 'utils/utils' ], function( Utils ) {

    /** Create default data request dictionary */
    function buildRequestDictionary( chart, dataset_id ) {
        var request_dictionary = { groups : [] };
        request_dictionary.id = dataset_id ? dataset_id : chart.get( 'dataset_id' );
        var group_index = 0;
        chart.groups.each( function( group ) {
            var columns = {};
            for ( var column_key in chart.definition.columns ) {
                var column_settings = chart.definition.columns[ column_key ];
                columns[ column_key ] = Utils.merge( { index : group.get( column_key ) }, column_settings );
            }
            request_dictionary.groups.push( Utils.merge({
                key     : ( ++group_index ) + ':' + group.get( 'key' ),
                columns : columns
            }, group.attributes ));
        });
        return request_dictionary;
    };

    /** Assists in assigning the viewport panels */
    function panelHelper( app, options ) {
        var self = this;
        var process             = options.process;
        var chart               = options.chart;
        var request_dictionary  = options.request_dictionary || buildRequestDictionary( app.chart );
        var render              = options.render;
        var canvas_list         = options.canvas_list;
        request_dictionary.success = function( result ) {
            try {
                if ( chart.settings.get( 'use_panels' ) === 'true' ) {
                    var valid = true;
                    for ( var group_index in result.groups ) {
                        var group = result.groups[ group_index ];
                        if (!render( canvas_list[ group_index ], [ group ] ) ) {
                            valid = false;
                            break;
                        }
                    }
                    if ( valid ) {
                        chart.state( 'ok', 'Multi-panel chart drawn.' );
                    }
                } else {
                    if ( render( canvas_list[ 0 ], result.groups ) ) {
                        chart.state( 'ok', 'Chart drawn.' );
                    }
                }
                process.resolve();
            } catch ( err ) {
                console.debug( 'FAILED: Utilities::panelHelper() - ' + err );
                chart.state( 'failed', err );
                process.reject();
            }
        };
        app.datasets.request( request_dictionary );
    };

    /** Get domain boundaries value */
    function getDomains( groups, keys ) {
        function _apply( operator, key ) {
            var value = undefined;
            for ( var group_index in groups ) {
                var value_sub = d3[ operator ]( groups[ group_index ].values, function( d ) { return d[ key ] } );
                value = value === undefined ? value_sub : Math[ operator ]( value, value_sub );
            }
            return value;
        };
        var result = {};
        for( var index in keys ) {
            var key = keys[ index ];
            result[ key ] = {
                min : _apply( 'min', key ),
                max : _apply( 'max', key ),
            };
           
        }
        return result;
    };

    /** Default series maker */
    function makeSeries( groups, keys ) {
        var plot_data = [];
        for ( var group_index in groups ) {
            var group = groups[ group_index ];
            var data = [];
            for ( var value_index in group.values ) {
                var point = [];
                if ( keys ) {
                    for ( var key_index in keys ) {
                        var column_index = keys[ key_index ];
                        point.push( group.values[ value_index ][ column_index ] );
                    }
                } else {
                    for ( var column_index in group.values[ value_index ] ) {
                        point.push( group.values[ value_index ][ column_index ] );
                    }
                }
                data.push( point );
            }
            plot_data.push( data );
        }
        return plot_data;
    };

    /** Default category maker */
    function makeCategories( groups, with_index ) {
        var array = {};
        // identify label columns
        var chart_definition = groups[ 0 ];
        for ( var key in chart_definition.columns ) {
            var column_def = chart_definition.columns[ key ];
            if ( column_def.is_label ) {
                array[ key ] = [];
            }
        }
        // collect string labels in array
        if ( groups && groups[ 0 ] ) {
            var group = groups[ 0 ];
            for ( var j in group.values ) {
                var value_dict = group.values[ j ];
                for ( var key in array ) {
                    array[ key ].push ( String( value_dict[ key ] ) );
                }
            }
        }
        // index all values contained in label columns (for all groups)
        mapCategories( array, groups );
        return { array : array }
    };

    /** Apply default mapping index all values contained in label columns (for all groups) */
    function mapCategories( array, groups ) {
        for ( var i in groups ) {
            var group = groups[ i ];
            for ( var j in group.values ) {
                var value_dict = group.values[ j ];
                for ( var key in array ) {
                    value_dict[ key ] = parseInt( j )
                }
            }
        }
    };

    /** Category make for unique category labels */
    function makeUniqueCategories( groups, with_index ) {
        var categories  = {};
        var array       = {};
        var counter     = {};
        var chart_definition = groups[ 0 ];
        for( var key in chart_definition.columns ) {
            var column_def = chart_definition.columns[ key ];
            if ( column_def.is_label ) {
                categories[ key ] = {};
                array[ key ]      = [];
                counter[ key ]    = 0;
            }
        }
        // index all values contained in label columns (for all groups)
        for ( var i in groups ) {
            var group = groups[ i ];
            for ( var j in group.values ) {
                var value_dict = group.values[ j ];
                for ( var key in categories ) {
                    var value = String( value_dict[ key ] );
                    if ( categories[ key ][ value ] === undefined ) {
                        categories[ key ][ value ] = counter[ key ];
                        array[ key ].push( with_index ? [counter[key], value] : value );
                        counter[ key ]++;
                    }
                }
            }
        }
        // convert group values into category indeces
        for ( var i in groups ) {
            var group = groups[ i ];
            for ( var j in group.values ) {
                var value_dict = group.values[ j ];
                for ( var key in categories ) {
                    var value = String( value_dict[ key ] );
                    value_dict[ key ] = categories[ key ][ value ];
                }
            }
        }
        return {
            categories  : categories,
            array       : array,
            counter     : counter
        }
    };

    /** Make axis */
    function makeTickFormat ( options ) {
        var type        = options.type;
        var precision   = options.precision;
        var categories  = options.categories;
        var formatter   = options.formatter;
        if ( type == 'hide' ) {
            formatter( function() { return '' } );
        } else if ( type == 'auto' ) {
            if ( categories ) {
                formatter( function( value ) { return categories[ value ] || '' } );
            }
        } else {
            var d3format = function( d ) {
                switch ( type ) {
                    case 's':
                        var prefix = d3.formatPrefix( d );
                        return prefix.scale( d ).toFixed() + prefix.symbol;
                    default :
                        return d3.format( '.' + precision + type )( d );
                }
            };
            if ( categories ) {
                formatter( function( value ) {
                    var label = categories[ value ];
                    if ( label ) {
                        if ( isNaN( label ) ) {
                            return label;
                        } else {
                            try {
                                return d3format( label );
                            } catch ( err ) {
                                return label;
                            }
                        }
                    } else {
                        return '';
                    }
                });
            } else {
                formatter( function( value ) { return d3format( value ) } );
            }
        }
    };

    /** Add zoom handler */
    function addZoom( options ) {
        var scaleExtent = 100;
        var yAxis       = options.yAxis;
        var xAxis       = options.xAxis;
        var xDomain     = options.xDomain || xAxis.scale().domain;
        var yDomain     = options.yDomain || yAxis.scale().domain;
        var redraw      = options.redraw;
        var svg         = options.svg;
        var xScale      = xAxis.scale();
        var yScale      = yAxis.scale();
        var x_boundary  = xScale.domain().slice();
        var y_boundary  = yScale.domain().slice();
        var d3zoom      = d3.behavior.zoom();
        xScale.nice();
        yScale.nice();
        function fixDomain( domain, boundary ) {
            domain[ 0 ] = Math.min( Math.max( domain[ 0 ], boundary[ 0 ] ), boundary[ 1 ] - boundary[ 1 ]/scaleExtent );
            domain[ 1 ] = Math.max( boundary[ 0 ] + boundary[ 1 ] / scaleExtent, Math.min( domain[ 1 ], boundary[ 1 ] ) );
            return domain;
        };
        function zoomed() {
            yDomain( fixDomain( yScale.domain(), y_boundary ) );
            xDomain( fixDomain( xScale.domain(), x_boundary ) );
            redraw();
        };
        function unzoomed() {
            xDomain( x_boundary );
            yDomain( y_boundary );
            redraw();
            d3zoom.scale( 1 );
            d3zoom.translate( [ 0 , 0 ] );
        };
        d3zoom.x( xScale )
              .y( yScale )
              .scaleExtent( [ 1, scaleExtent ] )
              .on( 'zoom', zoomed );
        svg.call( d3zoom ).on( 'dblclick.zoom', unzoomed );
        return d3zoom;
    };

    return {
        buildRequestDictionary  : buildRequestDictionary,
        panelHelper             : panelHelper,
        makeCategories          : makeCategories,
        makeUniqueCategories    : makeUniqueCategories,
        makeSeries              : makeSeries,
        getDomains              : getDomains,
        mapCategories           : mapCategories,
        makeTickFormat          : makeTickFormat,
        addZoom                 : addZoom
    }

});
