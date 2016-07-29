/** Manage User Information view under User Preferences */
define([], function() {

var ManageUserInformation = Backbone.View.extend({

    original_email: "",
    original_username: "",

    initialize: function ( ) {
        this.render( this );
        //original_email = $( '#email_input' ).val();
        //original_username = $( '#name_input' ).val();
        //this.submitForm();
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

    renderError: function( message ) {
        $(".donemessage").hide();
        if ($(".errormessage").length === 1) {
            $(".errormessage").html(message);
        } else {
            var div = document.createElement( "div" );
            div.className = "errormessage";
            div.innerHTML = message;
            document.body.insertBefore( div, document.body.firstChild );
        }
    },

    renderDone: function( message ) {
        $(".errormessage").hide();
        if ($(".donemessage").length === 1) {
            $(".donemessage").html(message);
        } 
        else {
            var div = document.createElement( "div" );
            div.className = "donemessage";
            div.innerHTML = message;
            document.body.insertBefore( div, document.body.firstChild );
        }
    },

    submitForm: function() {
        $( '#login_info' ).bind( 'submit', function( e ) {
            var error_text_email= 'Please enter your valid email address.',
                error_text_email_long= 'Email cannot be more than 255 characters in length.', 
                error_text_username_characters = 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 2.', 
                email = $( '#email_input' ).val(),
                name = $( '#name_input' ).val(), 
                validForm = true,
                nothing_changed = ( original_email === email && original_username === name ), 
                hidden_input = '<input type="hidden" id="login_info_button" name="login_info_button" value="Submit"/>'; 
                // we need this value to detect submitting at backend
            $( '#send' ).attr( 'disabled', 'disabled' );
            $( "#email_input" ).before( hidden_input );
            if ( original_email !== email ) {
                if ( email.length > 255 ) { renderError( error_text_email_long ); validForm = false; }
                else if ( !validateString( email, "email" ) ) { renderError( error_text_email ); validForm = false; }
            }
            if ( original_username !== name ){
                if ( name && !( validateString( name,"username" ) ) ) { renderError( error_text_username_characters ); validForm = false; }
            }
            if ( nothing_changed ) {
                renderDone( "Nothing has changed." );
            }
            if ( !validForm  || nothing_changed ) {
                e.preventDefault();
                // reactivate the button if the form wasn't submitted
                $( '#send' ).removeAttr( 'disabled' );
            }
        });
    },

    /** renders manage user information */
    render: function( self ) {
        var template = "";
        template = template + '<div class="manage-userinfo-section"> <h2>Manage User Information</h2>';
        if( !Galaxy.user.attributes.is_admin ) {
            template = template + '<ul class="manage-table-actions">' +
                       '<li>' +
                           '<a class="action-button back-user-info" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';
        }
        template = template + "</div>";
        $('.user-preferences-all').append(template);
    } 
});

return {
    ManageUserInformation: ManageUserInformation
};

});

