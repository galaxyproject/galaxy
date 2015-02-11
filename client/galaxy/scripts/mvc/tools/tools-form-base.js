/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'utils/deferred', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'mvc/citation/citation-model', 'mvc/citation/citation-view',
        'mvc/tools', 'mvc/tools/tools-template', 'mvc/tools/tools-content', 'mvc/tools/tools-section', 'mvc/tools/tools-tree'],
    function(Utils, Deferred, Portlet, Ui, CitationModel, CitationView,
             Tools, ToolTemplate, ToolContent, ToolSection, ToolTree) {

    // create form view
    return Backbone.View.extend({
        // initialize
        initialize: function(options) {
            // options
            this.optionsDefault = {
                // uses dynamic fields instead of text fields
                is_dynamic      : true,
                // shows form in narrow view mode
                narrow          : false,
                // shows errors on start
                initial_errors  : false,
                // portlet style
                cls_portlet     : 'ui-portlet-limited'
            };

            // configure options
            this.options = Utils.merge(options, this.optionsDefault);

            // log options
            console.debug(this.options);

            // link galaxy modal or create one
            var galaxy = parent.Galaxy;
            if (galaxy && galaxy.modal) {
                this.modal = galaxy.modal;
            } else {
                this.modal = new Ui.Modal.View();
            }

            // check if the user is an admin
            if (galaxy && galaxy.currUser) {
                this.is_admin = galaxy.currUser.get('is_admin');
            } else {
                this.is_admin = false;
            }

            // link container
            this.container = this.options.container || 'body';

            // create deferred processing queue handler
            // this handler reduces the number of requests to the api by filtering redundant requests
            this.deferred = new Deferred();

            // set element
            this.setElement('<div/>');

            // add to main element
            $(this.container).append(this.$el);

            // build this form
            this.build(this.options);
        },

        /** Main tool form build function. This function is called once a new model is available.
        */
        build: function(options) {
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

            // request history content and build form
            this.content = new ToolContent(this);

            // update model data
            self.options.inputs = options && options.inputs;

            // create ui elements
            this._renderForm(options);

            // rebuild the underlying data structure
            this.tree.finalize();

            // show errors on startup
            if (options.initial_errors) {
                this._errors(options);
            }

            // add refresh listener
            this.on('refresh', function() {
                // by using/resetting the deferred ajax queue the number of redundant calls is reduced
                self.deferred.reset();
                self.deferred.execute(function(){self._updateModel()});
            });

            // add reset listener
            this.on('reset', function() {
                for (var i in this.element_list) {
                    this.element_list[i].reset();
                }
            });

            // refresh
            this.trigger('refresh');
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

        /** Highlights errors
        */
        _errors: function(options) {
            // hide previous error statements
            this.trigger('reset');
        
            // highlight all errors
            if (options && options.errors) {
                var error_messages = this.tree.matchResponse(options.errors);
                for (var input_id in this.element_list) {
                    var input = this.element_list[input_id];
                    if (error_messages[input_id]) {
                        this.highlight(input_id, error_messages[input_id], true);
                    }
                }
            }
        },

        /** Renders the UI elements required for the form
        */
        _renderForm: function(options) {
            // link this
            var self = this;

            // create message view
            this.message = new Ui.Message();

            // button for version selection
            var versions_button = new Ui.ButtonMenu({
                icon    : 'fa-cubes',
                title   : (!options.narrow && 'Versions') || null,
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
                                self.options.id = self.options.id.replace(self.options.version, this.version);
                                self.options.version = this.version;
                                
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
                title   : (!options.narrow && 'Options') || null,
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

            // button for version selection
            if (options.requirements && options.requirements.length > 0) {
                menu_button.addMenu({
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
            }


            // add toolshed url
            if (this.options.sharable_url) {
                menu_button.addMenu({
                    icon    : 'fa-external-link',
                    title   : 'Open in Toolshed',
                    tooltip : 'Access the repository',
                    onclick : function() {
                        window.open(self.options.sharable_url);
                    }
                });
            }

            // create tool form section
            this.section = new ToolSection.View(self, {
                inputs : options.inputs
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
                cls     : this.options.cls_portlet,
                operations: {
                    menu        : menu_button,
                    versions    : versions_button
                },
                buttons : this.buttons
            });

            // append message
            this.portlet.append(this.message.$el.addClass('ui-margin-top'));

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
});
