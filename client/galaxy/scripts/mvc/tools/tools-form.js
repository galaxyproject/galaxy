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
            
            // link this
            var self = this;
            
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
        
        // reciept shows the final message usually upon successful job submission
        reciept: function($el) {
            $(this.container).empty();
            $(this.container).append($el);
        },
        
        // reset form
        reset: function() {
            for (var i in this.element_list) {
                this.element_list[i].reset();
            }
        },
        
        // rebuild underlying data structure representation for the tool form
        // this happens i.e. when repeat blocks are added or removed and on initialization
        rebuild: function() {
            this.tree.refresh();
            console.debug('tools-form::rebuild() - Rebuilding data structures.');
        },
        
        // refreshes input states i.e. for dynamic parameters
        refresh: function() {
            // only refresh the state if the form contains dynamic parameters
            // by using/reseting the deferred ajax queue the number of redundant calls is reduced
            if (this.is_dynamic) {
                var self = this;
                this.deferred.reset();
                this.deferred.execute(function(){self._updateModel()});
            };
        },
        
        // build tool model through api call
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
                        message     : 'Now you are using using \'' + self.options.name + '\' version ' + self.options.version + '.',
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
        
        // request a new model and update the form inputs
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
                success : function(response) {
                    // rebuild form
                    self._updateForm(response);
            
                    // unset wait mode
                    wait(false);
            
                    // process completed
                    self.deferred.done(process_id);
            
                    // log success
                    console.debug('tools-form::_refreshForm() - States refreshed.');
                    console.debug(response);
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
        
        // update form inputs
        _updateForm: function(new_model) {
            var self = this;
            this.tree.matchModel(new_model, function(input_id, node) {
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
        },
        
        // builds the tool form
        _buildForm: function() {
            // link this
            var self = this;
            
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
            
            // create message view
            this.message = new Ui.Message();
            
            // construct tool requirements message content
            var requirements_message = 'This tool requires ';
            for (var i in options.requirements) {
                var req = options.requirements[i];
                requirements_message += req.name;
                if (req.version) {
                    requirements_message += ' (Version ' + req.version + ')';
                }
                if (i < options.requirements.length - 2) {
                    requirements_message += ', ';
                }
                if (i == options.requirements.length - 2) {
                    requirements_message += ' and ';
                }
            }
            requirements_message += '.';
            
            // button for version selection
            var requirements_button = new Ui.ButtonIcon({
                icon    : 'fa-info-circle',
                tooltip : 'Click to show/hide the tool requirements.',
                onclick : function() {
                    if (!this.visible) {
                        this.visible = true;
                        self.message.update({
                            persistent  : true,
                            message     : requirements_message,
                            status      : 'warning'
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
                tooltip : 'Click to view available versions.'
            });
            if (options.versions && options.versions.length > 1) {
                for (var i in options.versions) {
                    versions_button.addMenu({
                        title   : options.versions[i],
                        icon    : 'fa-cube',
                        onclick : function() {
                            // here we update the tool version (some tools encode the version also in the id)
                            options.id = options.id.replace(options.version, this.title);
                            options.version = this.title;
                            
                            // rebuild the model and form
                            self.deferred.reset();
                            self.deferred.execute(function(){self._buildModel()});
                        }
                    });
                }
            } else {
                versions_button.$el.hide();
            }
            
            // button menu
            var menu_button = new Ui.ButtonMenu({
                icon    : 'fa-gear',
                tooltip : 'Click to view a list of options.'
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
                title   : '<b>' + options.name + '</b> ' + options.description + ' (Version ' + options.version + ')',
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
            
            // append message
            this.portlet.append(this.message.$el, true);
            
            // append tool section
            this.portlet.append(this.section.$el);
            
            // rebuild the underlying data structure
            this.rebuild();
            
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
