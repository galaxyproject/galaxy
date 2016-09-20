/** Show and edit user information */
define( [ 'mvc/form/form-view',
          'mvc/ui/ui-misc',
          'mvc/user/add-edit-address' ],
function( Form, Ui, Address ) {
    var ManageUserInformation = Backbone.View.extend({
        initialize: function ( app, $el, options, address_message ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.original_email = options["email"];
            this.original_username = options["username"];
            this.loginform = new Form({
                title   : 'Login Information',
                inputs  : options["user_login_form"],
                operations : {
                    'back' : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() {
                            self.loginform.$el.remove();
                            self.addressform.$el.remove(); 
                            app.showPreferences();
                        }
                    })
                },
                buttons : {
                    'save'  : new Ui.Button({
                        tooltip : 'Save',
                        title   : 'Save',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._saveEmailName( options, self ) }
                    })
                }
            });
            $el.append( this.loginform.$el );
            // Address display form
            this.addressform = self._buildAddressForm( self, options, app, $el );
            $el.append( self.addressform.$el );
            // Show message if an address is added or updated
            if( address_message ) {
                self.addressform.message.update({
                    message : address_message.message,
                    status  : address_message.status === 'error' ? 'danger' : 'success',
                });
            }
        },

        /** Build form for user addresses */
        _buildAddressForm: function( self, options, app, $el ) {
            return new Form({
                title   : 'User Addresses',
                inputs  : options['user_address_list'],
                buttons : {
                    'addaddress': new Ui.ButtonIcon({
                        id          : 'add-address',
                        type        : 'submit',
                        cls         : 'ui-button-icon',
                        tooltip     : 'Add new address',
                        title       : 'Add new address',
                        icon        : 'fa-plus',
                        floating    : 'clear',
                        onclick     : function() { self._addAddress( self, $el, app ); }
                    })
                },
                onchange: function() {
                    self._addressOperations( app, $el, self );
                }
            });
        },

        // Find the right operation on address id
        _addressOperations: function( app, $el, self ) {
            var changed_collection = self.addressform.data.create(),
                operation_type = "",
                id = "",
                eachitem = null;
            // Find the first non-null item
            for( var item in changed_collection ) {
                eachitem = changed_collection[item];
                if( eachitem !== null ) {
                    operation_type = eachitem.split("_")[0],
                    address_id = eachitem.split("_")[1];
                    break;
                }
            }
            // Apply the right operation using the address id
            switch ( operation_type ) {
                case 'edit':
                    self._editAddress( self, $el, app, address_id );
                    break;
                case 'delete':
                    self._deleteAddress( self, $el, app, address_id );
                    break;
                case 'undelete':
                    self._undeleteAddress( self, $el, app, address_id );
                    break;
            }
        },        

        /** Apply address filter */
        _applyAddressFilter: function( app, $el, self ) {
            var field = null,
                active_filter = "";
            active_filter = self.addressform.data.create()["address_filters"];
            // Fetch the addresses based on the selected filter
            $.getJSON( Galaxy.root + 'api/user_preferences/manage_user_info/', { 'show_filter': active_filter }, function( response ) {
                self._updateAddressForm( app, $el, self, response );
                // Get and set the active filter's value
                field = self.addressform.field_list[ self.addressform.data.match( 'address_filters' ) ];
                field.value( active_filter );
            });
        },

        /** Update address form with new data */
        _updateAddressForm: function( app, $el, self, response ) {
            self.addressform.$el.remove();
            self.addressform = self._buildAddressForm( self, response, app, $el );
            $el.append( self.addressform.$el );
        },

        /** Edit address */
        _editAddress: function( self, $el, app, address_id ) {
            self.loginform.$el.remove();
            self.addressform.$el.remove();
            $.getJSON( Galaxy.root + 'api/user_preferences/manage_user_info/', {'address_id': address_id, 'call': 'edit_address' }, function( response ) {
                 address = new Address.AddEditAddress( $el, app, response );
            });
        },

        /** Delete address */
        _deleteAddress: function( self, $el, app, address_id ) {
            var active_filter = self.addressform.data.create()["address_filters"];
            $.getJSON( Galaxy.root + 'api/user_preferences/manage_user_info/',{ 'address_id': address_id, 'call': 'delete_address'}, function( response ) {
                self._updateAddressForm( app, $el, self, response );
                self.addressform.message.update({
                    message : response.message,
                    status  : response.status === 'error' ? 'danger' : 'success',
                });
            });
        },

        /** Revert the delete status */
        _undeleteAddress: function( self, $el, app, address_id ) {
            $.getJSON( Galaxy.root + 'api/user_preferences/manage_user_info/', { 'address_id': address_id, 'call': 'undelete_address' }, function( response ) {
                self._updateAddressForm( app, $el, self, response );
                self.addressform.message.update({
                    message : response.message,
                    status  : response.status === 'error' ? 'danger' : 'success',
                });
            });
        },

        /** Add new address */
        _addAddress: function( self, $el, app ) {
            var address;
            self.loginform.$el.remove();
            self.addressform.$el.remove();
            address = new Address.AddEditAddress( $el, app );
        },

        /** Render message */
        _renderMessage: function( form, message, status ) {
            form.message.update({
                message     : message,
                status      : status
            });
        },

        /** Validate email and username */
        _validateString: function( test_string, type ) {
            var mail_re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/,
                username_re = /^[a-z0-9\-]{3,255}$/;
            if ( type === 'email' ) {
                return mail_re.test(test_string);
            }
            else if ( type === 'username' ) {
                return username_re.test(test_string);
            }
        },

        /** Save login information */
        _saveEmailName: function( data, self ) {
            var url = Galaxy.root +  'api/user_preferences/manage_user_info',
                data = {}, 
                error_text_email= 'Please enter your valid email address.',
                error_text_email_long= 'Email cannot be more than 255 characters in length.', 
                error_text_username_characters = 'Public name must contain only lowercase letters, numbers and "-". ' + 
                                                 'It also has to be shorter than 255 characters but longer than 2.',
                formdata = self.loginform.data.create(),
                email = formdata[ "email" ],
                name = formdata[ "username" ],
                validForm = true,
                nothing_changed = ( data["email"] === email && data["username"] === name );
            // Client side validations
            if ( data["email"] !== email ) {
                if ( email.length > 255 ) { 
                    self._renderMessage( self.loginform, error_text_email_long, 'danger' );
                    validForm = false;
                }
                else if ( !self._validateString( email, "email" ) ) {
                    self._renderMessage( self.loginform, error_text_email, 'danger' );
                    validForm = false;
                }
            }
            if ( data["username"] !== name ) {
                if ( name && !( self._validateString( name, "username" ) ) || name.length < 3 ) { 
                    self._renderMessage( self.loginform, error_text_username_characters, 'danger' );
                    validForm = false;
                }
            }
            if ( nothing_changed ) {
                self._renderMessage( self.loginform, "Nothing has changed.", 'success' );
                return;
            }
            // If values are changed and the form is valid
            if ( !nothing_changed && validForm ) {
                data = { 'email': email, 'username': name, 'save_type': 'login_info', 'call': 'edit_info' };
                $.getJSON( url, data, function( response ) {
                    // renders the user info again with the messages and updated data
                    self.original_email = email;
                    self.original_username = name;
                    self.loginform.message.update({
                        message     : response.message,
                        status      : response.status === 'error' ? 'danger' : 'success',
                    });
                }, 'json');
            }
        },

        _saveUserType: function() {
            //console.log("user type");
        }
     
    });

    return {
        ManageUserInformation: ManageUserInformation
    };
});

