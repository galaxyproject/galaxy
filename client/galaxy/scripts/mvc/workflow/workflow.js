/** Workflow view */
define( [], function() {

    /** View of the main workflow list page */
    var View = Backbone.View.extend({

        initialize: function() {
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this,
                min_query_length = 3;
            $.getJSON( Galaxy.root + 'api/workflows/', function( workflows ) {
                var $el_workflow = null;
                // Add workflow header
                self.$el.empty().append( self._templateHeader() );
                // Add user actions message if any
                self.build_messages( self );
                $el_workflow = self.$el.find( '.user-workflows' );
                // Add the actions buttons
                $el_workflow.append( self._templateActionButtons() );
                if( workflows.length > 0) {
                    $el_workflow.append( self._templateWorkflowTable( self, workflows) );
                    self.adjust_actiondropdown( $el_workflow );
                    // Register delete and run workflow events
                    _.each( workflows, function( wf ) {
                        self.confirm_delete( self, wf );
                    });
                    // Register search workflow event
                    self.search_workflow( self, self.$el.find( '.search-wf' ), self.$el.find( '.workflow-search tr' ), min_query_length );
                    //self.register_configure_menu( self );
                }
                else {
                    $el_workflow.append( self._templateNoWorkflow() );
                }
            });
        },

        /** Build messages after user action */
        build_messages: function( self ) {
            var $el_message = self.$el.find( '.response-message' ),
                status = self.get_querystring( 'status' ),
                message = self.get_querystring( 'message' );

            if( message && message !== null && message !== "" ) {
                $el_message.addClass( status + 'message' );
                $el_message.html( '<p>' + message + '</p>' );
            }
            else {
                $el_message.html("");
            }
        },

        /** Add confirm box before removing/unsharing workflow */
        confirm_delete: function( self, workflow ) {
            var $el_wf_link = self.$el.find( '.link-confirm-' + workflow.id ),
                $el_shared_wf_link = self.$el.find( '.link-confirm-shared-' + workflow.id );
            $el_wf_link.click( function() {
                return confirm( "Are you sure you want to delete workflow '" + workflow.name + "'?" );
            });
            $el_shared_wf_link.click( function() {
                return confirm( "Are you sure you want to remove the shared workflow '" + workflow.name + "'?" );
            });
        },

        /** Implement client side workflow search/filtering */
        search_workflow: function( self, $el_searchinput, $el_tabletr, min_querylen ) {
            $el_searchinput.on( 'keyup', function () {
                var query = $( this ).val();
                // Filter when query is at least 3 characters
                // otherwise show all rows
                if( query.length >= min_querylen ) {
                    // Ignore the query's case using 'i'
                    var regular_expression = new RegExp( query, 'i' );
                    $el_tabletr.hide();
                    $el_tabletr.filter(function () {
                        // Apply regular expression on each row's text
                        // and show when there is a match
                        return regular_expression.test( $( this ).text() );
                    }).show();
                }
                else {
                    $el_tabletr.show();
                }
            });
        },

        /** Get querystrings from url */
        get_querystring: function( key ) {
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

        /** Open configure workflow menu */
        register_configure_menu: function( self, workflows ) {
            self.$el.find( '.configure-wf-menu' ).click(function( e ) {
                // register_configure_menu
                
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
                    '<input class="search-wf form-control" type="text" autocomplete="off" placeholder="search for workflow...">' +
                '</li>' +
                '<li>' +
                    '<a class="action-button fa fa-plus wf-action" id="new-workflow" title="Create new workflow" href="'+ Galaxy.root +'workflow/create">' +
                    '</a>' +
                '</li>' +
                '<li>' +
                    '<a class="action-button fa fa-upload wf-action" id="import-workflow" title="Upload or import workflow" href="'+ Galaxy.root +'workflow/import_workflow">' +
                    '</a>' +
                '</li>' +
            '</ul>';
        },

        /** Template for workflow table */
        _templateWorkflowTable: function( self, workflows ) {
            var tableHtml = "", trHtml = "";
            tableHtml = tableHtml + '<table class="table colored"><thead>' +
                    '<tr class="header">' +
                        '<th class="wf-td">Name</th>' +
                        '<th class="wf-td">Owner</th>' +
                        '<th class="wf-td"># of Steps</th>' +
                        '<th class="wf-td">Published</th>' +
                    '</tr></thead>';
            _.each( workflows, function( wf ) {
                trHtml = trHtml + '<tr>' +
                             '<td class="wf-td wf-dpd">' +
                                 '<div class="dropdown">' +
                                     '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                         _.escape( wf.name ) + '<span class="caret"></span>' +
                                     '</button>' +
                                     self._templateActions( wf ) +
                                 '</div>' +
                              '</td>' +
                              '<td>' + ( wf.owner === Galaxy.user.attributes.username ? "You" : wf.owner ) +'</td>' +
                              '<td class="wf-td">' + wf.number_of_steps + '</td>' +
                              '<td class="wf-td">' + ( wf.published ? "Yes" : "No" ) + '</td>' +
                         '</tr>';
            });
            return tableHtml + '<tbody class="workflow-search">' + trHtml + '</tbody></table>';
        },

        /** Template for user actions for workflows */
        _templateActions: function( workflow ) {
            if( workflow.owner === Galaxy.user.attributes.username ) {
                return '<ul class="dropdown-menu action-dpd">' +
                           '<li><a href="'+ Galaxy.root +'workflow/editor?id='+ workflow.id +'">Edit</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/run?id='+ workflow.id +'" target="galaxy_main">Run</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/sharing?id='+ workflow.id +'">Share or Download</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/copy?id='+ workflow.id +'">Copy</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/rename?id='+ workflow.id +'">Rename</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/display_by_id?id='+ workflow.id +'">View</a></li>' +
                           '<li><a class="link-confirm-'+ workflow.id +'" href="'+ Galaxy.root +'workflow/delete?id='+ workflow.id +'">Delete</a></li>' +
                      '</ul>';
            }
            else {
                return '<ul class="dropdown-menu action-dpd">' +
                         '<li><a href="'+ Galaxy.root +'workflow/display_by_username_and_slug?username='+ workflow.owner +'&slug='+ workflow.slug +'">View</a></li>' +
                         '<li><a href="'+ Galaxy.root +'workflow/run?id='+ workflow.id +'" target="galaxy_main">Run</a></li>' +
                         '<li><a href="'+ Galaxy.root +'workflow/copy?id='+ workflow.id +'">Copy</a></li>' +
                         '<li><a class="link-confirm-shared-'+ workflow.id +'" href="'+ Galaxy.root +'workflow/sharing?unshare_me=True&id='+ workflow.id +'">Remove</a></li>' +
                      '</ul>';
            }
        },

        /** Main template */
        _templateHeader: function() {
            return '<div class="page-container">' +
                       '<div class="user-workflows wf">' +
                           '<div class="response-message"></div>' +
                           '<h2>Your workflows</h2>' +
                       '</div>'+
                       '<div class="other-options wf">' +
                           '<h2>Other options</h2>' +
                           '<a class="action-button fa fa-cog wf-action" href="'+ Galaxy.root +'workflow/configure_menu" title="Configure your workflow menu">' +
                               '<span>Configure your workflow menu</span>' +
                           '</a>' +
                       '</div>' +
                   '</div>';
        }
    });

    /** Configure Workflow Menu View */
    var Configure_Menu_View = Backbone.View.extend({

        initialize: function( options ) {
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/workflows/configure_workflow_menu/', function( response ) {
                var workflows = response.workflows,
                    ids_in_menu = response.ids_in_menu,
                    $el_config_worflow = null;

                // Add configure workflow header
                self.$el.empty().append( self._templateConfigWorkflowHeader() );
                $el_config_worflow = self.$el.find( '.configure-workflows' );
                if( workflows.length > 0 ) {
                    $el_config_worflow.append( self._templateConfigureWorkflow( self, workflows, ids_in_menu ) );
                    self.save_workflow_menu( self );
                    self.make_checked( self, ids_in_menu );
                }
                else {
                    $el_config_worflow.append( self._templateNoWorkflow() );
                }
            });
        },

        /** Make the worflows as checked if present in the menu */
        make_checked: function( self, ids_in_menu ) {
            $.each(self.$el.find( '.wf-config-item' ), function() {
                var wf_checkbox = $( this )[0];
                _.each( ids_in_menu, function( id ) {
                    if ( parseInt( wf_checkbox.value ) === id ) {
                        wf_checkbox.checked = true;
                    }
                });
            });
        },

        /** Save the changes for workflow menu */
        save_workflow_menu: function( self ) {
        var $el_save_workflow_menu = self.$el.find( '.wf-save-menu' );
            $el_save_workflow_menu.click( function( e ) {
                var ids = [];
                $.each(self.$el.find( '.wf-config-item' ), function() {
                    var wf_checkbox = $( this )[0];
                    if( wf_checkbox.checked || wf_checkbox.checked === 'true' ) {
                        ids.push( parseInt( wf_checkbox.value ) );
                    }
                });
                $.ajax({
                    type: 'PUT',
                    url: Galaxy.root + 'api/workflows/configure_workflow_menu/',
                    data: JSON.stringify( { 'workflow_ids': ids } ),
                    contentType : 'application/json'
                }).done( function( response ) {
                    window.location = Galaxy.root + 'workflow?status='+ response.status +'&message=' + response.message;
                });
            });
        },

        /** Template for configure workflow table */
        _templateConfigureWorkflow: function( self, workflows, ids_in_menu ) {
            var tableHtml = "", trHtml = "";
            tableHtml = tableHtml + '<table class="table colored"><thead>' +
                    '<tr class="header">' +
                        '<th class="wf-td">Name</th>' +
                        '<th class="wf-td">Owner</th>' +
                        '<th class="wf-td"># of Steps</th>' +
                        '<th class="wf-td">Show in menu</th>' +
                    '</tr></thead>';
            _.each( workflows, function( wf ) {
                trHtml = trHtml + '<tr>' +
                    '<td class="wf-td">' + _.escape( wf.name ) +'</td>' +
                    '<td>' + ( wf.owner === Galaxy.user.attributes.username ? "You" : wf.owner ) +'</td>' +
                    '<td class="wf-td">' + wf.number_of_steps + '</td>' +
                    '<td class="wf-td">' + self._templateInputCheckbox( self, wf, ids_in_menu ) + '</td>' +
                '</tr>';
            });
            tableHtml = tableHtml + '<tbody class="workflow-config-menu">' + trHtml + '</tbody></table>';
            tableHtml = tableHtml + '<a class="action-button wf-save-menu" href="#" title="Save">' +
                                        '<span>Save</span>' +
                                    '</a>';
            return tableHtml
        },

       /** Template for no workflow */
        _templateNoWorkflow: function() {
            return '<div class="wf-nodata"> You do not have any accessible workflows. </div>';
        },

        /** Template for checkboxes */
        _templateInputCheckbox: function( self, wf ) {
            return '<input type="checkbox" class="wf-config-item" name="workflow_ids" value="'+ wf.id +'" />';
        },

        /** Template for main config workflow menu */
        _templateConfigWorkflowHeader: function() {
            return '<div class="page-container">' +
                       '<div class="configure-workflows wf">' +
                           '<h2>Configure workflow menu</h2>' +
                       '</div>'+
                   '</div>';
        }
    });

    return {
        View  : View,
        Configure_Menu_View : Configure_Menu_View
    };
});
