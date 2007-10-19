function OutputTerminal( element, datatype ) {
    this.element = element;
    this.connectors = [];
    this.datatype = datatype
}
$.extend( OutputTerminal.prototype, {
    connect: function ( connector ) {
        this.connectors.push( connector );
    },
    disconnect: function ( connector ) {
        this.connectors.splice( this.connectors.indexOf( connector ), 1 );
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
    }
} )

function InputTerminal( element, datatypes ) {
    this.element = element;
    this.connectors = [];
    this.max_connections = 1;
    this.datatypes = datatypes;
}
$.extend( InputTerminal.prototype, {
    connect: function ( connector ) {
        this.connectors.push( connector );
    },
    disconnect: function ( connector ) {
        this.connectors.splice( this.connectors.indexOf( connector ), 1 );
    },
    can_accept: function ( other ) {
        if ( this.connectors.length < this.max_connections ) {
            for ( t in this.datatypes ) {
                // FIXME: No idea what to do about this case
                if ( other.datatype == "input" ) { return true; }
                if ( issubtype( other.datatype, this.datatypes[t] ) ) {
                    return true;
                }
            }
        }
        return false;
    },
    redraw: function () {
        $.each( this.connectors, function( _, c ) {
            c.redraw();  
        })
    },
    destroy: function () {
        $.each( this.connectors.slice(), function( _, c ) {
            c.destroy();
        });
    }
} );

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#EEEEEE";
}
$.extend( Connector.prototype, {
    connect: function ( t1, t2 ) {
        this.handle1 = t1;
        this.handle1.connect( this );
        this.handle2 = t2;
        this.handle2.connect( this );
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
    redraw : function () {
        if ( ! this.canvas ) {
            this.canvas = document.createElement( "canvas" );
            $("body").append( this.canvas );
            if ( this.dragging ) { this.canvas.style.zIndex = "300" }
            this.ctx = this.canvas.getContext("2d");
        }
        // Find the position of each handle
        var o = $(this.handle1.element).offset();
        var start_x = o.left + 5;
        var start_y = o.top + 5;
        var o = $(this.handle2.element).offset();
        var end_x = o.left + 5;
        var end_y = o.top + 5;
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
        var c = this.ctx
        c.lineCap = "round";
        c.strokeStyle = "#999";
        c.lineWidth = 7;
        c.beginPath();
        c.moveTo( start_x, start_y );
        c.bezierCurveTo( start_x + cp_shift, start_y, end_x - cp_shift, end_y, end_x, end_y );
        c.stroke();
        // Inner line
        c.strokeStyle = this.inner_color;
        c.lineWidth = 5;
        c.beginPath();
        c.moveTo( start_x, start_y );
        c.bezierCurveTo( start_x + cp_shift, start_y, end_x - cp_shift, end_y, end_x, end_y );
        c.stroke();
    }
} );

function Node( element ) {
    this.element = element;
    this.input_terminals = [];
    this.output_terminals = [];
}
$.extend( Node.prototype, {
    enable_input_terminal : function( elements, types ) {
        node = this;
        $(elements).each( function() {
            var terminal = this.terminal = new InputTerminal( this, types );
            $(this).droppable( {
                tolerance: 'intersect',
                accept: function( draggable ) {
                    return ( draggable.terminal ) && ( terminal.can_accept( draggable.terminal ) );
                },
                activeClass: 'input-terminal-active',
                // hoverClass: 'input-terminal-active',
                over: function( e, ui ) {
                    ui.helper.terminal.connectors[0].inner_color = "#A8C6AF";
                },
                out: function( e, ui ) {
                    ui.helper.terminal.connectors[0].inner_color = "#EEEEEE";
                },
                drop: function( e, ui ) {
                    var source = ui.draggable.element.terminal;
                    var target = ui.droppable.element.terminal;
                    var c = new Connector();
                    c.connect( source, target );
                    c.redraw();
                }
            }); 
            node.input_terminals.push( terminal );
        })
    },
    enable_output_terminal : function( elements, type ) {
        node = this;
        $(elements).each( function() {
           var terminal = this.terminal = new OutputTerminal( this, type ); 
           $(this).draggable( { 
               scroll: true,
               // containment: 'document',
               // appendTo: "body",
               // cursorAt: { top: 5, left: 5 },
               helper: function () { 
                   var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' ).get(0);
                   h.terminal = new OutputTerminal( h );
                   // // Already a connector? Destroy... no wait, don't
                   // if ( this.terminal.connector ) {
                   //     this.terminal.connector.destroy();
                   // }
                   var c = new Connector();
                   this.drag_temp_connector = c;
                   c.dragging = true;
                   c.connect( this.terminal, h.terminal );
                   return h;
               },
               drag: function ( e, options ) {
                   options.helper.terminal.redraw();
               },
               stop: function( e, options ) {
                   this.drag_temp_connector.destroy();
                   // options.helper.remove();
               }
           });
           node.output_terminals.push( terminal );
       });
    },
    destroy : function () {
        $.each( this.input_terminals, function( i, t ) {
            t.destroy();
            $(t.element).droppableDestroy();
        });
        $.each( this.output_terminals, function( i, t ) {
            t.destroy();
            $(t.element).draggableDestroy();
        });
        $(this.element).draggableDestroy().remove();
    },
    make_active : function () {
        $(this.element).addClass( "toolForm-active" );
    },
    make_inactive : function () {
        $(this.element).removeClass( "toolForm-active" );
    }
} );

function Workflow() {
    this.id_counter = 0;
    this.nodes = {}
}
$.extend( Workflow.prototype, {
    add_node : function( node ) {
        node.id = this.id_counter;
        this.id_counter++;
        this.nodes[ node.id ] = node;
    },
    remove_node : function( node ) {
        this.node[ node.id ] = undefined;
    }
});

function clear_active_node() {
    if ( active_node ) {
        active_node.make_inactive();
    }
    parent.show_form_for_tool( "<div>No node selected</div>" );
}

function activate_node( node ) {
    clear_active_node();
    parent.show_form_for_tool( node.form_html );
    node.make_active();
    active_node = node;
}

function prebuild_node_for_tool( title ) {
    var f = $("<div class='toolForm' style='position: absolute; min-width: 130px'></div>");
    var node = new Node( f );
    var title = $("<div class='toolFormTitle unselectable'>" + title + "</div>" )
    f.append( title );
    f.css( "left", $(window).scrollLeft() + 20 ); f.css( "top", $(window).scrollTop() + 20 );
    
    var b = $("<div class='toolFormBody'></div>")
    var tmp = "<div><img height='16' align='middle' src='../images/loading_small_white_bg.gif'/> loading tool info...</div>";
    b.append( tmp );
    node.form_html = tmp;
    f.append( b )
    // Fix width to computed width
    // Now add floats
    var buttons = $("<div class='buttons' style='float: right'></div>");
    buttons.append( $("<img src='../images/delete_icon.png' />").click( function() { 
        node.destroy();
    } ).hover( 
        function() { $(this).attr( 'src', "../images/delete_icon_dark.png" ) },
        function() { $(this).attr( 'src', "../images/delete_icon.png" ) }
    ) );
    f.appendTo( "body" );
    var width = f.width();
    buttons.prependTo( title );
    width += ( buttons.width() + 10 );
    f.css( "width", width );
    // Make draggable
    $(f).draggable( {
        cursor: 'move',
        handle: title,
        scroll: true,
        scrollSensitivity: 20,
        scrollSpeed: 50,
        containment: $("#shim"),
        // grow: true,
        click: function() {
            document.body.removeChild( this );
            document.body.appendChild( this );
            activate_node( node );
        },
        start: function() {
            activate_node( node );
            $(this).css( 'z-index', '1000' );
        },
        drag: function() { 
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            })
        },
        stop: function() { 
            document.body.removeChild( this );
            document.body.appendChild( this );
            $(this).css( 'z-index', '100' );
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            });
        }
    });
    return node;
}

function update_node_for_tool( node, data ) {
    var f = node.element;
    node.form_html = data.form_html
    b = f.find( ".toolFormBody" );
    b.find( "div" ).remove();
    $.each( data.data_inputs, function( i, input ) {
        t = $("<div class='terminal input-terminal'></div>")
        node.enable_input_terminal( t, input.extensions );
        b.append( $("<div class='form-row dataRow'>" + input.name + "</div></div>" ).prepend( t ) );
    });
    if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
        b.append( $( "<div class='rule'></div>" ) );
    }
    $.each( data.data_outputs, function( i, output ) {
        var t = $( "<div class='terminal output-terminal'></div>" );
        node.enable_output_terminal( t, output.extension );
        b.append( $("<div class='form-row dataRow'>" + output.name + "</div>" ).append( t ) );
    });
    if ( active_node == node ) {
        // Reactive with new form_html
        activate_node( node );
    }
    return node;
};


var ext_to_type = null;
var type_to_type = null;

function issubtype( child, parent ) {
    child = ext_to_type[child];
    parent = ext_to_type[parent];
    return ( parent in type_to_type[child] );
};

function populate_datatype_info( data ) {
    ext_to_type = data.ext_to_class_name;
    type_to_type = data.class_to_classes;
};
