/** Manage User Information view under User Preferences */
define([], function() {

var ManageUserInformation = Backbone.View.extend({

    original_email: "",
    original_username: "",
    user_id: "",

    initialize: function ( data ) {
        $(".manage-userinfo-section").remove();
        this.render( this, data );
        this.user_id = data["user_id"];
        this.original_email = data["email"];
        this.original_username = data["username"];
    },

    /** validates email and username */
    validateString: function( test_string, type ) {
        var mail_re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        var username_re = /^[a-z0-9\-]{3,255}$/;
        if ( type === 'email' ) {
            return mail_re.test(test_string);
        }
        else if ( type === 'username' ) {
            return username_re.test(test_string);
        }
    },

    /** renders the error message */
    renderError: function( message ) {
        $(".donemessage").hide();
        if ($(".validate.errormessage").length === 1) {
            $(".validate.errormessage").html(message);
            $(".validate.errormessage").show();
        } else {
            $('.user-preferences-all').prepend("<div class='validate errormessage'>" + message + "</div>");            
        }
    },
 
    /** renders the done message when nothing is changed */
    renderDone: function( message ) {
        $(".validate.errormessage").hide();
        if ($(".donemessage").length === 1) {
            $(".donemessage").html(message);
            $(".donemessage").show();
        } 
        else {
            $('.user-preferences-all').prepend("<div class='donemessage'>" + message + "</div>");
        }
    },

    /** validates the input values and save the data */
    saveUserData: function( self, e ) {
        var error_text_email= 'Please enter your valid email address.',
            error_text_email_long= 'Email cannot be more than 255 characters in length.', 
            error_text_username_characters = 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 2.', 
            email = $( '#email_input' ).val(),
            name = $( '#name_input' ).val(), 
            validForm = true,
            nothing_changed = ( self.original_email === email && self.original_username === name ), 
            hidden_input = '<input type="hidden" id="login_info_button" name="login_info_button" value="Submit"/>',
            url = ""; 

        // we need this value to detect submitting at backend
        $( '#send' ).attr( 'disabled', 'disabled' );
        $( "#email_input" ).before( hidden_input );
        if ( self.original_email !== email ) {
            if ( email.length > 255 ) { 
                self.renderError( error_text_email_long ); 
                validForm = false; 
            }
            else if ( !self.validateString( email, "email" ) ) { 
                self.renderError( error_text_email ); 
                validForm = false; 
            }
        }
        if ( self.original_username !== name ) {
            if ( name && !( self.validateString( name, "username" ) ) ) { 
                self.renderError( error_text_username_characters );
                validForm = false;
            }
        }
        if ( nothing_changed ) {
            self.renderDone( "Nothing has changed." );
        }
        if ( !validForm  || nothing_changed ) {
            e.preventDefault();
            // reactivate the button if the form wasn't submitted
            $( '#send' ).removeAttr( 'disabled' );
        }
        // if values are changed and the form is valid
        if ( !nothing_changed && validForm ) {
            url = Galaxy.root + 'api/user_preferences/edit_info/';
            data = { 'user_id': self.user_id, 'email': email, 'username': name, 'button_name': e.target.attributes['name'].nodeValue };
            $.getJSON( url, data, function( response ) {
                // renders the user info again with the messages and updated data
                $(".manage-userinfo-section").remove();
                $(".donemessage").remove();
                $(".validate.errormessage").remove();
                self.render( self, response );
            }, 'json');
        }
    },

    /** renders the error message when manage user info page is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ (status === "error" ? " validate" : "") + '">'+ msg +'</div>';
    },

    /** renders manage user information */
    render: function( self, data ) {
        var template = "",
            filters = ['Active', 'Deleted', 'All'];

        if( data["message"].length > 0 ) {
            template = self.renderMessage( data["message"], data['status'] );
        }
        
        template = template + '<div class="manage-userinfo-section"> <h2>Manage User Information</h2>';
        if( !Galaxy.user.attributes.is_admin ) {
            template = template + '<ul class="manage-table-actions">' +
                       '<li>' +
                           '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';
        }
        
        template = template + '<div class="toolForm">' +
                   '<form name="login_info" id="login_info">' +
                       '<div class="toolFormTitle">Login Information</div>' + 
                       '<div class="form-row">' + 
                           '<label>Email address:</label>' + 
                           '<input type="text" id ="email_input" name="email" value="'+ data["email"] +'" size="40"/>' + 
                           '<div class="toolParamHelp" style="clear: both;">' + 
                               'If you change your email address you will receive an activation link in the new mailbox and you have to ' + 
                               'activate your account by visiting it.' +
                           '</div>' +
                       '</div>' + 
                       '<div class="form-row">' +
                           '<label>Public name:</label>';

        if(data['webapp'] === 'tool_shed' ) {
            if( data['active_repositories'] ) {
                template = template + '<input type="hidden" id="name_input" name="username" value="' + data['username'] + '"/>' +
                           data['username'] + 
                           '<div class="toolParamHelp" style="clear: both;">' +
                               'You cannot change your public name after you have created a repository in this tool shed.' +
                           '</div>';
            }
            else {
                template = template + '<input type="text" id="name_input" name="username" size="40" value="'+ data['username'] +'"/>' +
                           '<div class="toolParamHelp" style="clear: both;">' +
                               'Your public name provides a means of identifying you publicly within this tool shed. Public ' +
                               'names must be at least three characters in length and contain only lower-case letters, numbers, ' +
                               'and the "-" character.  You cannot change your public name after you have created a repository ' +
                               'in this tool shed.' +
                            '</div>';
            }
        }
        else {
            template = template + '<input type="text" id="name_input" name="username" size="40" value="' + data['username'] + '"/>' +
                       '<div class="toolParamHelp" style="clear: both;">' +
                           'Your public name is an identifier that will be used to generate addresses for information ' +
                           'you share publicly. Public names must be at least three characters in length and contain only lower-case ' +
                           'letters, numbers, and the "-" character.' +
                       '</div>';
        }
        template = template + '</div>';           
        template = template + 
                   '<div class="form-row">' +
                       '<input type="button" class="save-userdata action-button" name="login_info_button" value="Save"/>' +
                   '</div>' +
                   '</form>' +
                   '</div>';

        if( data['values'] || data['user_info_forms'].length > 0 ) {
            template = template + '<p></p>' + 
                       '<div class="toolForm">' +
                           '<form name="user_info" id="user_info">' + 
                               '<div class="toolFormTitle">User information</div>';
            if( data["user_type_fd_id_select_field_options"].length > 0 ) {
                template = template + '<div class="form-row">' +
                           '<label>User type:</label>' +
                               data['user_type_fd_id_select_html'] +
                           '</div>';
            }
            else {
                template = template + '<input type="hidden" name="user_type_fd_id" value="' + data["user_type_fd_id_encoded"] + '"/>';
            }
            // build markup for all the widgets
            if( typeof data["widgets"] === "object" && Object.keys(data["widgets"]).length > 0 ) {

                for( var item in data["widgets"] ) { 
                    var item_object = data["widgets"][item];
                    template = template + '<div class="form-row">' +
                           '<label>'+ item_object['label'] + ':</label>' +
                           item_object['html'] +
                           '<div class="toolParamHelp" style="clear: both;">' +
                           item_object['helptext'] +
                           '</div>' +
                           '<div style="clear: both"></div>' +
                           '</div>';
                }
            }
            template = template + '<div class="form-row">' +
                           '<input type="submit" class="save-userdata action-button" name="edit_user_info_button" value="Save"/>' +
                       '</div>';
            template = template + '</form></div><p></p>';
        }
        // markup for user addresses
        template = template + '<div class="toolForm">' +
                   '<form name="user_addresses" id="user_addresses">' + 
                       '<div class="toolFormTitle">User Addresses</div>' +
                           '<div class="toolFormBody">';

        if( Object.keys( data["addresses"] ).length > 0 ) {
            template = template + '<div class="form-row">' +
                       '<div class="grid-header">';
            for( var counter = 0; counter < filters.length; counter++ ) {
                 if( counter > 0 ) {
                     template = template + '<span>|</span>';
                 }
                 if( data["show_filter"] === filters[counter] ) {
                     template = template + '<span class="filter">' + 
                                '<a class="current-filter"><b>' + filters[counter] + '</b></a></span>';
                 }
                 else {
                     template = template + '<span class="filter">' + 
                                '<a class="other-filter">' + filters[counter] + '</a></span>';
                 }
            }
            template = template + '</div></div>';

            template = template + '<table class="grid"><tbody>';
            for( var item in data["addresses"] ) {
                var item_object = data["addresses"][item];
                template = template + '<tr class="libraryRow libraryOrFolderRow" id="libraryRow">' +
                           '<td>' + 
                           '<div class="form-row">' + 
                           '<label>' + item_object['desc'] + ':</label>' +
                               item_object['html'] +
                           '</div>' + 
                           '<div class="form-row">' +
                               '<ul class="manage-table-actions">' +
                               '<li>';
                if( !item_object['deleted'] ) {
                    template = template + '<a class="action-button edit-address" data-id="'+ item_object['address_id'] +'">Edit</a>' +
                               '<a class="action-button delete-address" data-id="'+ item_object['address_id'] +'">Delete</a>';
                }
                else {
                    template = template + '<a class="action-button undelete-address" data-id="' +
                               item_object['address_id'] + '">Undelete</a>';
                }
                template = template + '</li></li></ul></div></td></tr>';
            }
            template = template + '</tbody></table>';
        }
        // markup for adding a new address
        template = template + ' <div class="form-row">' +
                   '<input type="submit" value="Add a new address">' +
                   '</div>';
        // end of markup of user addresses
        template = template + '</div></form></div>';
        // end of outermost div section
        template = template + "</div>";
        $('.user-preferences-all').append(template).on( 'click', '.back-user-pref', self.showUserPref )
                                                   .on( 'click', '.save-userdata', function( e ) {  self.saveUserData( self, e ); } );
    },

    /** go back to all user preferences */
    showUserPref: function( e ) {
        $(".donemessage").hide();
        $(".validate.errormessage").hide();
        $('.manage-userinfo-section').hide();
        $( '.user-pref' ).show();
    }
});

return {
    ManageUserInformation: ManageUserInformation
};

});

