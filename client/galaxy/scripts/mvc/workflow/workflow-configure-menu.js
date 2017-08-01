/** Configure Workflow Menu View */
define( [], function() {
    var View = Backbone.View.extend({

        initialize: function( options ) {
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/workflows/menu/', function( response ) {
                var workflows = response.workflows,
                    ids_in_menu = response.ids_in_menu,
                    $el_config_worflow = null;

                // Add configure workflow header
                self.$el.empty().append( self._templateConfigWorkflowHeader() );
                $el_config_worflow = self.$el.find( '.configure-workflows' );
                $el_config_worflow.append( self._templateActionButtons() );
                if( workflows.length > 0 ) {
                    $el_config_worflow.append( self._templateConfigureWorkflow( self, workflows, ids_in_menu ) );
                    self.save_workflow_menu( self );
                    self.make_checked( self, ids_in_menu );
                    self.register_check_uncheck_all( self );
                }
                else {
                    $el_config_worflow.append( self._templateNoWorkflow() );
                }
            });
        },

        /** Register check and uncheck all callbacks*/
        register_check_uncheck_all: function( self ) {
            var $el_check_all = self.$el.find( '.check-all-wf' ),
                $el_uncheck_all = self.$el.find( '.uncheck-all-wf' );
            
            $el_check_all.click(function( e ) {
                self.check_uncheck_all( self, true );
            });
            $el_uncheck_all.click(function( e ) {
                self.check_uncheck_all( self, false );
            });
        },

        /** Check or uncheck all workflows */
        check_uncheck_all: function( self, checked ) {
            $.each(self.$el.find( '.wf-config-item' ), function() {
                var wf_checkbox = $( this )[0];
                wf_checkbox.checked = checked;
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
                    url: Galaxy.root + 'api/workflows/menu/',
                    data: JSON.stringify( { 'workflow_ids': ids } ),
                    contentType : 'application/json'
                }).done( function( response ) {
                    window.location = Galaxy.root + 'user';
                });
            });
        },

        /** Template for actions buttons */
        _templateActionButtons: function() {
           return '<ul class="manage-table-actions">' +
                '<li>' +
                    '<a class="fa fa-check-square-o wf-action check-all-wf" title="Select all workflows" href="#">' +
                    '</a>' +
                '</li>' +
                '<li>' +
                    '<a class="fa fa-square-o wf-action uncheck-all-wf" title="Unselect all workflows" href="#">' +
                    '</a>' +
                '</li>' +
            '</ul>';
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
            tableHtml = tableHtml + '<a class="action-button wf-save-menu wf-action fa fa-floppy-o" href="#" title="Save">' +
                                        '<span>Save</span>' +
                                    '</a>' +
                                    '<a class="action-button wf-back wf-action fa fa-arrow-left" href="'+ Galaxy.root +'user" title="Back to User Preferences">' +
                                        '<span>Back to User Preferences</span>' +
                                    '</a>';
            return tableHtml;
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
        View : View
    };
});
