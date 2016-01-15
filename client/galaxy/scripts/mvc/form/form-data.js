/*
    This class maps the form dom to an api compatible javascript dictionary.
*/
define([ 'utils/utils' ], function( Utils ) {
    var Manager = Backbone.Model.extend({
        initialize: function( app ) {
            this.app = app;
        },

        /** Creates a checksum.
        */
        checksum: function() {
            var sum = '';
            var self = this;
            this.app.section.$el.find( '.section-row' ).each( function() {
                var id = $(this).attr( 'id' );
                var field = self.app.field_list[ id ];
                if ( field ) {
                    sum += id + ':' + JSON.stringify( field.value && field.value() ) + ':' + field.collapsed + ';';
                }
            });
            return sum;
        },

        /** Convert dom into a dictionary of flat id/value pairs used e.g. on job submission.
        */
        create: function() {
            var self = this;

            // get raw dictionary from dom
            var dict = {};
            this._iterate( this.app.section.$el, dict );

            // add to result dictionary, label elements
            var result_dict = {};
            this.flat_dict = {};
            function add( flat_id, input_id, input_value ) {
                self.flat_dict[ flat_id ] = input_id;
                result_dict[ flat_id ] = input_value;
                self.app.element_list[ input_id ] && self.app.element_list[ input_id ].$el.attr( 'tour_id', flat_id );
            }
            // converter between raw dictionary and job dictionary
            function convert( identifier, head ) {
                for ( var index in head ) {
                    var node = head[ index ];
                    if ( node.input ) {
                        var input = node.input;
                        var flat_id = identifier;
                        if ( identifier != '' ) {
                            flat_id += '|';
                        }
                        flat_id += input.name;
                        switch ( input.type ) {
                            case 'repeat':
                                var section_label = 'section-';
                                var block_indices = [];
                                var block_prefix = null;
                                for ( var block_label in node ) {
                                    var pos = block_label.indexOf( section_label );
                                    if ( pos != -1 ) {
                                        pos += section_label.length;
                                        block_indices.push( parseInt( block_label.substr( pos ) ));
                                        if ( !block_prefix ) {
                                            block_prefix = block_label.substr( 0, pos );
                                        }
                                    }
                                }
                                block_indices.sort( function( a, b ) { return a - b; });
                                var index = 0;
                                for ( var i in block_indices ) {
                                    convert( flat_id + '_' + index++, node[ block_prefix + block_indices[ i ] ]);
                                }
                                break;
                            case 'conditional':
                                var value = self.app.field_list[ input.id ].value();
                                add( flat_id + '|' + input.test_param.name, input.id, value );
                                var selectedCase = matchCase( input, value );
                                if ( selectedCase != -1 ) {
                                    convert( flat_id, head[ input.id + '-section-' + selectedCase ] );
                                }
                                break;
                            case 'section':
                                convert( !input.flat && flat_id || '', node );
                                break;
                            default:
                                var field = self.app.field_list[ input.id ];
                                if ( field && field.value ) {
                                    var value = field.value();
                                    if ( input.ignore === undefined || input.ignore != value ) {
                                        if ( field.collapsed && input.collapsible_value ) {
                                            value = input.collapsible_value;
                                        }
                                        add( flat_id, input.id, value );
                                        if ( input.payload ) {
                                            for ( var p_id in input.payload ) {
                                                add( p_id, input.id, input.payload[ p_id ] );
                                            }
                                        }
                                    }
                                }
                        }
                    }
                }
            }
            convert( '', dict );
            return result_dict;
        },

        /** Matches flat ids to corresponding input element
         * @param{string} flat_id - Flat input id to be looked up.
         */
        match: function ( flat_id ) {
            return this.flat_dict && this.flat_dict[ flat_id ];
        },

        /** Match conditional values to selected cases
        */
        matchCase: function( input, value ) {
            return matchCase( input, value );
        },

        /** Matches a new tool model to the current input elements e.g. used to update dynamic options
        */
        matchModel: function( model, callback ) {
            return matchIds( model.inputs, this.flat_dict, callback );
        },

        /** Matches identifier from api response to input elements e.g. used to display validation errors
        */
        matchResponse: function( response ) {
            var result = {};
            var self = this;
            function search ( id, head ) {
                if ( typeof head === 'string' ) {
                    var input_id = self.flat_dict[ id ];
                    input_id && ( result[ input_id ] = head );
                } else {
                    for ( var i in head ) {
                        var new_id = i;
                        if ( id !== '' ) {
                            var separator = '|';
                            if ( head instanceof Array ) {
                                separator = '_';
                            }
                            new_id = id + separator + new_id;
                        }
                        search ( new_id, head[ i ] );
                    }
                }
            }
            search( '', response );
            return result;
        },

        /** Map dom tree to dictionary tree with input elements.
        */
        _iterate: function( parent, dict ) {
            var self = this;
            var children = $( parent ).children();
            children.each( function() {
                var child = this;
                var id = $( child ).attr( 'id' );
                if ( $( child ).hasClass( 'section-row' ) ) {
                    var input = self.app.input_list[ id ];
                    dict[ id ] = ( input && { input : input } ) || {};
                    self._iterate( child, dict[ id ] );
                } else {
                    self._iterate( child, dict );
                }
            });
        }
    });

    /** Match conditional values to selected cases
     * @param{dict}   input     - Definition of conditional input parameter
     * @param{dict}   value     - Current value
     */
    var matchCase = function( input, value ) {
        if ( input.test_param.type == 'boolean' ) {
            if ( value == 'true' ) {
                value = input.test_param.truevalue || 'true';
            } else {
                value = input.test_param.falsevalue || 'false';
            }
        }
        for ( var i in input.cases ) {
            if ( input.cases[ i ].value == value ) {
                return i;
            }
        }
        return -1;
    };

    /** Match context
     * @param{dict}   inputs    - Dictionary of input elements
     * @param{dict}   key       - Reference key which is matched to an input name e.g. data_ref
     * @param{dict}   callback  - Called with matched context i.e. callback( input, referenced_input )
     */
    var matchContext = function( inputs, key, callback, context ) {
        context = $.extend( true, {}, context );
        _.each( inputs, function ( input ) {
            input && input.type && ( context[ input.name ] = input );
        });
        _.each( inputs, function ( input ) {
            if ( _.isObject( input ) ) {
                if ( input.type && context[ input[ key ] ] ) {
                    callback ( input, context[ input[ key ] ] );
                } else {
                    matchContext( input, key, callback, context );
                }
            }
        });
    };

    /** Matches a tool model to a dictionary, indexed with flat ids
     * @param{dict}   inputs    - Dictionary of input elements
     * @param{dict}   mapping   - Dictionary containing flat ids
     * @param{dict}   callback  - Called with the mapped dictionary object and corresponding model node
     */
    var matchIds = function( inputs, mapping, callback ) {
        var result = {};
        var self = this;
        function search ( id, head ) {
            for ( var i in head ) {
                var node = head[ i ];
                var index = node.name;
                id != '' && ( index = id + '|' + index );
                switch ( node.type ) {
                    case 'repeat':
                        for ( var j in node.cache ) {
                            search ( index + '_' + j, node.cache[ j ] );
                        }
                        break;
                    case 'conditional':
                        var selectedCase = matchCase( node, node.test_param && node.test_param.value );
                        selectedCase != -1 && search ( index, node.cases[ selectedCase ].inputs );
                        break;
                    case 'section':
                        search ( index, node.inputs );
                        break;
                    default:
                        var mapped = mapping[ index ];
                        mapped && callback( mapped, node );
                }
            }
        }
        search( '', inputs );
        return result;
    };

    return {
        Manager         : Manager,
        matchIds        : matchIds,
        matchContext    : matchContext
    }
});