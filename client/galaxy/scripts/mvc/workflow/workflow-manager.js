define([
    'mvc/workflow/workflow-connector',
    'libs/toastr'
    ],
function( Connector, Toastr ) {
    function Workflow( app, canvas_container ) {
        this.app = app;
        this.canvas_container = canvas_container;
        this.id_counter = 0;
        this.nodes = {};
        this.name = null;
        this.has_changes = false;
        this.active_form_has_changes = false;
        this.workflowOutputLabels = {};
    }
    $.extend( Workflow.prototype, {
        canLabelOutputWith: function( label ) {
            if( label ) {
                return ! (label in this.workflowOutputLabels);
            } else {
                // empty labels are non-exclusive, so allow this one.
                return true;
            }
        },
        registerOutputLabel: function( label ) {
            if( label ) {
                this.workflowOutputLabels[label] = true;
            }
        },
        unregisterOutputLabel: function( label ) {
            if( label ) {
                delete this.workflowOutputLabels[label];
            }
        },
        updateOutputLabel: function( fromLabel, toLabel ) {
            if( fromLabel ) {
                this.unregisterOutputLabel( fromLabel );
            }
            if( ! this.canLabelOutputWith( toLabel ) ) {
                Toastr.warning("Workflow contains duplicate workflow output labels " + toLabel + ". This must be fixed before it can be saved.");
            }
            if( toLabel ) {
                this.registerOutputLabel( toLabel );
            }
        },
        attemptUpdateOutputLabel: function( node, outputName, label ) {
            if( this.canLabelOutputWith( label ) ) {
                node.labelWorkflowOutput( outputName, label );
                node.nodeView.redrawWorkflowOutputs();
                return true;
            } else {
                return false;
            }
        },
        create_node: function ( type, title_text, content_id ) {
            var node = this.app.prebuildNode( type, title_text, content_id );
            this.add_node( node );
            this.fit_canvas_to_nodes();
            this.app.canvas_manager.draw_overview();
            this.activate_node( node );
            return node;
        },
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
            delete this.nodes[ node.id ];
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
                var self = this;
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
                                var create_pja = !node.isWorkflowOutput(ot.name);
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
                        if (self.active_node == node && node_changed === true) {
                            self.reload_active_node();
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
                        if ( c.handle1 ) {
                            var con_dict = { id: c.handle1.node.id, output_name: c.handle1.name };
                            var input_subworkflow_step_id = t.attributes.input.input_subworkflow_step_id;
                            if( input_subworkflow_step_id !== undefined ) {
                                con_dict["input_subworkflow_step_id"] = input_subworkflow_step_id;
                            }
                            cons[i] = con_dict;
                            input_connections[ t.name ] = cons;
                        }
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
                    content_id : node.content_id,
                    tool_state : node.tool_state,
                    errors : node.errors,
                    input_connections : input_connections,
                    position : $(node.element).position(),
                    annotation: node.annotation,
                    post_job_actions: node.post_job_actions,
                    uuid: node.uuid,
                    label: node.label,
                    workflow_outputs: node.workflow_outputs
                };
                nodes[ node.id ] = node_data;
            });
            return { steps: nodes };
        },
        from_simple : function ( data, initialImport_ ) {
            var initialImport = (initialImport_ === undefined) ? true : initialImport_;
            wf = this;
            var offset = 0;
            if( initialImport ) {
                wf.name = data.name;
            } else {
                offset = Object.keys(wf.nodes).length;
            }
            var max_id = offset;
            // First pass, nodes
            var using_workflow_outputs = false;
            $.each( data.steps, function( id, step ) {
                var node = wf.app.prebuildNode( step.type, step.name, step.content_id );
                // If workflow being copied into another, wipe UUID and let
                // Galaxy assign new ones.
                if( ! initialImport ) {
                    step.uuid = null;
                    $.each(step.workflow_outputs, function( name, workflow_output ) {
                        workflow_output.uuid = null;
                    });
                }
                node.init_field_data( step );
                if ( step.position ) {
                    node.element.css( { top: step.position.top, left: step.position.left } );
                }
                node.id = parseInt(step.id) + offset;
                wf.nodes[ node.id ] = node;
                max_id = Math.max( max_id, parseInt( id ) + offset );
                // For older workflows, it's possible to have HideDataset PJAs, but not WorkflowOutputs.
                // Check for either, and then add outputs in the next pass.
                if (!using_workflow_outputs){
                    if (node.workflow_outputs.length > 0){
                        using_workflow_outputs = true;
                    }
                    else{
                        $.each(node.post_job_actions || [], function(pja_id, pja){
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
                var node = wf.nodes[parseInt(id) + offset];
                $.each( step.input_connections, function( k, v ) {
                    if ( v ) {
                        if ( ! $.isArray( v ) ) {
                            v = [ v ];
                        }
                        $.each( v, function( l, x ) {
                            var other_node = wf.nodes[ parseInt(x.id) + offset ];
                            var c = new Connector();
                            c.connect( other_node.output_terminals[ x.output_name ],
                                       node.input_terminals[ k ] );
                            c.redraw();
                        });
                    }
                });
                if(using_workflow_outputs){
                    // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                    $.each(node.output_terminals, function(ot_id, ot){
                        if(node.post_job_actions['HideDatasetAction'+ot.name] === undefined){
                            node.addWorkflowOutput(ot.name);
                            callout = $(node.element).find('.callout.'+ot.name);
                            callout.find('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small.png');
                            wf.has_changes = true;
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
            this.app.showAttributes();
        },
        activate_node : function( node ) {
            if ( this.active_node != node ) {
                this.check_changes_in_active_form();
                this.clear_active_node();
                this.app.showForm( node.config_form, node );
                node.make_active();
                this.active_node = node;
            }
        },
        node_changed : function ( node, force ) {
            this.has_changes = true;
            if ( this.active_node == node && force ) {
                // Force changes to be saved even on new connection (previously dumped)
                this.check_changes_in_active_form();
                this.app.showForm( node.config_form, node );
            }
            this.app.showWorkflowParameters();
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
            // Math utils
            function round_up( x, n ) {
                return Math.ceil( x / n ) * n;
            }
            function fix_delta( x, n ) {
                if ( x < n|| x > 3*n ) {
                    new_pos = ( Math.ceil( ( ( x % n ) ) / n ) + 1 ) * n;
                    return ( - ( x - new_pos ) );
                }
                return 0;
            }
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
    return Workflow;
});
