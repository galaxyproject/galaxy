define(['mvc/workflow/workflow-view-node'], function( NodeView ) {
    var Node = Backbone.Model.extend({
        initialize: function( app, attr ) {
            this.app = app;
            this.element = attr.element;
            this.input_terminals = {};
            this.output_terminals = {};
            this.errors = {};
            this.workflow_outputs = [];
        },
        getWorkflowOutput: function(outputName) {
            return _.findWhere(this.workflow_outputs, {"output_name": outputName});
        },
        isWorkflowOutput: function(outputName) {
            return this.getWorkflowOutput(outputName) != undefined;
        },
        removeWorkflowOutput: function(outputName) {
            while(this.isWorkflowOutput(outputName)) {
                this.workflow_outputs.splice(this.getWorkflowOutput(outputName), 1);
            }
        },
        addWorkflowOutput: function(outputName, label) {
            if(!this.isWorkflowOutput(outputName)){
                var output = {"output_name": outputName};
                if( label ) {
                    output["label"] = label;
                }
                this.workflow_outputs.push(output);
                return true
            }
            return false;
        },
        labelWorkflowOutput: function(outputName, label) {
            var changed = false;
            var oldLabel = null;
            if( this.isWorkflowOutput(outputName) ) {
                var workflowOutput = this.getWorkflowOutput(outputName);
                oldLabel = workflowOutput["label"];
                workflowOutput["label"] = label;
                changed = oldLabel != label;
            } else {
                changed = this.addWorkflowOutput(outputName, label);
            }
            if( changed ) {
                this.app.workflow.updateOutputLabel(oldLabel, label);
                this.markChanged();
                this.nodeView.redrawWorkflowOutputs();
            }
            return changed;
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
            this.app.workflow.remove_node( this );
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
            this.config_form = data.config_form;
            this.tool_state = data.tool_state;
            this.errors = data.errors;
            this.tooltip = data.tooltip ? data.tooltip : "";
            this.annotation = data.annotation;
            this.post_job_actions = data.post_job_actions ? data.post_job_actions : {};
            this.label = data.label;
            this.uuid = data.uuid;
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
            this.app.workflow.node_changed( this, true);
        },
        update_field_data : function( data ) {
            var node = this;
            var nodeView = node.nodeView;
            this.tool_state = data.tool_state;
            this.config_form = data.config_form;
            this.errors = data.errors;
            this.annotation = data['annotation'];
            this.label = data.label;
            if( "post_job_actions" in data ) {
                // Won't be present in response for data inputs
                var pja_in = data.post_job_actions;
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
            node.nodeView.render();
            // In general workflow editor assumes tool outputs don't change in # or
            // type (not really valid right?) but adding special logic here for
            // data collection input parameters that can have their collection
            // change.
            if( data.data_outputs.length == 1 && "collection_type" in data.data_outputs[ 0 ] ) {
                nodeView.updateDataOutput( data.data_outputs[ 0 ] );
            }
            old_body.replaceWith( new_body );
            if( "workflow_outputs" in data ) {
                // Won't be present in response for data inputs
                this.workflow_outputs = workflow_outputs ? workflow_outputs : [];
            }
            // If active, reactivate with new config_form
            this.markChanged();
            this.redraw();
        },
        error : function ( text ) {
            var b = $(this.element).find( ".toolFormBody" );
            b.find( "div" ).remove();
            var tmp = "<div style='color: red; text-style: italic;'>" + text + "</div>";
            this.config_form = tmp;
            b.html( tmp );
            this.app.workflow.node_changed( this );
        },
        markChanged: function() {
            this.app.workflow.node_changed( this );
        }
    });
    return Node;
});