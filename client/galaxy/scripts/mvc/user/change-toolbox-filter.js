/** Save the toolbox filters view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    return Backbone.View.extend({
        initialize: function ( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title       : 'Manage Toolbox Filters',
                name        : 'toolbox_filter',
                inputs      : options.inputs,
                icon        : 'fa-filter',
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
                        title   : 'Save Filters',
                        icon    : 'fa-save',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._save() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        /** Save the changes made to the filters */
        _save: function() {
            var self = this;
            $.ajax({
                url      : Galaxy.root + 'api/user_preferences/' + Galaxy.user.id + '/toolbox_filters',
                type     : 'PUT',
                data     : self.form.data.create(),
            }).done( function( response ) {
                self.form.message.update( { message: response.message, status: 'success' } );
            }).fail( function( response ) {
                self.form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
            });
        }
    });
});