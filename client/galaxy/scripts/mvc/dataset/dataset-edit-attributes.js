
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
                    self.page.display( new Ui.Message( { 'message': 'Error occured', 'status': 'error',
                        'persistent': true, 'cls': 'errormessage' } ) );
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

            // Register submit events
            self.register_attr_events( self, response.dataset_id, $el_edit_attr );
        },

        /** Register submit button events */
        register_attr_events: function( self, dataset_id, $el_edit_attr ) {
            var post_url = Galaxy.root + 'dataset/edit';
            // Click event of Save attributes button
            $el_edit_attr.find( '.btn-submit-attributes' ).click( function( e ) {
                $el_edit_attr.find( '#formeditattr' ).submit( function( event ) {
                    event.preventDefault();
                    var fields = $( this ).serializeArray(),
                        post_obj = {},
                        repeated_fields = [];

                    _.each( fields, function( field ) {
                        if( !(field.name in post_obj) ) {
                            post_obj[ field.name ] = field.value;
                        }
                        else {
                            repeated_fields.push( field.name );
                        }
                    });

                    // To handle the case of multiple values of the fields
                    // having the same name
                    _.each( repeated_fields, function( rep_field ) {
                        var repeated_counter = 0;
                        post_obj[ rep_field ] = [];
                        _.each( fields, function( field ) {
                            if( field.name === rep_field ) {
                                post_obj[ rep_field ][ repeated_counter ] = field.value;
                                repeated_counter = repeated_counter + 1;
                            }
                        });
                    });

                    // Make dataset's name a mandatory field
                    if( post_obj.name === "" || post_obj.name === null || !post_obj.name ) {
                        self.display_message( self, { 'message': 'Please give a name to the dataset', 'status': 'error' }, $el_edit_attr );
                        return;
                    }
                    self.call_ajax( self, post_obj );
                });
            });

            // Click event for Auto-detect button
            $el_edit_attr.find( '.btn-auto-detect' ).click( function( e ) {
                e.preventDefault();
                self.call_ajax( self, { 'dataset_id': dataset_id, 'detect': 'Auto-detect' } );
            });
        },

        /** Perform AJAX post call */
        call_ajax: function( self, data, tab_name ) {
            var post_url = Galaxy.root + 'dataset/edit';
            $.ajax({
                type: "POST",
                url: post_url,
                data: data,
                success: function( response ) {
                    self.render_attribute_page( self, response );
                    self.tabs.showTab( tab_name );
                },
                error   : function( response ) {
                    self.page.display( new Ui.Message( { 'message': 'Error occured', 'status': 'error',
                        'persistent': true, 'cls': 'errormessage' } ) );
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
                $el     : $( self._attributesTabTemplate( self, response ) )
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
                title   : 'View Permissions',
                icon    : 'fa-user',
                tooltip : 'View permissions'
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

        /** Convert tab template */
        _getConvertFormTemplate: function( self, response ) {
            var form = new Form({
                title  : 'Convert to new format',
                inputs : response.convert_inputs,
                    operations: {
                        'submit': new Ui.ButtonIcon({
                            tooltip  : 'Convert the datatype to a new format',
                            title    : 'Convert',
                            onclick  : function() { self._submitConvert( self, form, response ) }
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
                        'submit': new Ui.ButtonIcon({
                            tooltip  : 'Convert the datatype to a new type',
                            title    : 'Save',
                            onclick  : function() { self._submitChangeDatatype( self, form, response ) }
                        })
                    }
                });
             return form.$el;

        },

        /** Convert format */
        _submitConvert: function( self, form, response ) {
            var form_data = form.data.create();
            if ( form_data.target_type !== null && form_data.target_type ) {
                form_data.dataset_id = response.dataset_id;
                form_data.convert_data = 'Convert';
                self.call_ajax( self, form_data, 'convert' );
            }
        },

        /** Change datatype */
        _submitChangeDatatype: function( self, form, response ) {
            var form_data = form.data.create();
            form_data.dataset_id = response.dataset_id;
            form_data.change = 'Save';
            self.call_ajax( self, form_data, 'datatype' );
        },

        /** Template for Attributes tab */
        _attributesTabTemplate: function( self, response ) {
            var template = "<div class='toolFormTitle'>Edit Attributes</div>" +
                               "<div class='toolFormBody'>" + 
                                   "<form name='edit_attributes' id='formeditattr'>" + 
                                       "<div class='form-row'>" +
                                           "<label>Name:</label>" +
                                           "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                               "<input type='text' name='name' value=" + response.display_name + " size='40'/>" +
                                               "<input type='hidden' name='dataset_id' value='" + response.dataset_id + "'>" +
                                               "<input type='hidden' name='save' value='Save'>" +
                                           "</div>" +
                                           "<div style='clear: both'></div>" +
                                       "</div>" +
                                       "<div class='form-row'>" +
                                           "<label>Info:</label>" +
                                           "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                               "<textarea name='info' cols='40' rows='2'>" + response.data_info + "</textarea>" +
                                           "</div>" +
                                           "<div style='clear: both'></div>" +
                                       "</div>";
            if( user ) {
                template = template + "<div class='form-row'>" +
                                           "<label>Annotation / Notes:</label>" +
                                           "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                               "<textarea name='annotation' cols='40' rows='2'>" +
                                                   ( response.data_annotation === null ? "" : response.data_annotation ) +
                                               "</textarea>" +
                                           "</div>" +
                                           "<div style='clear: both'></div>" +
                                           "<div class='toolParamHelp'>Add an annotation or notes to a dataset; annotations are available when a history is viewed.</div>" +
                                       "</div>";
            }

            _.each( response.data_metadata, function( item ) {
                if( item[ 1 ] ) {
                    template = template + "<div class='form-row'>" +
                                              "<label>" + item[ 2 ] + "</label>" +
                                              "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                                  response.metadata_html[ item[ 0 ] ] +
                                              "</div>" +
                                              "<div style='clear: both'></div>" +
                                          "</div>";
                }
            });
            template = template + "<div class='form-row'>" +
                                      "<input class='btn-submit-attributes' type='submit' name='save' value='Save'/>" +
                                  "</div>";
            template = template + "</form>";

            // Form for Auto-detect action
            template = template + "<form name='auto_detect'>" +
                                      "<div class='form-row'>" +
                                          "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                              "<input class='btn-auto-detect' type='submit' name='detect' value='Auto-detect' />" +
                                          "</div>" +
                                          "<div class='toolParamHelp' style='clear: both;'>This will inspect the dataset and attempt to correct the above column values if they are not accurate." +
                                          "</div>" +
                                      "</div>" +
                                  "</form>";
            if( response.data_missing_meta ) {
                template = template + "<div class='form-row'>" +
                                          "<div class='errormessagesmall'> Required metadata values are missing. Some of these values may not be editable by the user. Selecting 'Auto-detect' will attempt to fix these values. </div>" +
                                      "</div>";
            }
            template = template + "</div></div>";
            return template;
        }
    });

    return {
        View  : View
    };
});
