/** Change password view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ChangePassword = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title   : 'Change Password',
                icon    : 'fa-key',
                inputs  : [ { name: 'current',  type: 'password', label: 'Current password' }, {
                              name: 'password', type: 'password', label: 'New password'     }, {
                              name: 'confirm',  type: 'password', label: 'Confirm password' }, {
                              name: 'token',    type: 'hidden',   hidden: true, ignore: null  } ],
                operations      : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); app.showPreferences() }
                    })
                },
                buttons        : {
                    'save'  : new Ui.Button({
                        icon    : 'fa-save',
                        tooltip : 'Save settings',
                        title   : 'Save Password',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._savePassword() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        /** Saves the changed password */
        _savePassword: function( self ) {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences/change_password', this.form.data.create(), function( response ) {
                self.form.message.update({
                    message     : response.message,
                    status      : response.status === 'error' ? 'danger' : 'success',
                });
            });
        }
    });

    return {
        ChangePassword: ChangePassword
    };
});

