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
                url = Galaxy.root + 'api/workflows/';

            $.getJSON( url, function( response ) {
                self.$el.empty().append( self._templateHeader() );
                self.build_messages( self );

                // Add the actions buttons
                self.$el.find( '.user-workflows' ).append( self._templateActionButtons() );

                // Update the workflows collection with different attribute names
                // to be shown in dropdown lists
                var wf = self.build_workflows( response );
                workflows = wf.workflows;
                shared_workflows = wf.shared_workflows;

                // Make workflows and shared workflows select list only where there is at least
                // one workflow present in each category
                self.build_selectlist( self, workflows, 'user-workflows', 'workflow', 'wf-user', 'You have no workflows.' );
                self.build_selectlist( self, shared_workflows, 'shared-workflows', 'shared', 'wf-shared', 'No workflows have been shared with you.' );
            });
        },

        /** Build user workflows and shared workflows objects */
        build_workflows: function( response ) {
            var workflows = [],
                shared_workflows = [],
                username = Galaxy.user.attributes.username;
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
            return { 'workflows': workflows, 'shared_workflows': shared_workflows };
        },

        /** Build messages after user action */
        build_messages: function( self ) {
            var $el_message = $( '.response-message' ),
                status = self.getQueryStringValue( 'status' ),
                message = self.getQueryStringValue( 'message' );

            if( message && message !== null && message !== "" ) {
                $el_message.addClass( status + 'message' );
                $el_message.html( '<p>' + message + '</p>' );
            }
            else {
                $el_message.html("");
            }
        },

        /** Build workflow select lists */
        build_selectlist: function( self, collection, class_name, type, class_hr, no_data_text ) {
            // Add a select list if there is at least a workflow
            if( collection.length > 0 ) {
                // Workflows select box
                self.selectWorkflows = new Select.View({
                    css         : 'workflow-list',
                    container   : self.$( '.' + class_name ),
                    data        : collection,
                    value       : collection[0].id, // Defaults to the first value
                    onchange    : function( value ) { self.select_workflow( self, value, collection, class_name, type ) }
                });
                self.$el.append( self.selectWorkflows.$el );
                // Make table to show default selected workflow
                self.select_workflow( self, collection[0].id, collection, class_name, type );
            }
            else {
                self.$el.find( '.' + class_hr ).remove();
                self.$el.find( '.' + class_name ).append( '<div class="wf-nodata">' +  no_data_text + '</div>' );
            }
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

        /** Add confirm box before removing/unsharing workflow */
        confirm_delete: function( workflow ) {
            $( '.link-confirm-' + workflow.id ).click( function() {
                return confirm( "Are you sure you want to delete workflow '" + workflow.text + "'?" );
            });
            $( '.link-confirm-shared-' + workflow.id ).click( function() {
                return confirm( "Are you sure you want to remove the shared workflow '" + workflow.text + "'?" );
            });
        },

        /** Get querystrings from url */
        getQueryStringValue: function( key ) {
            return decodeURIComponent( window.location.search.replace(new RegExp("^(?:.*[&\\?]" + encodeURIComponent( key ).replace(/[\.\+\*]/g, "\\$&") + "(?:\\=([^&]*))?)?.*$", "i"), "$1") );
        },

        /** Template for actions buttons */
        _templateActionButtons: function() {
           return '<ul class="manage-table-actions">' +
                '<li>' +
                    '<a class="action-button fa fa-plus wf-action" id="new-workflow" href="/workflow/create">' +
                        '<span>Create new workflow</span>' +
                    '</a>' +
                '</li>' +
                '<li>' +
                    '<a class="action-button fa fa-upload wf-action" id="import-workflow" href="/workflow/import_workflow">' +
                        '<span>Upload or import workflow</span>' +
                    '</a>' +
                '</li>' +
            '</ul>';

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
                        '<td class="shared-wf-td">' + _.escape(options.email) + '</td>' +
                        '<td class="shared-wf-td">' + options.workflow_steps + '</td>' +
                    '</tr>' +
                '</table>';
        },

       
        /** Main template */
        _templateHeader: function( options ) {
            return '<div class="page-container"><div class="user-workflows wf">' +
                        '<div class="response-message"></div>' +
                        '<h2>Your workflows</h2>' +
                    '</div>'+
                    '<hr class="wf-table-bottom wf-user">' +
                    '<div class="shared-workflows wf">' +
                        '<h2>Workflows shared with you by others</h2>' +
                    '</div>' +
                    '<hr class="wf-table-bottom wf-shared">' +
                    '<div class="other-options wf">' +
                        '<h2>Other options</h2>' +
                            '<a class="action-button fa fa-cog wf-action" href="/workflow/configure_menu">' +
                                '<span>Configure your workflow menu</span>' +
                            '</a>' +
                    '</div></div>';
        }
    });

    return {
        View  : View
    };
});
