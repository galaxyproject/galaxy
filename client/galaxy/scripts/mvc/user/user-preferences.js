/** User Preferences view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {

    /** Contains descriptive dictionaries describing user forms */
    var Model = Backbone.Model.extend({
        initialize: function( options ) {
            options = options || {};
            options.user_id = options.user_id || Galaxy.user.id;
            this.set({
                'user_id'           : options.user_id,
                'information': {
                    title           : 'Manage information',
                    description     : 'Edit your email, addresses and custom parameters or change your username.',
                    url             : 'api/users/' + options.user_id + '/information/inputs',
                    icon            : 'fa-user'
                },
                'password': {
                    title           : 'Change password',
                    description     : 'Allows you to change your login credentials.',
                    icon            : 'fa-unlock-alt',
                    url             : 'api/users/' + options.user_id + '/password/inputs',
                    submit_title    : 'Save password',
                },
                'communication': {
                    title           : 'Change communication settings',
                    description     : 'Enable or disable the communication feature to chat with other users.',
                    url             : 'api/users/' + options.user_id + '/communication/inputs',
                    icon            : 'fa-comments-o'
                },
                'permissions': {
                    title           : 'Set dataset permissions for new histories',
                    description     : 'Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored.',
                    url             : 'api/users/' + options.user_id + '/permissions/inputs',
                    icon            : 'fa-users',
                    submit_title    : 'Save permissions'
                },
                'api_key': {
                    title           : 'Manage API key',
                    description     : 'Access your current API key or create a new one.',
                    url             : 'api/users/' + options.user_id + '/api_key/inputs',
                    icon            : 'fa-key',
                    submit_title    : 'Create a new key',
                    submit_icon     : 'fa-check'
                },
                'toolbox_filters': {
                    title           : 'Manage Toolbox filters',
                    description     : 'Customize your Toolbox by displaying or omitting sets of Tools.',
                    url             : 'api/users/' + options.user_id + '/toolbox_filters/inputs',
                    icon            : 'fa-filter',
                    submit_title    : 'Save filters'
                },
                'openids': {
                    title           : 'Manage OpenIDs',
                    description     : 'Associate OpenIDs with your account.',
                    icon            : 'fa-openid',
                    onclick         : function() {
                        window.location.href = Galaxy.root + 'user/openid_manage?cntrller=user&use_panels=True';
                    }
                },
                'custom_builds': {
                    title           : 'Manage custom builds',
                    description     : 'Add or remove custom builds using history datasets.',
                    icon            : 'fa-cubes',
                    onclick         : function() {
                        window.location.href = Galaxy.root + 'custom_builds';
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
                                'Sign out'  : function() { window.location.href = Galaxy.root + 'user/logout'; }
                            }
                        });
                    }
                }
            });
        }
    });

    /** View of the main user preference panel with links to individual user forms */
    var View = Backbone.View.extend({

        initialize: function() {
            this.model = new Model();
            this.message = new Ui.Message();
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            var config = Galaxy.config;
            $.getJSON( Galaxy.root + 'api/users/' + Galaxy.user.id, function( data ) {
                self.$preferences = $( '<div/>' ).addClass( 'ui-panel' )
                                                 .append( self.message.$el )
                                                 .append( $( '<h2/>' ).append( 'User preferences' ) )
                                                 .append( $( '<p/>' ).append( 'You are logged in as <strong>' +  _.escape( data.email ) + '</strong>.' ) )
                                                 .append( self.$table = $( '<table/>' ).addClass( 'ui-panel-table' ) );
                if( !config.use_remote_user ) {
                    self._addLink( 'information' );
                    self._addLink( 'password' );
                }
                if( config.enable_communication_server ) {
                    self._addLink( 'communication' );
                }
                self._addLink( 'custom_builds' );
                self._addLink( 'permissions' );
                self._addLink( 'api_key' );
                if( config.has_user_tool_filters ) {
                    self._addLink( 'toolbox_filters' );
                }
                if( config.enable_openid && !config.use_remote_user ) {
                    self._addLink( 'openids' );
                }
                self._addLink( 'logout' );
                self.$preferences.append( self._templateFooter( data ) );
                self.$el.empty().append( self.$preferences );
            });
        },

        _addLink: function( action ) {
            var options = this.model.get( action );
            var $row =   $( this._templateLink( options ) );
            var $a = $row.find( 'a' );
            if ( options.onclick ) {
                $a.on( 'click', function() { options.onclick() } );
            } else {
                $a.attr( 'href', Galaxy.root + 'user/' + action );
            }
            this.$table.append( $row );
        },

        _templateLink: function( options ) {
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
                        'You are using <strong>' + options.nice_total_disk_usage + '</strong> of disk space in this Galaxy instance. ' +
                        ( Galaxy.config.enable_quotas ? 'Your disk quota is: <strong>' + options.quota + '</strong>. ' : '' ) +
                        'Is your usage more than expected? See the <a href="https://wiki.galaxyproject.org/Learn/ManagingDatasets" target="_blank">documentation</a> for tips on how to find all of the data in your account.' +
                    '</p>';
        }
    });

    /** View of individual user forms */
    var Forms = Backbone.View.extend({

        initialize: function( options ) {
            this.model = new Model( options );
            this.page = this.model.get( options.form_id );
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            $.ajax({
                url     : Galaxy.root + this.page.url,
                type    : 'GET'
            }).done( function( response ) {
                var options = $.extend( {}, self.page, response );
                var form = new Form({
                    title  : options.title,
                    icon   : options.icon,
                    inputs : options.inputs,
                    operations: {
                        'submit': new Ui.ButtonIcon({
                            tooltip  : options.submit_tooltip,
                            title    : options.submit_title || 'Save settings',
                            icon     : options.submit_icon || 'fa-save',
                            onclick  : function() { self._submit( form, options ) }
                        })
                    }
                });
                self.$el.empty().append( form.$el );
            }).fail( function( response ) {
                self.$el.empty().append( new Ui.Message({
                    message     : 'Failed to load resource ' + self.page.url + '.',
                    status      : 'danger',
                    persistent  : true
                }).$el );
            });
        },

        _submit: function( form, options ) {
            var self = this;
            $.ajax( {
                url         : Galaxy.root + options.url,
                data        : JSON.stringify( form.data.create() ),
                type        : 'PUT',
                contentType : 'application/json'
            }).done( function( response ) {
                form.data.matchModel( response, function ( input, input_id ) {
                    form.field_list[ input_id ].value( input.value );
                });
                form.message.update( { message: response.message, status: 'success' } );
            }).fail( function( response ) {
                form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
            });
        }
    });

    return {
        View  : View,
        Forms : Forms
    };
});
