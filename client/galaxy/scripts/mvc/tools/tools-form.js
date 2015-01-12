/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tools/tools-form-base', 'mvc/tools/tools-jobs'],
    function(Utils, Ui, ToolFormBase, ToolJobs) {

    // create form view
    var View = ToolFormBase.extend({
        // initialize
        initialize: function(options) {
            var self = this;
            this.job_handler = new ToolJobs(this);
            this.buttons = {
                execute : new Ui.Button({
                    icon     : 'fa-check',
                    tooltip  : 'Execute: ' + options.name,
                    title    : 'Execute',
                    cls      : 'btn btn-primary',
                    floating : 'clear',
                    onclick  : function() {
                        self.job_handler.submit();
                    }
                })
            }
            ToolFormBase.prototype.initialize.call(this, options);
        },
        
        /** Builds a new model through api call and recreates the entire form
        */
        _buildModel: function() {
            // link this
            var self = this;
            
            // construct url
            var model_url = galaxy_config.root + 'api/tools/' + this.options.id + '/build?';
            if (this.options.job_id) {
                model_url += 'job_id=' + this.options.job_id;
            } else {
                if (this.options.dataset_id) {
                    model_url += 'dataset_id=' + this.options.dataset_id;
                } else {
                    model_url += 'tool_version=' + this.options.version + '&';
                    var loc = top.location.href;
                    var pos = loc.indexOf('?');
                    if (loc.indexOf('tool_id=') != -1 && pos !== -1) {
                        model_url += loc.slice(pos + 1);
                    }
                }
            }
            
            // register process
            var process_id = this.deferred.register();
            
            // get initial model
            Utils.request({
                type    : 'GET',
                url     : model_url,
                success : function(response) {
                    // link model data update options
                    self.options = response;
                    
                    // build form
                    self._buildForm();
                    
                    // notification
                    self.message.update({
                        status      : 'success',
                        message     : 'Now you are using \'' + self.options.name + '\' version ' + self.options.version + '.',
                        persistent  : false
                    });
                    
                    // process completed
                    self.deferred.done(process_id);
                    
                    // log success
                    console.debug('tools-form::initialize() - Initial tool model ready.');
                    console.debug(response);
                },
                error   : function(response) {
                    // process completed
                    self.deferred.done(process_id);
                    
                    // log error
                    console.debug('tools-form::initialize() - Initial tool model request failed.');
                    console.debug(response);
                    
                    // show error
                    var error_message = response.error || 'Uncaught error.';
                    self.modal.show({
                        title   : 'Tool cannot be executed',
                        body    : error_message,
                        buttons : {
                            'Close' : function() {
                                self.modal.hide();
                            }
                        }
                    });
                }
            });
        },
        
        /** Request a new model for an already created tool form and updates the form inputs
        */
        _updateModel: function() {
            // create the request dictionary
            var self = this;
            var current_state = this.tree.finalize({
                data : function(dict) {
                    if (dict.values.length > 0 && dict.values[0] && dict.values[0].src === 'hda') {
                        return self.content.get({id: dict.values[0].id, src: 'hda'}).id_uncoded;
                    }
                    return null;
                }
            });
            
            // log tool state
            console.debug('tools-form::_refreshForm() - Refreshing states.');
            console.debug(current_state);
            
            // activates/disables spinner for dynamic fields to indicate that they are currently being updated
            function wait(active) {
                for (var i in self.input_list) {
                    var field = self.field_list[i];
                    var input = self.input_list[i];
                    if (input.is_dynamic && field.wait && field.unwait) {
                        if (active) {
                            field.wait();
                        } else {
                            field.unwait();
                        }
                    }
                }
            }
            
            // set wait mode
            wait(true);
            
            // register process
            var process_id = this.deferred.register();

            // build model url for request
            var model_url = galaxy_config.root + 'api/tools/' + this.options.id + '/build?tool_version=' + this.options.version;
            
            // post job
            Utils.request({
                type    : 'GET',
                url     : model_url,
                data    : current_state,
                success : function(new_model) {
                    // update form
                    self.tree.matchModel(new_model, function(input_id, node) {
                        var input = self.input_list[input_id];
                        if (input && input.options) {
                            if (!_.isEqual(input.options, node.options)) {
                                // backup new options
                                input.options = node.options;
                                
                                // get/update field
                                var field = self.field_list[input_id];
                                if (field.update) {
                                    var new_options = [];
                                    if ((['data', 'data_collection', 'drill_down']).indexOf(input.type) != -1) {
                                        new_options = input.options;
                                    } else {
                                        for (var i in node.options) {
                                            var opt = node.options[i];
                                            if (opt.length > 2) {
                                                new_options.push({
                                                    'label': opt[0],
                                                    'value': opt[1]
                                                });
                                            }
                                        }
                                    }
                                    field.update(new_options);
                                    field.trigger('change');
                                    console.debug('Updating options for ' + input_id);
                                }
                            }
                        }
                    });
            
                    // unset wait mode
                    wait(false);
            
                    // process completed
                    self.deferred.done(process_id);
            
                    // log success
                    console.debug('tools-form::_refreshForm() - States refreshed.');
                    console.debug(new_model);
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
