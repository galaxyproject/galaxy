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
                workflows = [],
                shared_workflows = [],
                url = Galaxy.root + 'api/workflows/',
                username = Galaxy.user.attributes.username;

            $.getJSON( url, function( response ) {
                self.$el.empty().append( self._templateHeader() );
                // Update the workflows collection with different attributes names
                // to be shown as a dropdown list
                _.each( response, function( wf ) {
                    var wf_obj = {};
                    wf_obj.id = wf.id;
                    wf_obj.text = wf.name;
                    wf_obj.workflow_steps = wf.latest_workflow_steps;
                    // Check whether workflow belongs to user or shared
                    if( wf.owner === username ) {
                        workflows.push( wf_obj );
                    }
                    else {
                        wf_obj.email = wf.user_email;
                        shared_workflows.push( wf_obj );
                    }
                });
                // Button for new workflow
                self.btnNewWorkflow = new Ui.Button( {
                    title: 'Create new workflow',
                    tooltip: 'Create a workflow',
                    icon: 'fa-plus-circle',
                    cls: 'btn-wf',
                    onclick: function() { window.location.href = Galaxy.root + 'workflow/create'; }
                } );
                // Button for importing a workflow
                self.btnImportWorkflow = new Ui.Button( {
                    title: 'Upload or import workflow',
                    tooltip: 'Import a workflow',
                    icon: 'fa-upload',
                    cls: 'btn-wf',
                    onclick: function() { window.location.href = Galaxy.root + 'workflow/import_workflow'; }
                } );
                // Button for configuring workflow menu
                self.btnCongifureWorkflowMenu = new Ui.Button( {
                    title: 'Configure your workflow menu',
                    tooltip: 'Configure your workflow menu',
                    icon: 'fa-cog',
                    cls: 'btn-wf',
                    onclick: function() { window.location.href = Galaxy.root + 'workflow/configure_menu'; }
                } );

                // Make workflows select list only where there is at least
                // one workflow present
                if( workflows.length > 0 ) {
                    // Workflows select box
                    self.selectWorkflows = new Select.View({
                        css         : 'workflow-list',
                        container   : self.$( '.user-workflows' ),
                        data        : workflows,
                        value       : workflows[0].id, // Defaults to the first value
                        onchange    : function( value ) { self.select_workflow( self, value, workflows, 'user-workflows', 'workflow' ) }
                    });
                    self.$el.append( self.selectWorkflows.$el );
                    // Make table to show default selected workflow
                    self.select_workflow( self, workflows[0].id, workflows, 'user-workflows', 'workflow' );
                }
                else {
                    self.$el.find( '.wf-user' ).remove();
                    self.$el.find( '.user-workflows' ).append( '<div class="wf-nodata"> You have no workflows. </div>' );
                }

                // Make shared workflows select list only where there is at least
                // one shared workflow present
                if( shared_workflows.length > 0 ) {
                    // Workflows select box
                    self.selectSharedWorkflows = new Select.View({
                        css         : 'workflow-list',
                        container   : self.$( '.shared-workflows' ),
                        data        : shared_workflows,
                        value       : shared_workflows[0].id, // Defaults to the first value
                        onchange    : function( value ) { self.select_workflow( self, value, shared_workflows, 'shared-workflows', 'shared' ) }
                    });
                    self.$el.append( self.selectSharedWorkflows.$el );
                    // Make table to show default selected workflow
                    self.select_workflow( self, shared_workflows[0].id, shared_workflows, 'shared-workflows', 'shared' );                   
                }
                else {
                    self.$el.find( '.wf-shared' ).remove();
                    self.$el.find( '.shared-workflows' ).append( '<div class="wf-nodata"> No workflows have been shared with you. </div>' );
                }

                // Make new, import workflow and configure workflow menu buttons
                self.$el.append( self.btnNewWorkflow.$el );
                self.$el.append( self.btnImportWorkflow.$el );
                self.$el.append( self.btnCongifureWorkflowMenu.$el );
            });
        },

        /** Add confirm box before removing/unsharing workflow */
        confirm_delete: function( workflow ) {
            $( '.link-confirm-' + workflow.id ).click( function() {
                return confirm( "Are you sure you want to delete workflow '" + workflow.text + "'?" );
            });
            $( '.link-confirm-shared-' + workflow.id ).click( function() {
                return confirm( "Are you sure you want to remove the shared workflow '" + workflow.text + "'?" );
            });
        },

        /** Select a workflow */
        select_workflow: function( self, value, collection, cssClass, type ) {
            _.each( collection, function( item ) {
                if( value.toString() === item.id.toString() ) {
                    var $el = $( '.' + cssClass );
                    $el.find( '.manage-table' ).remove();
                    type === 'workflow' ? $el.append( self._templateWorkflowInfoTable( item ) ) : $el.append( self._templateSharedWorkflowInfoTable( item ) );
                    self.confirm_delete( item );
                }
            });
        },

        /** Template for workflow table */
        _templateWorkflowInfoTable: function( options ) {
            return '<table class="manage-table colored">' +
                    '<tr class="header">' +
                        '<th>Name</th>' +
                        '<th># of Steps</th>' +
                    '</tr>' +
                    '<tr>' +
                        '<td class="wf-td wf-dpd">' +
                            '<div class="dropdown">' +
                                '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                     _.escape( options.text ) + '<span class="caret"></span>' +
                                 '</button>' +
                                 '<ul class="dropdown-menu action-dpd">' +
                                     '<li><a href="/workflow/editor?id='+ options.id +'">Edit</a></li>' +
                                     '<li><a href="/root?workflow_id='+ options.id +'">Run</a></li>' +
                                     '<li><a href="/workflow/sharing?id='+ options.id +'">Share or Download</a></li>' +
                                     '<li><a href="/workflow/copy?id='+ options.id +'">Copy</a></li>' +
                                     '<li><a href="/workflow/rename?id='+ options.id +'">Rename</a></li>' +
                                     '<li><a href="/workflow/display_by_id?id='+ options.id +'">View</a></li>' +
                                     '<li><a class="link-confirm-'+ options.id +'" href="/workflow/delete?id='+ options.id +'">Delete</a></li>' +
                                 '</ul>' +
                            '</div>' +
                        '</td>' +
                        '<td class="wf-td">' + options.workflow_steps + '</td>' +
                    '</tr>' +
                '</table>';
        },

        /** Template for shared workflow table */
        _templateSharedWorkflowInfoTable: function( options ) {
            return '<table class="manage-table colored">' +
                    '<tr class="header">' +
                        '<th>Name</th>' +
                        '<th>Owner</th>' +
                        '<th># of Steps</th>' +
                    '</tr>' +
                    '<tr>' +
                        '<td class="shared-wf-td wf-dpd">' +
                            '<div class="dropdown">' +
                                '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                     _.escape( options.text ) + '<span class="caret"></span>' +
                                 '</button>' +
                                 '<ul class="dropdown-menu action-dpd">' +
                                     '<li><a href="">View</a></li>' +
                                     '<li><a href="/workflow/run?id='+ options.id +'">Run</a></li>' +
                                     '<li><a href="/workflow/copy?id='+ options.id +'">Copy</a></li>' +
                                     '<li><a class="link-confirm-shared-'+ options.id +'" href="/workflow/sharing?unshare_me=True&id='+ options.id +'">Remove</a></li>' +
                                 '</ul>' +
                            '</div>' +
                        '</td>' +
                        '<td class="shared-wf-td">' + options.email + '</td>' +
                        '<td class="shared-wf-td">' + options.workflow_steps + '</td>' +
                    '</tr>' +
                '</table>';
        },

       
        /** Main template */
        _templateHeader: function( options ) {
            return  '<div class="user-workflows wf">' +
                        '<div class="page-container">' +
                            '<h2>Your workflows</h2>' +
                        '</div>' +
                    '</div>'+
                    '<hr class="wf-table-bottom wf-user">' +
                    '<div class="shared-workflows wf">' +
                        '<div class="page-container">' +
                            '<h2>Workflows shared with you by others</h2>' +
                        '</div>' +
                    '</div>' +
                    '<hr class="wf-table-bottom wf-shared">';
        }
    });

    return {
        View  : View
    };
});
