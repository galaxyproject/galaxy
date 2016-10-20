/** Get API Keys view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title  : 'Web API Key',
                icon   : 'fa-key',
                inputs : options.inputs,
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon     : 'fa-caret-left',
                        tooltip  : 'Return to user preferences',
                        title    : 'Preferences',
                        onclick  : function() { self.remove(); options.onclose(); }
                    })
                },
                buttons: {
                    'submit': new Ui.Button({
                        tooltip  : 'Generate new key ' + ( options.api_key ? '(invalidates old key) ' : '' ),
                        title    : 'Generate a new key',
                        icon     : 'fa-check',
                        cls      : 'ui-button btn btn-primary',
                        floating : 'clear',
                        onclick  : function() { self._submit() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        /** Generate new API key */
        _submit: function() {
            var self = this;
            $.ajax( {
                url  : Galaxy.root + 'api/user_preferences/' + Galaxy.user.id + '/api_key',
                type : 'PUT',
                data : { new_api_key: true }
            }).done( function( response ) {
                self.form.data.matchModel( response, function ( input, input_id ) {
                    self.form.field_list[ input_id ].value( input.value );
                });
                self.form.message.update( { message: response.message, status: 'success' } );
            }).fail( function( response ) {
                self.form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
            });
        }
    });
});
