
define( [ 'utils/utils', 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/form/form-view' ], function( Utils, Tabs, Ui, Form ) {

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({

        initialize: function( dataset_id ) {
            this.setElement( '<div/>' );
            this.render( dataset_id );
        },

        // Fetch data for the selected dataset and 
        // build tabs for editing its attributes
        render: function( dataset_id ) {
            var url = Galaxy.root + 'dataset/edit',
                self = this;
            Utils.get({
                url     : url,
                data    : { 'dataset_id' : dataset_id },
                success : function( response ) {
                   self.render_attribute_page( self, response );
                },
                error   : function( response ) {
                    var error_response = { 'status': 'error',
                        'message': 'Error occured while loading the dataset.' };
                    self.display_message( self, error_response, self.$el.find( '.edit-attr' ) );
                }
            });
        },

        /** Render all the tabs view */
        render_attribute_page: function( self, response ) {
            var $el_edit_attr = null;
            self.$el.empty().append( self._templateHeader() );
            $el_edit_attr = self.$el.find( '.edit-attr' );
            self.display_message( self, response, $el_edit_attr );
            // Create all tabs
            self.create_tabs( self, response, $el_edit_attr );
        },

        /** Perform AJAX post call */
        call_ajax: function( self, data, tab_name ) {
            var post_url = Galaxy.root + 'dataset/edit';
            $.ajax({
                type: "PUT",
                url: post_url,
                data: data,
                success: function( response ) {
                    self.render_attribute_page( self, response );
                    self.reload_history();
                },
                error   : function( response ) {
                    var error_response = { 'status': 'error',
                        'message': 'Error occured while saving. Please fill all the required fields and try again.' };
                    self.display_message( self, error_response, self.$el.find( '.edit-attr' ) );
                }
            });
        },

        /** Display actions messages */
        display_message: function( self, response, $el ) {
            $el_message = $el.find( '.response-message' );
            // Remove all classes related to messages if present
            $el_message.removeClass( 'errormessage donemessage warningmessage' );
            if ( response.message && response.message !== null && response.message !== ""  ) {
                $el_message.addClass( response.status + 'message' );
                $el_message.html( '<p>' + _.escape( response.message ) + '</p>' );
            }
            else {
                $el_message.html("");
            }
        },

        /** Create tabs for different attributes of dataset*/
        create_tabs: function( self, response, $el_edit_attr ) {
            self.tabs = new Tabs.View();
            self.tabs.add({
                id      : 'attributes',
                title   : 'Attributes',
                icon    : 'fa fa-bars',
                tooltip : 'Edit dataset attributes',
                $el     : self._getAttributesFormTemplate( self, response )
            });

            self.tabs.add({
                id      : 'convert',
                title   : 'Convert',
                icon    : 'fa-gear',
                tooltip : 'Convert to new format',
                $el     :  self._getConvertFormTemplate( self, response )
            });

            self.tabs.add({
                id      : 'datatype',
                title   : 'Datatypes',
                icon    : 'fa-database',
                tooltip : 'Change data type',
                $el     : self._getChangeDataTypeFormTemplate( self, response )
            });

            self.tabs.add({
                id      : 'permissions',
                title   : 'Permissions',
                icon    : 'fa-user',
                tooltip : 'Permissions',
                $el     : self._getPermissionsFormTemplate( self, response )
            });
            $el_edit_attr.append( self.tabs.$el );
            self.tabs.showTab( 'attributes' );
        },

        /** Main template */
        _templateHeader: function() {
            return '<div class="page-container edit-attr">' +
                       '<div class="response-message"></div>' +
                       '<h3>Edit Dataset Attributes and Permissions</h3>' +
                   '</div>';
        },

        /** Attributes tab template */
        _getAttributesFormTemplate: function( self, response ) {
            var form = new Form({
                title  : 'Edit Attributes',
                inputs : response.edit_attributes_inputs,
                operations: {
                    'submit_editattr' : new Ui.ButtonIcon({
                        tooltip       : 'Save attributes of the dataset',
                        icon          : 'fa-floppy-o ',
                        title         : 'Save Attributes',
                        onclick       : function() { self._submit( self, form, response, "edit_attributes" ) }
                    }),
                    'submit_autocorrect' : new Ui.ButtonIcon({
                        tooltip          : 'This will inspect the dataset and attempt to correct the above column values if they are not accurate.',
                        icon             : 'fa-undo ',
                        title            : 'Auto-detect',
                        onclick          : function() { self._submit( self, form, response, "auto-detect" ) }
                    })
                }
            });
            return form.$el;
        },

        /** Convert tab template */
        _getConvertFormTemplate: function( self, response ) {
            var form = new Form({
                title  : 'Convert to new format',
                inputs : response.convert_inputs,
                operations: {
                        'submit' : new Ui.ButtonIcon({
                        tooltip  : 'Convert the datatype to a new format',
                        title    : 'Convert Datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( self, form, response, "convert" ) }
                    })
                }
            });
            return form.$el;
        },

        /** Change datatype template */
        _getChangeDataTypeFormTemplate: function( self, response ) {
            var form = new Form({
                title  : 'Change data type',
                inputs : response.convert_datatype_inputs,
                operations: {
                        'submit' : new Ui.ButtonIcon({
                        tooltip  : 'Change the datatype to a new type',
                        title    : 'Change Datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( self, form, response, "change" ) }
                    })
                }
            });
            return form.$el;
        },

        /** Permissions template */
        _getPermissionsFormTemplate: function( self, response ) {
            var template = "";
            if( response.can_manage_dataset ) {
                var form = new Form({
                    title  : 'Manage dataset permissions on ' + response.display_name,
                    inputs : response.permission_inputs,
                    operations: {
                        'submit': new Ui.ButtonIcon({
                            tooltip  : 'Save Permissions',
                            title    : 'Save Permissions',
                            icon     : 'fa-floppy-o ',
                            onclick  : function() { self._submit( self, form, response, "permissions" ) }
                        })
                    }
                });
                return form.$el;
            }
            else {
                var form = new Form({
                    title  : 'View Permissions',
                    inputs : response.permission_inputs
                });
                return form.$el;
            }
        },

        /** Submit action */
        _submit: function( self, form, response, type ) {
            var form_data = form.data.create();
            form_data.dataset_id = response.dataset_id;
            switch( type ) {
                case "edit_attributes":
                    form_data.save = 'Save';
                    break;

                case "auto-detect":
                    form_data.detect = 'Auto-detect';
                    break;
          
                case "convert":
                    if ( form_data.target_type !== null && form_data.target_type ) {
                        form_data.dataset_id = response.dataset_id;
                        form_data.convert_data = 'Convert';
                    }
                    break;

                case "change":
                    form_data.change = 'Save';
                    break;

                case "permissions":
                    var post_data = {};
                    post_data.permissions = JSON.stringify( form_data );
                    post_data.update_roles_button = "Save";
                    post_data.dataset_id = response.dataset_id;
                    form_data = post_data;
                    break; 
            }
            self.call_ajax( self, form_data );
        },

        /** Reload Galaxy's history after updating dataset's attributes */
        reload_history: function() {
            if ( window.Galaxy ) {
                window.Galaxy.currHistoryPanel.loadCurrentHistory();
            }
        }
    });

    return {
        View  : View
    };
});
