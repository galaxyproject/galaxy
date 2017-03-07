define( [ 'utils/utils', 'mvc/form/form-view', 'mvc/tool/tool-form-base' ], function( Utils, Form, ToolFormBase ) {

    /** Default form wrapper for non-tool modules in the workflow editor. */
    var Default = Backbone.View.extend({
        initialize: function( options ) {
            this.form = new Form( options );
        }
    });

    /** Tool form wrapper for the workflow editor. */
    var Tool = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.workflow = options.workflow;
            this.node     = options.node;
            if ( this.node ) {
                this.post_job_actions = this.node.post_job_actions || {};
                Utils.deepeach( options.inputs, function( input ) {
                    if ( input.type ) {
                        if ( [ 'data', 'data_collection' ].indexOf( input.type ) != -1 ) {
                            input.type = 'hidden';
                            input.info = 'Data input \'' + input.name + '\' (' + Utils.textify( input.extensions ) + ')';
                            input.value = { '__class__': 'RuntimeValue' };
                        } else if ( !input.fixed ) {
                            input.collapsible_value = { '__class__': 'RuntimeValue' };
                            input.is_workflow = ( input.options && input.options.length == 0 ) ||
                                                ( [ 'integer', 'float' ].indexOf( input.type ) != -1 );
                        }
                    }
                });
                Utils.deepeach( options.inputs, function( input ) {
                    input.type == 'conditional' && ( input.test_param.collapsible_value = undefined );
                });
                this._makeSections( options );
                this.form = new ToolFormBase( Utils.merge( options, {
                    text_enable     : 'Set in Advance',
                    text_disable    : 'Set at Runtime',
                    narrow          : true,
                    initial_errors  : true,
                    sustain_version : true,
                    cls             : 'ui-portlet-narrow',
                    postchange      : function( process, form ) {
                        var options = form.model.attributes;
                        var current_state = {
                            tool_id         : options.id,
                            tool_version    : options.version,
                            type            : 'tool',
                            inputs          : $.extend( true, {}, form.data.create() )
                        }
                        Galaxy.emit.debug( 'tool-form-workflow::postchange()', 'Sending current state.', current_state );
                        Utils.request({
                            type    : 'POST',
                            url     : Galaxy.root + 'api/workflows/build_module',
                            data    : current_state,
                            success : function( data ) {
                                form.update( data.config_form );
                                form.errors( data.config_form );
                                // This hasn't modified the workflow, just returned
                                // module information for the tool to update the workflow
                                // state stored on the client with. User needs to save
                                // for this to take effect.
                                self.node.update_field_data( data );
                                Galaxy.emit.debug( 'tool-form-workflow::postchange()', 'Received new model.', data );
                                process.resolve();
                            },
                            error   : function( response ) {
                                Galaxy.emit.debug( 'tool-form-workflow::postchange()', 'Refresh request failed.', response );
                                process.reject();
                            }
                        });
                    },
                }));
            } else {
                Galaxy.emit.debug('tool-form-workflow::initialize()', 'Node not found in workflow.');
            }
        },

        /** Builds all sub sections */
        _makeSections: function( options ){
            var inputs = options.inputs;
            var datatypes = options.datatypes;
            var output_id = this.node.output_terminals && Object.keys( this.node.output_terminals )[ 0 ];
            if ( output_id ) {
                inputs.push({
                    name        : 'pja__' + output_id + '__EmailAction',
                    label       : 'Email notification',
                    type        : 'boolean',
                    value       : String( Boolean( this.post_job_actions[ 'EmailAction' + output_id ] ) ),
                    ignore      : 'false',
                    help        : 'An email notification will be sent when the job has completed.',
                    payload     : {
                        'host'  : window.location.host
                    }
                });
                inputs.push({
                    name        : 'pja__' + output_id + '__DeleteIntermediatesAction',
                    label       : 'Output cleanup',
                    type        : 'boolean',
                    value       : String( Boolean( this.post_job_actions[ 'DeleteIntermediatesAction' + output_id ] ) ),
                    ignore      : 'false',
                    help        : 'Upon completion of this step, delete non-starred outputs from completed workflow steps if they are no longer required as inputs.'
                });
                for ( var i in this.node.output_terminals ) {
                    inputs.push( this._makeSection( i, datatypes ) );
                }
            }
        },

        /** Builds sub section with step actions/annotation */
        _makeSection: function( output_id, datatypes ){
            var self = this;
            var extensions = [];
            var input_terminal_names = [];
            for ( key in datatypes  ) {
                extensions.push( { 0 : datatypes[ key ], 1 : datatypes[ key ] } );
            }
            for ( key in this.node.input_terminals ){
                input_terminal_names.push( this.node.input_terminals[ key ].name );
            }
            extensions.sort( function( a, b ) {
                return a.label > b.label ? 1 : a.label < b.label ? -1 : 0;
            });
            extensions.unshift({
                0 : 'Sequences',
                1 : 'Sequences'
            });
            extensions.unshift({
                0 : 'Roadmaps',
                1 : 'Roadmaps'
            });
            extensions.unshift({
                0 : 'Leave unchanged',
                1 : '__empty__'
            });
            var input_config = {
                title   : 'Configure Output: \'' + output_id + '\'',
                type    : 'section',
                flat    : true,
                inputs  : [{
                    label       : 'Label',
                    type        : 'text',
                    value       : ( output = this.node.getWorkflowOutput( output_id ) ) && output.label || '',
                    help        : 'This will provide a short name to describe the output - this must be unique across workflows.',
                    onchange    : function( new_value ) {
                        self.workflow.attemptUpdateOutputLabel( self.node, output_id, new_value );
                    }
                },{
                    action      : 'RenameDatasetAction',
                    pja_arg     : 'newname',
                    label       : 'Rename dataset',
                    type        : 'text',
                    value       : '',
                    ignore      : '',
                    help        : 'This action will rename the output dataset. Click <a href="https://wiki.galaxyproject.org/Learn/AdvancedWorkflow/Variables">here</a> for more information. Valid inputs are: <strong>' + input_terminal_names.join(', ') + '</strong>.'
                },{
                    action      : 'ChangeDatatypeAction',
                    pja_arg     : 'newtype',
                    label       : 'Change datatype',
                    type        : 'select',
                    ignore      : '__empty__',
                    value       : '__empty__',
                    options     : extensions,
                    help        : 'This action will change the datatype of the output to the indicated value.'
                },{
                    action      : 'TagDatasetAction',
                    pja_arg     : 'tags',
                    label       : 'Tags',
                    type        : 'text',
                    value       : '',
                    ignore      : '',
                    help        : 'This action will set tags for the dataset.'
                },{
                    title   : 'Assign columns',
                    type    : 'section',
                    flat    : true,
                    inputs  : [{
                        action      : 'ColumnSetAction',
                        pja_arg     : 'chromCol',
                        label       : 'Chrom column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        pja_arg     : 'startCol',
                        label       : 'Start column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        pja_arg     : 'endCol',
                        label       : 'End column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        pja_arg     : 'strandCol',
                        label       : 'Strand column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        pja_arg     : 'nameCol',
                        label       : 'Name column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    }],
                    help    : 'This action will set column assignments in the output dataset. Blank fields are ignored.'
                }]
            };

            // visit input nodes and enrich by name/value pairs from server data
            function visit ( head, head_list ) {
                head_list = head_list || [];
                head_list.push( head );
                for ( var i in head.inputs ) {
                    var input = head.inputs[ i ];
                    var action = input.action;
                    if ( action ) {
                        input.name = 'pja__' + output_id + '__' + input.action;
                        if ( input.pja_arg ) {
                            input.name += '__' + input.pja_arg;
                        }
                        if ( input.payload ) {
                            for ( var p_id in input.payload ) {
                                var p = input.payload[ p_id ];
                                input.payload[ input.name + '__' + p_id ] = p;
                                delete p;
                            }
                        }
                        var d = self.post_job_actions[ input.action + output_id ];
                        if ( d ) {
                            for ( var j in head_list ) {
                                head_list[ j ].expanded = true;
                            }
                            if ( input.pja_arg ) {
                                input.value = d.action_arguments && d.action_arguments[ input.pja_arg ] || input.value;
                            } else {
                                input.value = 'true';
                            }
                        }
                    }
                    input.inputs && visit( input, head_list.slice( 0 ) );
                }
            }
            visit( input_config );
            return input_config;
        }
    });

    return {
        Default: Default,
        Tool: Tool
    };
});
