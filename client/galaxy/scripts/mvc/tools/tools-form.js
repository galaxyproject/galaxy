/*
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'mvc/citation/citation-model', 'mvc/citation/citation-view',
        'mvc/tools', 'mvc/tools/tools-template', 'mvc/tools/tools-datasets', 'mvc/tools/tools-section', 'mvc/tools/tools-tree', 'mvc/tools/tools-jobs'],
    function(Portlet, Ui, CitationModel, CitationView,
             Tools, ToolTemplate, ToolDatasets, ToolSection, ToolTree, ToolJobs) {

    // create tool model
    var Model = Backbone.Model.extend({
        initialize: function (options) {
            this.url = galaxy_config.root + 'api/tools/' + options.id + '?io_details=true';
        }
    });

    // create form view
    var View = Backbone.View.extend({
        // base element
        main_el: 'body',
        
        // initialize
        initialize: function(options) {
            // link this
            var self = this;
            
            // link options
            this.options = options;
            
            // load tool model
            this.model = new Model({
                id : options.id
            });
            
            // creates a tree/json structure from the input form
            this.tree = new ToolTree(this);
            
            // creates the job handler
            this.job_handler = new ToolJobs(this);
            
            // reset field list
            this.field_list = {};
            
            // reset sequential input definition list
            this.input_list = {};
            
            // reset input element definition list
            this.element_list = {};
            
            // initialize datasets
            this.datasets = new ToolDatasets({
                history_id  : this.options.history_id,
                success     : function() {
                    self._initializeToolForm();
                }
            });
        },
        
        // message
        message: function(options) {
            $(this.main_el).empty();
            $(this.main_el).append(ToolTemplate.message(options));
        },
        
        // reset form
        reset: function() {
            for (var i in this.element_list) {
                this.element_list[i].reset();
            }
        },
        
        // refresh
        refresh: function() {
            // recreate tree structure
            this.tree.refresh();
            
            // trigger change
            for (var id in this.field_list) {
                this.field_list[id].trigger('change');
            }
            
            // log
            console.debug('tools-form::refresh() - Recreated tree structure. Refresh.');
        },
        
        // initialize tool form
        _initializeToolForm: function() {
            // link this
            var self = this;
            
            // create question button
            var button_question = new Ui.ButtonIcon({
                icon    : 'fa-question-circle',
                title   : 'Question?',
                tooltip : 'Ask a question about this tool (Biostar)',
                onclick : function() {
                    window.open(self.options.biostar_url + '/p/new/post/');
                }
            });
            
            // create search button
            var button_search = new Ui.ButtonIcon({
                icon    : 'fa-search',
                title   : 'Search',
                tooltip : 'Search help for this tool (Biostar)',
                onclick : function() {
                    window.open(self.options.biostar_url + '/t/' + self.options.id + '/');
                }
            });
            
            // create share button
            var button_share = new Ui.ButtonIcon({
                icon    : 'fa-share',
                title   : 'Share',
                tooltip : 'Share this tool',
                onclick : function() {
                    prompt('Copy to clipboard: Ctrl+C, Enter', galaxy_config.root + 'root?tool_id=' + self.options.id);
                }
            });
            
            // fetch model and render form
            this.model.fetch({
                error: function(response) {
                    console.debug('tools-form::_initializeToolForm() : Attempt to fetch tool model failed.');
                },
                success: function() {
                    // inputs
                    self.inputs = self.model.get('inputs');
            
                    // create portlet
                    self.portlet = new Portlet.View({
                        icon : 'fa-wrench',
                        title: '<b>' + self.model.get('name') + '</b> ' + self.model.get('description'),
                        buttons: {
                            execute: new Ui.ButtonIcon({
                                icon     : 'fa-check',
                                tooltip  : 'Execute the tool',
                                title    : 'Execute',
                                floating : 'clear',
                                onclick  : function() {
                                    self.job_handler.submit();
                                }
                            })
                        },
                        operations: {
                            button_question: button_question,
                            button_search: button_search,
                            button_share: button_share
                        }
                    });
                    
                    // configure button selection
                    if(!self.options.biostar_url) {
                        button_question.$el.hide();
                        button_search.$el.hide();
                    }
                    
                    // append form
                    $(self.main_el).append(self.portlet.$el);
                    
                    // append help
                    if (self.options.help != '') {
                        $(self.main_el).append(ToolTemplate.help(self.options.help));
                    }
                    
                    // append citations
                    if (self.options.citations) {
                        // append html
                        $(self.main_el).append(ToolTemplate.citations());
            
                        // fetch citations
                        var citations = new CitationModel.ToolCitationCollection();
                        citations.tool_id = self.options.id;
                        var citation_list_view = new CitationView.CitationListView({ collection: citations } );
                        citation_list_view.render();
                        citations.fetch();
                    }
                    
                    // configure portlet and form table
                    self.setElement(self.portlet.content());
                    
                    // create tool form section
                    self.section = new ToolSection.View(self, {
                        inputs : self.model.get('inputs'),
                        cls    : 'ui-table-plain'
                    });
                    
                    // append tool section
                    self.portlet.append(self.section.$el);
                    
                    // trigger refresh
                    self.refresh();
                    //self.job_handler.submit();
                    self.tree.finalize();
                }
            });
        }
    });

    return {
        View: View
    };
});
