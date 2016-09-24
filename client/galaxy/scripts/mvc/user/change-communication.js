/** Change communication settings view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ChangeCommunication = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title: 'Enable real-time communication with other Galaxy users',
                icon: 'fa-child',
                inputs: [ { name: 'change-communication', type: 'boolean', label: 'Enable communication', value: options.activated } ],
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon: 'fa-caret-left',
                        tooltip: 'Return to user preferences',
                        title: 'Preferences',
                        onclick: function() { self.remove(); app.showPreferences() }
                    })
                },
                onchange: function() {
                   self.saveCommunicationChanges();
               }
            });
            this.setElement( this.form.$el );
        },

        /** Saves changes */
        saveCommunicationChanges: function() {
            var self = this;
            var data = { 'enable_communication_server': self.form.data.create()[ 'change-communication' ] };
            $.getJSON( Galaxy.root + 'api/user_preferences/change_communication', data, function( response ) {
                self.form.message.update({
                   message: response.message,
                   status: response.status === 'error' ? 'danger' : 'success'
                });
            });
        }
    });

    return {
        ChangeCommunication: ChangeCommunication
    };
});

