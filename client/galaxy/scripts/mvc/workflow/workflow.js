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
                workflows = [];

            $.getJSON( Galaxy.root + 'api/workflows/', function( response ) {
                self.$el.empty().append( self._templateHeader() );
                // Update the workflows collection with different attributes names
                // to be shown as a dropdown list
                for(var i = 0; i < response.length; i++) {
                    var wf_obj = {},
                        wf = response[ i ];
                    wf_obj.id = wf.id;
                    wf_obj.text = wf.name;
                    wf_obj.update_time = wf.update_time;
                    wf_obj.workflow_steps = wf.latest_workflow_steps;
                    workflows.push( wf_obj );
                }
                // Button for new workflow
                self.btnNewWorkflow = new Ui.Button( {
                    title: 'New Workflow',
                    tooltip: 'Create a workflow',
                    icon: 'fa-plus-circle',
                    onclick: function() { self.new_workflow(); }
                } );
                // Button for importing a workflow
                self.btnImportWorkflow = new Ui.Button( {
                    title: 'Import Workflow',
                    tooltip: 'Import a workflow',
                    icon: 'fa-upload',
                    onclick: function() { self.import_workflow(); }
                } );

                // Make new and import workflow buttons
                self.$el.append( self.btnNewWorkflow.$el );
                self.$el.append( self.btnImportWorkflow.$el );

                // Make workflows select list only where there is at least
                // one workflow present
                if( workflows.length > 0 ) {
                    // Workflows select box
                    self.selectWorkflows = new Select.View({
                        css         : 'workflow-list',
                        container   : self.$( '.user-workflows' ),
                        data        : workflows,
                        value       : workflows[0].id, // Defaults to the first value
                        onchange    : function( value ) { self.select_workflow( self, value, workflows ) }
                    });
                    self.$el.append( self.selectWorkflows.$el );
                    // Make table to show default selected workflow
                    self.select_workflow( self, workflows[0].id, workflows );
                }
                else {
                    self.$el.append( '<div class="wf-nodata"> You have no workflows. </div>' );
                }
            });
        },

        /* Select a workflow */
        select_workflow: function( self, value, collection ) {
            var template = "",
                $el = $( '.user-workflows' );
            $el.find( '.manage-table' ).remove();

            for(var i = 0; i < collection.length; i++) {
                var item = collection[i];
                if( value.toString() === item.id.toString() ) {
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
                    '</tr>' +
                    '<tr>' +
                        '<td class="wf-td">' + options.text + '</td>' +
                        '<td class="wf-td">' + options.workflow_steps + '</td>' +
                        '<td class="wf-td">' + options.update_time + '</td>' +
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
