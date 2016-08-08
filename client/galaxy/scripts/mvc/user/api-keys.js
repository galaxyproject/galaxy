/** Generate API keys view */
define(['mvc/user/manage-user-information'], function( Manage ) {
var APIKeys = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the error message when view is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ ( status === "error" ? " validate" : "" ) + '">'+ msg +'</div>';
    },

    /** builds the html for get API key view */
    render: function( data ) {
        var template = "",
            self = this,
            app_name = ( data["app_name"] === 'galaxy' ? 'Galaxy' : 'the Tool Shed' );
        Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        if( data["message"] && data["message"].length > 0 ) {
            template = this.renderMessage( data["message"], data['status'] );
        }
        template = template + '<div class="api-key-section"> <h2>Web API Key</h2>';
        template = template + '<ul class="manage-table-actions">' +
                              '<li>' +
                              '<a class="action-button back-user-info" target="galaxy_main">User preferences</a>' +
                              '</li></ul>';
        template = template + '<div class="toolForm">' +
                              '<div class="toolFormTitle">Web API Key</div>' +
                              '<div class="toolFormBody">' +
                              '<form name="user_api_keys" id="user_api_keys">' +
                              '<div class="form-row">' +
                              '<label>Current API key:</label>' +
                              '<span class="new-api-key">' + ( data["has_api_key"] ? data["user_api_key"] : 'none set' ) + '</span>' +
                              '</div>';
        template = template + '<div class="form-row">' +
                              '<input type="button" class="get-new-key action-button" name="new_api_key_button"' +
                                      'value="Generate a new key now"/>' +
                               ( data["has_api_key"] ? ' (invalidates old key) ' : '' ) +
                               '<div class="toolParamHelp" style="clear: both; margin-top: 1%;">' +
                                   'An API key will allow you to access ' + app_name + ' via its web API. ' +
                                   'Please note that <strong>this key acts as an alternate means ' +
                                   'to access your account and should be treated with the same care as your login password</strong>.' +
                               '</div>' +
                               '</div></form></div></div>';
        // end of outermost div section
        template = template + "</div>";
        $('.user-preferences-all').append( template );
        $('.back-user-info').on( 'click', function( e ) {
            e.preventDefault();
            $( ".user-pref" ).show();
            $( ".api-key-section" ).remove();
            Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        });
        $('.get-new-key').on( 'click', function( e ){ self.getNewApiKey( self, e ); });
    },

    /** generates new API key */
    getNewApiKey: function( self, e ) {
        var url = Galaxy.root + 'api/user_preferences/api_keys',
            data = {},
            messageBar = Manage.ManageUserInformation.prototype;
        data = { 'message': "", 'status': "", 'new_api_key_button': true };
        $.getJSON( url, data, function( response ) {
            if( response["has_api_key"] ) {
                $(".new-api-key").text( response["user_api_key"] );
                messageBar.renderDone( response["message"] );
            }
        });
    }
});

return {
    APIKeys  : APIKeys
};

});

