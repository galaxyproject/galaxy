function CollectionTypeDescription( collectionType ) {
    this.collectionType = collectionType;
    this.isCollection = true;
    this.rank = collectionType.split(":").length;
}

$.extend( CollectionTypeDescription.prototype, {
    append: function( otherCollectionTypeDescription ) {
        if( otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION ) {
            return this;
        }
        if( otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION ) {
            return otherCollectionType;
        }
        return new CollectionTypeDescription( this.collectionType + ":" + otherCollectionTypeDescription.collectionType );
    },
    canMatch: function( otherCollectionTypeDescription ) {
        if( otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        if( otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION ) {
            return true;
        }
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    },
    canMapOver: function( otherCollectionTypeDescription ) {
        if( otherCollectionTypeDescription === NULL_COLLECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        if( otherCollectionTypeDescription === ANY_COLLECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        if( this.rank <= otherCollectionTypeDescription.rank ) {
            // Cannot map over self...
            return false;
        }
        var requiredSuffix = otherCollectionTypeDescription.collectionType
        return this._endsWith( this.collectionType, requiredSuffix );
    },
    effectiveMapOver: function( otherCollectionTypeDescription ) {
        var otherCollectionType = otherCollectionTypeDescription.collectionType;
        var effectiveCollectionType = this.collectionType.substring( 0, this.collectionType.length - otherCollectionType.length - 1 );
        return new CollectionTypeDescription( effectiveCollectionType );
    },
    equal: function( otherCollectionTypeDescription ) {
        return otherCollectionTypeDescription.collectionType == this.collectionType;
    },
    toString: function() {
        return "CollectionType[" + this.collectionType + "]";
    },
    _endsWith: function( str, suffix ) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    }
} );

NULL_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: false,
    canMatch: function( other ) { return false; },
    canMapOver: function( other ) {
        return false;
    },
    toString: function() {
        return "NullCollectionType[]";
    },
    append: function( otherCollectionType ) {
        return otherCollectionType;
    },
    equal: function( other ) {
        return other === this;
    }
};

ANY_COLLECTION_TYPE_DESCRIPTION = {
    isCollection: true,
    canMatch: function( other ) { return NULL_COLLECTION_TYPE_DESCRIPTION !== other; },
    canMapOver: function( other ) {
        return false;
    },
    toString: function() {
        return "AnyCollectionType[]";
    },
    append: function( otherCollectionType ) {
        throw "Cannot append to ANY_COLLECTION_TYPE_DESCRIPTION";
    },
    equal: function( other ) {
        return other === this;
    }
};

var TerminalMapping = Backbone.Model.extend( {
    initialize: function( attr ) {
        this.mapOver = attr.mapOver || NULL_COLLECTION_TYPE_DESCRIPTION;
        this.terminal = attr.terminal;
        this.terminal.terminalMapping = this;
    },
    disableMapOver: function() {
        this.setMapOver( NULL_COLLECTION_TYPE_DESCRIPTION );
    },
    setMapOver: function( collectionTypeDescription ) {
        // TODO: Can I use "attributes" or something to auto trigger "change"
        // event?
        this.mapOver = collectionTypeDescription;
        this.trigger("change");
    }
} );

var TerminalMappingView = Backbone.View.extend( {
    tagName: "div",
    className: "fa-icon-button fa fa-folder-o",

    initialize: function( options ) {
        var mapText = "Run tool in parallel over collection";
        this.$el.tooltip( {delay: 500, title: mapText } );
        this.model.bind( "change", _.bind( this.render, this ) );
    },

    render: function() {
        if( this.model.mapOver.isCollection ) {
            this.$el.show();
        } else {
            this.$el.hide();
        }
    },

} );

var InputTerminalMappingView = TerminalMappingView.extend( {
    events: {
        "click": "onClick",
        "mouseenter": "onMouseEnter",
        "mouseleave": "onMouseLeave",
    },
    onMouseEnter: function( e ) {
        var model = this.model;
        if( ! model.terminal.connected() && model.mapOver.isCollection ) {
            this.$el.css( "color", "red" );
        }
    },
    onMouseLeave: function( e ) {
        this.$el.css( "color", "black" );
    },
    onClick: function( e ) {
        var model = this.model;
        if( ! model.terminal.connected() && model.mapOver.isCollection ) {
            // TODO: Consider prompting...
            model.terminal.resetMapping();
        }
    },
} );

var InputTerminalMapping = TerminalMapping;
var InputCollectionTerminalMapping = TerminalMapping;
var OutputTerminalMapping = TerminalMapping;
var OutputTerminalMappingView = TerminalMappingView;
var InputCollectionTerminalMappingView = InputTerminalMappingView;
var OutputCollectionTerminalMapping = TerminalMapping;
var OutputCollectionTerminalMappingView = TerminalMappingView;

var Terminal = Backbone.Model.extend( {
    initialize: function( attr ) {
        this.element = attr.element;
        this.connectors = [];
    },
    connect: function ( connector ) {
        this.connectors.push( connector );
        if ( this.node ) {
            this.node.markChanged();
        }
    },
    disconnect: function ( connector ) {
        this.connectors.splice( $.inArray( connector, this.connectors ), 1 );
        if ( this.node ) {
            this.node.markChanged();
            this.resetMappingIfNeeded();
        }
    },
    redraw: function () {
        $.each( this.connectors, function( _, c ) {
            c.redraw();  
        });
    },
    destroy: function () {
        $.each( this.connectors.slice(), function( _, c ) {
            c.destroy();
        });
    },
    destroyInvalidConnections: function( ) {
        _.each( this.connectors, function( connector ) {
            connector.destroyIfInvalid();
        } );
    },
    setMapOver : function( val ) {
        if( this.multiple ) {
            return; // Cannot set this to be multirun...
        }

        if( ! this.mapOver().equal( val ) ) {
            this.terminalMapping.setMapOver( val );
            _.each( this.node.output_terminals, function( outputTerminal ) {
                outputTerminal.setMapOver( val );
            } );
        }
    },
    mapOver: function( ) {
        if ( ! this.terminalMapping ) {
            return NULL_COLLECTION_TYPE_DESCRIPTION;
        } else {
            return this.terminalMapping.mapOver;
        }
    },
    isMappedOver: function( ) {
        return this.terminalMapping && this.terminalMapping.mapOver.isCollection;
    },
    resetMapping: function() {
        this.terminalMapping.disableMapOver();
    },

    resetMappingIfNeeded: function( ) {}, // Subclasses should override this...

} );

var OutputTerminal = Terminal.extend( {
    initialize: function( attr ) {
        Terminal.prototype.initialize.call( this, attr );
        this.datatypes = attr.datatypes;
    },

    resetMappingIfNeeded: function( ) {
        // If inputs were only mapped over to preserve
        // an output just disconnected reset these...
        if( ! this.node.hasConnectedOutputTerminals() && ! this.node.hasConnectedMappedInputTerminals()){
            _.each( this.node.mappedInputTerminals(), function( mappedInput ) {
                mappedInput.resetMappingIfNeeded();
            } );
        }

        var noMappedInputs = ! this.node.hasMappedOverInputTerminals();
        if( noMappedInputs ) {
            this.resetMapping();
        }
    },

    resetMapping: function() {
        this.terminalMapping.disableMapOver();
        _.each( this.connectors, function( connector ) {
            var connectedInput = connector.handle2;
            if( connectedInput ) {
                // Not exactly right because this is still connected.
                // Either rewrite resetMappingIfNeeded or disconnect
                // and reconnect if valid.
                connectedInput.resetMappingIfNeeded();
                connector.destroyIfInvalid();
            }
        } );
    }

} );


var BaseInputTerminal = Terminal.extend( {
    initialize: function( attr ) {
        Terminal.prototype.initialize.call( this, attr );
        this.update( attr.input ); // subclasses should implement this...
    },
    canAccept: function ( other ) {
        if( this._inputFilled() ) {
            return false;
        } else {
            return this.attachable( other );
        }
    },
    resetMappingIfNeeded: function( ) {
        var mapOver = this.mapOver();
        if( ! mapOver.isCollection ) {
            return;
        }
        // No output terminals are counting on this being mapped
        // over if connected inputs are still mapped over or if none
        // of the outputs are connected...
        var reset = this.node.hasConnectedMappedInputTerminals() ||
                        ( ! this.node.hasConnectedOutputTerminals() );
        if( reset ) {
            this.resetMapping();
        }
    },
    resetMapping: function() {
        this.terminalMapping.disableMapOver();
        if( ! this.node.hasMappedOverInputTerminals() ) {
            _.each( this.node.output_terminals, function( terminal) {
                // This shouldn't be called if there are mapped over
                // outputs.
                terminal.resetMapping();
            } );
        }
    },
    connected: function() {
        return this.connectors.length !== 0;
    },
    _inputFilled: function() {
        var inputFilled;
        if( ! this.connected() ) {
            inputFilled = false;
        } else {
            if( this.multiple ) {
                if(this._collectionAttached()) {
                    // Can only attach one collection to multiple input
                    // data parameter.
                    inputsFilled = true;
                } else {
                    inputFilled = false;
                }
            } else {
                inputFilled = true;
            }
        }
        return inputFilled;
    },
    _collectionAttached: function( ) {
        if( ! this.connected() ) {
            return false;
        } else {
            var firstOutput = this.connectors[ 0 ].handle1;
            if( ! firstOutput ){
                return false;
            } else {
                if( firstOutput.isDataCollectionInput || firstOutput.isMappedOver() || firstOutput.datatypes.indexOf( "input_collection" ) > 0 ) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    },
    _mappingConstraints: function( ) {
        // If this is a connected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        if( ! this.node ) {
            return [];  // No node - completely unconstrained
        }
        var mapOver = this.mapOver();
        if( mapOver.isCollection ) {
            return [ mapOver ];
        }

        var constraints = [];
        if( ! this.node.hasConnectedOutputTerminals() ) {
            _.each( this.node.connectedMappedInputTerminals(), function( inputTerminal ) {
                constraints.push( inputTerminal.mapOver() );
            } );
        } else {
            // All outputs should have same mapOver status - least specific.
            constraints.push( _.first( _.values( this.node.output_terminals ) ).mapOver() );
        }
        return constraints;
    },
    _producesAcceptableDatatype: function( other ) {
        // other is a non-collection output...
        for ( var t in this.datatypes ) {
            var cat_outputs = new Array();
            cat_outputs = cat_outputs.concat(other.datatypes);
            if (other.node.post_job_actions){
                for (var pja_i in other.node.post_job_actions){
                    var pja = other.node.post_job_actions[pja_i];
                    if (pja.action_type == "ChangeDatatypeAction" && (pja.output_name == '' || pja.output_name == other.name) && pja.action_arguments){
                        cat_outputs.push(pja.action_arguments['newtype']);
                    }
                }
            }
            // FIXME: No idea what to do about case when datatype is 'input'
            for ( var other_datatype_i in cat_outputs ) {
                var other_datatype = cat_outputs[other_datatype_i];
                if ( other_datatype == "input" || other_datatype == "input_collection" || issubtype( cat_outputs[other_datatype_i], this.datatypes[t] ) ) {
                    return true;
                }
            }
        }
        return false;
    },
    _otherCollectionType: function( other ) {
        var otherCollectionType = NULL_COLLECTION_TYPE_DESCRIPTION;
        if( other.isDataCollectionInput ) {
            otherCollectionType = other.collectionType;
        } else {
            var otherMapOver = other.mapOver();
            if( otherMapOver.isCollection ) {
                otherCollectionType = otherMapOver;
            }
        }
        return otherCollectionType;
    },
} );





var InputTerminal = BaseInputTerminal.extend( {
    update: function( input ) {
        this.datatypes = input.extensions;
        this.multiple = input.multiple;
        this.collection = false;    	
    },
    connect: function( connector ) {
        BaseInputTerminal.prototype.connect.call( this, connector );
        var other_output = connector.handle1;
        if( ! other_output ) {
            return;
        }
        var otherCollectionType = this._otherCollectionType( other_output );
        if( otherCollectionType.isCollection ) {
            this.setMapOver( otherCollectionType );
        }
    },
    attachable: function( other ) {
        var otherCollectionType = this._otherCollectionType( other );
        var thisMapOver = this.mapOver();
        if( otherCollectionType.isCollection ) {
            if( this.multiple ) {
                if( this.connected() && ! this._collectionAttached() ) {
                    // if single inputs attached, cannot also attach a
                    // collection (yet...)
                    return false;
                }
                if( otherCollectionType.rank == 1 ) {
                    return this._producesAcceptableDatatype( other );
                } else {
                    // TODO: Allow subcollection mapping over this as if it were
                    // a list collection input.
                    return false;
                }
            }
            if( thisMapOver.isCollection && thisMapOver.canMatch( otherCollectionType ) ) {
                return this._producesAcceptableDatatype( other );
            } else {
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
                if( mappingConstraints.every( _.bind( otherCollectionType.canMatch, otherCollectionType ) ) ) {
                    return this._producesAcceptableDatatype( other );
                } else {
                    return false;
                }
            }
        } else if( thisMapOver.isCollection ) {
            // Attempting to match a non-collection output to an
            // explicitly collection input.
            return false;
        }
        return this._producesAcceptableDatatype( other );
    }

});

var InputCollectionTerminal = BaseInputTerminal.extend( {
    update: function( input ) {
        this.multiple = false;
        this.collection = true;
        this.datatypes = input.extensions;
        if( input.collection_type ) {
            this.collectionType = new CollectionTypeDescription( input.collection_type );
        } else {
            this.collectionType = ANY_COLLECTION_TYPE_DESCRIPTION;
        }
    },
    connect: function( connector ) {
        BaseInputTerminal.prototype.connect.call( this, connector );
        var other = connector.handle1;
        if( ! other ) {
            return;
        }

        var effectiveMapOver = this._effectiveMapOver( other );
        this.setMapOver( effectiveMapOver );
    },
    _effectiveMapOver: function( other ) {
        var collectionType = this.collectionType;
        var otherCollectionType = this._otherCollectionType( other );
        if( ! collectionType.canMatch( otherCollectionType ) ) {
            return otherCollectionType.effectiveMapOver( collectionType );
        } else {
            return NULL_COLLECTION_TYPE_DESCRIPTION;
        }
    },
    _effectiveCollectionType: function( ) {
        var collectionType = this.collectionType;
        var thisMapOver = this.mapOver();
        return thisMapOver.append( collectionType );
    },
    attachable: function ( other ) {
        var otherCollectionType = this._otherCollectionType( other );
        if( otherCollectionType.isCollection ) {
            var effectiveCollectionType = this._effectiveCollectionType( );
            var thisMapOver = this.mapOver();
            if( effectiveCollectionType.canMatch( otherCollectionType ) ) {
                // Only way a direct match...
                return this._producesAcceptableDatatype( other );
                // Otherwise we need to mapOver
            } else if( thisMapOver.isCollection ) {
                // In this case, mapOver already set and we didn't match skipping...
                return false;
            } else if( otherCollectionType.canMapOver( this.collectionType ) ) {
                var effectiveMapOver = this._effectiveMapOver( other );
                if( ! effectiveMapOver.isCollection ) {
                    return false;
                }
                //  Need to check if this would break constraints...
                var mappingConstraints = this._mappingConstraints();
                if( mappingConstraints.every( effectiveMapOver.canMatch ) ) {
                    return this._producesAcceptableDatatype( other );
                }
            }
        }
        return false;
    }
});

var OutputCollectionTerminal = Terminal.extend( {
    initialize: function( attr ) {
        Terminal.prototype.initialize.call( this, attr );
        this.datatypes = attr.datatypes;
        this.collectionType = new CollectionTypeDescription( attr.collection_type );
        this.isDataCollectionInput = true;
    },
    update: function( output ) {
        var newCollectionType = new CollectionTypeDescription( output.collection_type );
        if( newCollectionType.collectionType != this.collectionType.collectionType ) {
            _.each( this.connectors, function( connector ) {
                // TODO: consider checking if connection valid before removing...
                connector.destroy();
            } );
        }
        this.collectionType = newCollectionType;
    }
} );

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#D8B365";
    if ( handle1 && handle2 ) {
        this.connect( handle1, handle2 );
    }
}
$.extend( Connector.prototype, {
    connect: function ( t1, t2 ) {
        this.handle1 = t1;
        if ( this.handle1 ) {
            this.handle1.connect( this );
        }
        this.handle2 = t2;
        if ( this.handle2 ) {
            this.handle2.connect( this );
        }
    },
    destroy : function () {
        if ( this.handle1 ) {
            this.handle1.disconnect( this );
        }
        if ( this.handle2 ) {
            this.handle2.disconnect( this );
        }
        $(this.canvas).remove();
    },
    destroyIfInvalid: function() {
        if( this.handle1 && this.handle2 && ! this.handle2.attachable( this.handle1 ) ) {
            this.destroy();
        }        
    },
    redraw : function () {
        var canvas_container = $("#canvas-container");
        if ( ! this.canvas ) {
            this.canvas = document.createElement( "canvas" );
            // excanvas specific hack
            if ( window.G_vmlCanvasManager ) {
                G_vmlCanvasManager.initElement( this.canvas );
            }
            canvas_container.append( $(this.canvas) );
            if ( this.dragging ) {
                this.canvas.style.zIndex = "300";
            }
        }
        var relativeLeft = function( e ) {
            return $(e).offset().left - canvas_container.offset().left;
        };
        var relativeTop = function( e ) {
            return $(e).offset().top - canvas_container.offset().top;
        };
        if (!this.handle1 || !this.handle2) {
            return;
        }
        // Find the position of each handle
        var start_x = relativeLeft( this.handle1.element ) + 5;
        var start_y = relativeTop( this.handle1.element ) + 5;
        var end_x = relativeLeft( this.handle2.element ) + 5;
        var end_y = relativeTop( this.handle2.element ) + 5;
        // Calculate canvas area
        var canvas_extra = 100;
        var canvas_min_x = Math.min( start_x, end_x );
        var canvas_max_x = Math.max( start_x, end_x );
        var canvas_min_y = Math.min( start_y, end_y );
        var canvas_max_y = Math.max( start_y, end_y );
        var cp_shift = Math.min( Math.max( Math.abs( canvas_max_y - canvas_min_y ) / 2, 100 ), 300 );
        var canvas_left = canvas_min_x - canvas_extra;
        var canvas_top = canvas_min_y - canvas_extra;
        var canvas_width = canvas_max_x - canvas_min_x + 2 * canvas_extra;
        var canvas_height = canvas_max_y - canvas_min_y + 2 * canvas_extra;
        // Place the canvas
        this.canvas.style.left = canvas_left + "px";
        this.canvas.style.top = canvas_top + "px";
        this.canvas.setAttribute( "width", canvas_width );
        this.canvas.setAttribute( "height", canvas_height );
        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;
        // Draw the line

        var c = this.canvas.getContext("2d"),
            start_offsets = null,
            end_offsets = null;
        var num_offsets = 1;
        if ( this.handle1 && this.handle1.isMappedOver() ) {
            var start_offsets = [ -6, -3, 0, 3, 6 ];
            num_offsets = 5;
        } else {
            var start_offsets = [ 0 ];
        }
        if ( this.handle2 && this.handle2.isMappedOver() ) {
            var end_offsets = [ -6, -3, 0, 3, 6 ];
            num_offsets = 5;
        } else {
            var end_offsets = [ 0 ];
        }
        var connector = this;
        for( var i = 0; i < num_offsets; i++ ) {
            var inner_width = 5,
                outer_width = 7;
            if( start_offsets.length > 1 || end_offsets.length > 1 ) {
                // We have a multi-run, using many lines, make them small.
                inner_width = 1;
                outer_width = 3;
            }
            connector.draw_outlined_curve( start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, start_offsets[ i % start_offsets.length ], end_offsets[ i % end_offsets.length ] ); 
        }
    },
    draw_outlined_curve : function( start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, offset_start, offset_end ) {
        var offset_start = offset_start || 0;
        var offset_end = offset_end || 0;
        var c = this.canvas.getContext("2d");
        c.lineCap = "round";
        c.strokeStyle = this.outer_color;
        c.lineWidth = outer_width;
        c.beginPath();
        c.moveTo( start_x, start_y + offset_start );
        c.bezierCurveTo( start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end);
        c.stroke();
        // Inner line
        c.strokeStyle = this.inner_color;
        c.lineWidth = inner_width;
        c.beginPath();
        c.moveTo( start_x, start_y + offset_start );
        c.bezierCurveTo( start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end );
        c.stroke();
    }
} );

var Node = Backbone.Model.extend({

    initialize: function( attr ) {
        this.element = attr.element;
        this.input_terminals = {};
        this.output_terminals = {};
        this.tool_errors = {};
    },
    connectedOutputTerminals: function() {
        return this._connectedTerminals( this.output_terminals );
    },
    _connectedTerminals: function( terminals ) {
        var connectedTerminals = [];
        $.each( terminals, function( _, t ) {
            if( t.connectors.length > 0 ) {
                connectedTerminals.push( t );
            }
        } );
        return connectedTerminals;        
    },
    hasConnectedOutputTerminals: function() {
        // return this.connectedOutputTerminals().length > 0; <- optimized this
        var outputTerminals = this.output_terminals;
        for( var outputName in outputTerminals ) {
            if( outputTerminals[ outputName ].connectors.length > 0 ) {
                return true;
            }
        }
        return false;
    },
    connectedMappedInputTerminals: function() {
        return this._connectedMappedTerminals( this.input_terminals );
    },
    hasConnectedMappedInputTerminals: function() {
        // return this.connectedMappedInputTerminals().length > 0; <- optimized this
        var inputTerminals = this.input_terminals;
        for( var inputName in inputTerminals ) {
            var inputTerminal = inputTerminals[ inputName ];
            if( inputTerminal.connectors.length > 0 && inputTerminal.isMappedOver() ) {
                return true;
            }
        }
        return false;
    },
    _connectedMappedTerminals: function( terminals ) {
        var mapped_outputs = [];
        $.each( terminals, function( _, t ) {
            var mapOver = t.mapOver();
            if( mapOver.isCollection ) {
                if( t.connectors.length > 0 ) {
                    mapped_outputs.push( t );
                }
            }
        });
        return mapped_outputs;
    },
    mappedInputTerminals: function() {
        return this._mappedTerminals( this.input_terminals );
    },
    _mappedTerminals: function( terminals ) {
        var mappedTerminals = [];
        $.each( terminals, function( _, t ) {
            var mapOver = t.mapOver();
            if( mapOver.isCollection ) {
                mappedTerminals.push( t );
            }
        } );
        return mappedTerminals;
    },
    hasMappedOverInputTerminals: function() {
        var found = false;
        _.each( this.input_terminals, function( t ) {
            var mapOver = t.mapOver();
            if( mapOver.isCollection ) {
                found = true;
            }
        } );
        return found;
    },
    redraw : function () {
        $.each( this.input_terminals, function( _, t ) {
            t.redraw();
        });
        $.each( this.output_terminals, function( _, t ) {
            t.redraw();
        });
    },
    destroy : function () {
        $.each( this.input_terminals, function( k, t ) {
            t.destroy();
        });
        $.each( this.output_terminals, function( k, t ) {
            t.destroy();
        });
        workflow.remove_node( this );
        $(this.element).remove();
    },
    make_active : function () {
        $(this.element).addClass( "toolForm-active" );
    },
    make_inactive : function () {
        // Keep inactive nodes stacked from most to least recently active
        // by moving element to the end of parent's node list
        var element = this.element.get(0);
        (function(p) { p.removeChild( element ); p.appendChild( element ); })(element.parentNode);
        // Remove active class
        $(element).removeClass( "toolForm-active" );
    },
    init_field_data : function ( data ) {
        if ( data.type ) {
            this.type = data.type;
        }
        this.name = data.name;
        this.form_html = data.form_html;
        this.tool_state = data.tool_state;
        this.tool_errors = data.tool_errors;
        this.tooltip = data.tooltip ? data.tooltip : "";
        this.annotation = data.annotation;
        this.post_job_actions = data.post_job_actions ? data.post_job_actions : {};
        this.workflow_outputs = data.workflow_outputs ? data.workflow_outputs : [];

        var node = this;
        var nodeView = new NodeView({
            el: this.element[ 0 ],
            node: node,
        });
        node.nodeView = nodeView;

        $.each( data.data_inputs, function( i, input ) {
            nodeView.addDataInput( input );
        });
        if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
            nodeView.addRule();
        }
        $.each( data.data_outputs, function( i, output ) {
            nodeView.addDataOutput( output );
        } );
        nodeView.render();
        workflow.node_changed( this );
    },
    update_field_data : function( data ) {
        var node = this;
            nodeView = node.nodeView;
        this.tool_state = data.tool_state;
        this.form_html = data.form_html;
        this.tool_errors = data.tool_errors;
        this.annotation = data['annotation'];
        if( "post_job_actions" in data ) {
            // Won't be present in response for data inputs
            var pja_in = $.parseJSON(data.post_job_actions);
            this.post_job_actions = pja_in ? pja_in : {};
        }
        node.nodeView.renderToolErrors();
        // Update input rows
        var old_body = nodeView.$( "div.inputs" );
        var new_body = nodeView.newInputsDiv();
        var newTerminalViews = {};
        _.each( data.data_inputs, function( input ) {
            var terminalView = node.nodeView.addDataInput( input, new_body );
            newTerminalViews[ input.name ] = terminalView;
        });
        // Cleanup any leftover terminals
        _.each( _.difference( _.values( nodeView.terminalViews ), _.values( newTerminalViews ) ), function( unusedView ) {
            unusedView.el.terminal.destroy();
        } );
        nodeView.terminalViews = newTerminalViews;
        // In general workflow editor assumes tool outputs don't change in # or
        // type (not really valid right?) but adding special logic here for
        // data collection input parameters that can have their collection
        // change.
        if( data.data_outputs.length == 1 && "collection_type" in data.data_outputs[ 0 ] ) {
            nodeView.updateDataOutput( data.data_outputs[ 0 ] );
        }

        old_body.replaceWith( new_body );
        // If active, reactivate with new form_html
        this.markChanged();
        this.redraw();
    },
    error : function ( text ) {
        var b = $(this.element).find( ".toolFormBody" );
        b.find( "div" ).remove();
        var tmp = "<div style='color: red; text-style: italic;'>" + text + "</div>";
        this.form_html = tmp;
        b.html( tmp );
        workflow.node_changed( this );
    },
    markChanged: function() {
        workflow.node_changed( this );
    }
} );

function Workflow( canvas_container ) {
    this.canvas_container = canvas_container;
    this.id_counter = 0;
    this.nodes = {};
    this.name = null;
    this.has_changes = false;
    this.active_form_has_changes = false;
}
$.extend( Workflow.prototype, {
    add_node : function( node ) {
        node.id = this.id_counter;
        node.element.attr( 'id', 'wf-node-step-' + node.id );
        this.id_counter++;
        this.nodes[ node.id ] = node;
        this.has_changes = true;
        node.workflow = this;
    },
    remove_node : function( node ) {
        if ( this.active_node == node ) {
            this.clear_active_node();
        }
        delete this.nodes[ node.id ] ;
        this.has_changes = true;
    },
    remove_all : function() {
        wf = this;
        $.each( this.nodes, function ( k, v ) {
            v.destroy();
            wf.remove_node( v );
        });
    },
    rectify_workflow_outputs : function() {
        // Find out if we're using workflow_outputs or not.
        var using_workflow_outputs = false;
        var has_existing_pjas = false;
        $.each( this.nodes, function ( k, node ) {
            if (node.workflow_outputs && node.workflow_outputs.length > 0){
                using_workflow_outputs = true;
            }
            $.each(node.post_job_actions, function(pja_id, pja){
                if (pja.action_type === "HideDatasetAction"){
                    has_existing_pjas = true;
                }
            });
        });
        if (using_workflow_outputs !== false || has_existing_pjas !== false){
            // Using workflow outputs, or has existing pjas.  Remove all PJAs and recreate based on outputs.
            $.each(this.nodes, function (k, node ){
                if (node.type === 'tool'){
                    var node_changed = false;
                    if (node.post_job_actions == null){
                        node.post_job_actions = {};
                        node_changed = true;
                    }
                    var pjas_to_rem = [];
                    $.each(node.post_job_actions, function(pja_id, pja){
                        if (pja.action_type == "HideDatasetAction"){
                            pjas_to_rem.push(pja_id);
                        }
                    });
                    if (pjas_to_rem.length > 0 ) {
                        $.each(pjas_to_rem, function(i, pja_name){
                            node_changed = true;
                            delete node.post_job_actions[pja_name];
                        });
                    }
                    if (using_workflow_outputs){
                        $.each(node.output_terminals, function(ot_id, ot){
                            var create_pja = true;
                            $.each(node.workflow_outputs, function(i, wo_name){
                                if (ot.name === wo_name){
                                    create_pja = false;
                                }
                            });
                            if (create_pja === true){
                                node_changed = true;
                                var pja = {
                                    action_type : "HideDatasetAction",
                                    output_name : ot.name,
                                    action_arguments : {}
                                }
                                node.post_job_actions['HideDatasetAction'+ot.name] = null;
                                node.post_job_actions['HideDatasetAction'+ot.name] = pja;
                            }
                        });
                    }
                    // lastly, if this is the active node, and we made changes, reload the display at right.
                    if (workflow.active_node == node && node_changed === true) {
                        workflow.reload_active_node();
                    }
                }
            });
        }
    },
    to_simple : function () {
        var nodes = {};
        $.each( this.nodes, function ( i, node ) {
            var input_connections = {};
            $.each( node.input_terminals, function ( k, t ) {
                input_connections[ t.name ] = null;
                // There should only be 0 or 1 connectors, so this is
                // really a sneaky if statement
                var cons = []
                $.each( t.connectors, function ( i, c ) {
                    cons[i] = { id: c.handle1.node.id, output_name: c.handle1.name };
                    input_connections[ t.name ] = cons;
                });
            });
            var post_job_actions = {};
            if (node.post_job_actions){
                $.each( node.post_job_actions, function ( i, act ) {
                    var pja = {
                        action_type : act.action_type, 
                        output_name : act.output_name, 
                        action_arguments : act.action_arguments
                    }
                    post_job_actions[ act.action_type + act.output_name ] = null;
                    post_job_actions[ act.action_type + act.output_name ] = pja;
                });
            }
            if (!node.workflow_outputs){
                node.workflow_outputs = [];
                // Just in case.
            }
            var node_data = {
                id : node.id,
                type : node.type,
                tool_id : node.tool_id,
                tool_state : node.tool_state,
                tool_errors : node.tool_errors,
                input_connections : input_connections,
                position : $(node.element).position(),
                annotation: node.annotation,
                post_job_actions: node.post_job_actions,
                workflow_outputs: node.workflow_outputs
            };
            nodes[ node.id ] = node_data;
        });
        return { steps: nodes };
    },
    from_simple : function ( data ) {
        wf = this;
        var max_id = 0;
        wf.name = data.name;
        // First pass, nodes
        var using_workflow_outputs = false;
        $.each( data.steps, function( id, step ) {
            var node = prebuild_node( step.type, step.name, step.tool_id );
            node.init_field_data( step );
            if ( step.position ) {
                node.element.css( { top: step.position.top, left: step.position.left } );
            }
            node.id = step.id;
            wf.nodes[ node.id ] = node;
            max_id = Math.max( max_id, parseInt( id ) );
            // For older workflows, it's possible to have HideDataset PJAs, but not WorkflowOutputs.
            // Check for either, and then add outputs in the next pass.
            if (!using_workflow_outputs && node.type === 'tool'){
                if (node.workflow_outputs.length > 0){
                    using_workflow_outputs = true;
                }
                else{
                    $.each(node.post_job_actions, function(pja_id, pja){
                        if (pja.action_type === "HideDatasetAction"){
                            using_workflow_outputs = true;
                        }
                    });
                }
            }
        });
        wf.id_counter = max_id + 1;
        // Second pass, connections
        $.each( data.steps, function( id, step ) {
            var node = wf.nodes[id];
            $.each( step.input_connections, function( k, v ) {
                if ( v ) {
                    if ( ! $.isArray( v ) ) {
                        v = [ v ];
                    }
                    $.each( v, function( l, x ) {
                        var other_node = wf.nodes[ x.id ];
                        var c = new Connector();
                        c.connect( other_node.output_terminals[ x.output_name ],
                                   node.input_terminals[ k ] );
                        c.redraw();
                    });
                }
            });
            if(using_workflow_outputs && node.type === 'tool'){
                // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                $.each(node.output_terminals, function(ot_id, ot){
                    if(node.post_job_actions['HideDatasetAction'+ot.name] === undefined){
                        node.workflow_outputs.push(ot.name);
                        callout = $(node.element).find('.callout.'+ot.name);
                        callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                        workflow.has_changes = true;
                    }
                });
            }
        });
    },
    check_changes_in_active_form : function() {
        // If active form has changed, save it
        if (this.active_form_has_changes) {
            this.has_changes = true;
            // Submit form.
            $("#right-content").find("form").submit();
            this.active_form_has_changes = false;
        }
    },
    reload_active_node : function() {
        if (this.active_node){
            var node = this.active_node;
            this.clear_active_node();
            this.activate_node(node);
        }
    },
    clear_active_node : function() {
        if ( this.active_node ) {
            this.active_node.make_inactive();
            this.active_node = null;
        }
        parent.show_form_for_tool( "<div>No node selected</div>" );
    },
    activate_node : function( node ) {
        if ( this.active_node != node ) {
            this.check_changes_in_active_form();
            this.clear_active_node();
            parent.show_form_for_tool( node.form_html + node.tooltip, node );
            node.make_active();
            this.active_node = node;
        }
    },
    node_changed : function ( node ) {
        this.has_changes = true;
        if ( this.active_node == node ) {
            // Reactive with new form_html
            this.check_changes_in_active_form(); //Force changes to be saved even on new connection (previously dumped)
            parent.show_form_for_tool( node.form_html + node.tooltip, node );
        }
    },
    layout : function () {
        this.check_changes_in_active_form();
        this.has_changes = true;
        // Prepare predecessor / successor tracking
        var n_pred = {};
        var successors = {};
        // First pass to initialize arrays even for nodes with no connections
        $.each( this.nodes, function( id, node ) {
            if ( n_pred[id] === undefined ) { n_pred[id] = 0; }
            if ( successors[id] === undefined ) { successors[id] = []; }
        });
        // Second pass to count predecessors and successors
        $.each( this.nodes, function( id, node ) {
            $.each( node.input_terminals, function ( j, t ) {
                $.each( t.connectors, function ( k, c ) {
                    // A connection exists from `other` to `node`
                    var other = c.handle1.node;
                    // node gains a predecessor
                    n_pred[node.id] += 1;
                    // other gains a successor
                    successors[other.id].push( node.id );
                });
            });
        });
        // Assemble order, tracking levels
        node_ids_by_level = [];
        while ( true ) {
            // Everything without a predecessor
            level_parents = [];
            for ( var pred_k in n_pred ) {
                if ( n_pred[ pred_k ] == 0 ) {
                    level_parents.push( pred_k );
                }
            }        
            if ( level_parents.length == 0 ) {
                break;
            }
            node_ids_by_level.push( level_parents );
            // Remove the parents from this level, and decrement the number
            // of predecessors for each successor
            for ( var k in level_parents ) {
                var v = level_parents[k];
                delete n_pred[v];
                for ( var sk in successors[v] ) {
                    n_pred[ successors[v][sk] ] -= 1;
                }
            }
        }
        if ( n_pred.length ) {
            // ERROR: CYCLE! Currently we do nothing
            return;
        }
        // Layout each level
        var all_nodes = this.nodes;
        var h_pad = 80; v_pad = 30;
        var left = h_pad;        
        $.each( node_ids_by_level, function( i, ids ) {
            // We keep nodes in the same order in a level to give the user
            // some control over ordering
            ids.sort( function( a, b ) {
                return $(all_nodes[a].element).position().top - $(all_nodes[b].element).position().top;
            });
            // Position each node
            var max_width = 0;
            var top = v_pad;
            $.each( ids, function( j, id ) {
                var node = all_nodes[id];
                var element = $(node.element);
                $(element).css( { top: top, left: left } );
                max_width = Math.max( max_width, $(element).width() );
                top += $(element).height() + v_pad;
            });
            left += max_width + h_pad;
        });
        // Need to redraw all connectors
        $.each( all_nodes, function( _, node ) { node.redraw(); } );
    },
    bounds_for_all_nodes: function() {
        var xmin = Infinity, xmax = -Infinity,
            ymin = Infinity, ymax = -Infinity,
            p;
        $.each( this.nodes, function( id, node ) {
            e = $(node.element);
            p = e.position();
            xmin = Math.min( xmin, p.left );
            xmax = Math.max( xmax, p.left + e.width() );
            ymin = Math.min( ymin, p.top );
            ymax = Math.max( ymax, p.top + e.width() );
        });
        return  { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax };
    },
    fit_canvas_to_nodes: function() {
        // Span of all elements
        var bounds = this.bounds_for_all_nodes();
        var position = this.canvas_container.position();
        var parent = this.canvas_container.parent();
        // Determine amount we need to expand on top/left
        var xmin_delta = fix_delta( bounds.xmin, 100 );
        var ymin_delta = fix_delta( bounds.ymin, 100 );
        // May need to expand farther to fill viewport
        xmin_delta = Math.max( xmin_delta, position.left );
        ymin_delta = Math.max( ymin_delta, position.top );
        var left = position.left - xmin_delta;
        var top = position.top - ymin_delta;
        // Same for width/height
        var width = round_up( bounds.xmax + 100, 100 ) + xmin_delta;
        var height = round_up( bounds.ymax + 100, 100 ) + ymin_delta;
        width = Math.max( width, - left + parent.width() );
        height = Math.max( height, - top + parent.height() );
        // Grow the canvas container
        this.canvas_container.css( {
            left: left,
            top: top,
            width: width,
            height: height
        });
        // Move elements back if needed
        this.canvas_container.children().each( function() {
            var p = $(this).position();
            $(this).css( "left", p.left + xmin_delta );
            $(this).css( "top", p.top + ymin_delta );
        });
    }
});

function fix_delta( x, n ) {
    if ( x < n|| x > 3*n ) {
        new_pos = ( Math.ceil( ( ( x % n ) ) / n ) + 1 ) * n;
        return ( - ( x - new_pos ) );
    }
    return 0;
}
    
function round_up( x, n ) {
    return Math.ceil( x / n ) * n;
}
     
function prebuild_node( type, title_text, tool_id ) {
    var f = $("<div class='toolForm toolFormInCanvas'></div>");
    var node = new Node( { element: f } );
    node.type = type;
    if ( type == 'tool' ) {
        node.tool_id = tool_id;
    }
    var title = $("<div class='toolFormTitle unselectable'>" + title_text + "</div>" );
    f.append( title );
    f.css( "left", $(window).scrollLeft() + 20 ); f.css( "top", $(window).scrollTop() + 20 );    
    var b = $("<div class='toolFormBody'></div>");
    var tmp = "<div><img height='16' align='middle' src='" + galaxy_config.root + "static/images/loading_small_white_bg.gif'/> loading tool info...</div>";
    b.append( tmp );
    node.form_html = tmp;
    f.append( b );
    // Fix width to computed width
    // Now add floats
    var buttons = $("<div class='buttons' style='float: right;'></div>");
    buttons.append( $("<div>").addClass("fa-icon-button fa fa-times").click( function( e ) {
        node.destroy();
    }));
    // Place inside container
    f.appendTo( "#canvas-container" );
    // Position in container
    var o = $("#canvas-container").position();
    var p = $("#canvas-container").parent();
    var width = f.width();
    var height = f.height();
    f.css( { left: ( - o.left ) + ( p.width() / 2 ) - ( width / 2 ), top: ( - o.top ) + ( p.height() / 2 ) - ( height / 2 ) } );
    buttons.prependTo( title );
    width += ( buttons.width() + 10 );
    f.css( "width", width );
    $(f).bind( "dragstart", function() {
        workflow.activate_node( node );
    }).bind( "dragend", function() {
        workflow.node_changed( this );
        workflow.fit_canvas_to_nodes();
        canvas_manager.draw_overview();
    }).bind( "dragclickonly", function() {
       workflow.activate_node( node ); 
    }).bind( "drag", function( e, d ) {
        // Move
        var po = $(this).offsetParent().offset(),
            x = d.offsetX - po.left,
            y = d.offsetY - po.top;
        $(this).css( { left: x, top: y } );
        // Redraw
        $(this).find( ".terminal" ).each( function() {
            this.terminal.redraw();
        });
    });
    return node;
}

function add_node( type, title_text, tool_id ) {
    // Abstraction for use by galaxy.workflow.js to hide
    // some editor details from workflow code and reduce duplication
    // between add_node_for_tool and add_node_for_module.
    var node = prebuild_node( type, title_text, tool_id );
    workflow.add_node( node );
    workflow.fit_canvas_to_nodes();
    canvas_manager.draw_overview();
    workflow.activate_node( node );    
    return node;
}


var ext_to_type = null;
var type_to_type = null;

function issubtype( child, parent ) {
    child = ext_to_type[child];
    parent = ext_to_type[parent];
    return ( type_to_type[child] ) && ( parent in type_to_type[child] );
}

function populate_datatype_info( data ) {
    ext_to_type = data.ext_to_class_name;
    type_to_type = data.class_to_classes;
}


//////////////
// START VIEWS
//////////////


var NodeView = Backbone.View.extend( {
    initialize: function( options ){
        this.node = options.node;
        this.output_width = Math.max(150, this.$el.width());
        this.tool_body = this.$el.find( ".toolFormBody" );
        this.tool_body.find( "div" ).remove();
        this.newInputsDiv().appendTo( this.tool_body );
        this.terminalViews = {};
        this.outputTerminlViews = {};
    },

    render : function() {
        this.renderToolErrors();
        this.$el.css( "width", Math.min(250, Math.max(this.$el.width(), this.output_width )));
    },

    renderToolErrors: function( ) {
        if ( this.node.tool_errors ) {
            this.$el.addClass( "tool-node-error" );
        } else {
            this.$el.removeClass( "tool-node-error" );
        }
    },

    newInputsDiv: function() {
        return $("<div class='inputs'></div>");
    },

    updateMaxWidth: function( newWidth ) {
        this.output_width = Math.max( this.output_width, newWidth );
    },

    addRule: function() {
        this.tool_body.append( $( "<div class='rule'></div>" ) );
    },

    addDataInput: function( input, body ) {
        var skipResize = true;
        if( ! body ) {
            body = this.$( ".inputs" );
            // initial addition to node - resize input to help calculate node
            // width.
            skipResize = false;
        }
        var terminalView = this.terminalViews[ input.name ];
        var terminalViewClass = ( input.input_type == "dataset_collection" ) ? InputCollectionTerminalView : InputTerminalView;
        if( terminalView && ! ( terminalView instanceof terminalViewClass ) ) {
            terminalView.el.terminal.destroy();
            terminalView = null;
        }
        if( ! terminalView ) {
            terminalView = new terminalViewClass( {
                node: this.node,
                input: input
            } );             
        } else {
            var terminal = terminalView.el.terminal;
            terminal.update( input );
            terminal.destroyInvalidConnections();
        }
        this.terminalViews[ input.name ] = terminalView;
        var terminalElement = terminalView.el;
        var inputView = new DataInputView( {
            terminalElement: terminalElement,
            input: input, 
            nodeView: this,
            skipResize: skipResize
        } );
        var ib = inputView.$el;

        // Append to new body
        body.append( ib.prepend( terminalView.terminalElements() ) );
        return terminalView;
    },

    addDataOutput: function( output ) {
        var terminalViewClass = ( output.collection_type ) ? OutputCollectionTerminalView : OutputTerminalView;
        var terminalView = new terminalViewClass( {
            node: this.node,
            output: output
        } );
        var outputView = new DataOutputView( {
            "output": output,
            "terminalElement": terminalView.el,
            "nodeView": this,
        } );
        this.tool_body.append( outputView.$el.append( terminalView.terminalElements() ) );
    },

    updateDataOutput: function( output ) {
        var outputTerminal = this.node.output_terminals[ output.name ];
        outputTerminal.update( output );
    }

} );



var DataInputView = Backbone.View.extend( {
    className: "form-row dataRow input-data-row",

    initialize: function( options ){
        this.input = options.input;
        this.nodeView = options.nodeView;
        this.terminalElement = options.terminalElement;

        this.$el.attr( "name", this.input.name )
                .html( this.input.label );

        if( ! options.skipResize ) {
            this.$el.css({  position:'absolute',
                            left: -1000,
                            top: -1000,
                            display:'none'});
        $('body').append(this.el);
            this.nodeView.updateMaxWidth( this.$el.outerWidth() );
            this.$el.css({ position:'',
                           left:'',
                           top:'',
                           display:'' });
            this.$el.remove();
        }
    },

} );



var OutputCalloutView = Backbone.View.extend( {
    tagName: "div",

    initialize: function( options ) {
        this.label = options.label;
        this.node = options.node;
        this.output = options.output;

        var view = this;
        this.$el
            .attr( "class", 'callout '+this.label )
            .css( { display: 'none' } )
            .append(
                $("<div class='buttons'></div>").append(
                    $("<img/>").attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png').click( function() {
                        if ($.inArray(view.output.name, view.node.workflow_outputs) != -1){
                            view.node.workflow_outputs.splice($.inArray(view.output.name, view.node.workflow_outputs), 1);
                            view.$('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png');
                        }else{
                            view.node.workflow_outputs.push(view.output.name);
                            view.$('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                        }
                        workflow.has_changes = true;
                        canvas_manager.draw_overview();
                    })))
            .tooltip({delay:500, title: "Mark dataset as a workflow output. All unmarked datasets will be hidden." });
        
        this.$el.css({
                top: '50%',
                margin:'-8px 0px 0px 0px',
                right: 8
            });
        this.$el.show();
        this.resetImage();
    },

    resetImage: function() {
        if ($.inArray( this.output.name, this.node.workflow_outputs) === -1){
            this.$('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png');
        } else{
            this.$('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
        }
    },

    hoverImage: function() {
        this.$('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-yellow.png');
    }

} );




var DataOutputView = Backbone.View.extend( {
    className: "form-row dataRow",

    initialize: function( options ) {
        this.output = options.output;
        this.terminalElement = options.terminalElement;
        this.nodeView = options.nodeView;

        var output = this.output;
        var label = output.name;
        var node = this.nodeView.node;

        var isInput = output.extensions.indexOf( 'input' ) >= 0 || output.extensions.indexOf( 'input_collection' ) >= 0;
        if ( ! isInput ) {
            label = label + " (" + output.extensions.join(", ") + ")";
        }
        this.$el.html( label )

        if (node.type == 'tool'){
            var calloutView = new OutputCalloutView( {
                "label": label,
                "output": output,
                "node": node,
            });
            this.$el.append( calloutView.el );
            this.$el.hover( function() { calloutView.hoverImage() }, function() { calloutView.resetImage() } );
        }
        this.$el.css({  position:'absolute',
                        left: -1000,
                        top: -1000,
                        display:'none'});
        $('body').append( this.el );
        this.nodeView.updateMaxWidth( this.$el.outerWidth() + 17 );
        this.$el.css({ position:'',
                       left:'',
                       top:'',
                       display:'' })
                .detach();
    }

} );


var TerminalView = Backbone.View.extend( {

    setupMappingView: function( terminal ) {
        var terminalMapping = new this.terminalMappingClass( { terminal: terminal } );
        var terminalMappingView = new this.terminalMappingViewClass( { model: terminalMapping } );
        terminalMappingView.render();
        terminal.terminalMappingView = terminalMappingView;
        this.terminalMappingView = terminalMappingView;
    },

    terminalElements: function() {
        if( this.terminalMappingView ) {
            return [ this.terminalMappingView.el, this.el ];
        } else{
            return [ this.el ];
        }
    }

} );


var BaseInputTerminalView = TerminalView.extend( {
    className: "terminal input-terminal",

    initialize: function( options ) {
        var node = options.node;
        var input = options.input;
        var name = input.name;
        var terminal = this.terminalForInput( input );
        if( ! terminal.multiple ) {
            this.setupMappingView( terminal );
        }
        this.el.terminal = terminal;
        terminal.node = node;
        terminal.name = name;
        node.input_terminals[name] = terminal;
    },

    events: {
        "dropinit": "onDropInit",
        "dropstart": "onDropStart",
        "dropend": "onDropEnd",
        "drop": "onDrop",
        "hover": "onHover",
    },

    onDropInit: function( e, d ) {
        var terminal = this.el.terminal;
        // Accept a dragable if it is an output terminal and has a
        // compatible type
        return $(d.drag).hasClass( "output-terminal" ) && terminal.canAccept( d.drag.terminal );
    },

    onDropStart: function( e, d  ) {
        if (d.proxy.terminal) { 
            d.proxy.terminal.connectors[0].inner_color = "#BBFFBB";
        }
    },

    onDropEnd: function ( e, d ) {
        if (d.proxy.terminal) { 
            d.proxy.terminal.connectors[0].inner_color = "#FFFFFF";
        }
    },

    onDrop: function( e, d ) {
        var terminal = this.el.terminal;        
        new Connector( d.drag.terminal, terminal ).redraw();
    },

    onHover: function() {
        var element = this.el;
        var terminal = element.terminal;

        // If connected, create a popup to allow disconnection
        if ( terminal.connectors.length > 0 ) {
            // Create callout
            var t = $("<div class='callout'></div>")
                .css( { display: 'none' } )
                .appendTo( "body" )
                .append(
                    $("<div class='button'></div>").append(
                        $("<div/>").addClass("fa-icon-button fa fa-times").click( function() {
                            $.each( terminal.connectors, function( _, x ) {
                                if (x) {
                                    x.destroy();
                                }
                            });
                            t.remove();
                        })))
                .bind( "mouseleave", function() {
                    $(this).remove();
                });
            // Position it and show
            t.css({
                    top: $(element).offset().top - 2,
                    left: $(element).offset().left - t.width(),
                    'padding-right': $(element).width()
                }).show();
        }
    },

} );

var InputTerminalView = BaseInputTerminalView.extend( {
    terminalMappingClass: InputTerminalMapping,
    terminalMappingViewClass: InputTerminalMappingView,

    terminalForInput: function( input ) {
        return new InputTerminal( { element: this.el, input: input } );
    },

} );

var InputCollectionTerminalView = BaseInputTerminalView.extend( {
    terminalMappingClass: InputCollectionTerminalMapping,
    terminalMappingViewClass: InputCollectionTerminalMappingView,

    terminalForInput: function( input ) {
        return new InputCollectionTerminal( { element: this.el, input: input } );
    },

} );

var BaseOutputTerminalView = TerminalView.extend( {
    className: "terminal output-terminal",

    initialize: function( options ) {
        var node = options.node;
        var output = options.output;

        var name = output.name;
        var terminal = this.terminalForOutput( output );
        this.setupMappingView( terminal );
        this.el.terminal = terminal;
        terminal.node = node;
        terminal.name = name;
        node.output_terminals[name] = terminal;
    },

    events: {
        "drag": "onDrag",
        "dragstart": "onDragStart",
        "dragend": "onDragEnd",
    },

    onDrag: function ( e, d ) {
        var onmove = function() {
            var po = $(d.proxy).offsetParent().offset(),
                x = d.offsetX - po.left,
                y = d.offsetY - po.top;
            $(d.proxy).css( { left: x, top: y } );
            d.proxy.terminal.redraw();
            // FIXME: global
            canvas_manager.update_viewport_overlay();
        };
        onmove();
        $("#canvas-container").get(0).scroll_panel.test( e, onmove );
    },

    onDragStart: function( e, d ) { 
        $( d.available ).addClass( "input-terminal-active" );
        // Save PJAs in the case of change datatype actions.
        workflow.check_changes_in_active_form(); 
        // Drag proxy div
        var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' )
            .appendTo( "#canvas-container" ).get(0);
        // Terminal and connection to display noodle while dragging
        h.terminal = new OutputTerminal( { element: h } );
        var c = new Connector();
        c.dragging = true;
        c.connect( this.el.terminal, h.terminal );
        return h;
    },

    onDragEnd: function ( e, d ) {
        var connector = d.proxy.terminal.connectors[0];
        // check_changes_in_active_form may change the state and cause a
        // the connection to have already been destroyed. There must be better
        // ways to handle this but the following check fixes some serious GUI
        // bugs for now.
        if(connector) {
            connector.destroy();
        }
        $(d.proxy).remove();
        $( d.available ).removeClass( "input-terminal-active" );
        $("#canvas-container").get(0).scroll_panel.stop();
    }

} );

var OutputTerminalView = BaseOutputTerminalView.extend( {
    terminalMappingClass: OutputTerminalMapping,
    terminalMappingViewClass: OutputTerminalMappingView,

    terminalForOutput: function( output ) {
        var type = output.extensions;
        var terminal = new OutputTerminal( { element: this.el, datatypes: type } );
        return terminal;
    },

} );

var OutputCollectionTerminalView = BaseOutputTerminalView.extend( {
    terminalMappingClass: OutputCollectionTerminalMapping,
    terminalMappingViewClass: OutputCollectionTerminalMappingView,

    terminalForOutput: function( output ) {
        var collection_type = output.collection_type;
        var terminal = new OutputCollectionTerminal( { element: this.el, collection_type: collection_type, datatypes: output.extensions } );
        return terminal;
    },

} );


////////////
// END VIEWS
////////////


// FIXME: merge scroll panel into CanvasManager, clean up hardcoded stuff.

function ScrollPanel( panel ) {
    this.panel = panel;
}
$.extend( ScrollPanel.prototype, {
    test: function( e, onmove ) {
        clearTimeout( this.timeout );
        var x = e.pageX,
            y = e.pageY,
            // Panel size and position
            panel = $(this.panel),
            panel_pos = panel.position(),
            panel_w = panel.width(),
            panel_h = panel.height(),
            // Viewport size and offset
            viewport = panel.parent(),
            viewport_w = viewport.width(),
            viewport_h = viewport.height(),
            viewport_offset = viewport.offset(),
            // Edges of viewport (in page coordinates)
            min_x = viewport_offset.left,
            min_y = viewport_offset.top,
            max_x = min_x + viewport.width(),
            max_y = min_y + viewport.height(),
            // Legal panel range
            p_min_x = - ( panel_w - ( viewport_w / 2 ) ),
            p_min_y = - ( panel_h - ( viewport_h / 2 )),
            p_max_x = ( viewport_w / 2 ),
            p_max_y = ( viewport_h / 2 ),
            // Did the panel move?
            moved = false,
            // Constants
            close_dist = 5,
            nudge = 23;
        if ( x - close_dist < min_x ) {
            if ( panel_pos.left < p_max_x ) {
                var t = Math.min( nudge, p_max_x - panel_pos.left );
                panel.css( "left", panel_pos.left + t );
                moved = true;
            }
        } else if ( x + close_dist > max_x ) {
            if ( panel_pos.left > p_min_x ) {
                var t = Math.min( nudge, panel_pos.left  - p_min_x );
                panel.css( "left", panel_pos.left - t );
                moved = true;
            }
        } else if ( y - close_dist < min_y ) {
            if ( panel_pos.top < p_max_y ) {
                var t = Math.min( nudge, p_max_y - panel_pos.top );
                panel.css( "top", panel_pos.top + t );
                moved = true;
            }
        } else if ( y + close_dist > max_y ) {
            if ( panel_pos.top > p_min_y ) {
                var t = Math.min( nudge, panel_pos.top  - p_min_x );
                panel.css( "top", ( panel_pos.top - t ) + "px" );
                moved = true;
            }
        }
        if ( moved ) {
            // Keep moving even if mouse doesn't move
            onmove();
            var panel = this;
            this.timeout = setTimeout( function() { panel.test( e, onmove ); }, 50 );
        }
    },
    stop: function( e, ui ) {
        clearTimeout( this.timeout );
    }
});

function CanvasManager( canvas_viewport, overview ) {
    this.cv = canvas_viewport;
    this.cc = this.cv.find( "#canvas-container" );
    this.oc = overview.find( "#overview-canvas" );
    this.ov = overview.find( "#overview-viewport" );
    // Make overview box draggable
    this.init_drag();
}
$.extend( CanvasManager.prototype, {
    init_drag : function () {
        var self = this;
        var move = function( x, y ) {
            x = Math.min( x, self.cv.width() / 2 );
            x = Math.max( x, - self.cc.width() + self.cv.width() / 2 );
            y = Math.min( y, self.cv.height() / 2 );
            y = Math.max( y, - self.cc.height() + self.cv.height() / 2 );
            self.cc.css( {
                left: x,
                top: y
            });
            self.update_viewport_overlay();
        };
        // Dragging within canvas background
        this.cc.each( function() {
            this.scroll_panel = new ScrollPanel( this );
        });
        var x_adjust, y_adjust;
        this.cv.bind( "dragstart", function() {
            var o = $(this).offset();
            var p = self.cc.position();
            y_adjust = p.top - o.top;
            x_adjust = p.left - o.left;
        }).bind( "drag", function( e, d ) {
            move( d.offsetX + x_adjust, d.offsetY + y_adjust );
        }).bind( "dragend", function() {
            workflow.fit_canvas_to_nodes();
            self.draw_overview();
        });
        // Dragging for overview pane
        this.ov.bind( "drag", function( e, d ) {
            var in_w = self.cc.width(),
                in_h = self.cc.height(),
                o_w = self.oc.width(),
                o_h = self.oc.height(),
                p = $(this).offsetParent().offset(),
                new_x_offset = d.offsetX - p.left,
                new_y_offset = d.offsetY - p.top;
            move( - ( new_x_offset / o_w * in_w ),
                  - ( new_y_offset / o_h * in_h ) );
        }).bind( "dragend", function() {
            workflow.fit_canvas_to_nodes();
            self.draw_overview();
        });
        // Dragging for overview border (resize)
        $("#overview-border").bind( "drag", function( e, d ) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max( op.width() - ( d.offsetX - opo.left ),
                                     op.height() - ( d.offsetY - opo.top ) );
            $(this).css( {
                width: new_size,
                height: new_size
            });
            self.draw_overview();
        });
        
        /*  Disable dragging for child element of the panel so that resizing can
            only be done by dragging the borders */
        $("#overview-border div").bind("drag", function() { });
        
    },
    update_viewport_overlay: function() {
        var cc = this.cc,
            cv = this.cv,
            oc = this.oc,
            ov = this.ov,
            in_w = cc.width(),
            in_h = cc.height(),
            o_w = oc.width(),
            o_h = oc.height(),
            cc_pos = cc.position();        
        ov.css( {
            left: - ( cc_pos.left / in_w * o_w ),
            top: - ( cc_pos.top / in_h * o_h ),
            // Subtract 2 to account for borders (maybe just change box sizing style instead?)
            width: ( cv.width() / in_w * o_w ) - 2,
            height: ( cv.height() / in_h * o_h ) - 2
        });
    },
    draw_overview: function() {
        var canvas_el = $("#overview-canvas"),
            size = canvas_el.parent().parent().width(),
            c = canvas_el.get(0).getContext("2d"),
            in_w = $("#canvas-container").width(),
            in_h = $("#canvas-container").height();
        var o_h, shift_h, o_w, shift_w;
        // Fit canvas into overview area
        var cv_w = this.cv.width();
        var cv_h = this.cv.height();
        if ( in_w < cv_w && in_h < cv_h ) {
            // Canvas is smaller than viewport
            o_w = in_w / cv_w * size;
            shift_w = ( size - o_w ) / 2;
            o_h = in_h / cv_h * size;
            shift_h = ( size - o_h ) / 2;
        } else if ( in_w < in_h ) {
            // Taller than wide
            shift_h = 0;
            o_h = size;
            o_w = Math.ceil( o_h * in_w / in_h );
            shift_w = ( size - o_w ) / 2;
        } else {
            // Wider than tall
            o_w = size;
            shift_w = 0;
            o_h = Math.ceil( o_w * in_h / in_w );
            shift_h = ( size - o_h ) / 2;
        }
        canvas_el.parent().css( {
           left: shift_w,
           top: shift_h,
           width: o_w,
           height: o_h
        });
        canvas_el.attr( "width", o_w );
        canvas_el.attr( "height", o_h );
        // Draw overview
        $.each( workflow.nodes, function( id, node ) {
            c.fillStyle = "#D2C099";
            c.strokeStyle = "#D8B365";
            c.lineWidth = 1;
            var node_element = $(node.element),
                position = node_element.position(),
                x = position.left / in_w * o_w,
                y = position.top / in_h * o_h,
                w = node_element.width() / in_w * o_w,
                h = node_element.height() / in_h * o_h;
            if (node.tool_errors){
                c.fillStyle = "#FFCCCC";
                c.strokeStyle = "#AA6666";
            } else if (node.workflow_outputs != undefined && node.workflow_outputs.length > 0){
                c.fillStyle = "#E8A92D";
                c.strokeStyle = "#E8A92D";
            }
            c.fillRect( x, y, w, h );
            c.strokeRect( x, y, w, h );
        });
        this.update_viewport_overlay();
    }
});
