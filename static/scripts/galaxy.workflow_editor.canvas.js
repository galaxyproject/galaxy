function Terminal( element ) {
    this.element = element;
    this.connectors = [];
}
Terminal.prototype = {
    connect: function ( connector ) {
        this.connectors.push( connector );
        if ( this.node ) {
            this.node.changed();
        }
    },
    disconnect: function ( connector ) {
        this.connectors.splice( $.inArray( connector, this.connectors ), 1 );
        if ( this.node ) {
            this.node.changed();
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
    }
}

function OutputTerminal( element, datatype ) {
    Terminal.call( this, element );
    this.datatype = datatype;
}

OutputTerminal.prototype.__proto__ = Terminal.prototype;

function InputTerminal( element, datatypes ) {
    Terminal.call( this, element );
    this.datatypes = datatypes;
}

InputTerminal.prototype = {
    __proto__: Terminal.prototype,
    can_accept: function ( other ) {
        if ( this.connectors.length < 1 ) {
            for ( t in this.datatypes ) {
                // FIXME: No idea what to do about this case
                if ( other.datatype == "input" ) { return true; }
                if ( issubtype( other.datatype, this.datatypes[t] ) ) {
                    return true;
                }
            }
        }
        return false;
    }
}

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#D8B365"
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
        var canvas_container = $("#canvas-container");
        if ( ! this.canvas ) {
            this.canvas = document.createElement( "canvas" );
            canvas_container.append( $(this.canvas) );
            if ( this.dragging ) { this.canvas.style.zIndex = "300" }
        }
        var relativeLeft = function( e ) { return $(e).offset().left - canvas_container.offset().left }
        var relativeTop = function( e ) { return $(e).offset().top - canvas_container.offset().top }
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
        var c = this.canvas.getContext("2d");
        c.lineCap = "round";
        c.strokeStyle = this.outer_color;
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
    this.input_terminals = {};
    this.output_terminals = {};
    this.tool_errors = {};
}
$.extend( Node.prototype, {
    enable_input_terminal : function( elements, name, types ) {
        node = this;
        $(elements).each( function() {
            var terminal = this.terminal = new InputTerminal( this, types );
            terminal.node = node;
            terminal.name = name;
            $(this).droppable( {
                tolerance: 'intersect',
                accept: function( draggable ) {
                    draggable = draggable.get( 0 );
                    return ( draggable.terminal ) && ( terminal.can_accept( draggable.terminal ) );
                },
                activeClass: 'input-terminal-active',
                // hoverClass: 'input-terminal-active',
                over: function( e, ui ) {
                    ui.helper.get(0).terminal.connectors[0].inner_color = "#BBFFBB";
                },
                out: function( e, ui ) {
                    ui.helper.get(0).terminal.connectors[0].inner_color = "#FFFFFF";
                },
                drop: function( e, ui ) {
                    var source = ui.draggable.get(0).terminal;
                    var target = ui.element.get(0).terminal;
                    var c = new Connector();
                    c.connect( source, target );
                    c.redraw();
                }
            });
            $(this).hoverIntent(
                function() {
                    // If connected, create a popup to allow disconnection
                    if ( terminal.connectors.length > 0 ) {
                        // Create callout
                        var t = $("<div class='callout'></div>")
                            .css( { display: 'none' } )
                            .appendTo( "body" )
                            .append(
                                $("<div class='buttons'></div>").append(
                                    $("<img src='../images/delete_icon.png' />").click( function() {
                                        $.each( terminal.connectors, function( _, x ) { x.destroy() } );
                                        t.remove();
                                    })))
                            .bind( "mouseleave", function() {
                                $(this).fadeOut( "fast", function() { $(this).remove() } )
                            });
                        // Position it and show
                        t.css( {
                                top: $(this).offset().top - 2,
                                left: $(this).offset().left - t.width(),
                                'padding-right': $(this).width() }
                            ).fadeIn( "fast" );
                    }
                },
                function() {}
            );
            node.input_terminals[name] = terminal;
        })
    },
    enable_output_terminal : function( elements, name, type ) {
        node = this;
        $(elements).each( function() {
           var terminal = this.terminal = new OutputTerminal( this, type ); 
		   terminal.node = node;
		   terminal.name = name;
           $(this).draggable( { 
               scrollPanel: true,
               panel: $("#canvas-container"),
               // containment: 'document',
               // appendTo: "body",
               // cursorAt: { top: 5, left: 5 },
               helper: function () { 
                   var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' ).appendTo( "#canvas-container" ).get(0);
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
                    h = options.helper.get(0);
                    h.terminal.redraw();
               },
               stop: function( e, options ) {
                   this.drag_temp_connector.destroy();
                   // options.helper.remove();
               }
           });
           node.output_terminals[name] = terminal;
       });
    },
    redraw : function () {
        $.each( this.input_terminals, function( _, t ) { t.redraw() } );
        $.each( this.output_terminals, function( _, t ) { t.redraw() } );
    },
    destroy : function () {
        $.each( this.input_terminals, function( k, t ) {
            t.destroy();
            $(t.element).droppable('destroy');
        });
        $.each( this.output_terminals, function( k, t ) {
            t.destroy();
            $(t.element).draggable('destroy');
        });
        $(this.element).draggable('destroy').remove();
	workflow.remove_node( this );
    },
    make_active : function () {
        $(this.element).addClass( "toolForm-active" );
    },
    make_inactive : function () {
        $(this.element).removeClass( "toolForm-active" );
    },
    init_field_data : function ( data ) {
        var f = this.element;
        this.form_html = data.form_html;
        this.tool_state = data.tool_state;
        this.tool_errors = data.tool_errors;
        if ( this.tool_errors ) {
            f.addClass( "tool-node-error" );
        } else {
            f.removeClass( "tool-node-error" );
        }
        var node = this;
        var b = f.find( ".toolFormBody" );
        b.find( "div" ).remove();
        var ibox = $("<div class='inputs'/>").appendTo( b );
        $.each( data.data_inputs, function( i, input ) {
            t = $("<div class='terminal input-terminal'></div>")
            node.enable_input_terminal( t, input.name, input.extensions );
            ibox.append( $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div></div>" ).prepend( t ) );
        });
        if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
            b.append( $( "<div class='rule'></div>" ) );
        }
        $.each( data.data_outputs, function( i, output ) {
            var t = $( "<div class='terminal output-terminal'></div>" );
            node.enable_output_terminal( t, output.name, output.extension );
            b.append( $("<div class='form-row dataRow'>" + output.name + "</div>" ).append( t ) );
        });
        workflow.node_changed( this );
    },
    update_field_data : function( data ) {
        var el = $(this.element),
            node = this;
        this.tool_state = data.state;
        this.form_html = data.form_html;
	this.tool_errors = data.tool_errors;
        if ( this.tool_errors ) {
                el.addClass( "tool-node-error" );
        } else {
                el.removeClass( "tool-node-error" );
        }
        // Update input rows
        var old_body = el.find( "div.inputs" );
        var new_body = $("<div class='inputs'/>");
        old = old_body.find( "div.input-data-row")
        $.each( data.data_inputs, function( i, input ) {
            var t = $("<div class='terminal input-terminal'></div>");
            node.enable_input_terminal( t, input.name, input.extensions );
            // If already connected save old connection
            old_body.find( "div[name=" + input.name + "]" ).each( function() {
                $(this).find( ".input-terminal" ).each( function() {
                    var c = this.terminal.connectors[0];
                    if ( c ) {
                        t[0].terminal.connectors[0] = c;
                        c.handle2 = t[0].terminal;
                    }
                });
                $(this).remove();
            });
            // Append to new body
            new_body.append( $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div></div>" ).prepend( t ) );
        });
        old_body.replaceWith( new_body );
        // Cleanup any leftover terminals
        old_body.find( "div.input-data-row > .terminal" ).each( function() {
            this.terminal.destroy();
        })
        // If active, reactivate with new form_html
        this.changed();
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
    changed: function() {
        workflow.node_changed( this );
    }
} );

function Workflow() {
    this.id_counter = 0;
    this.nodes = {}
    this.name = null;
    this.has_changes = false;
}
$.extend( Workflow.prototype, {
    add_node : function( node ) {
        node.id = this.id_counter;
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
    to_simple : function () {
        var nodes = {}
        $.each( this.nodes, function ( i, node ) {
            var input_connections = {}
            $.each( node.input_terminals, function ( k, t ) {
                input_connections[ t.name ] = null;
                // There should only be 0 or 1 connectors, so this is
                // really a sneaky if statement
                $.each( t.connectors, function ( i, c ) {
                    input_connections[ t.name ] = { id: c.handle1.node.id, output_name: c.handle1.name };
                });
            });
            var node_data = {
                id : node.id,
                tool_id : node.tool_id,
                tool_state : node.tool_state,
                tool_errors : node.tool_errors,
                input_connections : input_connections,
                position : $(node.element).position()
            }
            nodes[ node.id ] = node_data;
        })
        return { steps: nodes }
    },
    from_simple : function ( data ) {
        wf = this;
        var max_id = 0;
        wf.name = data.name;
        // First pass, nodes
        $.each( data.steps, function( id, step ) {
            var node = prebuild_node_for_tool( step.tool_id, step.name );
            node.init_field_data( step );
            if ( step.position ) {
                node.element.css( { top: step.position.top, left: step.position.left } );
            }
            node.id = step.id;
            wf.nodes[ node.id ] = node;
            max_id = Math.max( max_id, parseInt( id ) )
        });
        wf.id_counter = max_id + 1;
        // Second pass, connections
        $.each( data.steps, function( id, step ) {
            var node = wf.nodes[id];
            $.each( step.input_connections, function( k, v ) {
                if ( v ) {
                    var other_node = wf.nodes[ v.id ];
                    var c = new Connector();
                    c.connect( other_node.output_terminals[ v.output_name ],
                               node.input_terminals[ k ] );
                    c.redraw();
                }
            })
        });
    },
    clear_active_node : function() {
        if ( this.active_node ) {
            this.active_node.make_inactive();
        }
        parent.show_form_for_tool( "<div>No node selected</div>" );
    },
    activate_node : function( node ) {
        this.clear_active_node();
        parent.show_form_for_tool( node.form_html, node );
        node.make_active();
        this.active_node = node;
    },
    node_changed : function ( node ) {
        this.has_changes = true;
        if ( this.active_node == node ) {
            // Reactive with new form_html
            this.activate_node( node );
        }
    }
});

function prebuild_node_for_tool( id, title_text ) {
    var f = $("<div class='toolForm toolFormInCanvas'></div>");
    var node = new Node( f );
	node.tool_id = id;
    var title = $("<div class='toolFormTitle unselectable'>" + title_text + "</div>" )
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
    f.appendTo( "#canvas-container" );
    var width = f.width();
    buttons.prependTo( title );
    width += ( buttons.width() + 10 );
    f.css( "width", width );
    // Make draggable
    $(f).draggable( {
        cursor: 'move',
        // handle: title,
        scrollPanel: true,
        panel: $("#canvas-container"),
        scrollSensitivity: 10,
        scrollSpeed: 20,
        // containment: $("#shim"),
        // grow: true,
        click: function( _, element ) {
            (function(p) { p.removeChild( element ); p.appendChild( element ) })(element.parentNode)
            workflow.activate_node( node );
        },
        start: function() {
            workflow.activate_node( node );
            $(this).css( 'z-index', '1000' );
        },
        drag: function() { 
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            })
        },
        stop: function( _, ui  ) {
            element = ui.element.get(0);
            (function(p) { p.removeChild( element ); p.appendChild( element ) })(element.parentNode)
            $(this).css( 'z-index', '100' );
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            });
        }
    });
    return node;
}


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
