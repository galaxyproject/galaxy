/** Show and edit user information */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
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
                        onclick: function() { self.remove(); options.onclose(); }
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
            $.ajax( {
                url      : Galaxy.root + 'api/user_preferences/' + Galaxy.user.id + '/information',
                type     : 'PUT',
                data     : self.form.data.create()
            }).done( function( response ) {
                self.form.message.update( { message: response.message, status: 'success' } );
            }).fail( function( response ) {
                self.form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
            });
        }
    });
});