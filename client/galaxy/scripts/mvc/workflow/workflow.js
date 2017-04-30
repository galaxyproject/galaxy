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
                var $el_workflow = null;
                self.$el.empty().append( self._templateHeader() );
                self.build_messages( self );
                $el_workflow = self.$el.find( '.user-workflows' );
                // Add the actions buttons
                $el_workflow.append( self._templateActionButtons() );
                workflows = self.build_workflows( response );
                if( workflows.length > 0) {
                    $el_workflow.append( self._templateWorkflowTable( self, workflows) );
                    self.adjust_actiondropdown( $el_workflow );
                    // Register delete workflow events
                    _.each( workflows, function( wf ) {
                        self.confirm_delete( wf );
                    });
                }
                else {
                    $el_workflow.append( self._templateNoWorkflow() );
                }
            });
        },

        /** Build workflows object */
        build_workflows: function( response ) {
            var workflows = [],
                username = Galaxy.user.attributes.username;
            _.each( response, function( wf ) {
                var wf_obj = {};
                wf_obj.id = wf.id;
                wf_obj.text = wf.name;
                wf_obj.workflow_steps = wf.latest_workflow_steps;
                wf_obj.published = ( wf.published ? "Yes" : "No" );
                wf_obj.email = wf.user_email ? wf.user_email : "You";
                wf_obj.slug = wf.slug ? wf.slug : "";
                wf_obj.username = wf.user_name ? wf.user_name : "";
                workflows.push( wf_obj );
            });
            return workflows;
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

        /** Ajust the position of dropdown with respect to table */
        adjust_actiondropdown: function( $el ) {
            $el.on( 'show.bs.dropdown', function () {
                $el.css( "overflow", "inherit" );
            });

            $el.on( 'hide.bs.dropdown', function () {
                $el.css( "overflow", "auto" );
            });
        },

        /** Template for no workflow */
        _templateNoWorkflow: function() {
            return '<div class="wf-nodata"> You have no workflows. </div>';
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
        _templateWorkflowTable: function( self, workflows ) {
            var tableHtml = "", trHtml = "";
            tableHtml = tableHtml + '<table class="table colored">' +
                    '<tr class="header">' +
                        '<th>Name</th>' +
                        '<th>Owner</th>' +
                        '<th># of Steps</th>' +
                        '<th>Published</th>' +
                    '</tr>';
            _.each( workflows, function( wf ) {
                trHtml = trHtml + '<tr>' +
                             '<td class="wf-td wf-dpd">' +
                                 '<div class="dropdown">' +
                                     '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                         _.escape( wf.text ) + '<span class="caret"></span>' +
                                     '</button>' +
                                     self._templateActions( wf ) +
                                 '</div>' +
                              '</td>' +
                              '<td>' + _.escape( wf.email ) +'</td>' +
                              '<td class="wf-td">' + wf.workflow_steps + '</td>' +
                              '<td class="wf-td">' + wf.published + '</td>' +
                         '</tr>';
            });
            return tableHtml + trHtml + '</table>';
        },

        /** Template for user actions for workflows */
        _templateActions: function( workflow ) {
            if( workflow.username === "" ) {
                return '<ul class="dropdown-menu action-dpd">' +
                           '<li><a href="/workflow/editor?id='+ workflow.id +'">Edit</a></li>' +
                           '<li><a href="/root?workflow_id='+ workflow.id +'">Run</a></li>' +
                           '<li><a href="/workflow/sharing?id='+ workflow.id +'">Share or Download</a></li>' +
                           '<li><a href="/workflow/copy?id='+ workflow.id +'">Copy</a></li>' +
                           '<li><a href="/workflow/rename?id='+ workflow.id +'">Rename</a></li>' +
                           '<li><a href="/workflow/display_by_id?id='+ workflow.id +'">View</a></li>' +
                           '<li><a class="link-confirm-'+ workflow.id +'" href="/workflow/delete?id='+ workflow.id +'">Delete</a></li>' +
                      '</ul>';
            }
            else {
                return '<ul class="dropdown-menu action-dpd">' +
                         '<li><a href="/workflow/display_by_username_and_slug?username='+ workflow.username +'&slug='+ workflow.slug +'">View</a></li>' +
                         '<li><a href="/workflow/run?id='+ workflow.id +'">Run</a></li>' +
                         '<li><a href="/workflow/copy?id='+ workflow.id +'">Copy</a></li>' +
                         '<li><a class="link-confirm-shared-'+ workflow.id +'" href="/workflow/sharing?unshare_me=True&id='+ workflow.id +'">Remove</a></li>' +
                      '</ul>';
            }
        },      

        /** Main template */
        _templateHeader: function() {
            return '<div class="page-container"><div class="user-workflows wf">' +
                        '<div class="response-message"></div>' +
                        '<h2>Your workflows</h2>' +
                    '</div>'+
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
