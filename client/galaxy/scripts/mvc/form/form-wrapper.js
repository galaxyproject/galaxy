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
                    status : options.status || 'warning',
                    icon   : options.icon,
                    inputs : options.inputs,
                    buttons: {
                        'submit': new Ui.Button({
                            tooltip  : options.submit_tooltip,
                            title    : options.submit_title || 'Save',
                            icon     : options.submit_icon || 'fa-save',
                            cls      : 'btn btn-primary ui-clear-float',
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
                var success_message = { message: response.message, status: 'success', persistent: false };
                if ( self.redirect ) {
                    window.location = Galaxy.root + self.redirect + '?' + $.param( success_message );
                } else {
                    form.data.matchModel( response, function ( input, input_id ) {
                        form.field_list[ input_id ].value( input.value );
                    });
                    self._showMessage( form, success_message );
                }
            }).fail( function( response ) {
                self._showMessage( form, { message: response.responseJSON.err_msg, status: 'danger', persistent: false } );
            });
        },

        _showMessage: function( form, options ) {
            var $panel = form.$el.parents().filter(function() {
                return [ 'auto', 'scroll' ].indexOf( $( this ).css( 'overflow' ) ) != -1;
            }).first();
            $panel.animate( { scrollTop : 0 }, 500 );
            form.message.update( options );
        }
    });

    return {
        View  : View
    };
});
