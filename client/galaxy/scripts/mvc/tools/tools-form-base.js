/**
    This is the base class of the tool form plugin. This class is e.g. inherited by the regular and the workflow tool form.
*/
define(['utils/utils', 'utils/deferred', 'mvc/ui/ui-misc', 'mvc/form/form-view',
        'mvc/tools/tools-template', 'mvc/citation/citation-model', 'mvc/citation/citation-view'],
    function(Utils, Deferred, Ui, Form, ToolTemplate, CitationModel, CitationView) {

    // create form view
    return Backbone.View.extend({
        // initialize
        initialize: function(options) {
            this.options = Utils.merge(options, {});
            this.setElement('<div/>');

            // create deferred processing queue handler
            // this handler reduces the number of requests to the api by filtering redundant requests
            this.deferred = new Deferred();

            // create form
            if (options.inputs) {
                this._buildForm(options);
            } else {
                var self = this;
                this.deferred.execute(function(process) {
                    self._buildModel(process, options, true);
                });
            }
        },

        /** Wait for deferred build processes before removal */
        remove: function() {
            var self = this;
            this.$el.hide();
            this.deferred.execute(function(){
                Backbone.View.prototype.remove.call(self);
                Galaxy.emit.debug('tools-form-base::remove()', 'Destroy view.');
            });
        },

        /** Build form */
        _buildForm: function(options) {
            // link this
            var self = this;

            // merge form options
            this.options = Utils.merge(options, this.options);
            this.options = Utils.merge({
                icon            : 'fa-wrench',
                title           : '<b>' + options.name + '</b> ' + options.description + ' (Galaxy Tool Version ' + options.version + ')',
                operations      : this._operations(),
                onchange        : function() {
                    self.deferred.reset();
                    self.deferred.execute(function(process) {
                        self._updateModel(process);
                    });
                }
            }, this.options);

            // allow option customization
            this.options.customize && this.options.customize( this.options );

            // create form
            this.form = new Form(this.options);

            // create footer
            this._footer();

            // create element
            this.$el.empty();
            this.$el.append(this.form.$el);
        },

        /** Builds a new model through api call and recreates the entire form
        */
        _buildModel: function(process, options, hide_message) {
            var self = this;
            this.options.id = options.id;
            this.options.version = options.version;

            // build request url
            var build_url = '';
            var build_data = {};
            if ( options.job_id ) {
                build_url = Galaxy.root + 'api/jobs/' + options.job_id + '/build_for_rerun';
            } else {
                build_url = Galaxy.root + 'api/tools/' + options.id + '/build';
                if ( Galaxy.params && Galaxy.params.tool_id == options.id ) {
                    build_data = $.extend( {}, Galaxy.params );
                    options.version && ( build_data[ 'tool_version' ] = options.version );
                }
            }

            // get initial model
            Utils.request({
                type    : 'GET',
                url     : build_url,
                data    : build_data,
                success : function(new_model) {
                    self._buildForm(new_model['tool_model'] || new_model);
                    !hide_message && self.form.message.update({
                        status      : 'success',
                        message     : 'Now you are using \'' + self.options.name + '\' version ' + self.options.version + '.',
                        persistent  : false
                    });
                    Galaxy.emit.debug('tools-form-base::initialize()', 'Initial tool model ready.', new_model);
                    process.resolve();

                },
                error   : function(response) {
                    var error_message = ( response && response.err_msg ) || 'Uncaught error.';
                    if ( self.$el.is(':empty') ) {
                        self.$el.prepend((new Ui.Message({
                            message     : error_message,
                            status      : 'danger',
                            persistent  : true,
                            large       : true
                        })).$el);
                    } else {
                        Galaxy.modal.show({
                            title   : 'Tool request failed',
                            body    : error_message,
                            buttons : {
                                'Close' : function() {
                                    Galaxy.modal.hide();
                                }
                            }
                        });
                    }
                    Galaxy.emit.debug('tools-form::initialize()', 'Initial tool model request failed.', response);
                    process.reject();
                }
            });
        },

        /** Request a new model for an already created tool form and updates the form inputs
        */
        _updateModel: function(process) {
            // model url for request
            var model_url = this.options.update_url || Galaxy.root + 'api/tools/' + this.options.id + '/build';

            // link this
            var self = this;

            // create the request dictionary
            var form = this.form;

            // create the request dictionary
            var current_state = {
                tool_id         : this.options.id,
                tool_version    : this.options.version,
                inputs          : $.extend(true, {}, self.form.data.create())
            }

            // set wait mode
            form.wait(true);

            // log tool state
            Galaxy.emit.debug('tools-form-base::_updateModel()', 'Sending current state.', current_state);

            // post job
            Utils.request({
                type    : 'POST',
                url     : model_url,
                data    : current_state,
                success : function(new_model) {
                    self.form.update(new_model['tool_model'] || new_model);
                    self.options.update && self.options.update(new_model);
                    form.wait(false);
                    Galaxy.emit.debug('tools-form-base::_updateModel()', 'Received new model.', new_model);
                    process.resolve();
                },
                error   : function(response) {
                    Galaxy.emit.debug('tools-form-base::_updateModel()', 'Refresh request failed.', response);
                    process.reject();
                }
            });
        },

        // create tool operation menu
        _operations: function() {
            // link this
            var self = this;
            var options = this.options;

            // button for version selection
            var versions_button = new Ui.ButtonMenu({
                icon    : 'fa-cubes',
                title   : (!options.narrow && 'Versions') || null,
                tooltip : 'Select another tool version'
            });
            if (!options.is_workflow && options.versions && options.versions.length > 1) {
                for (var i in options.versions) {
                    var version = options.versions[i];
                    if (version != options.version) {
                        versions_button.addMenu({
                            title   : 'Switch to ' + version,
                            version : version,
                            icon    : 'fa-cube',
                            onclick : function() {
                                // here we update the tool version (some tools encode the version also in the id)
                                var id = options.id.replace(options.version, this.version);
                                var version = this.version;
                                // queue model request
                                self.deferred.reset();
                                self.deferred.execute(function(process) {
                                    self._buildModel(process, {id: id, version: version})
                                });
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
                    prompt('Copy to clipboard: Ctrl+C, Enter', window.location.origin + Galaxy.root + 'root?tool_id=' + options.id);
                }
            });

            // add admin operations
            if (Galaxy.user && Galaxy.user.get('is_admin')) {
                // create download button
                menu_button.addMenu({
                    icon    : 'fa-download',
                    title   : 'Download',
                    tooltip : 'Download this tool',
                    onclick : function() {
                        window.location.href = Galaxy.root + 'api/tools/' + options.id + '/download';
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