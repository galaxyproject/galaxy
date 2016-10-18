/** User Preferences view */
define( [ 'mvc/user/change-user-information', 'mvc/user/change-password', 'mvc/user/change-permissions', 'mvc/user/change-api-key', 'mvc/user/change-toolbox-filter', 'mvc/user/change-communication' ], function( UserInformation, Password, Permissions, ApiKey, ToolboxFilter, Communication ) {
    var UserPreferences = Backbone.View.extend({

        initialize: function() {
            this.setElement( '<div/>' );
            this.render();
        },

        /** Render the user preferences list */
        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences', function( data ) {
                var pages = [];
                if ( data.id !== null ) {
                    if( !data.remote_user ) {
                        pages.push( { title  : 'Manage your information (email, address, etc.)',
                                      url    : 'api/user_preferences/get_information',
                                      module : UserInformation } );
                        pages.push( { title  : 'Change your password',
                                      url    : 'api/user_preferences/change_password',
                                      module : Password } );
                    }
                    if ( data.webapp == 'galaxy' ) {
                        pages.push( { title  : 'Change your communication settings',
                                      url    : 'api/user_preferences/change_communication',
                                      module : Communication } );
                        pages.push( { title  : 'Change default permissions for new histories',
                                      url    : 'api/user_preferences/change-permissions',
                                      module : Permissions } );
                        pages.push( { title  : 'Manage your API keys',
                                      url    : 'api/user_preferences/change_api_key',
                                      module : ApiKey } );
                        pages.push( { title  : 'Manage your ToolBox filters',
                                      url    : 'api/user_preferences/change_toolbox_filters',
                                      module : ToolboxFilter } );
                        if ( data.openid && !data.remote_user ) {
                            pages.push( { title  : 'Manage OpenIDs linked to your account',
                                          module : null } );
                        }
                    } else {
                        pages.push( { title  : 'Manage your API keys',
                                      module : ApiKey } );
                        pages.push( { title  : 'Manage your email alerts',
                                      module : null } );
                    }
                }
                var $preferences = $( '<div/>' ).addClass( 'user-pref' );
                if ( data.id !== null ) {
                    $preferences.append( '<h2>User preferences</h2>' )
                                .append( '<p>You are currently logged in as ' +  data.email + '.</p>' )
                                .append( $pages = $( '<ul/>' ) );
                    _.each( pages, function( page ) {
                        $page_link = $( '<a target="galaxy_main"> ' + page.title + '</a>' ).on( 'click', function() {
                            $.getJSON( Galaxy.root + page.url, function( data ) {
                                $preferences.hide();
                                data.onclose = function() { $preferences.show() };
                                self.$el.append( new page.module( data ).$el );
                            });
                        });
                        $pages.append( $( '<li/>' ).append( $page_link ) );
                    });
                }
                self.$el.empty().append( $preferences );
            });
        }
    });

    return {
        UserPreferences: UserPreferences
    };
});