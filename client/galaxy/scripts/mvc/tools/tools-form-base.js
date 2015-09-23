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
                this._buildModel(options, true);
            }
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
                onchange        : function(current_state) {
                    // by resetting the deferred ajax queue the number of redundant calls is reduced
                    self.deferred.reset();
                    self.deferred.execute(function(){
                        self._updateModel();
                    });
                }
            }, this.options);

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
        _buildModel: function(options, hide_message) {
            // link this
            var self = this;

            // update current version
            this.options.id = options.id;
            this.options.version = options.version;

            if (options.job_id) {
                build_url = Galaxy.root + 'api/jobs/' + options.job_id + '/build_for_rerun';
            } else {
                // construct url
                var build_url = Galaxy.root + 'api/tools/' + options.id + '/build?';
                if (options.dataset_id) {
                    build_url += 'dataset_id=' + options.dataset_id;
                } else {
                    build_url += 'tool_version=' + options.version + '&';
                    var loc = top.location.href;
                    var pos = loc.indexOf('?');
                    if (loc.indexOf('tool_id=') != -1 && pos !== -1) {
                        build_url += loc.slice(pos + 1);
                    }
                }
            }

            // register process
            var process_id = this.deferred.register();

            // get initial model
            Utils.request({
                type    : 'GET',
                url     : build_url,
                success : function(new_model) {
                    // rebuild form
                    self._buildForm(new_model['tool_model'] || new_model);

                    // show version message
                    !hide_message && self.form.message.update({
                        status      : 'success',
                        message     : 'Now you are using \'' + self.options.name + '\' version ' + self.options.version + '.',
                        persistent  : false
                    });

                    // process completed
                    self.deferred.done(process_id);

                    // log success
                    console.debug('tools-form::initialize() - Initial tool model ready.');
                    console.debug(new_model);
                },
                error   : function(response) {
                    // process completed
                    self.deferred.done(process_id);

                    // log error
                    console.debug('tools-form::initialize() - Initial tool model request failed.');
                    console.debug(response);

                    // show error
                    var error_message = response.error || response.err_msg || 'Uncaught error.';
                    if (self.form == undefined){
                        self.form = new Form();
                    }
                    Galaxy.modal.show({
                        title   : 'Tool cannot be executed',
                        body    : error_message,
                        buttons : {
                            'Close' : function() {
                                Galaxy.modal.hide();
                            }
                        }
                    });
                }
            });
        },

        /** Request a new model for an already created tool form and updates the form inputs
        */
        _updateModel: function() {
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

            // register process
            var process_id = this.deferred.register();

            // log tool state
            console.debug('tools-form-base::_updateModel() - Sending current state (see below).');
            console.debug(current_state);

            // post job
            Utils.request({
                type    : 'POST',
                url     : model_url,
                data    : current_state,
                success : function(new_model) {
                    // update form with new model
                    self.form.update(new_model['tool_model'] || new_model);

                    // custom update
                    self.options.update && self.options.update(new_model);

                    // unset wait mode
                    form.wait(false);

                    // log success
                    console.debug('tools-form-base::_updateModel() - Received new model (see below).');
                    console.debug(new_model);

                    // process completed
                    self.deferred.done(process_id);
                },
                error   : function(response) {
                    // process completed
                    self.deferred.done(process_id);

                    // log error
                    console.debug('tools-form-base::_updateModel() - Refresh request failed.');
                    console.debug(response);
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
                                self.deferred.execute(function() {
                                    self._buildModel({id: id, version: version})
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
