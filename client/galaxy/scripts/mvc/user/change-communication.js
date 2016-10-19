/** Change communication settings view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title: 'Enable real-time communication with other Galaxy users',
                icon: 'fa-child',
                inputs: [ { name: 'enable', type: 'boolean', label: 'Enable communication', value: options.activated } ],
                operations: {
                    'back': new Ui.ButtonIcon({
                        icon: 'fa-caret-left',
                        tooltip: 'Return to user preferences',
                        title: 'Preferences',
                        onclick: function() { self.remove(); options.onclose(); }
                    })
                },
                onchange: function() {
                   self._save();
               }
            });
            this.setElement( this.form.$el );
        },

        /** Saves changes */
        _save: function() {
            var self = this;
            $.ajax({
                url      : Galaxy.root + 'api/user_preferences/' + Galaxy.user.id + '/communication',
                type     : 'PUT',
                data     : { enable: self.form.data.create()[ 'enable' ] },
                success  : function( response ) {
                    self.form.message.update({
                       message: response.message,
                       status: response.status === 'error' ? 'danger' : 'success'
                    });
                }
            });
        }
    });
});