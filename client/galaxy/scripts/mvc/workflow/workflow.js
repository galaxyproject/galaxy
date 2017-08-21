/** Workflow view */
define( [ 'utils/utils', 'mvc/ui/ui-misc', "mvc/tag", "mvc/workflow/workflow-model"  ], function( Utils, Ui, TAGS, WorkflowModel ) {

    /** Build messages after user action */
    function build_messages() {
        var $el_message = this.$( '.response-message' ),
            response = {};
        response = {
            'status': Utils.getQueryString( 'status' ),
            'message': _.escape( Utils.getQueryString( 'message' ) ),
            'persistent': true,
            'cls': Utils.getQueryString( 'status' ) + 'message'
        };
        $el_message.empty().html( new Ui.Message( response ).$el );
    }
 
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
                build_messages();
                $el_workflow = self.$( '.user-workflows' );
                // Add the actions buttons
                $el_workflow.append( self._templateActionButtons() );
                if( workflows.length > 0) {
                    $el_workflow.append( self._templateWorkflowTable( self, workflows) );
                    self._renderTags(self, workflows);
                    self.adjust_actiondropdown( $el_workflow );
                    // Register delete and run workflow events
                    _.each( workflows, function( wf ) {
                        self.confirm_delete( wf );
                    });
                    self.register_show_tool_menu();
                    // Register search workflow event
                    self.search_workflow( self.$( '.search-wf' ), self.$( '.workflow-search tr' ), min_query_length );
                }
                else {
                    $el_workflow.append( self._templateNoWorkflow() );
                }
            });
        },



        _renderTags : function( self, workflows ){
        self.tag_editors = [];
        console.log('render workflows');
        _.each( workflows, function ( wf ) {
            // console.log(wf);
            var wf_model = new WorkflowModel( { id: wf.id,
                                                name: wf.name,
                                                tags: wf.tags } );
            console.log(wf_model);
            var el =  $.find( '.' + wf.id + '.tags-display' );
            var tag_editor = new TAGS.WorkflowTagsEditor({
            model           : wf_model,
            el              : el});

            tag_editor.toggle( true );
            tag_editor.render();
            self.tag_editors.push(tag_editor) ;

            });
        },

        // Save the workflow as an item in Tool panel
        register_show_tool_menu: function() {
            var $el_checkboxes = this.$( '.show-in-tool-panel' );
            $el_checkboxes.on( 'click', function( e ) {
                var ids = [];
                // Look for all the checked checkboxes
                for( var item = 0; item < $el_checkboxes.length; item++ ) {
                    var checkbox = $el_checkboxes[ item ];
                    if( checkbox.checked ) {
                        ids.push( checkbox.value );
                    }
                }
                // Save all the checked workflows
                $.ajax({
                    type: 'PUT',
                    url: Galaxy.root + 'api/workflows/menu/',
                    data: JSON.stringify( { 'workflow_ids': ids } ),
                    contentType : 'application/json'
                }).done( function( response ) {
                    window.location = Galaxy.root + 'workflow';
                });
            });
        },

        /** Add confirm box before removing/unsharing workflow */
        confirm_delete: function( workflow ) {
            var $el_wf_link = this.$( '.link-confirm-' + workflow.id ),
                $el_shared_wf_link = this.$( '.link-confirm-shared-' + workflow.id );
            $el_wf_link.click( function() {
                return confirm( "Are you sure you want to delete workflow '" + workflow.name + "'?" );
            });
            $el_shared_wf_link.click( function() {
                return confirm( "Are you sure you want to remove the shared workflow '" + workflow.name + "'?" );
            });
        },

        /** Implement client side workflow search/filtering */
        search_workflow: function( $el_searchinput, $el_tabletr, min_querylen ) {
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
                        '<th>Name</th>' +
                        '<th>Tags</th>' +
                        '<th>Owner</th>' +
                        '<th># of Steps</th>' +
                        '<th>Published</th>' +
                        '<th>Show in tools panel</th>' +
                    '</tr></thead>';
            _.each( workflows, function( wf ) {
                var checkbox_html = '<input type="checkbox" class="show-in-tool-panel" '+ ( wf.show_in_tool_panel ? 'checked="' + wf.show_in_tool_panel + '"' : "" ) +' value="' + wf.id + '">';
                trHtml = trHtml + '<tr>' +
                             '<td>' +
                                 '<div class="dropdown">' +
                                     '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                         _.escape( wf.name ) + '<span class="caret"></span>' +
                                     '</button>' +
                                     self._templateActions( wf ) +
                                 '</div>' +
                              '</td>' +
                              '<td>' + '<div class="' + wf.id + ' tags-display"></div>' + '</td>' +
                              '<td>' + ( wf.owner === Galaxy.user.attributes.username ? "You" : wf.owner ) +'</td>' +
                              '<td>' + wf.number_of_steps + '</td>' +
                              '<td>' + ( wf.published ? "Yes" : "No" ) + '</td>' +
                              '<td>'+ checkbox_html +'</td>' +
                         '</tr>';
            });
            return tableHtml + '<tbody class="workflow-search">' + trHtml + '</tbody></table>';
        },

        /** Template for user actions for workflows */
        _templateActions: function( workflow ) {
            if( workflow.owner === Galaxy.user.attributes.username ) {
                return '<ul class="dropdown-menu action-dpd">' +
                           '<li><a href="'+ Galaxy.root +'workflow/editor?id='+ workflow.id +'">Edit</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/run?id='+ workflow.id +'">Run</a></li>' +
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
                         '<li><a href="'+ Galaxy.root +'workflow/run?id='+ workflow.id +'">Run</a></li>' +
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
                   '</div>';
        }
    });

    var ImportWorkflowView = Backbone.View.extend({

        initialize: function() {
            this.setElement( '<div/>' );
            this.render();
        },

        /** Open page to import workflow */
        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'workflow/upload_import_workflow', function( options ) {
                self.$el.empty().append( self._mainTemplate( options ) );
            });
        },

        /** Template for the import workflow page */
        _mainTemplate: function( options ) {
            return "<div class='toolForm'>" +
                       "<div class='toolFormTitle'>Import Galaxy workflow</div>" +
                        "<div class='toolFormBody'>" +
                            "<form name='import_workflow' id='import_workflow' action='"+ Galaxy.root + 'workflow/upload_import_workflow' +"' enctype='multipart/form-data' method='POST'>" +
                            "<div class='form-row'>" +
                                "<label>Galaxy workflow URL:</label>" + 
                                "<input type='text' name='url' class='input-url' value='"+ options.url +"' size='40'>" +
                                "<div class='toolParamHelp' style='clear: both;'>" +
                                    "If the workflow is accessible via a URL, enter the URL above and click <b>Import</b>." +
                                "</div>" +
                                "<div style='clear: both'></div>" +
                            "</div>" +
                            "<div class='form-row'>" +
                                "<label>Galaxy workflow file:</label>" +
                            "<div class='form-row-input'>" +
                                "<input type='file' name='file_data' class='input-file'/>" +
                            "</div>" +
                            "<div class='toolParamHelp' style='clear: both;'>" +
                                "If the workflow is in a file on your computer, choose it and then click <b>Import</b>." +
                            "</div>" +
                            "<div style='clear: both'></div>" +
                            "</div>" +
                            "<div class='form-row'>" +
                                "<input type='submit' class='primary-button wf-import' name='import_button' value='Import'>" +
                            "</div>" +
                            "</form>" +
                           "<hr/>" +
                           "<div class='form-row'>" +
                               "<label>Import a Galaxy workflow from myExperiment:</label>" +
                               "<div class='form-row-input'>" +
                                   "<a href='" + options.myexperiment_target_url + "'> Visit myExperiment</a>" +
                               "</div>" +
                               "<div class='toolParamHelp' style='clear: both;'>" +
                                   "Click the link above to visit myExperiment and browse for Galaxy workflows." +
                               "</div>" +
                               "<div style='clear: both'></div>" +
                           "</div>" +
                       "</div>" +
                   "</div>";
        },

    });

    return {
        View  : View,
        ImportWorkflowView : ImportWorkflowView
    };
});
