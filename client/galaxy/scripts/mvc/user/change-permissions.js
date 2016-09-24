/** Show and save permissions view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ChangePermissions = Backbone.View.extend({
        initialize: function ( app, options, $el ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = self._buildForm( options, app, self, $el );
            $el.append( this.form.$el );
        },

        /** Build the form for changing permissions */
        _buildForm: function( options, app, self, $el ) {
            return new Form({
                title: 'Manage ' + options["obj_type"] + ' permissions on ' + options["obj_str"],
                icon: 'fa-universal-access',
                inputs: options['role_form'],
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.form.$el.remove(); app.showPreferences() }
                    })
                },
                onchange: function() {
                    self._savePermissions( self, app, $el );
                }
            });
        },

        /** Update form with new data */
        _updateForm: function( app, $el, self, response ) {
            self.form.$el.remove();
            self.form = self._buildForm( response, app, self, $el );
            $el.append( self.form.$el );
            self.form.message.update({
                message : response.message,
                status : response.status === 'error' ? 'danger' : 'success',
            });
        },

        /** Save the permissions */
        _savePermissions: function( self, app, $el ) {
            var objects = self.form.data.create(),
                save = false,
                action = false,
                data = {};
            for( var item in objects ) {
                // check if move up or down button is selected
                if( item.indexOf('actionrole') > 0 && objects[item] !== null ) {
                    save = true;
                }
                // add checked item(s) from the select box
                if( ( item.indexOf('_in') > 0 || item.indexOf('_out') > 0 ) &&  objects[item] !== null ) {
                    action = true;
                    data[item] = objects[item][0];
                }
            }
            if( save && action ) {
                data.update_roles = action;
                $.getJSON( Galaxy.root + 'api/user_preferences/set_default_permissions', data, function( response ) {
                    self._updateForm( app, $el, self, response );
                });
            }
        }
    });

    return {
        ChangePermissions: ChangePermissions
    };
});

