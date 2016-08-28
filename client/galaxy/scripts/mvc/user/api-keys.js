/** Get API Keys view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var APIKeys = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.help_text = ' An API key will allow you to access ' + ( options["app_name"] === 'galaxy' ? 'Galaxy' : 'the Tool Shed' ) +   
                             ' via its web API. Please note that this key acts as an alternate means to access your account and should be' +   
                             ' treated with the same care as your login password.';
            this.key = options["has_api_key"] ? options["user_api_key"] : 'none set';
            this.form = new Form({
                title   : 'Web API Key',
                inputs  : [ { name: 'api-key', type: 'text', label: 'Current API key:', value: self.key },
                            { name: 'API Key Information', type: 'section', label: 'API Key Information', help: self.help_text,
                              inputs: { }, expanded: true }
                          ],
                operations      : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); app.showPreferences() }
                    })
                },
                buttons        : {
                    'generatenewkey'  : new Ui.Button({
                        tooltip : 'Generate new key ' + ( options["has_api_key"] ? '(invalidates old key) ' : '' ),
                        title   : 'Generate a new key now',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._getNewApiKey() }
                    })
                }
            });
            this.setElement( this.form.$el );
            setTimeout( function(){ $('div[tour_id="api-key"] .ui-input').attr( 'readonly', 'readonly'); $('tmessage').remove(); });
        },

        /** generates new API key */
        _getNewApiKey: function() {
            var url = Galaxy.root + 'api/user_preferences/api_keys',
                data = {},
                self = this;
            data = { 'message': "", 'status': "", 'new_api_key_button': true };
            $.getJSON( url, data, function( response ) {
                var $key_input = $( 'div[tour_id="api-key"] .ui-input' );
                if( response["has_api_key"] ) {
                    $key_input.val( response["user_api_key"] );
                    self.form.message.update({
                        message     : response.message,
                        status      : response.status === 'error' ? 'danger' : 'success',
                    });
                }
            });
        }
    });

    return {
        APIKeys: APIKeys
    };
});

