/** Get API Keys view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title: 'Web API Key',
                inputs: [ { name: 'api-key',
                            type: 'text',
                            label: 'Current API key:',
                            value: options.user_api_key || 'Not available.',
                            readonly: true,
                            help: ' An API key will allow you to access ' + ( options.app_name === 'galaxy' ? 'Galaxy' : 'the Tool Shed' ) + ' via its web API. Please note that this key acts as an alternate means to access your account and should be treated with the same care as your login password.' } ],
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon: 'fa-caret-left',
                        tooltip: 'Return to user preferences',
                        title: 'Preferences',
                        onclick: function() { self.remove(); options.onclose(); }
                    })
                },
                buttons : {
                    'generatenewkey': new Ui.Button({
                        tooltip: 'Generate new key ' + ( options.user_api_key ? '(invalidates old key) ' : '' ),
                        title: 'Generate a new key',
                        cls: 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick: function() { self._submit() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        /** Generate new API key */
        _submit: function() {
            var self = this;
            $.getJSON( Galaxy.root + 'api/user_preferences/change_api_key', { 'new_api_key': true }, function( response ) {
                if( response.user_api_key ) {
                    var input_id = self.form.data.match( 'api-key' );
                    self.form.field_list[ input_id ].value( response.user_api_key );
                    self.form.message.update({
                        message: response.message,
                        status: response.status === 'error' ? 'danger' : 'success',
                    });
                }
            });
        }
    });
});

