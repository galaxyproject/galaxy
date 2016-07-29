/** User Preferences view */
define(['mvc/user/manage-user-information'], function( Manage ) {
var UserPreferences = Backbone.View.extend({

    initialize: function ( ) {
        this.render();
    },

    /** redirects to manage user information view */
    callManageInfo: function( e ) {
        var userInfo = null;
        e.preventDefault();
        $( '.user-pref' ).css( 'display','none' );
        userInfo = new Manage.ManageUserInformation();
    },

    /** renders the user preferences list */
    render: function() {
        var template = "", 
            self = this;
        if( Galaxy.user.id !== null ) {
            template = "<div class='user-preferences-all'>"
            template = template + '<div class="user-pref"> <h2> User preferences </h2>' + 
                       '<p>You are currently logged in as ' +  Galaxy.user.attributes.email + '.</p>';
            if( Galaxy._logNamespace === "GalaxyApp" ) {
                if( !Galaxy.config.use_remote_user ) {
                    template = template + '<ul>' + 
                               "<li><a target='galaxy_main' class='manage-userinfo'>Manage your information</a> (email, address, etc.) </li>" + 
                               "<li><a target='galaxy_main' class='change-password'>Change your password</a> </li>" +
                               "</ul>";
                    template = template + "</div>";
                }
            }
            template = template + "</div>";
        }
        this.$el.html(template).on( "click", ".manage-userinfo", self.callManageInfo);
    }
});

return {
    UserPreferences  : UserPreferences
};

});

