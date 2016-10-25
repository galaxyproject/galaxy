/** User Preferences view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {

    var UserPreferences = Backbone.View.extend({

        initialize: function() {
            this.defs = {
                'information': {
                    title           : 'Manage information',
                    description     : 'Edit your email, addresses and custom parameters or change your username.',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/information',
                    icon            : 'fa-info-circle'
                },
                'password': {
                    title           : 'Change password',
                    description     : 'Allows you to change your login credentials.',
                    icon            : 'fa-unlock-alt',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/password',
                    submit_title    : 'Save password',
                },
                'communication': {
                    title           : 'Change communication settings',
                    description     : 'Enable or disable the communication feature to chat with other users.',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/communication',
                    icon            : 'fa-child',
                    auto_save       : true
                },
                'permissions': {
                    title           : 'Change default permissions',
                    description     : 'Grant others default access to newly created histories.',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/permissions',
                    icon            : 'fa-users',
                    submit_title    : 'Save permissions'
                },
                'api_key': {
                    title           : 'Manage API key',
                    description     : 'Access your current API key or create a new one.',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/api_key',
                    icon            : 'fa-key',
                    submit_title    : 'Create a new key',
                    submit_icon     : 'fa-check'
                },
                'toolbox_filters': {
                    title           : 'Manage Toolbox filters',
                    description     : 'Customize your Toolbox by displaying or omitting sets of Tools.',
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/toolbox_filters',
                    icon            : 'fa-filter',
                    submit_title    : 'Save filters'
                },
                'openids': {
                    title           : 'Manage OpenIDs',
                    description     : 'Associate OpenIDs with your account.',
                    icon            : 'fa-openid',
                    onclick         : function() {
                        $( '#galaxy_main' ).attr( 'src', Galaxy.root + 'user/openid_manage?cntrller=user' );
                    }
                },
                'logout': {
                    title           : 'Sign out',
                    description     : 'Click here to sign out of all sessions.',
                    icon            : 'fa-sign-out',
                    onclick         : function() {
                        Galaxy.modal.show({
                            title   : 'Sign out',
                            body    : 'Do you want to continue and sign out of all active sessions?',
                            buttons : {
                                'Cancel'    : function() { Galaxy.modal.hide(); },
                                'Sign out'  : function() {
                                    $.ajax( { url : 'api/users/' + Galaxy.user.id + '/logout', method: 'POST', data: { all: true } } )
                                     .done( function( response ) {
                                        window.location.href = response.redirect_url || Galaxy.root;
                                    });
                                }
                            }
                        });
                    }
                }
            }
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences', function( data ) {
                self.$preferences = $( '<div/>' ).addClass( 'ui-panel' )
                                                 .append( $( '<h2/>' ).append( 'User preferences' ) )
                                                 .append( $( '<p/>' ).append( 'You are logged in as <strong>' +  _.escape( data.email ) + '</strong>.' ) )
                                                 .append( self.$table = $( '<table/>' ).addClass( 'ui-panel-table' ) );
                if( !data.remote_user ) {
                    self._link( self.defs.information );
                    self._link( self.defs.password );
                }
                if ( data.webapp == 'galaxy' ) {
                    self._link( self.defs.communication );
                    self._link( self.defs.permissions );
                    self._link( self.defs.api_key );
                    self._link( self.defs.toolbox_filters );
                    data.openid && !data.remote_user && self._link( self.defs.openids );
                    self._link( self.defs.logout );
                    self.$preferences.append( self._templateFooter( data ) );
                } else {
                    self._link( self.defs.api_key );
                    self._link( { title  : 'Manage your email alerts' } );
                }
                self.$el.empty().append( self.$preferences );
            });
        },

        _link: function( page ) {
            var self = this;
            var $page_item = $( this._templateRow( page ) );
            this.$table.append( $page_item );
            $page_item.find( 'a' ).on( 'click', function() {
                if ( page.url ) {
                    $.ajax({ url: Galaxy.root + page.url, type: 'GET' }).always( function( response ) {
                        var options = $.extend( {}, page, response );
                        var form = new Form({
                            title  : options.title,
                            icon   : options.icon,
                            inputs : options.inputs,
                            operations: {
                                'back': new Ui.ButtonIcon({
                                    icon     : 'fa-caret-left',
                                    tooltip  : 'Return to user preferences',
                                    title    : 'Preferences',
                                    onclick  : function() { form.remove(); self.$preferences.show(); }
                                })
                            },
                            onchange : function() { options.auto_save && self._submit( form, options ) },
                            buttons: !options.auto_save && {
                                'submit': new Ui.Button({
                                    tooltip  : options.submit_tooltip,
                                    title    : options.submit_title || 'Save settings',
                                    icon     : options.submit_icon || 'fa-save',
                                    cls      : 'ui-button btn btn-primary',
                                    floating : 'clear',
                                    onclick  : function() { self._submit( form, options ) }
                                })
                            }
                        });
                        self.$preferences.hide();
                        self.$el.append( form.$el );
                    });
                } else {
                    page.onclick();
                }
            });
        },

        _submit: function( form, options ) {
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
        },

        _templateRow: function( options ) {
            return  '<tr>' +
                        '<td>' +
                            '<div class="ui-panel-icon fa ' + options.icon + '">' +
                        '</td>' +
                        '<td>' +
                            '<a class="ui-panel-anchor" href="javascript:void(0)">' + options.title + '</a>' +
                            '<div class="ui-form-info">' + options.description + '</div>' +
                        '</td>' +
                    '</tr>';
        },

        _templateFooter: function( options ) {
            return  '<p class="ui-panel-footer">' +
                        'You are using <strong>' + options.disk_usage + '</strong> of disk space in this Galaxy instance. ' +
                        ( options.enable_quotas ? 'Your disk quota is: <strong>' + options.quota + '</strong>. ' : '' ) +
                        'Is your usage more than expected? See the <a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.' +
                    '</p>';
        }
    });

    return {
        UserPreferences: UserPreferences
    };
});