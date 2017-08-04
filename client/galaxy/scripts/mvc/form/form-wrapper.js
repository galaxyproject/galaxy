/** Generic form view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {

    var View = Backbone.View.extend({

        initialize: function( options ) {
            this.model = new Backbone.Model( options );
            this.url = this.model.get( 'url' );
            this.redirect = this.model.get( 'redirect' );
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            var self = this;
            $.ajax({
                url     : Galaxy.root + this.url,
                type    : 'GET'
            }).done( function( response ) {
                var options = $.extend( {}, self.model.attributes, response );
                var form = new Form({
                    title  : options.title,
                    message: options.message,
                    status : options.status,
                    icon   : options.icon,
                    inputs : options.inputs,
                    operations: {
                        'submit': new Ui.ButtonIcon({
                            tooltip  : options.submit_tooltip,
                            title    : options.submit_title || 'Save settings',
                            icon     : options.submit_icon || 'fa-save',
                            onclick  : function() { self._submit( form ) }
                        })
                    }
                });
                self.$el.empty().append( form.$el );
            }).fail( function( response ) {
                self.$el.empty().append( new Ui.Message({
                    message     : 'Failed to load resource ' + self.url + '.',
                    status      : 'danger',
                    persistent  : true
                }).$el );
            });
        },

        _submit: function( form ) {
            var self = this;
            $.ajax( {
                url         : Galaxy.root + self.url,
                data        : JSON.stringify( form.data.create() ),
                type        : 'PUT',
                contentType : 'application/json'
            }).done( function( response ) {
                var success_message = { message: response.message, status: 'success' };
                if ( self.redirect ) {
                    window.location = self.redirect + '?' + $.param( success_message );
                } else {
                    form.data.matchModel( response, function ( input, input_id ) {
                        form.field_list[ input_id ].value( input.value );
                    });
                    form.message.update( success_message );
                }
            }).fail( function( response ) {
                form.message.update( { message: response.responseJSON.err_msg, status: 'danger' } );
            });
        }
    });

    return {
        View  : View
    };
});
