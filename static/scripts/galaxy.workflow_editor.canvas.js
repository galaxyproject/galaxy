function Terminal( element ) {
    this.element = element;
    this.connectors = [];
}
$.extend( Terminal.prototype, {
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
});

function OutputTerminal( element, datatypes ) {
    Terminal.call( this, element );
    this.datatypes = datatypes;
}

OutputTerminal.prototype = new Terminal();

function InputTerminal( element, datatypes ) {
    Terminal.call( this, element );
    this.datatypes = datatypes;
}

InputTerminal.prototype = new Terminal();

$.extend( InputTerminal.prototype, {
    can_accept: function ( other ) {
        if ( this.connectors.length < 1 ) {
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
                    if ( cat_outputs[other_datatype_i] == "input" || issubtype( cat_outputs[other_datatype_i], this.datatypes[t] ) ) {
                        return true;
                    }
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
    this.outer_color = "#D8B365";
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
            $(this).bind( "dropinit", function( e, d ) {
                // Accept a dragable if it is an output terminal and has a
                // compatible type
                return $(d.drag).hasClass( "output-terminal" ) && terminal.can_accept( d.drag.terminal );
            }).bind( "dropstart", function( e, d  ) {
                d.proxy.terminal.connectors[0].inner_color = "#BBFFBB";
            }).bind( "dropend", function ( e, d ) {
                d.proxy.terminal.connectors[0].inner_color = "#FFFFFF";
            }).bind( "drop", function( e, d ) {
                ( new Connector( d.drag.terminal, terminal ) ).redraw();
            }).bind( "hover", function() {
                // If connected, create a popup to allow disconnection
                if ( terminal.connectors.length > 0 ) {
                    // Create callout
                    var t = $("<div class='callout'></div>")
                        .css( { display: 'none' } )
                        .appendTo( "body" )
                        .append(
                            $("<div class='buttons'></div>").append(
                                $("<img/>").attr("src", galaxy_paths.attributes.image_path + '/delete_icon.png').click( function() {
                                    $.each( terminal.connectors, function( _, x ) {
                                        x.destroy();
                                    });
                                    t.remove();
                                })))
                        .bind( "mouseleave", function() {
                            $(this).remove();
                        });
                    // Position it and show
                    t.css({
                            top: $(this).offset().top - 2,
                            left: $(this).offset().left - t.width(),
                            'padding-right': $(this).width()
                        }).show();
                }
            });
            node.input_terminals[name] = terminal;
        });
    },
    enable_output_terminal : function( elements, name, type ) {
        var node = this;
        $(elements).each( function() {
            var terminal_element = this;
            var terminal = this.terminal = new OutputTerminal( this, type );
            terminal.node = node;
            terminal.name = name;
            $(this).bind( "dragstart", function( e, d ) { 
                $( d.available ).addClass( "input-terminal-active" );
                // Save PJAs in the case of change datatype actions.
                workflow.check_changes_in_active_form(); 
                // Drag proxy div
                var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' )
                    .appendTo( "#canvas-container" ).get(0);
                // Terminal and connection to display noodle while dragging
                h.terminal = new OutputTerminal( h );
                var c = new Connector();
                c.dragging = true;
                c.connect( this.terminal, h.terminal );
                return h;
            }).bind( "drag", function ( e, d ) {
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
            }).bind( "dragend", function ( e, d ) {
                d.proxy.terminal.connectors[0].destroy();
                $(d.proxy).remove();
                $( d.available ).removeClass( "input-terminal-active" );
                $("#canvas-container").get(0).scroll_panel.stop();
            });
            node.output_terminals[name] = terminal;
        });
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
        var f = this.element;
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

        if ( this.tool_errors ) {
            f.addClass( "tool-node-error" );
        } else {
            f.removeClass( "tool-node-error" );
        }
        var node = this;
        var output_width = Math.max(150, f.width());
        var b = f.find( ".toolFormBody" );
        b.find( "div" ).remove();
        var ibox = $("<div class='inputs'></div>").appendTo( b );
        $.each( data.data_inputs, function( i, input ) {
            var t = $("<div class='terminal input-terminal'></div>");
            node.enable_input_terminal( t, input.name, input.extensions );
            var ib = $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div>" );
            ib.css({  position:'absolute',
                        left: -1000,
                        top: -1000,
                        display:'none'});
            $('body').append(ib);
            output_width = Math.max(output_width, ib.outerWidth());
            ib.css({ position:'',
                       left:'',
                       top:'',
                       display:'' });
            ib.remove();
            ibox.append( ib.prepend( t ) );
        });
        if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
            b.append( $( "<div class='rule'></div>" ) );
        }
        $.each( data.data_outputs, function( i, output ) {
            var t = $( "<div class='terminal output-terminal'></div>" );
            node.enable_output_terminal( t, output.name, output.extensions );
            var label = output.name;
            if ( output.extensions.indexOf( 'input' ) < 0 ) {
                label = label + " (" + output.extensions.join(", ") + ")";
            }
            var r = $("<div class='form-row dataRow'>" + label + "</div>" );
            if (node.type == 'tool'){
                var callout = $("<div class='callout "+label+"'></div>")
                    .css( { display: 'none' } )
                    .append(
                        $("<div class='buttons'></div>").append(
                            $("<img/>").attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small-outline.png').click( function() {
                                if ($.inArray(output.name, node.workflow_outputs) != -1){
                                    node.workflow_outputs.splice($.inArray(output.name, node.workflow_outputs), 1);
                                    callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small-outline.png');
                                }else{
                                    node.workflow_outputs.push(output.name);
                                    callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small.png');
                                }
                                workflow.has_changes = true;
                                canvas_manager.draw_overview();
                            })))
                    .tipsy({delayIn:500, fallback: "Flag this as a workflow output.  All non-flagged outputs will be hidden." });
                callout.css({
                        top: '50%',
                        margin:'-8px 0px 0px 0px',
                        right: 8
                    });
                callout.show();
                r.append(callout);
                if ($.inArray(output.name, node.workflow_outputs) === -1){
                    callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small-outline.png');
                }else{
                    callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small.png');
                }
                r.hover(
                    function(){
                        callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small-yellow.png');
                    },
                    function(){
                        if ($.inArray(output.name, node.workflow_outputs) === -1){
                            callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small-outline.png');
                        }else{
                            callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small.png');
                        }
                    });
            }
            r.css({  position:'absolute',
                        left: -1000,
                        top: -1000,
                        display:'none'});
            $('body').append(r);
            output_width = Math.max(output_width, r.outerWidth() + 17);
            r.css({ position:'',
                       left:'',
                       top:'',
                       display:'' });
            r.detach();
            b.append( r.append( t ) );
        });
        f.css( "width", Math.min(250, Math.max(f.width(), output_width )));
        workflow.node_changed( this );
    },
    update_field_data : function( data ) {
        var el = $(this.element),
            node = this;
        this.tool_state = data.tool_state;
        this.form_html = data.form_html;
        this.tool_errors = data.tool_errors;
        this.annotation = data['annotation'];
        var pja_in = $.parseJSON(data.post_job_actions);
        this.post_job_actions = pja_in ? pja_in : {};
        if ( this.tool_errors ) {
                el.addClass( "tool-node-error" );
        } else {
                el.removeClass( "tool-node-error" );
        }
        // Update input rows
        var old_body = el.find( "div.inputs" );
        var new_body = $("<div class='inputs'></div>");
        var old = old_body.find( "div.input-data-row");
        $.each( data.data_inputs, function( i, input ) {
            var t = $("<div class='terminal input-terminal'></div>");
            node.enable_input_terminal( t, input.name, input.extensions );
            // If already connected save old connection
            old_body.find( "div[name='" + input.name + "']" ).each( function() {
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
        });
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
        var using_workflow_outputs, has_existing_pjas = false;
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
                    if (pjas_to_rem.length > 0 && node == workflow.active_node) {
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
                $.each( t.connectors, function ( i, c ) {
                    input_connections[ t.name ] = { id: c.handle1.node.id, output_name: c.handle1.name };
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
            var node = prebuild_node( "tool", step.name, step.tool_id );
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
                    var other_node = wf.nodes[ v.id ];
                    var c = new Connector();
                    c.connect( other_node.output_terminals[ v.output_name ],
                               node.input_terminals[ k ] );
                    c.redraw();
                }
            });
            if(using_workflow_outputs && node.type === 'tool'){
                // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                $.each(node.output_terminals, function(ot_id, ot){
                    if(node.post_job_actions['HideDatasetAction'+ot.name] === undefined){
                        node.workflow_outputs.push(ot.name);
                        callout = $(node.element).find('.callout.'+ot.name);
                        callout.find('img').attr('src', galaxy_paths.attributes.image_path + '/fugue/asterisk-small.png');
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
    var node = new Node( f );
    node.type = type;
    if ( type == 'tool' ) {
        node.tool_id = tool_id;
    }
    var title = $("<div class='toolFormTitle unselectable'>" + title_text + "</div>" );
    f.append( title );
    f.css( "left", $(window).scrollLeft() + 20 ); f.css( "top", $(window).scrollTop() + 20 );    
    var b = $("<div class='toolFormBody'></div>");
    var tmp = "<div><img height='16' align='middle' src='" +galaxy_paths.attributes.image_path+ "/loading_small_white_bg.gif'/> loading tool info...</div>";
    b.append( tmp );
    node.form_html = tmp;
    f.append( b );
    // Fix width to computed width
    // Now add floats
    var buttons = $("<div class='buttons' style='float: right;'></div>");
    buttons.append( $("<img/>").attr("src", galaxy_paths.attributes.image_path + '/delete_icon.png').click( function( e ) {
        node.destroy();
    } ).hover( 
        function() { $(this).attr( "src", galaxy_paths.attributes.image_path + "/delete_icon_dark.png" ); },
        function() { $(this).attr( "src", galaxy_paths.attributes.image_path + "/delete_icon.png" ); }
    ) );
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
