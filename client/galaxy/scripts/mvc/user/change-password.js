/** Change password view */
define(['mvc/user/manage-user-information'], function( Manage ) {

var ChangePassword = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the error message when manage user info page is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ ( status === "error" ? " validate" : "" ) + '">'+ msg +'</div>';
    },

    /** renders the markup of change password feature */
    render: function( data ) {
        var template = "",
            self = this;
        $( '.user-pref' ).css( 'display', 'none' );
        $('.change-password-section').remove();
        Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        if( data["status"] ) {
            template = self.renderMessage( data["message"], data["status"] );
        }
        template = template + '<div class="change-password-section"> <h2>Change Password</h2>';
        template = template + '<ul class="manage-table-actions">' +
                       '<li>' +
                           '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';

        template = template + '<div class="toolForm">' +
                   '<form name="change_password" id="change_password">' +
                       '<input type="hidden" name="display_top" value="'+ data["display_top"] +'"/>' +
                       '<div class="toolFormTitle">Change Password</div>';
        if( data["token"] ) {
            template = template + '<input type="hidden" name="token" value="'+ data["token"] +'"/>';
        }
        else {
            template = template + '<div class="form-row">' +
                       '<label>Current password:</label>' +
                           '<input type="password" name="current" value="" size="40"/>' +
                       '</div>';
        }
        template = template + '<div class="form-row">' +
                   '<label>New password:</label>' +
                       '<input type="password" name="password" value="" size="40"/>' +
                   '</div>' +
                   '<div class="form-row">' +
                       '<label>Confirm:</label>' +
                       '<input type="password" name="confirm" value="" size="40"/>' +
                   '</div>' +
                   '<div class="form-row">' +
                       '<input type="button" class="save-password action-button" name="change_password_button" value="Save"/>' +
                   '</div>' + 
                   '</form>' +
                   '</div>';
         template = template + '</div>';
         $('.user-preferences-all').append( template );
         $('.save-password').on( 'click', function( e ) { self.savePassword( self, e ) } );
         $('.back-user-pref').on( 'click', function( e ) {
             $('.change-password-section').remove();
             Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
             $( '.user-pref' ).show();
         });
    },

    /** saves the changed password */
    savePassword: function( self, e ) {
        var url = Galaxy.root + 'api/user_preferences/change_password',
            current = $( "input[name='current']" ).val(),
            password = $( "input[name='password']" ).val(),
            confirm = $( "input[name='confirm']" ).val(),
            data = {},
            messageBar = Manage.ManageUserInformation.prototype;

        data = { 'change_password_button': true, 'password': password, 'current': current, 'confirm': confirm, 'token': "" }
        $.getJSON( url, data, function( response ) {
             if( response["status"] === 'error' ) {
                  messageBar.renderError( response["message"] );
             }
             else {
                  $('.change-password-section').remove();
                  messageBar.renderDone( response["message"] );
                  $( '.user-pref' ).show();
             }            
        });
    }
});

return {
    ChangePassword: ChangePassword
};

});

