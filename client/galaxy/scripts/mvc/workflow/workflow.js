/** Workflow view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc', 'mvc/ui/ui-select' ], function( Form, Ui, Select ) {

    /** View of the main workflow list page */
    var View = Backbone.View.extend({

        initialize: function() {
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this,
                url = Galaxy.root + 'workflow';
            $.ajax({
                url     : url,
                type    : 'GET'
            }).done( function( response ) {
                self.$el.empty().append( self._templateHeader() );
                response = JSON.parse( response );
                // Button for new workflow
                self.btnNewWorkflow = new Ui.Button( { 
                    title: 'New Workflow',
                    tooltip: 'Create a workflow',
                    icon: 'fa-plus',
                    onclick: function() { self.create_workflow(); } 
                } );
                // Button for importing a workflow
                self.btnImportWorkflow = new Ui.Button( {
                    title: 'Import Workflow',
                    tooltip: 'Import a workflow',
                    icon: 'fa-code-fork',
                    onclick: function() { self.import_workflow(); }
                } );
                // Workflows select box
                self.selectWorkflows = new Select.View({
                    css         : 'workflow-list',
                    container   : self.$( '.user-workflows' ),
                    data        : response[ "workflows" ],
                    value       : 1, // Defaults to the first value
                    onchange    : function( value ) { /*TODO: Add logic when workflow is changed */  }
                });
                // Make HTML for workflows
                self.$el.append( self.btnNewWorkflow.$el );
                self.$el.append( self.btnImportWorkflow.$el );
                self.$el.append( self.selectWorkflows.$el );

            }).fail( function( response ) {
                self.$el.empty().append( new Ui.Message({
                    message     : 'Failed to load resource ' + self.url + '.',
                    status      : 'danger',
                    persistent  : true
                }).$el );
            });
        },

        create_workflow: function() {
            // TODO: Add logic for creating workflow
        },

        import_workflow: function() {
            // TODO: Add logic for importing workflow
        },
       
        _templateHeader: function( options ) {
            return  '<div class="user-workflows">' +
                        '<div class="page-container">' +
                            '<h2>Your workflows</h2>' +
                        '</div>' +
                    '</div>';
        }
    });

    return {
        View  : View
    };
});
