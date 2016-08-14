/** Change communication settings view */
define(['mvc/user/manage-user-information'], function( Manage ) {

var ChangeCommunication = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the error message when change communication is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ ( status === "error" ? " validate" : "" ) + '">'+ msg +'</div>';
    },

    /** renders the markup of change communication feature */
    render: function( data ) {
        var template = "",
            self = this,
            show_active = false;
        $( '.user-pref' ).hide();
        $('.change-communication-section').remove();
        Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        // builds the template 
        if( data["status"] && data["message"].length > 0 ) {
            template = self.renderMessage( data["message"], data["status"] );
        }
        template = template + '<div class="change-communication-section"> <h2>Change your communication settings</h2>';
        template = template + '<ul class="manage-table-actions">' +
                       '<li>' +
                           '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';
        show_active = ( data["activated"] === 'enable' ? true : false );
        template = template + '<div class="toolForm">' +
                   '<form name="change_communication" id="change_communication">' +
                   '<div class="toolFormTitle">Activate real-time communication with other Galaxy users</div>' +
                   '<div class="form-row">' +
                   '<div class="btn-group ui-radiobutton" data-toggle="buttons" style="display: inline-block;">' +
                   '<label class="btn btn-default ui-option yes-label '+ (show_active ? 'active' : '' ) +'" data-original-title="" title="">' +
                   '<input type="radio" name="enable-yes" value="'+ show_active +'">Yes</label>' +

                   '<label class="btn btn-default ui-option no-label '+ (!show_active ? 'active' : '' ) +'" data-original-title="" title="">' +
                   '<input type="radio" name="enable-no" value="'+ !show_active +'">No</label>' +
                   '</div>' +
                   '</div>' +
                   '</form>' +
                   '</div>';
         template = template + '</div>';

         $('.user-preferences-all').append( template );
         // registers click events
         $('.yes-label').on( 'click', function( e ) { self.saveCommunicationChanges( self, e, true ) } );
         $('.no-label').on( 'click', function( e ) { self.saveCommunicationChanges( self, e, false ) } );
         $('.back-user-pref').on( 'click', function( e ) {
             $('.change-communication-section').remove();
             Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
             $( '.user-pref' ).show();
         });
    },

    /** saves the change in communication settings */
    saveCommunicationChanges: function( self, e, enable_server ) {
        var url = Galaxy.root + 'api/user_preferences/change_communication',
            data = {},
            messageBar = Manage.ManageUserInformation.prototype;

        e.stopPropagation();
        if( enable_server ) {
            // returns if the active button is clicked
            if( $('.yes-label').hasClass('active') ) {
                return;
            }
            // toggles the active class
            $('.yes-label').addClass(' active');
            $('.no-label').removeClass('active');
        }
        else {
            // returns if the active button is clicked
            if( $('.no-label').hasClass('active') ) {
                return;
            }
            // toggles the active class
            $('.no-label').addClass('active');
            $('.yes-label').removeClass(' active');
        }

        data = { 'button_comm_server': true, 'enable_communication_server': ( enable_server ? 'enable' : 'disable' ) };
        $.getJSON( url, data, function( response ) {
             if( response["status"] === 'error' ) {
                  messageBar.renderError( response["message"] );
             }
             else {
                  messageBar.renderDone( response["message"] );
             }    
        });
    }
});

return {
    ChangeCommunication: ChangeCommunication
};

});

