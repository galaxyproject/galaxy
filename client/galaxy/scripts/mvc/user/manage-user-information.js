/** Edits user information */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ManageUserInformation = Backbone.View.extend({
        initialize: function ( app, $el, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.original_email = options["email"];
            this.original_username = options["username"];
            this.loginform = new Form({
                title   : 'Login Information',
                inputs  : self._buildLoginInputs( self, options ),
                operations      : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.loginform.$el.remove();
                                               self.addressform.$el.remove(); 
                                               app.showPreferences() }
                    })
                },
                buttons        : {
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
            // address display form
            this.addressform = new Form({
                title   : 'User Addresses',
                inputs  : self._buildAddressInputs( self, options ),
                buttons        : {
                    'addaddress': new Ui.ButtonIcon({
                        id          : 'add-address',
                        type        : 'submit',
                        cls         : 'ui-button-icon',
                        tooltip     : 'Add new address',
                        title       : 'Add new address',
                        icon        : 'fa-plus',
                        floating: 'clear',
                        onclick     : function() { self._addAddress( self ) }
                    }) 
                }
            });
            $el.append( this.addressform.$el );
        },

        /** builds inputs for user login information form */
        _buildLoginInputs: function( self, data ) {
            var all_inputs = [],
                email = {},
                username = {};
            email = { id: 'email_input', name: 'email', type: 'text', label: 'Email address:', value: data["email"], size: "40",
                      help: 'If you change your email address you will receive an activation link in the new mailbox and you have to' + 
                            ' activate your account by visiting it.' };
            all_inputs.push( email );
            if(data['webapp'] === 'tool_shed') {
                if( data['active_repositories'] ) {
                    username = { id: 'name_input', name: 'username', label: 'Public name:', type: 'hidden', value: data["username"], 
                                 help: 'You cannot change your public name after you have created a repository in this tool shed.' };
                }
                else {
                    username = { id: 'name_input', name: 'username', label: 'Public name:', type: 'text', value: data["username"], size: "40",
                                 help: 'Your public name provides a means of identifying you publicly within this tool shed. Public ' +
                                       'names must be at least three characters in length and contain only lower-case letters, numbers, ' +
                                       'and the "-" character.  You cannot change your public name after you have created a repository ' +
                                       'in this tool shed.' };
                }
            }
            else {
                username = { id: 'name_input', name: 'username', label: 'Public name:', type: 'text', value: data["username"], size: "40",
                             help: 'Your public name is an identifier that will be used to generate addresses for information ' +
                                   'you share publicly. Public names must be at least three characters in length and contain only lower-case ' +
                                   'letters, numbers, and the "-" character.' };
            }
            all_inputs.push( username );
            return all_inputs;
        },

        /** builds inputs for displaying address */
        _buildAddressInputs: function( self, data ) {
            var all_inputs = [],
                labels = {};
            if( data["addresses"] || data["addresses"].length > 0 ) {
                labels = { id: 'address_labels', name: 'address_labels', label: 'Choose filter', type: 'select', display: 'radiobutton',
                           data: [ { label: 'Active', value: '0' }, { label: 'Deleted', value: '1' }, { label: 'All', value: '2' } ] };
                all_inputs.push( labels );
                
                for( var item in data["addresses"] ) {
                    var item_object = data["addresses"][item],
                        address_id = item_object['address_id'],
                        desc = item_object['desc'],
                        html = item_object['html'];
                    // anonymous function added to have closures
                    // i.e. to bind correct data to the delete, edit etc methods
                    ( function() {
                        var _self = this;
                        all_inputs.push( { id: this['address_id'], title: this['desc'] + ': ', type: 'label', help: '<br>' + this['html'] } );
                        if( !item_object['deleted'] ) {
                            all_inputs.push( { id: 'edit_' + this['address_id'], type: 'submit', title: 'Edit', tooltip: 'Edit', 
                                           onclick: function() { self._editAddress.call( _self ); }, 
                                           icon: 'fa-pencil-square-o' } );

                            all_inputs.push( { id: 'delete_' + this['address_id'], type: 'submit', title: 'Delete', tooltip: 'Delete',
                                           onclick: function() { self._deleteAddress.call( _self ); }, 
                                           icon: 'fa-remove' } );
                        }
                        else {
                            all_inputs.push( { id: 'undelete_' + this['address_id'], type: 'submit', title: 'Undelete', tooltip: 'Undelete',
                                           onclick: function() { self._undeleteAddress.call( _self ); }, icon: 'fa-reply' } );
                        }
                        // adds a horizontal line at the end of each address section
                        all_inputs.push( { id: '', title: '', type: 'label', help: '<hr class="docutils">' } )

                    } ).call( data["addresses"][item] );
                } 
            }
            return all_inputs;
        },

        /** edits the address */
        _editAddress: function() {
            //console.log('edit clicked');
            //console.log( this );
        },

        /** deletes the address */
        _deleteAddress: function() {
            //console.log('delete clicked');
            //console.log( this );
        },

        /** reverts the delete status */
        _undeleteAddress: function() {
            //console.log('undelete clicked');
            //console.log( this );
        },

        /** adds new address */
        _addAddress: function() {
            //console.log( "add address" );
        },

        /** renders message */
        _renderMessage: function( form, message, status ) {
            form.message.update({
                message     : message,
                status      : status
            });
        },

        /** validates email and username */
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

        /** saves login information */
        _saveEmailName: function( data, self ) {
            var url = Galaxy.root + 'api/user_preferences/edit_info',
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
            // client side validations
            if ( data["email"] !== email ) {
                if ( email.length > 255 ) { 
                    //self.renderError( error_text_email_long );
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
            // if values are changed and the form is valid
            if ( !nothing_changed && validForm ) {
                data = { 'email': email, 'username': name, 'button_name': 'login_info_button' };
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

