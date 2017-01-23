/**
    This is the main class of the form plugin. It is referenced as 'app' in lower level modules.
*/
define( [ 'utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'mvc/form/form-section', 'mvc/form/form-data' ],
function( Utils, Portlet, Ui, FormSection, FormData ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {
                initial_errors  : false,
                cls             : 'ui-portlet-limited',
                icon            : null,
                always_refresh  : true
            });
            this.setElement( '<div/>' );
            this.render();
        },

        /** Update available options */
        update: function( new_model ){
            var self = this;
            this.data.matchModel( new_model, function( node, input_id ) {
                var input = self.input_list[ input_id ];
                if ( input && input.options ) {
                    if ( !_.isEqual( input.options, node.options ) ) {
                        input.options = node.options;
                        var field = self.field_list[ input_id ];
                        if ( field.update ) {
                            var new_options = [];
                            if ( ( [ 'data', 'data_collection', 'drill_down' ] ).indexOf( input.type ) != -1 ) {
                                new_options = input.options;
                            } else {
                                for ( var i in node.options ) {
                                    var opt = node.options[ i ];
                                    if ( opt.length > 2 ) {
                                        new_options.push( { label: opt[ 0 ], value: opt[ 1 ] } );
                                    }
                                }
                            }
                            field.update( new_options );
                            field.trigger( 'change' );
                            Galaxy.emit.debug( 'form-view::update()', 'Updating options for ' + input_id );
                        }
                    }
                }
            });
        },

        /** Set form into wait mode */
        wait: function( active ) {
            for ( var i in this.input_list ) {
                var field = this.field_list[ i ];
                var input = this.input_list[ i ];
                if ( input.is_dynamic && field.wait && field.unwait ) {
                    field[ active ? 'wait' : 'unwait' ]();
                }
            }
        },

        /** Highlight and scroll to input element (currently only used for error notifications) */
        highlight: function ( input_id, message, silent ) {
            var input_element = this.element_list[ input_id ];
            if ( input_element ) {
                input_element.error( message || 'Please verify this parameter.' );
                this.portlet.expand();
                this.trigger( 'expand', input_id );
                if ( !silent ) {
                    var $panel = this.$el.parents().filter(function() {
                        return [ 'auto', 'scroll' ].indexOf( $( this ).css( 'overflow' ) ) != -1;
                    }).first();
                    $panel.animate( { scrollTop : $panel.scrollTop() + input_element.$el.offset().top - 120 }, 500 );
                }
            }
        },

        /** Highlights errors */
        errors: function( options ) {
            this.trigger( 'reset' );
            if ( options && options.errors ) {
                var error_messages = this.data.matchResponse( options.errors );
                for ( var input_id in this.element_list ) {
                    var input = this.element_list[ input_id ];
                    if ( error_messages[ input_id ] ) {
                        this.highlight( input_id, error_messages[ input_id ], true );
                    }
                }
            }
        },

        /** Render tool form */
        render: function() {
            var self = this;
            this.off('change');
            this.off('reset');
            // contains the dom field elements as created by the parameter factory i.e. form-parameters
            this.field_list = {};
            // contains input definitions/dictionaries as provided by the parameters to_dict() function through the api
            this.input_list = {};
            // contains the dom elements of each input element i.e. form-input which wraps the actual input field
            this.element_list = {};
            // converts the form into a json data structure
            this.data = new FormData.Manager( this );
            this._renderForm();
            this.data.create();
            this.options.initial_errors && this.errors( this.options );
            // add listener which triggers on checksum change, and reset the form input wrappers
            var current_check = this.data.checksum();
            this.on('change', function( input_id ) {
                var input = self.input_list[ input_id ];
                if ( !input || input.refresh_on_change || self.options.always_refresh ) {
                    var new_check = self.data.checksum();
                    if ( new_check != current_check ) {
                        current_check = new_check;
                        self.options.onchange && self.options.onchange();
                    }
                }
            });
            this.on('reset', function() {
                _.each( self.element_list, function( input_element ) { input_element.reset() } );
            });
            return this;
        },

        /** Renders/appends dom elements of the form */
        _renderForm: function() {
            $( '.tooltip' ).remove();
            this.message = new Ui.UnescapedMessage();
            this.section = new FormSection.View( this, { inputs: this.options.inputs } );
            this.portlet = new Portlet.View({
                icon        : this.options.icon,
                title       : this.options.title,
                cls         : this.options.cls,
                operations  : this.options.operations,
                buttons     : this.options.buttons,
                collapsible : this.options.collapsible,
                collapsed   : this.options.collapsed
            });
            this.portlet.append( this.message.$el );
            this.portlet.append( this.section.$el );
            this.$el.empty();
            this.options.inputs && this.$el.append( this.portlet.$el );
            this.options.message && this.message.update( { persistent: true, status: 'warning', message: this.options.message } );
            Galaxy.emit.debug( 'form-view::initialize()', 'Completed' );
        }
    });
});
