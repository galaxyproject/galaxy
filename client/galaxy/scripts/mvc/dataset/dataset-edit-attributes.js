
define( [ 'utils/utils', 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc' ], function( Utils, Tabs, Ui ) {

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
                    self.page.display( new Ui.Message( { 'message': 'Error occured', 'status': 'error', 'persistent': true, 'cls': 'errormessage' } ) );
                }
            });
        },

        /** Render the attributes tab view */
        render_attribute_page: function( self, response ) {
            var $el_edit_attr = null;
            self.$el.empty().append( self._templateHeader() );
            $el_edit_attr = self.$el.find( '.edit-attr' );
            self.build_messages( self, response, $el_edit_attr );
            // Create all tabs
            self.create_tabs( self, response, $el_edit_attr );
            // Register submit events
            self.register_events( self, response.dataset_id, $el_edit_attr );
        },

        convert_to_object: function( collection ) {
            var post_object = {};
            for(var counter = 0; counter < collection.length; counter++) {
                var name = collection[ counter ].name,
                    value = collection[ counter ].value;   
                post_object[ name ] = value;
            }
            return post_object;
        },

        /** Register submit button events */
        register_events: function( self, dataset_id, $el_edit_attr ) {
            var post_url = Galaxy.root + 'dataset/edit';
            $el_edit_attr.find( '.btn-submit-attributes' ).click( function( e ) {
                e.preventDefault();
                var post_data = $el_edit_attr.find( "form[name='edit_attributes']" ).serializeArray();
                self.call_ajax( self, post_url, self.convert_to_object( post_data ) );
            });

            $el_edit_attr.find( '.btn-auto-detect' ).click( function( e ) {
                e.preventDefault();
                self.call_ajax( self, post_url, { 'dataset_id': dataset_id, 'detect': 'Auto-detect' } );
            });
        },

        /** Perform AJAX post call */
        call_ajax: function( self, url, data ) {
            $.ajax({
                type: "POST",
                url: url,
                data: data,
                success: function( response ) {
                    self.render_attribute_page( self, response );
                }
            });
        },

        // Display actions messages
        build_messages: function( self, response, $el ) {
            var message = "",
                options = {};
            // If the api call does not exist
            if ( !response.message ) {
                options = { 'message': response, 'status': 'error', 'persistent': true, 'cls': 'errormessage' };
            }
            else {
                options = { 'message': response.message, 'status': response.status, 'persistent': true, 'cls': response.status+'message' };
            }
            $el.append( new Ui.Message( options ) );
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
                tooltip : 'Convert to new format'
            });

            self.tabs.add({
                id      : 'datatype',
                title   : 'Datatypes',
                icon    : 'fa-database',
                tooltip : 'Change data type'
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
            return '<div class="page-container edit-attr"></div>';
        },

        /** Template for Attributes tab */
        _attributesTabTemplate: function( self, response ) {
            var template = "<div class='toolFormTitle'>Edit Attributes</div>" +
                               "<div class='toolFormBody'>" + 
                                   "<form name='edit_attributes'>" + 
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

            for( var counter = 0; counter < response.data_metadata.length; counter++ ) {
                var metadata = response.data_metadata[ counter ];
                if( metadata[ 1 ] ) {
                    template = template + "<div class='form-row'>" +
                                              "<label>" + metadata[ 2 ] + "</label>" +
                                              "<div style='float: left; width: 250px; margin-right: 10px;'>" +
                                                  response.metadata_html[ metadata[ 0 ] ] +
                                              "</div>" +
                                              "<div style='clear: both'></div>" +
                                          "</div>";
                }
            }

            template = template + "<div class='form-row'>" +
                                      "<input class='btn-submit-attributes' type='submit' name='save' value='Save'/>" +
                                  "</div>";
            template = template + "</form>";

            // Auto-detect action
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
