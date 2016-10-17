/** Show and edit user information */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( app, options, address_message ) {
            var self = this;
            this.app = app;
            this.model = options && options.model || new Backbone.Model( options );
            this.original_email = options.email;
            this.original_username = options.username;
            this.form = new Form({
                title   : 'Login Information',
                inputs  : options.inputs,
                operations : {
                    'back' : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() {
                            self.remove();
                            app.showPreferences();
                        }
                    })
                },
                buttons : {
                    'save'  : new Ui.Button({
                        tooltip : 'Save',
                        title   : 'Save Changes',
                        icon    : 'fa-save',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() {
                            self._save();
                        }
                    })
                }
            });
            this.setElement( '<div/>' );
            this.$el.append( this.form.$el );
        },

        /** Saves changes */
        _save: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences/set_information', self.form.data.create(), function( response ) {
                self.form.message.update({
                   message: response.message,
                   status: response.status === 'error' ? 'danger' : 'success'
                });
            }).always( function() {
                self.form.message.update({
                   message: 'Failed to contact server. Please wait and try again.', status: 'danger'
                });
            });
        }
    });
});