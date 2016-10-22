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
                    url             : 'api/user_preferences/' + Galaxy.user.id + '/openids',
                    icon            : 'fa-openid'
                },
                'logout': {
                    title           : 'Sign out',
                    description     : 'Click here to sign out of all sessions.',
                    icon            : 'fa-sign-out',
                    onclick         : function() {
                        Galaxy.modal.show({
                            title   : 'Sign out',
                            body    : 'Do you want to continue and sign out of all sessions?',
                            buttons : {
                                'Cancel'    : function() { Galaxy.modal.hide(); },
                                'Sign out'  : function() { Galaxy.modal.hide(); }
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
                self.$preferences = $( '<div/>' ).append( $( '<h2/>' ).append( 'User preferences' ) )
                                                 .append( $( '<p/>' ).append( 'You are logged in as <strong>' +  _.escape( data.email ) + '</strong>.' ) )
                                                 .append( self.$table = $( '<table/>' ) );
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
                    var footer_template = '<p style="margin-top: 10px;">' + 'You are using <strong>' + data.disk_usage + '</strong> of disk space in this Galaxy instance. ';
                    if ( data.enable_quotas ) {
                        footer_template += 'Your disk quota is: <strong>' + data.quota + '</strong>. ';
                    }
                    footer_template += 'Is your usage more than expected?  See the <a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.</p>';
                    self.$preferences.append( footer_template );
                } else {
                    self._link( self.defs.api_key );
                    self._link( { title  : 'Manage your email alerts' } );
                }
                self.$el.empty().append( self.$preferences );
            });
        },

        _link: function( page ) {
            var self = this;
            var $page_item = $( this._templatePage( page ) );
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

        _templatePage: function( options ) {
            return  '<div style="margin-left: 20px;">' +
                        '<table>' +
                            '<tr>' +
                                '<td>' +
                                    '<div class="fa ' + options.icon + '" style="width: 30px; margin: 10px; font-size: 1.6em;">' +
                                '</td>' +
                                '<td>' +
                                    '<a style="font-weight: bold;" href="javascript:void(0)">' + options.title + '</a>' +
                                    '<div class="ui-form-info">' + options.description + '</div>' +
                                '</td>' +
                            '</tr>' +
                    '<div>';
        }
    });

    return {
        UserPreferences: UserPreferences
    };
});