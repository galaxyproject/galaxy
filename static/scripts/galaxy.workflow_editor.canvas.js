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

OutputTerminal.prototype = new Terminal;

function InputTerminal( element, datatypes ) {
    Terminal.call( this, element );
    this.datatypes = datatypes;
}

InputTerminal.prototype = new Terminal;

$.extend( InputTerminal.prototype, {
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
});

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#D8B365"
    if ( handle1 && handle2 ) {
        this.connect( handle1, handle2 );
    }
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
            // excanvas specific hack
            if ( window.G_vmlCanvasManager ) {
                G_vmlCanvasManager.initElement( this.canvas );
            }
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
        var node = this;
        $(elements).each( function() {
            var terminal = this.terminal = new InputTerminal( this, types );
            terminal.node = node;
            terminal.name = name;
            $(this).bind( "dropstart", function( e ) {
                e.dragProxy.terminal.connectors[0].inner_color = "#BBFFBB";
            }).bind( "dropend", function ( e ) {
                e.dragProxy.terminal.connectors[0].inner_color = "#FFFFFF";
            }).bind( "drop", function( e ) {
                new Connector( e.dragTarget.terminal, e.dropTarget.terminal ).redraw();
            }).bind( "hover", function() {
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
                            $(this).remove();
                        });
                    // Position it and show
                    t.css( {
                            top: $(this).offset().top - 2,
                            left: $(this).offset().left - t.width(),
                            'padding-right': $(this).width() }
                        ).show();
                }
            });
            node.input_terminals[name] = terminal;
        })
    },
    enable_output_terminal : function( elements, name, type ) {
        var node = this;
        $(elements).each( function() {
            var terminal_element = this;
            var terminal = this.terminal = new OutputTerminal( this, type );
            terminal.node = node;
            terminal.name = name;
            $(this).bind( "dragstart", function( e ) { 
                    var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' ).appendTo( "#canvas-container" ).get(0);
                    h.terminal = new OutputTerminal( h );
                    var c = new Connector();
                    c.dragging = true;
                    c.connect( this.terminal, h.terminal );
                    $.dropManage({
                        filter: function( e ) {
                            return this.terminal.can_accept( terminal );
                        }
                    }).addClass( "input-terminal-active" );
                    return h;
            }).bind( "drag", function ( e ) {
                var onmove = function() {
                    var po = $(e.dragProxy).offsetParent().offset(),
                        x = e.offsetX - po.left,
                        y = e.offsetY - po.top;
                    $(e.dragProxy).css( { left: x, top: y } );
                    e.dragProxy.terminal.redraw();
                }
                onmove();
                $("#canvas-container").get(0).scroll_panel.test( e, onmove );
            }).bind( "dragend", function ( e ) {
                e.dragProxy.terminal.connectors[0].destroy();
                $(e.dragProxy).remove();
                $.dropManage().removeClass( "input-terminal-active" );
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
        (function(p) { p.removeChild( element ); p.appendChild( element ) })(element.parentNode);
        // Remove active class
        $(element).removeClass( "toolForm-active" );
    },
    init_field_data : function ( data ) {
        var f = this.element;
        if ( data.type ) {
            this.type = data.type;
        }
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
        var ibox = $("<div class='inputs'></div>").appendTo( b );
        $.each( data.data_inputs, function( i, input ) {
            var t = $("<div class='terminal input-terminal'></div>");
            node.enable_input_terminal( t, input.name, input.extensions );
            ibox.append( $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div>" ).prepend( t ) );
        });
        if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
            b.append( $( "<div class='rule'></div>" ) );
        }
        $.each( data.data_outputs, function( i, output ) {
            var t = $( "<div class='terminal output-terminal'></div>" );
            node.enable_output_terminal( t, output.name, output.extension );
            var label = output.name
            if ( output.extension != 'input' ) {
                label = label + " (" + output.extension + ")";
            }
            b.append( $("<div class='form-row dataRow'>" + label + "</div>" ).append( t ) );
        });
        workflow.node_changed( this );
    },
    update_field_data : function( data ) {
        var el = $(this.element),
            node = this;
        this.tool_state = data.tool_state;
        this.form_html = data.form_html;
        this.tool_errors = data.tool_errors;
        if ( this.tool_errors ) {
                el.addClass( "tool-node-error" );
        } else {
                el.removeClass( "tool-node-error" );
        }
        // Update input rows
        var old_body = el.find( "div.inputs" );
        var new_body = $("<div class='inputs'></div>");
        var old = old_body.find( "div.input-data-row")
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
            new_body.append( $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div>" ).prepend( t ) );
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
                type : node.type,
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
            var node = prebuild_node( "tool", step.name, step.tool_id );
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
            this.active_node = null;
        }
        parent.show_form_for_tool( "<div>No node selected</div>" );
    },
    activate_node : function( node ) {
        if ( this.active_node != node ) {
            this.clear_active_node();
            parent.show_form_for_tool( node.form_html, node );
            node.make_active();
            this.active_node = node;
        }
    },
    node_changed : function ( node ) {
        this.has_changes = true;
        if ( this.active_node == node ) {
            // Reactive with new form_html
            parent.show_form_for_tool( node.form_html, node );
        }
    },
    layout : function () {
        // Prepare predecessor / successor tracking
        var n_pred = {};
        var successors = {};
        $.each( this.nodes, function( i, node ) {
            $.each( node.input_terminals, function ( j, t ) {
                $.each( t.connectors, function ( k, c ) {
                    // A connection exists from `other` to `node`
                    var other = c.handle1.node;
                    // Init all tracking arrays
                    if ( n_pred[other.id] === undefined ) { n_pred[other.id] = 0; }
                    if ( n_pred[node.id] === undefined ) { n_pred[node.id] = 0; }
                    if ( successors[other.id] === undefined ) { successors[other.id] = []; }
                    if ( successors[node.id] === undefined ) { successors[node.id] = []; }
                    // node gains a predecessor
                    n_pred[node.id] += 1;
                    // other gains a successor
                    successors[other.id].push( node.id );
                });
            });
        });
        // Assemble order, tracking levels
        node_ids_by_level = []
        while ( true ) {
            // Everything without a predecessor
            level_parents = []
            $.each( n_pred, function( k, v ) {
                if ( v == 0 ) {
                    level_parents.push( k );
                }
            });            
            if ( level_parents.length == 0 ) {
                break;
            }
            node_ids_by_level.push( level_parents )
            // Remove the parents from this level, and decrement the number
            // of predecessors for each successor
            $.each( level_parents, function( k, v ) {
                delete n_pred[v];
                $.each( successors[v], function( sk, sv ) {
                    n_pred[sv] -= 1;
                });
            });
        }
        if ( n_pred.length ) {
            // ERROR: CYCLE! Currently we do nothing
            return
        }
        // Layout each level
        var all_nodes = this.nodes;
        var h_pad = 80; v_pad = 30;
        var left = h_pad;        
        $.each( node_ids_by_level, function( i, ids ) {
            // We keep nodes in the same order in a level to give the user
            // some control over ordering
            ids.sort( function( a, b ) {
                return $(all_nodes[a].element).position().top - $(all_nodes[b].element).position().top
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
        $.each( all_nodes, function( _, node ) { node.redraw() } );
    }
});

function prebuild_node( type, title_text, tool_id ) {
    var f = $("<div class='toolForm toolFormInCanvas'></div>");
    var node = new Node( f );
    node.type = type
    if ( type == 'tool' ) {
        node.tool_id = tool_id;
    }
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
    var buttons = $("<div class='buttons' style='float: right;'></div>");
    buttons.append( $("<img src='../images/delete_icon.png' />").click( function( e ) {
        node.destroy();
    } ).hover( 
        function() { $(this).attr( 'src', "../images/delete_icon_dark.png" ) },
        function() { $(this).attr( 'src', "../images/delete_icon.png" ) }
    ) );
    // Place inside container
    f.appendTo( "#canvas-container" );
    // Position in container
    var o = $("#canvas-container").position();
    f.css( { left: ( - o.left ) + 10, top: ( - o.top ) + 10 } );
    var width = f.width();
    buttons.prependTo( title );
    width += ( buttons.width() + 10 );
    f.css( "width", width );
    $(f).bind( "dragstart", function() {
        workflow.activate_node( node );
    }).bind( "dragend", function() {
        workflow.node_changed( this );
    }).bind( "dragclickonly", function() {
       workflow.activate_node( node ); 
    }).bind( "drag", function( e ) {
        // Move
        var po = $(this).offsetParent().offset(),
            x = e.offsetX - po.left,
            y = e.offsetY - po.top;
        $(this).css( { left: x, top: y } );
        // Redraw
        $(this).find( ".terminal" ).each( function() {
            this.terminal.redraw();
        });
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

function ScrollPanel( panel ) {
    this.panel = panel;
}
$.extend( ScrollPanel.prototype, {
    test: function( e, onmove ) {
        clearTimeout( this.timeout );
        var x = e.pageX,
            y = e.pageY;
            // Panel size and position
            panel = $(this.panel),
            panel_pos = panel.position(),
            panel_w = panel.width(),
            panel_h = panel.height()
            // Viewport size and offset
            viewport = panel.parent();
            viewport_w = viewport.width(),
            viewport_h = viewport.height(),
            viewport_offset = viewport.offset(),
            // Edges of viewport (in page coordinates)
            min_x = viewport_offset.left,
            min_y = viewport_offset.top,
            max_x = min_x + viewport.width(),
            max_y = min_y + viewport.height(),
            // Legal panel range
            p_min_x = - ( panel_w - viewport_w ),
            p_min_y = - ( panel_h - viewport_h ),
            p_max_x = 0,
            p_max_y = 0,
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
    drag: function( e, ui ) {
        clearTimeout( this.timeout );
        var element = e.dragProxy,
            panel = this.panel,
            panel_pos = panel.position(),
            panel_w = panel.width(),
            panel_h = panel.height()
            viewport = panel.parent();
            viewport_w = viewport.width(),
            viewport_h = viewport.height(),
            element_w = element.width(),
            element_h = element.height(),
            moved = false,
            close_dist = 5,
            nudge = 23,
            // Legal panel range
            p_min_x = - ( panel_w - viewport_w ),
            p_min_y = - ( panel_h - viewport_h ),
            p_max_x = 0,
            p_max_y = 0,
            // Visible
            min_vis_x = - panel_pos.left,
            max_vis_x = min_vis_x + viewport_w,
            min_vis_y = - panel_pos.top,
            max_vis_y = min_vis_y + viewport_h,
            // Mouse
            mouse_x = ui.position.left + instance.offset.click.left;
            mouse_y = ui.position.top + instance.offset.click.top;
        // Move it
        if ( ( panel_pos.left < p_max_x ) && ( mouse_x - close_dist < min_vis_x ) ) {
            var t = Math.min( nudge, p_max_x - panel_pos.left );
            panel.css( "left", panel_pos.left + t );
            moved = true;
            instance.offset.parent.left += t;
            ui.position.left -= t
        }
        if ( ( ! moved ) && ( panel_pos.left > p_min_x ) && ( mouse_x + close_dist > max_vis_x ) ) {
            var t = Math.min( nudge, panel_pos.left  - p_min_x );
            panel.css( "left", panel_pos.left - t );
            moved = true;
            instance.offset.parent.left -= t;
            ui.position.left += t;      
        }
        if ( ( ! moved ) && ( panel_pos.top < p_max_y ) && ( mouse_y - close_dist < min_vis_y ) ) {
            var t = Math.min( nudge, p_max_y - panel_pos.top );
            panel.css( "top", panel_pos.top + t );
            // Firefox sometimes moves by less, so we need to check. Yuck.
            var amount_moved = panel.position().top - panel_pos.top;
            instance.offset.parent.top += amount_moved;
            ui.position.top -= amount_moved;
            moved = true;
        }
        if ( ( ! moved ) && ( panel_pos.top > p_min_y ) && ( mouse_y + close_dist > max_vis_y ) ) {
            var t = Math.min( nudge, panel_pos.top  - p_min_x );
            panel.css( "top", ( panel_pos.top - t ) + "px" );
            // Firefox sometimes moves by less, so we need to check. Yuck.
            var amount_moved = panel_pos.top - panel.position().top;   
            instance.offset.parent.top -= amount_moved;
            ui.position.top += amount_moved;
            moved = true;
        }
        // Still contain in panel
        ui.position.left = Math.max( ui.position.left, 0 );
        ui.position.top = Math.max( ui.position.top, 0 );
        ui.position.left = Math.min( ui.position.left, panel_w - element_w );
        ui.position.top = Math.min( ui.position.top, panel_h - element_h );
        // Update offsets
        if ( moved ) {
            $.ui.ddmanager.prepareOffsets( instance, e );
        }
        // Keep moving even if mouse doesn't move
        if ( moved ) {
            this.timeout = setTimeout( function() { instance.mouseMove( e ) }, 50 );
        }
    },
    stop: function( e, ui ) {
        var instance = $(this).data("draggable");
        clearTimeout( instance.timeout );
    }
});