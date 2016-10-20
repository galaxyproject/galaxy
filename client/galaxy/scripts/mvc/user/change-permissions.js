/** Show and save permissions view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            window.console.log( options );
            this.form = new Form({
                title       : 'Manage dataset permissions',
                name        : 'toolbox_filter',
                inputs      : options.inputs,
                icon        : 'fa-universal-access',
                operations  : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); options.onclose(); }
                    })
                },
                buttons     : {
                    'save'  : new Ui.Button({
                        tooltip : 'Save changes',
                        title   : 'Save Permissions',
                        icon    : 'fa-save',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._save() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        initializedssd: function ( app, options, $el ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = self._buildForm( options, app, self, $el );
            $el.append( this.form.$el );
        },

        /** Build the form for changing permissions */
        _buildForm: function( options, app, self, $el ) {
            return new Form({
                title: 'Manage dataset permissions on EMAIL',
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
});

