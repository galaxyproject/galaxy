/** User Preferences view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {

    var UserPreferences = Backbone.View.extend({

        initialize: function() {
            this.form_def = {
                'information': {
                    title           : 'Manage your information (email, address, etc.)',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/information',
                    icon            : 'fa-info-circle'
                },
                'password': {
                    title           : 'Change your password',
                    icon            : 'fa-key',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/password',
                    submit_title    : 'Save password',
                },
                'communication': {
                    title           : 'Change your communication settings',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/communication',
                    icon            : 'fa-child'
                },
                'permissions': {
                    title           : 'Change default permissions for new histories',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/permissions',
                    icon            : 'fa-lock',
                    submit_title    : 'Save permissions'
                },
                'api_key': {
                    title           : 'Manage your API keys',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/api_key',
                    icon            : 'fa-key',
                    submit_title    : 'Create a new key',
                    submit_icon     : 'fa-check'
                },
                'toolbox_filters': {
                    title           : 'Manage your Toolbox filters',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/toolbox_filters',
                    icon            : 'fa-filter'
                }
            }
            this.setElement( '<div/>' );
            this.render();
        },

        _load: function( options ) {
            var self = this;
            var form = new Form({
                title  : options.title,
                icon   : options.icon,
                inputs : options.inputs,
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon     : 'fa-caret-left',
                        tooltip  : 'Return to user preferences',
                        title    : 'Preferences',
                        onclick  : function() { form.remove(); self.$preferences.show() }
                    })
                },
                buttons: {
                    'submit': new Ui.Button({
                        tooltip  : options.submit_tooltip,
                        title    : options.submit_title || 'Save settings',
                        icon     : options.submit_icon || 'fa-save',
                        cls      : 'ui-button btn btn-primary',
                        floating : 'clear',
                        onclick  : function() {
                            $.ajax( {
                                url         : options.url,
                                data        : form.data.create(),
                                type        : 'PUT',
                                traditional : true,
                            }).done( function( response ) {
                                form.data.matchModel( response, function ( input, input_id ) {
                                    form.field_list[ input_id ].value( input.value );
                                });
                                form.message.update( { message: response.message, status: 'success' } );
                            }).fail( function( response ) {
                                form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
                            });
                        }
                    })
                }
            });
            this.$preferences.hide();
            this.$el.append( form.$el );
        },

        _link: function( page ) {
            var self = this;
            var $page_link = $( '<a target="galaxy_main" href="javascript:void(0)">' + page.title + '</a>' ).on( 'click', function() {
                $.ajax({ url: Galaxy.root + page.url, type: 'GET' }).always( function( response ) {
                    self._load( $.extend( {}, page, response ) );
                });
            });
            this.$pages.append( $( '<li/>' ).append( $page_link ) );
        },

        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences', function( data ) {
                self.$preferences = $( '<div/>' );
                if ( data.id !== null ) {
                    self.$preferences.append( $( '<h2/>' ).append( 'User preferences' ) )
                                     .append( $( '<p/>' ).append( 'You are currently logged in as ' +  _.escape( data.email ) + '.' ) )
                                     .append( self.$pages = $( '<ul/>' ) );
                    if( !data.remote_user ) {
                        self._link( self.form_def.information );
                        self._link( self.form_def.password );
                    }
                    if ( data.webapp == 'galaxy' ) {
                        self._link( self.form_def.communication );
                        self._link( self.form_def.permissions );
                        self._link( self.form_def.api_key );
                        self._link( self.form_def.toolbox_filters );
                        if ( data.openid && !data.remote_user ) {
                            self._link( { title  : 'Manage OpenIDs linked to your account' } );
                        }
                    } else {
                        self._link( self.form_def.api_key );
                        self._link( { title  : 'Manage your email alerts' } );
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