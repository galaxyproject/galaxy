/** User Preferences view */
define(['mvc/user/manage-user-information', 'mvc/user/change-password'], function( Manage, Password ) {
var UserPreferences = Backbone.View.extend({

    initialize: function ( ) {
        this.getUserPreferencesData()
    },

    /** redirects to manage user information view */
    callManageInfo: function( e ) {
        var userInfo = null,
            url = Galaxy.root + 'api/user_preferences/manage_user_info';
        e.preventDefault();
        $( '.user-pref' ).css( 'display', 'none' );
        $.getJSON( url, function( data ) {
              userInfo = new Manage.ManageUserInformation( data );  
        });
    },
  
    /** redirects to change password view */
    callChangePassword: function( e ) {
        $( '.user-pref' ).css( 'display', 'none' );
        var url = Galaxy.root + 'api/user_preferences/change_password';
        $.getJSON( url, function( data ) {
            console.log( data );
            changePassword = new Password.ChangePassword( data );     
        });
    },

    /** fetch data for user preferences */
    getUserPreferencesData: function() {
        var url = Galaxy.root + 'api/user_preferences',
            self = this;
        $.getJSON( url, function( data ) {
              self.render(data);  
        });
    },

    /** renders the user preferences list */
    render: function( data ) {
        var template = "", 
            self = this;
        if( data["id"] !== null ) {
            template = "<div class='user-preferences-all'>"
            template = template + '<div class="user-pref"> <h2> User preferences </h2>' + 
                       '<p>You are currently logged in as ' +  data["email"] + '.</p>';
            template = template + '<ul>';
            if( data["webapp"] === "galaxy" ) {
                if( !data["remote_user"] ) {
                       template = template +
                       "<li><a target='galaxy_main' class='manage-userinfo'>Manage your information</a> (email, address, etc.) </li>" + 
                       "<li><a target='galaxy_main' class='change-password'>Change your password</a> </li>";
                }
                template = template + 
                           "<li><a target='galaxy_main' class='change-permissions'>Change default permissions</a> for new histories </li>" + 
                           "<li><a target='galaxy_main' class='manage-api-keys'>Manage your API keys</a></li>" + 
                           "<li><a target='galaxy_main' class='manage-toolbox-filters'>Manage your ToolBox filters</a></li>";

                if( data["openid"] && !data["remote_user"] ) {
                    template = template + 
                           "<li><a target='galaxy_main' class='change-permissions'>Manage OpenIDs</a> linked to your account </li>";
                }
                template = template + 
                           "<li><a target='galaxy_main' class='change-permissions'>Logout</a> of all user sessions </li>";
            }
            else {
                template = template + 
                           "<li><a target='galaxy_main' class='manage-userinfo'> Manage your information </a> for new histories </li>" + 
                           "<li><a target='galaxy_main' class='change-password'> Change your password </a> </li>" + 
                           "<li><a target='galaxy_main' class='manage-api-keys'> Manage your API keys </a> </li>" + 
                           "<li><a target='galaxy_main' class='manage-email-alert'> Manage your email alerts </a> </li>" + 
                           "<li><a target='galaxy_main' class='logout-user'> Logout </a> of all user sessions </li>";
            }
            template = template + "</ul>";

            if( data["webapp"] === "galaxy" ) {
                template = template + '<p>' + 'You are using <strong>' +
                           data['disk_usage'] + '</strong> of disk space in this Galaxy instance.';
                if( data["enable_quotas"] ) {
                    template = template + 'Your disk quota is: <strong>' + data['quota'] + '</strong>.';
                }
                template = template + 'Is your usage more than expected?  See the ' + 
                           '<a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> ' + 
                           'for tips on how to find all of the data in your account.'

                template = template + '</p>'
            }
        }
        else {
            if( !data['message'] ) {
                template = template + '<p>You are currently not logged in.</p>'
            }
            template = template + '<ul><li> <a target="galaxy_main" class="user-login"> Login </a></li>' +
                       "<li> <a target='galaxy_main' class='user-register'> Register </a></li>" +
                       "</ul>";
        }
        template = template + "</div></div>";
        $( "#center-panel" ).html(template);
        $( ".manage-userinfo" ).on( "click", self.callManageInfo );
        $( ".change-password" ).on( "click", self.callChangePassword );
    }
});

return {
    UserPreferences  : UserPreferences
};

});

