/** Workflow view */
define( [ "libs/toastr", "mvc/tag", "mvc/workflow/workflow-model", "utils/query-string-parsing" ], function( mod_toastr, TAGS, WORKFLOWS, QueryStringParsing ) {

    /** View of the individual workflows */
    var WorkflowItemView = Backbone.View.extend({
        tagName: 'tr', // name of (orphan) root tag in this.el
        initialize: function(){
            _.bindAll(this, 'render', '_rowTemplate', 'renderTagEditor', '_templateActions', 'removeWorkflow', 'copyWorkflow'); // every function that uses 'this' as the current object should be in here
            mod_toastr.options.timeOut = 1500;
        },

        events: {
            'click #show-in-tool-panel': 'showInToolPanel',
            'click #delete-workflow'   : 'removeWorkflow',
            'click #rename-workflow'   : 'renameWorkflow',
            'click #copy-workflow'     : 'copyWorkflow',
        },

        render: function(){
            $(this.el).html(this._rowTemplate());
            return this;
        },

        showInToolPanel: function(){
            this.model.set('show_in_tool_panel', !this.model.get('show_in_tool_panel'));
            this.model.save();
            // This reloads the whole page, so that the workflow appears in the tool panel.
            // Ideally we would notify only the tool panel of a change
            window.location = Galaxy.root + 'workflow';
        },

        removeWorkflow: function(){
            var wfName = this.model.get('name');
            if (window.confirm( "Are you sure you want to delete workflow '" + wfName + "'?" )) {
                this.model.destroy({
                    success: function() {
                        mod_toastr.success("Successfully deleted workflow '" + wfName + "'");
                        }
                });
                this.remove();
            }
        },

        renameWorkflow: function(){
            var oldName = this.model.get('name');
            var newName = window.prompt("Enter a new Name for workflow '" + oldName + "'", oldName );
            if (newName) {
                this.model.save(
                    { 'name': newName },
                    { success: function() {
                        mod_toastr.success("Successfully renamed workflow '" + oldName + "' to '" + newName + "'");
                    }
                });
                this.render();
            }
        },

        copyWorkflow: function(){
            var self = this;
            var oldName = this.model.get('name');
            $.getJSON(this.model.urlRoot + '/' + this.model.id + '/download', function(wfJson) {
                var newName = 'Copy of ' + oldName;
                var currentOwner = self.model.get('owner');
                if (currentOwner != Galaxy.user.attributes.username) {
                    newName += ' shared by user ' + currentOwner;
                }
                wfJson.name = newName;
                self.collection.create(wfJson, { at: 0,
                                                 wait: true,
                                                 success: function() {
                                                     mod_toastr.success("Successfully copied workflow '" + oldName + "' to '" + newName + "'");
                                                 },
                                                 error : function(model, resp, options) {
                                                     // signature seems to have changed over the course of backbone dev
                                                     // see https://github.com/jashkenas/backbone/issues/2606#issuecomment-19289483
                                                     mod_toastr.error(options.errorThrown);
                                                 }
                });
            }).error(function(jqXHR, textStatus, errorThrown) {
                  mod_toastr.error(jqXHR.responseJSON.err_msg);
            });
        },

        _rowTemplate: function() {
            var show = this.model.get("show_in_tool_panel");
            var wfId = this.model.id;
            var checkboxHtml = '<input id="show-in-tool-panel" type="checkbox" class="show-in-tool-panel" '+ ( show ? 'checked="' + show + '"' : "" ) +' value="' + wfId + '">';
            var trHtml =  '<td>' +
                             '<div class="dropdown">' +
                                 '<button class="menubutton" type="button" data-toggle="dropdown">' +
                                     _.escape( this.model.get("name") ) + '<span class="caret"></span>' +
                                 '</button>' +
                                 this._templateActions( ) +
                             '</div>' +
                          '</td>' +
                          '<td><span>' + '<div class="' + wfId + ' tags-display"></div>' + '</td>' +
                          '<td>' + ( this.model.get('owner') === Galaxy.user.attributes.username ? "You" : this.model.get('owner') ) +'</span></td>' +
                          '<td>' + this.model.get("number_of_steps") + '</td>' +
                          '<td>' + ( this.model.get("published") ? "Yes" : "No" ) + '</td>' +
                          '<td>'+ checkboxHtml + '</td>';
            return trHtml;
        },

        renderTagEditor: function(){
            var TagEditor = new TAGS.TagsEditor({
            model           : this.model,
            el              : $.find( '.' + this.model.id + '.tags-display' ),
            workflow_mode   : true });
            TagEditor.toggle( true );
            TagEditor.render();
        },

        /** Template for user actions for workflows */
        _templateActions: function( ) {
            if( this.model.get("owner") === Galaxy.user.attributes.username ) {
                return '<ul class="dropdown-menu action-dpd">' +
                           '<li><a href="'+ Galaxy.root +'workflow/editor?id='+ this.model.id +'">Edit</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/run?id='+ this.model.id +'">Run</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/sharing?id='+ this.model.id +'">Share</a></li>' +
                           '<li><a href="'+ Galaxy.root +'api/workflows/'+ this.model.id +'/download?format=json-download">Download</a></li>' +
                           '<li><a id="copy-workflow" style="cursor: pointer;">Copy</a></li>' +
                           '<li><a id="rename-workflow" style="cursor: pointer;">Rename</a></li>' +
                           '<li><a href="'+ Galaxy.root +'workflow/display_by_id?id='+ this.model.id +'">View</a></li>' +
                           '<li><a id="delete-workflow" style="cursor: pointer;">Delete</a></li>' +
                      '</ul>';
            }
            else {
                return '<ul class="dropdown-menu action-dpd">' +
                         '<li><a href="'+ Galaxy.root +'workflow/display_by_username_and_slug?username='+ this.model.get("owner") +'&slug='+ this.model.get("slug") +'">View</a></li>' +
                         '<li><a href="'+ Galaxy.root +'workflow/run?id='+ this.model.id +'">Run</a></li>' +
                         '<li><a id="copy-workflow" style="cursor: pointer;">Copy</a></li>' +
                         '<li><a class="link-confirm-shared-'+ this.model.id +'" href="'+ Galaxy.root +'workflow/sharing?unshare_me=True&id='+ this.model.id +'">Remove</a></li>' +
                      '</ul>';
            }
        },
    });

    /** View of the main workflow list page */
    var WorkflowListView = Backbone.View.extend({
        title: "Workflows",
        initialize: function() {
            this.setElement( '<div/>' );
            _.bindAll(this, 'adjustActiondropdown');
            this.collection = new WORKFLOWS.WorkflowCollection();
            this.collection.fetch().done(this.render());
            this.collection.bind('add', this.appendItem);
            this.collection.on('sync', this.render, this);
        },

        events: {
            'dragleave' : 'unhighlightDropZone',
            'drop' : 'drop',
            'dragover': function(ev) {
                $( '.hidden_description_layer' ).addClass( 'dragover' );
                $('.menubutton').addClass('background-none');
                ev.preventDefault();
            }
        },

        unhighlightDropZone: function() {
            $( '.hidden_description_layer' ).removeClass( 'dragover' );
            $('.menubutton').removeClass('background-none');
        },

        drop: function(e) {
            // TODO: check that file is valid galaxy workflow
            this.unhighlightDropZone();
            e.preventDefault();
            var files = e.dataTransfer.files;
            var self = this;
            for (var i = 0, f; f = files[i]; i++) {
                self.readWorkflowFiles(f);
            }
        },

        readWorkflowFiles: function(f) {
                var self = this;
                var reader = new FileReader();
                reader.onload = function(theFile) {
                    var wf_json;
                    try {
                        wf_json = JSON.parse(reader.result);
                    } catch(e) {
                        mod_toastr.error("Could not read file '" + f.name + "'. Verify it is a valid Galaxy workflow");
                        wf_json = null;
                    }
                    if (wf_json) {
                        self.collection.create(wf_json, {
                            at: 0,
                            wait: true,
                            success: function() {
                                mod_toastr.success("Successfully imported workflow '" + wf_json.name + "'");
                            },
                            error : function(model, resp, options) {
                                mod_toastr.error(options.errorThrown);
                            }
                        });
                    }
                };
                reader.readAsText(f, 'utf-8');
            },

        _showArgErrors: _.once(function(){
            // Parse args out of params, display if there's a message.
            var msg_text = QueryStringParsing.get('message');
            var msg_status = QueryStringParsing.get('status');
            if (msg_status === "error"){
                mod_toastr.error(_.escape(msg_text || "Unknown Error, please report this to an administrator."));
            } else if (msg_text){
                mod_toastr.info(_.escape(msg_text));
            }
        }),

        render: function() {
            // Add workflow header
            var header = this._templateHeader();
            // Add the actions buttons
            var templateActions = this._templateActionButtons();
            var tableTemplate = this._templateWorkflowTable();
            this.$el.html( header + templateActions + tableTemplate);
            var self = this;
            _(this.collection.models).each(function(item){ // in case collection is not empty
                self.appendItem(item);
                self.confirmDelete(item);
            }, this);
            var minQueryLength = 3;
            this.searchWorkflow( this.$( '.search-wf' ), this.$( '.workflow-search tr' ), minQueryLength );
            this.adjustActiondropdown();
            this._showArgErrors();
            return this;
        },

        appendItem: function(item){
            var workflowItemView = new WorkflowItemView({
                model: item,
                collection: this.collection,
            });
            $( '.workflow-search' ).append(workflowItemView.render().el);
            workflowItemView.renderTagEditor();
        },

        /** Add confirm box before removing/unsharing workflow */
        confirmDelete: function( workflow ) {
            var $el_shared_wf_link = this.$( '.link-confirm-shared-' + workflow.id );
            $el_shared_wf_link.click( function() {
                return window.confirm( "Are you sure you want to remove the shared workflow '" + workflow.attributes.name + "'?" );
            });
        },

        /** Implement client side workflow search/filtering */
        searchWorkflow: function( $el_searchinput, $el_tabletr, min_querylen ) {
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
        adjustActiondropdown: function( ) {
            $(this.el).on( 'show.bs.dropdown', function () {
                $(this.el).css( "overflow", "inherit" );
            });
            $(this.el).on( 'hide.bs.dropdown', function () {
                $(this.el).css( "overflow", "auto" );
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
        _templateWorkflowTable: function( ) {
            var tableHtml = '<table class="table colored"><thead>' +
                    '<tr class="header">' +
                        '<th>Name</th>' +
                        '<th>Tags</th>' +
                        '<th>Owner</th>' +
                        '<th># of Steps</th>' +
                        '<th>Published</th>' +
                        '<th>Show in tools panel</th>' +
                    '</tr></thead>';
            return tableHtml + '<tbody class="workflow-search "><div class="hidden_description_layer"><p>Drop workflow files here to import</p>' + '</tbody></table></div>';
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
        View  : WorkflowListView,
        ImportWorkflowView : ImportWorkflowView
    };
});
