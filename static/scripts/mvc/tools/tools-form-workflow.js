/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'mvc/tools/tools-form-base'],
    function(Utils, ToolFormBase) {

    // create form view
    var View = ToolFormBase.extend({
        initialize: function(options) {
            // link with node representation in workflow module
            this.node = workflow.active_node;
            if (!this.node) {
                console.debug('FAILED - tools-form-workflow:initialize() - Node not found in workflow.');
                return;
            }

            // link actions
            this.post_job_actions = this.node.post_job_actions || {};

            // initialize parameters
            this.options = options;

            // set labels
            this.options.text_enable    = 'Set in Advance';
            this.options.text_disable   = 'Set at Runtime';

            // configure workflow style
            this.options.is_dynamic     = false;
            this.options.narrow         = true;
            this.options.initial_errors = true;
            this.options.cls_portlet    = 'ui-portlet-narrow';

            // declare fields as optional
            Utils.deepeach(options.inputs, function(item) {
                if (item.type) {
                    item.optional = (['data', 'data_hidden', 'hidden', 'repeat', 'conditional']).indexOf(item.type) == -1;
                }
            });

            // declare conditional fields as not optional
            Utils.deepeach(options.inputs, function(item) {
                if (item.type) {
                    if (item.type == 'conditional') {
                        item.test_param.optional = false;
                    }
                }
            });

            // load extension
            var self = this;
            Utils.get({
                url     : galaxy_config.root + 'api/datatypes',
                cache   : true,
                success : function(datatypes) {
                    self.datatypes = datatypes;
                    self._makeSections(options.inputs);
                    ToolFormBase.prototype.initialize.call(self, options);
                }
            });
        },

        /** Builds all sub sections
        */
        _makeSections: function(inputs){
            // for annotation
            inputs[Utils.uuid()] = {
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
                inputs[Utils.uuid()] = {
                    name        : 'pja__' + output_id + '__EmailAction',
                    label       : 'Email notification',
                    type        : 'boolean',
                    value       : String(Boolean(this.post_job_actions['EmailAction' + output_id])),
                    ignore      : 'false',
                    help        : 'An email notification will be send when the job has completed.',
                    payload     : {
                        'host'  : window.location.host
                    }
                };

                // delete non-output files
                inputs[Utils.uuid()] = {
                    name        : 'pja__' + output_id + '__DeleteIntermediatesAction',
                    label       : 'Output cleanup',
                    type        : 'boolean',
                    value       : String(Boolean(this.post_job_actions['DeleteIntermediatesAction' + output_id])),
                    ignore      : 'false',
                    help        : 'Delete intermediate outputs if they are not used as input for another job.'
                };

                // add output specific actions
                for (var i in this.node.output_terminals) {
                    inputs[Utils.uuid()] = this._makeSection(i);
                }
            }
        },

        /** Builds sub section with step actions/annotation
        */
        _makeSection: function(output_id){
            // format datatypes
            var extensions = [];
            for (key in this.datatypes) {
                extensions.push({
                    0 : this.datatypes[key],
                    1 : this.datatypes[key]
                });
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
                1 : ''
            });

            // create custom sub section
            var input_config = {
                label   : 'Add Actions: \'' + output_id + '\'',
                type    : 'section',
                inputs  : [{
                    action      : 'RenameDatasetAction',
                    argument    : 'newname',
                    label       : 'Rename dataset',
                    type        : 'text',
                    value       : '',
                    ignore      : '',
                    help        : 'This action will rename the result dataset. Click <a href="https://wiki.galaxyproject.org/Learn/AdvancedWorkflow/Variables">here</a> for more information.'
                },{
                    action      : 'ChangeDatatypeAction',
                    argument    : 'newtype',
                    label       : 'Change datatype',
                    type        : 'select',
                    ignore      : '',
                    options     : extensions,
                    help        : 'This action will change the datatype of the output to the indicated value.'
                },{
                    action      : 'TagDatasetAction',
                    argument    : 'tags',
                    label       : 'Tags',
                    type        : 'text',
                    value       : '',
                    ignore      : '',
                    help        : 'This action will set tags for the dataset.'
                },{
                    label   : 'Assign columns',
                    type    : 'section',
                    inputs  : [{
                        action      : 'ColumnSetAction',
                        argument    : 'chromCol',
                        label       : 'Chrom column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        argument    : 'startCol',
                        label       : 'Start column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        argument    : 'endCol',
                        label       : 'End column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        argument    : 'strandCol',
                        label       : 'Strand column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    },{
                        action      : 'ColumnSetAction',
                        argument    : 'nameCol',
                        label       : 'Name column',
                        type        : 'integer',
                        value       : '',
                        ignore      : ''
                    }],
                    help    : 'This action will set column assignments in the output dataset. Blank fields are ignored.'
                }]
            };

            // visit input nodes and enrich by name/value pairs from server data
            var self = this;
            function visit (head, head_list) {
                head_list = head_list || [];
                head_list.push(head);
                for (var i in head.inputs) {
                    var input = head.inputs[i];
                    if (input.action) {
                        // construct identifier as expected by backend
                        input.name = 'pja__' + output_id + '__' + input.action;
                        if (input.argument) {
                            input.name += '__' + input.argument;
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
                                head_list[j].expand = true;
                            }

                            // update input field value
                            if (input.argument) {
                                input.value = d.action_arguments && d.action_arguments[input.argument] || input.value;
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
        },

        /** Builds a new model through api call and recreates the entire form
        */
        _buildModel: function() {
            Galaxy.modal.show({
                title   : 'Coming soon...',
                body    : 'This feature has not been implemented yet.',
                buttons : {
                    'Close' : function() {
                        Galaxy.modal.hide();
                    }
                }
            });
        },

        /** Request a new model for an already created tool form and updates the form inputs
        */
        _updateModel: function(current_state) {
            // link self
            var self = this;
            
            // create the request dictionary
            current_state = {
                tool_id         : this.options.id,
                tool_version    : this.options.version,
                inputs          : current_state
            }
        
            // log tool state
            console.debug('tools-form-workflow::_refreshForm() - Refreshing states.');
            console.debug(current_state);

            // register process
            var process_id = this.deferred.register();

            // build model url for request
            var model_url = galaxy_config.root + 'api/workflows/build_module';

            // post job
            Utils.request({
                type    : 'POST',
                url     : model_url,
                data    : current_state,
                success : function(data) {
                    // update node in workflow module
                    self.node.update_field_data(data);

                    // highlight errors
                    self._errors(data && data.tool_model);

                    // process completed
                    self.deferred.done(process_id);
            
                    // log success
                    console.debug('tools-form::_refreshForm() - States refreshed.');
                    console.debug(data);
                },
                error   : function(response) {
                    // process completed
                    self.deferred.done(process_id);
                    
                    // log error
                    console.debug('tools-form::_refreshForm() - Refresh request failed.');
                    console.debug(response);
                }
            });
        }
    });

    return {
        View: View
    };
});
