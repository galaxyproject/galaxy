define([ 'utils/utils' ], function( Utils ) {
var View = Backbone.View.extend({
    initialize : function( options ) {
        var self = this;
        this.options = Utils.merge( options, {
            id      : Utils.uid(),
            min     : null,
            max     : null,
            step    : null,
            precise : false,
            split   : 10000
        } );

        // create new element
        this.setElement( this._template( this.options ) );

        // determine wether to use the slider
        this.useslider = this.options.max !== null && this.options.min !== null && this.options.max > this.options.min;

        // set default step size
        if ( this.options.step === null ) {
            this.options.step = 1.0;
            if ( this.options.precise && this.useslider ) {
                this.options.step = ( this.options.max - this.options.min ) / this.options.split;
            }
        }

        // create slider if min and max are defined properly
        if ( this.useslider ) {
            this.$slider = this.$( '#slider' );
            this.$slider.slider( this.options );
            this.$slider.on( 'slide', function ( event, ui ) {
                self.value( ui.value );
            });
        } else {
            this.$( '.ui-form-slider-text' ).css( 'width', '100%' );
        }

        // link text input field
        this.$text = this.$( '#text' );

        // set initial value
        this.options.value !== undefined && ( this.value( this.options.value ) );

        // add text field event
        var pressed = [];
        this.$text.on( 'change', function () {
            self.value( $( this ).val() );
        });
        this.$text.on( 'keyup', function( e ) {
            pressed[e.which] = false;
            self.options.onchange && self.options.onchange( $( this ).val() );
        });
        this.$text.on( 'keydown', function ( e ) {
            var v = e.which;
            pressed[ v ] = true;
            if ( self.options.is_workflow && pressed[ 16 ] && v == 52 ) {
                self.value( '$' )
                event.preventDefault();
            } else if (!( v == 8 || v == 9 || v == 13 || v == 37 || v == 39 || ( v >= 48 && v <= 57 && !pressed[ 16 ] ) || ( v >= 96 && v <= 105 )
                || ( ( v == 190 || v == 110 ) && $( this ).val().indexOf( '.' ) == -1 && self.options.precise )
                || ( ( v == 189 || v == 109 ) && $( this ).val().indexOf( '-' ) == -1 )
                || self._isParameter( $( this ).val() )
                || pressed[ 91 ] || pressed[ 17 ] ) ) {
                event.preventDefault();
            }
        });
    },

    /** Set and Return the current value
    */
    value : function ( new_val ) {
        if ( new_val !== undefined ) {
            if ( new_val !== null && new_val !== '' && !this._isParameter( new_val ) ) {
                isNaN( new_val ) && ( new_val = 0 );
                this.options.max !== null && ( new_val = Math.min( new_val, this.options.max ) );
                this.options.min !== null && ( new_val = Math.max( new_val, this.options.min ) );
            }
            this.$slider && this.$slider.slider( 'value', new_val );
            this.$text.val( new_val );
            this.options.onchange && this.options.onchange( new_val );
        }
        return this.$text.val();
    },

    /** Return true if the field contains a workflow parameter i.e. $('name')
    */
    _isParameter: function( value ) {
        return this.options.is_workflow && String( value ).substring( 0, 1 ) === '$';
    },

    /** Slider template
    */
    _template: function( options ) {
        return  '<div id="' + options.id + '" class="ui-form-slider">' +
                    '<input id="text" type="text" class="ui-form-slider-text"/>' +
                    '<div id="slider" class="ui-form-slider-element"/>' +
                '</div>';
    }
});

return {
    View : View
};
});