/**
    This is the base class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'utils/deferred', 'mvc/ui/ui-misc', 'mvc/form/form-view',
        'mvc/tools/tools-template', 'mvc/citation/citation-model', 'mvc/citation/citation-view'],
    function(Utils, Deferred, Ui, Form, ToolTemplate, CitationModel, CitationView) {

    // create form view
    return Backbone.View.extend({
        // initialize
        initialize: function(options) {
            // check if the user is an admin
            var galaxy = parent.Galaxy;
            if (galaxy && galaxy.currUser) {
                this.is_admin = galaxy.currUser.get('is_admin');
            } else {
                this.is_admin = false;
            }

            // create deferred processing queue handler
            // this handler reduces the number of requests to the api by filtering redundant requests
            this.deferred = new Deferred();

            // set element
            this.setElement('<div/>');

            // append to body
            this.container = options.container || 'body';
            $(this.container).append(this.$el);

            // create form
            this._buildForm(options);
        },

        /** Build form */
        _buildForm: function(options) {
            // link this
            var self = this;

            // configure options
            this.options = Utils.merge(options, this.optionsDefault);

            // merge form options
            var form_options = Utils.merge({
                icon            : 'fa-wrench',
                title           : '<b>' + options.name + '</b> ' + options.description + ' (Galaxy Tool Version ' + options.version + ')',
                operations      : this._operations(),
                onchange        : function(current_state) {
                    // by resetting the deferred ajax queue the number of redundant calls is reduced
                    self.deferred.reset();
                    self.deferred.execute(function(){
                        self._updateModel($.extend(true, {}, self.form.data.create()));
                    });
                }
            }, options);

            // create form
            this.form = new Form(form_options);

            // create footer
            this._footer();

            // create element
            this.$el.empty();
            this.$el.append(this.form.$el);
        },

        // create tool operation menu
        _operations: function() {
            // link this
            var self = this;
            var options = self.options;

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
                        window.open(options.biostar_url + '/local/search/page/?q=' + options.name);
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
            if (self.is_admin) {
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
                            self.form.message.update({
                                persistent  : true,
                                message     : ToolTemplate.requirements(options),
                                status      : 'info'
                            });
                        } else {
                            this.visible = false;
                            self.form.message.update({
                                message     : ''
                            });
                        }
                    }
                });
            }

            // add toolshed url
            if (options.sharable_url) {
                menu_button.addMenu({
                    icon    : 'fa-external-link',
                    title   : 'See in Tool Shed',
                    tooltip : 'Access the repository',
                    onclick : function() {
                        window.open(options.sharable_url);
                    }
                });
            }

            // return operations
            return {
                menu        : menu_button,
                versions    : versions_button
            }
        },

        // create footer
        _footer: function() {
            // link options
            var options = this.options;

            // append help
            if (options.help != '') {
                this.form.$el.append(ToolTemplate.help(options));
            }

            // create and append tool citations
            if (options.citations) {
                var $citations = $('<div/>');
                var citations = new CitationModel.ToolCitationCollection();
                citations.tool_id = options.id;
                var citation_list_view = new CitationView.CitationListView({ el: $citations, collection: citations } );
                citation_list_view.render();
                citations.fetch();
                this.form.$el.append($citations);
            }
        }
    });
});
