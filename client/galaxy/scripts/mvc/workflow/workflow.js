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
                url = Galaxy.root + 'workflow',
                workflow_list = null;
            $.ajax({
                url     : url,
                type    : 'GET'
            }).done( function( response ) {
                self.$el.empty().append( self._templateHeader() );
                response = JSON.parse( response );
                workflow_list = response[ "workflows" ];
                // Button for new workflow
                self.btnNewWorkflow = new Ui.Button( { 
                    title: 'New Workflow',
                    tooltip: 'Create a workflow',
                    icon: 'fa-plus',
                    onclick: function() { self.new_workflow(); } 
                } );
                // Button for importing a workflow
                self.btnImportWorkflow = new Ui.Button( {
                    title: 'Import Workflow',
                    tooltip: 'Import a workflow',
                    icon: 'fa-code-fork',
                    onclick: function() { self.import_workflow(); }
                } );

                // Make workflows select list only where there is at least 
                // one workflow present
                if( workflow_list.length > 0 ) {
                    // Workflows select box
                    self.selectWorkflows = new Select.View({
                        css         : 'workflow-list',
                        container   : self.$( '.user-workflows' ),
                        data        : workflow_list,
                        value       : workflow_list[0].id, // Defaults to the first value
                        onchange    : function( value ) { self.select_workflow( self, value, workflow_list ) }
                    });
                    self.$el.append( self.selectWorkflows.$el );
                    // Make table to show default selected workflow
                    self.select_workflow( self, workflow_list[0].id, workflow_list );
                }
                else {
                    self.$el.append( '<div style="padding-left: 1%"> You have no workflows. </div>' );
                }

                // Make new and import workflow buttons
                self.$el.append( self.btnNewWorkflow.$el );
                self.$el.append( self.btnImportWorkflow.$el );

            }).fail( function( response ) {
                self.$el.empty().append( new Ui.Message({
                    message     : 'Failed to load resource ' + self.url + '.',
                    status      : 'danger',
                    persistent  : true
                }).$el );
            });
        },

        /* Select a workflow */
        select_workflow: function( self, value, collection ) {
            var template = "",
                $el = $( '.user-workflows' );
            $el.find( '.manage-table' ).remove();

            for(var i = 0; i < collection.length; i++) {
                var item = collection[i];
                if( parseInt(value) === parseInt(item.id) ) {
                    template = self._templateWorkflowInfoTable( item );
                    $el.append( template );
                    break;
                }
            }
        },

        /* Open a url for creating new workflow */
        new_workflow: function() {
            window.location.href = Galaxy.root + 'workflow/create';
        },

        import_workflow: function() {
            // TODO: Add logic for importing workflow
        },

        _templateWorkflowInfoTable: function( options ) {
            return '<table class="manage-table colored">' +
                    '<tr class="header">' +
                        '<th>Name</th>' +
                        '<th># of Steps</th>' +
                        '<th>Last Updated Time</th>' +
                        '<th></th>' +
                    '</tr>' +
                    '<tr>' +
                        '<td>' +
                            '<div class="menubutton" style="float: left;" id="'+ options.id +'">' + options.text + '</div>' +
                        '</td>' +
                        '<td>' + options.workflow_steps + '</td>' +
                        '<td>' + options.update_time + '</td>' +
                        '<td></td>' +
                    '</tr>' +
                '</table>';
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
