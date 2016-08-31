/** Edits user information */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ManageUserInformation = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.original_email = options["email"],
            this.original_username = options["username"],
            this.userform = new Form({
                title   : 'Login Information',
                name    : "login_info",
                id      : "login_info",
                inputs  : self._buildLoginInputs( options ),
                operations      : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); app.showPreferences() }
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
            this.setElement( this.userform.$el );
        },

        /** builds inputs for user login information form */
        _buildLoginInputs: function( data ) {
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

        /** renders message */
        _renderMessage: function( self, message, status ) {
            self.userform.message.update({
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
                formdata = self.userform.data.create(),
                email = formdata["email"],
                name = formdata["username"],
                validForm = true,
                nothing_changed = ( data["email"] === email && data["username"] === name );

            // client side validations
            if ( data["email"] !== email ) {
                if ( email.length > 255 ) { 
                    //self.renderError( error_text_email_long );
                    self._renderMessage( self, error_text_email_long, 'danger' );
                    validForm = false;
                }
                else if ( !self._validateString( email, "email" ) ) {
                    self._renderMessage( self, error_text_email, 'danger' );
                    validForm = false;
                }
            }
            if ( data["username"] !== name ) {
                if ( name && !( self._validateString( name, "username" ) ) || name.length < 3 ) { 
                    self._renderMessage( self, error_text_username_characters, 'danger' );
                    validForm = false;
                }
            }
            if ( nothing_changed ) {
                self._renderMessage( self, "Nothing has changed.", 'success' );
                return;
            }
            // if values are changed and the form is valid
            if ( !nothing_changed && validForm ) {
                data = { 'email': email, 'username': name, 'button_name': 'login_info_button' };
                $.getJSON( url, data, function( response ) {
                    // renders the user info again with the messages and updated data
                    self.original_email = email;
                    self.original_username = name;
                    self.userform.message.update({
                        message     : response.message,
                        status      : response.status === 'error' ? 'danger' : 'success',
                    });
                }, 'json');
            }
        }
    });

    return {
        ManageUserInformation: ManageUserInformation
    };
});

