/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'utils/deferred', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'mvc/citation/citation-model', 'mvc/citation/citation-view',
        'mvc/tools', 'mvc/tools/tools-template', 'mvc/tools/tools-content', 'mvc/tools/tools-section', 'mvc/tools/tools-tree', 'mvc/tools/tools-jobs'],
    function(Utils, Deferred, Portlet, Ui, CitationModel, CitationView,
             Tools, ToolTemplate, ToolContent, ToolSection, ToolTree, ToolJobs) {

    // create form view
    var View = Backbone.View.extend({
        // base element
        container: 'body',
        
        // initialize
        initialize: function(options) {
            // log options
            console.debug(options);
            
            // link galaxy modal or create one
            var galaxy = parent.Galaxy;
            if (galaxy && galaxy.modal) {
                this.modal = galaxy.modal;
            } else {
                this.modal = new Ui.Modal.View();
            }
    
            // check if the user is an admin
            if (galaxy && galaxy.currUser) {
                this.is_admin = galaxy.currUser.get('is_admin')
            } else {
                this.is_admin = false;
            }
            
            // link options
            this.options = options;
            
            // create deferred processing queue handler
            // this handler reduces the number of requests to the api by filtering redundant requests
            this.deferred = new Deferred();
            
            // set element
            this.setElement('<div/>');
            
            // add to main element
            $(this.container).append(this.$el);
            
            // build this form
            this._buildForm();
        },
        
        /** Shows the final message (usually upon successful job submission)
        */
        reciept: function($el) {
            $(this.container).empty();
            $(this.container).append($el);
        },
                
        /** Highlight and scroll to input element (currently only used for error notifications)
        */
        highlight: function (input_id, message, silent) {
            // get input field
            var input_element = this.element_list[input_id];
            
            // check input element
            if (input_element) {
                // mark error
                input_element.error(message || 'Please verify this parameter.');
            
                // scroll to first input element
                if (!silent) {
                    $(this.container).animate({
                        scrollTop: input_element.$el.offset().top - 20
                    }, 500);
                }
            }
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
        },
        
        /** Main tool form build function. This function is called once a new model is available.
        */
        _buildForm: function() {
            // link this
            var self = this;
            
            // reset events
            this.off('refresh');
            this.off('reset');
            
            // reset field list, which contains the input field elements
            this.field_list = {};
            
            // reset sequential input definition list, which contains the input definitions as provided from the api
            this.input_list = {};
            
            // reset input element list, which contains the dom elements of each input element (includes also the input field)
            this.element_list = {};
            
            // creates a tree/json data structure from the input form
            this.tree = new ToolTree(this);
            
            // creates the job handler
            this.job_handler = new ToolJobs(this);

            // request history content and build form
            this.content = new ToolContent(this);
            
            // link model options
            var options = this.options;
            
            // create ui elements
            this._renderForm(options);
            
            // rebuild the underlying data structure
            this.tree.finalize();
            
            // show errors
            if (options.errors) {
                var error_messages = this.tree.matchResponse(options.errors);
                for (var input_id in error_messages) {
                    this.highlight(input_id, error_messages[input_id], true);
                }
            }
            
            // add refresh listener
            this.on('refresh', function() {
                // by using/reseting the deferred ajax queue the number of redundant calls is reduced
                self.deferred.reset();
                self.deferred.execute(function(){self._updateModel()});
            });
            
            // add reset listener
            this.on('reset', function() {
                for (var i in this.element_list) {
                    this.element_list[i].reset();
                }
            });
        },

        /** Renders the UI elements required for the form
        */
        _renderForm: function(options) {
            // link this
            var self = this;
            
            // create message view
            this.message = new Ui.Message();
            
            // button for version selection
            var requirements_button = new Ui.ButtonIcon({
                icon    : 'fa-info-circle',
                title   : 'Requirements',
                tooltip : 'Display tool requirements',
                onclick : function() {
                    if (!this.visible) {
                        this.visible = true;
                        self.message.update({
                            persistent  : true,
                            message     : ToolTemplate.requirements(options),
                            status      : 'info'
                        });
                    } else {
                        this.visible = false;
                        self.message.update({
                            message     : ''
                        });
                    }
                }
            });
            if (!options.requirements || options.requirements.length == 0) {
                requirements_button.$el.hide();
            }
            
            // button for version selection
            var versions_button = new Ui.ButtonMenu({
                icon    : 'fa-cubes',
                title   : 'Versions',
                tooltip : 'Select another tool version'
            });
            if (options.versions && options.versions.length > 1) {
                for (var i in options.versions) {
                    var version = options.versions[i];
                    if (version != options.version) {
                        versions_button.addMenu({
                            title   : 'Switch to ' + version,
                            version : version,
                            icon    : 'fa-cube',
                            onclick : function() {
                                // here we update the tool version (some tools encode the version also in the id)
                                options.id = options.id.replace(options.version, this.version);
                                options.version = this.version;
                                
                                // rebuild the model and form
                                self.deferred.reset();
                                self.deferred.execute(function(){self._buildModel()});
                            }
                        });
                    }
                }
            } else {
                versions_button.$el.hide();
            }
            
            // button menu
            var menu_button = new Ui.ButtonMenu({
                icon    : 'fa-caret-down',
                title   : 'Options',
                tooltip : 'View available options'
            });
            
            // configure button selection
            if(options.biostar_url) {
                // add question option
                menu_button.addMenu({
                    icon    : 'fa-question-circle',
                    title   : 'Question?',
                    tooltip : 'Ask a question about this tool (Biostar)',
                    onclick : function() {
                        window.open(options.biostar_url + '/p/new/post/');
                    }
                });
                
                // create search button
                menu_button.addMenu({
                    icon    : 'fa-search',
                    title   : 'Search',
                    tooltip : 'Search help for this tool (Biostar)',
                    onclick : function() {
                        window.open(options.biostar_url + '/t/' + options.id + '/');
                    }
                });
            };
            
            // create share button
            menu_button.addMenu({
                icon    : 'fa-share',
                title   : 'Share',
                tooltip : 'Share this tool',
                onclick : function() {
                    prompt('Copy to clipboard: Ctrl+C, Enter', window.location.origin + galaxy_config.root + 'root?tool_id=' + options.id);
                }
            });
            
            // add admin operations
            if (this.is_admin) {
                // create download button
                menu_button.addMenu({
                    icon    : 'fa-download',
                    title   : 'Download',
                    tooltip : 'Download this tool',
                    onclick : function() {
                        window.location.href = galaxy_config.root + 'api/tools/' + options.id + '/download';
                    }
                });
            }
            
            // create tool form section
            this.section = new ToolSection.View(self, {
                inputs : options.inputs,
                cls    : 'ui-table-plain'
            });
            
            // switch to classic tool form mako if the form definition is incompatible
            if (this.incompatible) {
                this.$el.hide();
                $('#tool-form-classic').show();
                return;
            }
            
            // create portlet
            this.portlet = new Portlet.View({
                icon    : 'fa-wrench',
                title   : '<b>' + options.name + '</b> ' + options.description + ' (Galaxy Tool Version ' + options.version + ')',
                cls     : 'ui-portlet-slim',
                operations: {
                    requirements    : requirements_button,
                    menu            : menu_button,
                    versions        : versions_button
                },
                buttons: {
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
            });
            
            // append message
            this.portlet.append(this.message.$el, true);
            
            // append tool section
            this.portlet.append(this.section.$el);
            
            // start form
            this.$el.empty();
            this.$el.append(this.portlet.$el);
            
            // append help
            if (options.help != '') {
                this.$el.append(ToolTemplate.help(options.help));
            }
            
            // append citations
            if (options.citations) {
                var $citations = $('<div/>');
                var citations = new CitationModel.ToolCitationCollection();
                citations.tool_id = options.id;
                var citation_list_view = new CitationView.CitationListView({ el: $citations, collection: citations } );
                citation_list_view.render();
                citations.fetch();
                this.$el.append($citations);
            }
            
            // show message if available in model
            if (options.message) {
                this.message.update({
                    persistent  : true,
                    status      : 'warning',
                    message     : options.message
                });
            }
        }
    });

    return {
        View: View
    };
});
