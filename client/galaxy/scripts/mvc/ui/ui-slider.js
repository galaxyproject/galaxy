define([ 'utils/utils' ], function( Utils ) {
    var View = Backbone.View.extend({
        initialize : function( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                id      : Utils.uid(),
                min     : null,
                max     : null,
                step    : null,
                precise : false,
                split   : 10000,
                value   : null
            }).set( options );

            // create new element
            this.setElement( this._template( this.model.attributes ) );
            this.$text      = this.$( '.ui-form-slider-text' );
            this.$slider    = this.$( '.ui-form-slider-element' );

            // add text field event
            var pressed = [];
            this.$text.on( 'change', function () {
                self.value( $( this ).val() );
            }).on( 'keyup', function( e ) {
                pressed[e.which] = false;
                self.model.get( 'onchange' ) && self.model.get( 'onchange' )( $( this ).val() );
            }).on( 'keydown', function ( e ) {
                var v = e.which;
                pressed[ v ] = true;
                if ( self.model.get( 'is_workflow' ) && pressed[ 16 ] && v == 52 ) {
                    self.value( '$' )
                    event.preventDefault();
                } else if (!( v == 8 || v == 9 || v == 13 || v == 37 || v == 39 || ( v >= 48 && v <= 57 && !pressed[ 16 ] ) || ( v >= 96 && v <= 105 )
                    || ( ( v == 190 || v == 110 ) && $( this ).val().indexOf( '.' ) == -1 && self.model.get( 'precise' ) )
                    || ( ( v == 189 || v == 109 ) && $( this ).val().indexOf( '-' ) == -1 )
                    || self._isParameter( $( this ).val() )
                    || pressed[ 91 ] || pressed[ 17 ] ) ) {
                    event.preventDefault();
                }
            });

            // add change listener
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
        },

        render: function() {
            var options = this.model.attributes;
            var useslider = options.max !== null && options.min !== null && options.max > options.min;
            var step = options.step;
            if ( !step ) {
                if ( options.precise && useslider ) {
                    step = ( options.max - options.min ) / options.split;
                } else {
                    step = 1.0;
                }
            }
            if ( useslider ) {
                this.$slider.slider( { min: options.min, max: options.max, step: step } )
                            .on( 'slide', function ( event, ui ) {
                                self.value( ui.value );
                            }).show();
                this.$text.css( 'width', 'auto' );
            } else {
                this.$slider.hide();
                this.$text.css( 'width', '100%' );
            }
        },

        /** Set and Return the current value */
        value : function ( new_val ) {
            var options = this.model.attributes;
            if ( new_val !== undefined ) {
                if ( new_val !== null && new_val !== '' && !this._isParameter( new_val ) ) {
                    isNaN( new_val ) && ( new_val = 0 );
                    options.max !== null && ( new_val = Math.min( new_val, options.max ) );
                    options.min !== null && ( new_val = Math.max( new_val, options.min ) );
                }
                this.$slider && this.$slider.slider( 'value', new_val );
                this.$text.val( new_val );
                options.onchange && options.onchange( new_val );
            }
            return this.$text.val();
        },

        /** Return true if the field contains a workflow parameter i.e. $('name') */
        _isParameter: function( value ) {
            return this.model.get( 'is_workflow' ) && String( value ).substring( 0, 1 ) === '$';
        },

        /** Slider template */
        _template: function( options ) {
            return  '<div id="' + options.id + '" class="ui-form-slider">' +
                        '<input type="text" class="ui-form-slider-text"/>' +
                        '<div class="ui-form-slider-element"/>' +
                    '</div>';
        }
    });

    return {
        View : View
    };
});