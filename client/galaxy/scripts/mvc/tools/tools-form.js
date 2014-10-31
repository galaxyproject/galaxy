/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'mvc/citation/citation-model', 'mvc/citation/citation-view',
        'mvc/tools', 'mvc/tools/tools-template', 'mvc/tools/tools-content', 'mvc/tools/tools-section', 'mvc/tools/tools-tree', 'mvc/tools/tools-jobs'],
    function(Utils, Portlet, Ui, CitationModel, CitationView,
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
            if (parent.Galaxy && parent.Galaxy.modal) {
                this.modal = parent.Galaxy.modal;
            } else {
                this.modal = new Ui.Modal.View();
            }
            
            // link options
            this.options = options;
            
            // set element
            this.setElement('<div/>');
            
            // add to main element
            $(this.container).append(this.$el);
            
            // creates a tree/json structure from the input form
            this.tree = new ToolTree(this);
            
            // creates the job handler
            this.job_handler = new ToolJobs(this);

            // request history content and build form
            this.content = new ToolContent({
                history_id  : self.options.history_id,
                success     : function() {
                    self._buildForm(self.options);
                }
            });
        },
        
        // message
        message: function($el) {
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
            console.debug('tools-form::refresh() - Refreshed form structure.');
        },
        
        // refreshes input states i.e. for dynamic parameters
        refresh: function() {
            // link this
            var self = this;
            
            // only refresh the state if the form contains dynamic parameters
            if (!this.is_dynamic) {
                return;
            }
            
            // finalize data
            var current_state = this.tree.finalize({
                data : function(dict) {
                    if (dict.values.length > 0 && dict.values[0] && dict.values[0].src === 'hda') {
                        return self.content.get({id: dict.values[0].id}).dataset_id;
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
            
            // post job
            Utils.request({
                type    : 'GET',
                url     : galaxy_config.root + 'api/tools/' + this.options.id + '/build',
                data    : current_state,
                success : function(response) {
                    // rebuild form
                    self._rebuildForm(response);
            
                    // unset wait mode
                    wait(false);
            
                    // log success
                    console.debug('tools-form::_refreshForm() - States refreshed.');
                    console.debug(response);
                },
                error   : function(response) {
                    console.debug('tools-form::_refreshForm() - Refresh request failed.');
                    console.debug(response);
                }
            });
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
                    var loc = top.location.href;
                    var pos = loc.indexOf('?');
                    if (loc.indexOf('tool_id=') != -1 && pos !== -1) {
                        model_url += loc.slice(pos + 1);
                    }
                }
            }
        
            // get initial model
            Utils.request({
                type    : 'GET',
                url     : model_url,
                success : function(response) {
                    // link model data update options
                    self.options    = $.extend(self.options, response);
                    self.model      = response;
                    self.inputs     = response.inputs;
                    
                    // log success
                    console.debug('tools-form::initialize() - Initial tool model ready.');
                    console.debug(response);

                    // build form
                    self._buildForm();
                },
                error   : function(response) {
                    console.debug('tools-form::initialize() - Initial tool model request failed.');
                    console.debug(response);
                }
            });
        },
        
        // rebuild the form elements
        _rebuildForm: function(new_model) {
            var self = this;
            this.tree.matchModel(new_model, function(input_id, node) {
                var input = self.input_list[input_id];
                if (input && input.options) {
                    if (JSON.stringify(input.options) != JSON.stringify(node.options)) {
                        // backup new options
                        input.options = node.options;
                        
                        // get/update field
                        var field = self.field_list[input_id];
                        if (field.update && input.type != 'data') {
                            var new_options = [];
                            for (var i in node.options) {
                                var opt = node.options[i];
                                if (opt.length > 2) {
                                    new_options.push({
                                        'label': opt[0],
                                        'value': opt[1]
                                    });
                                }
                            }
                            field.update(new_options);
                            console.debug('Updating options for ' + input_id);
                        }
                    }
                }
            });
        },
        
        // builds the tool form
        _buildForm: function(options) {
            // link this
            var self = this;
            
            // reset field list, which contains the input field elements
            this.field_list = {};
            
            // reset sequential input definition list, which contains the input definitions as provided from the api
            this.input_list = {};
            
            // reset input element list, which contains the dom elements of each input element (includes also the input field)
            this.element_list = {};
            
            // for now the initial tool model is parsed through the mako
            this.model  = options;
            this.inputs = options.inputs;
            
            // button menu
            var menu = new Ui.ButtonMenu({
                icon    : 'fa-gear',
                tooltip : 'Click to see a list of options.'
            });
            
            // configure button selection
            if(options.biostar_url) {
                // add question option
                menu.addMenu({
                    icon    : 'fa-question-circle',
                    title   : 'Question?',
                    tooltip : 'Ask a question about this tool (Biostar)',
                    onclick : function() {
                        window.open(self.options.biostar_url + '/p/new/post/');
                    }
                });
                
                // create search button
                menu.addMenu({
                    icon    : 'fa-search',
                    title   : 'Search',
                    tooltip : 'Search help for this tool (Biostar)',
                    onclick : function() {
                        window.open(self.options.biostar_url + '/t/' + self.options.id + '/');
                    }
                });
            };
            
            // create share button
            menu.addMenu({
                icon    : 'fa-share',
                title   : 'Share',
                tooltip : 'Share this tool',
                onclick : function() {
                    prompt('Copy to clipboard: Ctrl+C, Enter', window.location.origin + galaxy_config.root + 'root?tool_id=' + self.options.id);
                }
            });
            
            // add admin operations
            if (Galaxy.currUser.get('is_admin')) {
                // create download button
                menu.addMenu({
                    icon    : 'fa-download',
                    title   : 'Download',
                    tooltip : 'Download this tool',
                    onclick : function() {
                        window.location.href = galaxy_config.root + 'api/tools/' + self.options.id + '/download';
                    }
                });
            }
            
            // create tool form section
            this.section = new ToolSection.View(self, {
                inputs : this.inputs,
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
                icon : 'fa-wrench',
                title: '<b>' + this.model.name + '</b> ' + this.model.description,
                operations: {
                    menu    : menu
                },
                buttons: {
                    execute : new Ui.Button({
                        icon     : 'fa-check',
                        tooltip  : 'Execute the tool',
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
                // fetch citations
                var citations = new CitationModel.ToolCitationCollection();
                citations.tool_id = options.id;
                var citation_list_view = new CitationView.CitationListView({ collection: citations } );
                citation_list_view.render();
                citations.fetch();
                
                // append to element
                this.$el.append(citation_list_view.$el);
            }
            
            // append tool section
            this.portlet.append(this.section.$el);
            
            // rebuild the underlying data structure
            this.rebuild();
        }
    });

    return {
        View: View
    };
});
