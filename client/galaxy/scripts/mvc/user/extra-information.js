/** Get extra information */
define([], function() {

var ExtraInformation = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the markup of extra information */
    render: function( data ) {
        var template = "",
            self = this;
        $( '.user-pref' ).css( 'display', 'none' );
        template = template + '<div class="extra-information-section"> <h2>Extra Information</h2>';
        template = template + '<ul class="manage-table-actions"> <li>' +
                              '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';

        template = template + '<div class="toolForm">' +
                   '<form name="extra_information" id="extra_information">' +
                       '<div class="toolFormTitle">Extra Information</div>';
        for( var item in data["preferences"] ) {
            var item_object = data["preferences"][item];
            template = template + '<div class="form-row">';
            template = template + "<label>" + item_object["description"] + ":</label>";
            for( var i = 0; i < item_object["inputs"].length; i++ ) {
                var input_object = item_object["inputs"][i];
                template = template + '<div class="form-row">';
                template = template + "<label>" + input_object.label + ':</label><input type="'+ input_object.type +
                           '" name="'+ input_object.name +'" value="" '+ (input_object.required ? 'required': '') + '/>';
                template = template + '</div>';
            }
            template = template + '</div>';
        }
        template = template + '</div>';
        template = template + '<div class="form-row">' +
            '<input type="button" class="save-password action-button" name="change_password_button" value="Save"/>' +
            '</div></form></div></div>';
        $('.save-password').on( 'click', function( e ) { self.saveExtraInformation( self, e ) } );
        $('.user-preferences-all').append( template );
        $('.back-user-pref').on( 'click', function( e ) {
             $('.extra-information-section').remove();
             $( '.user-pref' ).show();
        });
    },

    /** saves extra user information */
    saveExtraInformation: function( self, e ) {
        /* var url = Galaxy.root + 'api/user_preferences/change_password',
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
        */
    }



});

return {
    ExtraInformation: ExtraInformation
};

});

