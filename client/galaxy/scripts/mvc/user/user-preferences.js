/** User Preferences view */
define( [ 'mvc/user/change-user-information', 'mvc/user/change-password', 'mvc/user/change-permissions', 'mvc/user/change-api-key', 'mvc/user/change-toolbox-filter', 'mvc/user/change-communication' ], function( Manage, Password, Permissions, Keys, ToolboxFilter, ChangeCommunication ) {
    var UserPreferences = Backbone.View.extend({

        initialize: function ( ) {
            this.setElement( '<div/>' );
            this.getUserPreferencesData();
        },

        /** Redirect to manage user information view */
        callManageInfo: function() {
            var self = this;
            $( '.user-pref' ).hide();
            $.getJSON( Galaxy.root + 'api/user_preferences/manage_user_info', function( data ) {
                var userInfo = new Manage.ManageUserInformation( self, data );
                self.$( '.user-preferences-all' ).append( userInfo.$el );
            });
        },

        /** Redirect to change password view */
        callChangePassword: function( e ) {
            var self = this;
            $( '.user-pref' ).hide();
            $.getJSON( Galaxy.root + 'api/user_preferences/change_password', function( data ) {
                var changePassword = new Password.ChangePassword( self, data );
                self.$( '.user-preferences-all' ).append( changePassword.$el );
            });
        },

        /** Show preferences */
        showPreferences: function() {
            this.$( '.user-pref' ).show();
        },

        /** Redirect to change permissions view */
        callChangePermissions: function( e ) {
            var url = Galaxy.root + 'api/user_preferences/set_default_permissions',
                self = this,
                $el = $( '.user-preferences-all' );
            $( '.user-pref' ).hide();
            $.getJSON( url, function( data ) {
                changePermissions = new Permissions.ChangePermissions( self, data, $el );
            });
        },

        /** Redirect to API keys view */
        callApiKeys: function( e ) {
            var url = Galaxy.root + 'api/user_preferences/api_keys',
                data = {},
                self = this;
            $( '.user-pref' ).hide();
            data = { 'message': "", 'status': "" };
            $.getJSON( url, data, function( response ) {
                apiKey = new Keys.APIKeys( self, response );
                self.$( '.user-preferences-all' ).append( apiKey.$el );
            });
        },

        /** Redirect to manage toolbox filters */
        callManageToolboxFilter: function( e ) {
            var url = Galaxy.root + 'api/user_preferences/toolbox_filters',
                data = {},
                self = this;
            $( '.user-pref' ).hide();
            $.getJSON( url, function( response ) {
                toolbox = new ToolboxFilter.ToolboxFilter( self, response );
                self.$( '.user-preferences-all' ).append( toolbox.$el );
            });
        },

        /** Redirect to change communication setting view */
        callChangeCommunication: function( e ) {
            $( '.user-pref' ).hide();
            var self = this;
            var url = Galaxy.root + 'api/user_preferences/change_communication';
            $.getJSON( url, function( response ) {
                changeCommunication = new ChangeCommunication.ChangeCommunication( self, response );
                self.$( '.user-preferences-all' ).append( changeCommunication.$el );
            });
        },

        /** Fetch data for user preferences */
        getUserPreferencesData: function() {
            var url = Galaxy.root + 'api/user_preferences',
                self = this;
            $.getJSON( url, function( data ) {
                  self.render(data);
            });
        },

        /** Render the user preferences list */
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
                               "<li><a target='galaxy_main' class='change-communication-setting'>Change your communication settings</a></li>" +  
                               "<li><a target='galaxy_main' class='change-permissions'>Change default permissions</a> for new histories </li>" + 
                               "<li><a target='galaxy_main' class='manage-api-keys'>Manage your API keys</a></li>" + 
                               "<li><a target='galaxy_main' class='manage-toolbox-filters'>Manage your ToolBox filters</a></li>";

                    if( data["openid"] && !data["remote_user"] ) {
                        template = template + 
                               "<li><a target='galaxy_main' class='manage-openid'>Manage OpenIDs</a> linked to your account </li>";
                    }
                }
                else {
                    template = template + 
                               "<li><a target='galaxy_main' class='manage-userinfo'> Manage your information </a> for new histories </li>" + 
                               "<li><a target='galaxy_main' class='change-password'> Change your password </a> </li>" + 
                               "<li><a target='galaxy_main' class='manage-api-keys'> Manage your API keys </a> </li>" + 
                               "<li><a target='galaxy_main' class='manage-email-alert'> Manage your email alerts </a> </li>";
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
            // add this markup to the middle section of the Galaxy
            this.$el.empty().append( template );
            $( ".manage-userinfo" ).on( "click", function() { self.callManageInfo() } );
            $( ".change-password" ).on( "click", function() { self.callChangePassword() } );
            $( ".change-permissions" ).on( "click", function() { self.callChangePermissions() } );
            $( ".manage-api-keys" ).on( "click", function() { self.callApiKeys() } );
            $( ".manage-toolbox-filters" ).on( "click", function() { self.callManageToolboxFilter() } );
            $( ".change-communication-setting" ).on( "click", function() { self.callChangeCommunication() } );
        }
    });

    return {
        UserPreferences: UserPreferences
    };
});

