/** User Preferences view */
define( [ 'mvc/user/change-information', 'mvc/user/change-password', 'mvc/user/change-permissions', 'mvc/user/change-api-key', 'mvc/user/change-toolbox-filter', 'mvc/user/change-communication' ], function( Information, Password, Permissions, ApiKey, ToolboxFilter, Communication ) {
    var UserPreferences = Backbone.View.extend({

        initialize: function() {
            this.setElement( '<div/>' );
            this.render();
        },

        _link: function( page ) {
            var self = this;
            var $page_link = $( '<a target="galaxy_main" href="javascript:void(0)">' + page.title + '</a>' ).on( 'click', function() {
                $.ajax({
                    url  : Galaxy.root + page.url,
                    type : 'GET'
                }).always( function( response ) {
                    self.$preferences.hide();
                    response.onclose = function() { self.$preferences.show() };
                    self.$el.append( new page.module( response ).$el );
                });
            });
            this.$pages.append( $( '<li/>' ).append( $page_link ) );
        },

        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences', function( data ) {
                self.$preferences = $( '<div/>' );
                if ( data.id !== null ) {
                    self.$preferences.append( '<h2>User preferences</h2>' )
                                     .append( '<p>You are currently logged in as ' +  _.escape( data.email ) + '.</p>' )
                                     .append( self.$pages = $( '<ul/>' ) );
                    if( !data.remote_user ) {
                        self._link( { title  : 'Manage your information (email, address, etc.)',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/information',
                                      module : Information } );
                        self._link( { title  : 'Change your password',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/password',
                                      module : Password } );
                    }
                    if ( data.webapp == 'galaxy' ) {
                        self._link( { title  : 'Change your communication settings',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/communication',
                                      module : Communication } );
                        self._link( { title  : 'Change default permissions for new histories',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/permissions',
                                      module : Permissions } );
                        self._link( { title  : 'Manage your API keys',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/api_key',
                                      module : ApiKey } );
                        self._link( { title  : 'Manage your ToolBox filters',
                                      url    : 'api/user_preferences/' + Galaxy.user.id + '/toolbox_filters',
                                      module : ToolboxFilter } );
                        if ( data.openid && !data.remote_user ) {
                            self._link( { title  : 'Manage OpenIDs linked to your account',
                                          module : null } );
                        }
                    } else {
                        self._link( { title  : 'Manage your API keys',
                                      module : ApiKey } );
                        self._link( { title  : 'Manage your email alerts',
                                      module : null } );
                    }
                    if ( data.webapp == 'galaxy' ) {
                        var footer_template = '<p>' + 'You are using <strong>' + data.disk_usage + '</strong> of disk space in this Galaxy instance. ';
                        if ( data.enable_quotas ) {
                            footer_template += 'Your disk quota is: <strong>' + data.quota + '</strong>. ';
                        }
                        footer_template += 'Is your usage more than expected?  See the <a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.</p>';
                        self.$preferences.append( footer_template );
                    }
                } else {
                    if( !data.message ) {
                        self.$preferences.append( '<p>You are currently not logged in.</p>' );
                    }
                    $preferences(   '<ul>' +
                                        '<li><a target="galaxy_main">Login</a></li>' +
                                        '<li><a target="galaxy_main">Register</a></li>' +
                                    '</ul>' );
                }
                self.$el.empty().append( self.$preferences );
            });
        }
    });

    return {
        UserPreferences: UserPreferences
    };
});