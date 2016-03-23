/**
    This is the workflow tool form.
*/
define(['utils/utils', 'mvc/tool/tool-form-base'],
    function(Utils, ToolFormBase) {

    // create form view
    var View = ToolFormBase.extend({
        initialize: function(options) {
            var self = this;
            this.workflow = options.workflow;

            // link with node representation in workflow module
            this.node = options.node;
            if (!this.node) {
                Galaxy.emit.debug('tool-form-workflow::initialize()', 'Node not found in workflow.');
                return;
            }

            // link actions
            this.post_job_actions = this.node.post_job_actions || {};

            // initialize parameters
            options = Utils.merge(options, {
                // set labels
                text_enable     : 'Set in Advance',
                text_disable    : 'Set at Runtime',

                // configure workflow style
                narrow          : true,
                initial_errors  : true,
                sustain_version : true,
                cls             : 'ui-portlet-narrow',

                // configure model update
                update_url      : Galaxy.root + 'api/workflows/build_module',
                update          : function(data) {
                    // This hasn't modified the workflow, just returned
                    // module information for the tool to update the workflow
                    // state stored on the client with. User needs to save
                    // for this to take effect.
                    self.node.update_field_data(data);
                    self.errors(data && data.tool_model)
                }
            });

            // mark values which can be determined at runtime
            Utils.deepeach (options.inputs, function( input ) {
                if ( input.type ) {
                    if ( [ 'data', 'data_collection' ].indexOf( input.type ) != -1 ) {
                        input.type = 'hidden';
                        input.info = 'Data input \'' + input.name + '\' (' + Utils.textify( input.extensions && input.extensions.toString() ) + ')';
                        input.value = { '__class__': 'RuntimeValue' };
                    } else {
                        input.collapsible_value = { '__class__': 'RuntimeValue' };
                        input.is_workflow = ( input.options && input.options.length == 0 ) ||
                                            ( [ 'integer', 'float' ].indexOf( input.type ) != -1 );
                    }
                }
            });

            // declare conditional and data input fields as not collapsible
            Utils.deepeach(options.inputs, function(item) {
                item.type == 'conditional' && ( item.test_param.collapsible_value = undefined );
            });

            // configure custom sections
            this._makeSections(options);

            // create final tool form
            ToolFormBase.prototype.initialize.call(this, options);
        },

        /** Builds all sub sections
        */
        _makeSections: function(options){
            // initialize local variables
            var inputs = options.inputs;
            var datatypes = options.datatypes;

            // for annotation
            inputs[Utils.uid()] = {
                label   : 'Annotation / Notes',
                name    : 'annotation',
                type    : 'text',
                area    : true,
                help    : 'Add an annotation or note for this step. It will be shown with the workflow.',
                value   : this.node.annotation
            }

            // get first output id
            var output_id = this.node.output_terminals && Object.keys(this.node.output_terminals)[0];
            if (output_id) {
                // send email on job completion
                inputs[Utils.uid()] = {
                    name        : 'pja__' + output_id + '__EmailAction',
                    label       : 'Email notification',
                    type        : 'boolean',
                    value       : String(Boolean(this.post_job_actions['EmailAction' + output_id])),
                    ignore      : 'false',
                    help        : 'An email notification will be sent when the job has completed.',
                    payload     : {
                        'host'  : window.location.host
                    }
                };

                // delete non-output files
                inputs[Utils.uid()] = {
                    name        : 'pja__' + output_id + '__DeleteIntermediatesAction',
                    label       : 'Output cleanup',
                    type        : 'boolean',
                    value       : String(Boolean(this.post_job_actions['DeleteIntermediatesAction' + output_id])),
                    ignore      : 'false',
                    help        : 'Delete intermediate outputs if they are not used as input for another job.'
                };

                // add output specific actions
                for (var i in this.node.output_terminals) {
                    inputs[Utils.uid()] = this._makeSection(i, datatypes);
                }
            }
        },

        /** Builds sub section with step actions/annotation
        */
        _makeSection: function(output_id, datatypes){
            // format datatypes
            var self = this;
            var extensions = [];
            var input_terminal_names = [];

            for (key in datatypes) {
                extensions.push({
                    0 : datatypes[key],
                    1 : datatypes[key]
                });
            }

            for (key in this.node.input_terminals){
                input_terminal_names.push(this.node.input_terminals[key].name);
            }

            // sort extensions
            extensions.sort(function(a, b) {
                return a.label > b.label ? 1 : a.label < b.label ? -1 : 0;
            });

            // add additional options
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

            // create custom sub section
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
            function visit (head, head_list) {
                head_list = head_list || [];
                head_list.push(head);
                for (var i in head.inputs) {
                    var input = head.inputs[i];
                    var action = input.action;
                    if (action) {
                        // construct identifier as expected by backend
                        input.name = 'pja__' + output_id + '__' + input.action;
                        if (input.pja_arg) {
                            input.name += '__' + input.pja_arg;
                        }

                        // modify names of payload arguments
                        if (input.payload) {
                            for (var p_id in input.payload) {
                                var p = input.payload[p_id];
                                input.payload[input.name + '__' + p_id] = p;
                                delete p;
                            }
                        }

                        // access/verify existence of value
                        var d = self.post_job_actions[input.action + output_id];
                        if (d) {
                            // mark as expanded
                            for (var j in head_list) {
                                head_list[j].expanded = true;
                            }

                            // update input field value
                            if (input.pja_arg) {
                                input.value = d.action_arguments && d.action_arguments[input.pja_arg] || input.value;
                            } else {
                                input.value = 'true';
                            }
                        }
                    }
                    // continue with sub section
                    if (input.inputs) {
                        visit(input, head_list.slice(0));
                    }
                }
            }
            visit(input_config);

            // return final configuration
            return input_config;
        }
    });

    return {
        View: View
    };
});
