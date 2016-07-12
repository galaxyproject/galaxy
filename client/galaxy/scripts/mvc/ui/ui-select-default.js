/**
 *  This class creates/wraps a default html select field as backbone class.
 */
define([ 'utils/utils', 'mvc/ui/ui-buttons' ], function( Utils, Buttons ) {
var View = Backbone.View.extend({
    initialize: function( options ) {
        var self = this;
        this.data = [];
        this.model = options && options.model || new Backbone.Model({
            id          : Utils.uid(),
            cls         : 'ui-select',
            error_text  : 'No options available',
            empty_text  : 'Nothing selected',
            visible     : true,
            wait        : false,
            multiple    : false,
            searchable  : true,
            optional    : false,
            disabled    : false,
            onchange    : function(){}
        }).set( options );
        this.on( 'change', function() { self.model.get( 'onchange' )( self.value() ) } );
        this.listenTo( this.model, 'change:data', this._changeData, this );
        this.listenTo( this.model, 'change:disabled', this._changeDisabled, this );
        this.listenTo( this.model, 'change:wait', this._changeWait, this );
        this.listenTo( this.model, 'change:visible', this._changeVisible, this );
        this.listenTo( this.model, 'change:value', this._changeValue, this );
        this.listenTo( this.model, 'change:multiple change:searchable change:cls change:id', this.render, this );
        this.render();
    },

    render: function() {
        var self = this;
        this.model.get( 'searchable' ) ? this._renderSearchable() : this._renderClassic();
        this.$el.addClass( this.model.get( 'cls' ) )
                .attr( 'id', this.model.get( 'id' ) );
        this.$select.empty().addClass( 'select' )
                    .attr( 'id', this.model.get( 'id' ) + '_select' )
                    .prop( 'multiple', this.model.get( 'multiple' ) )
                    .on( 'change', function() {
                        self.value( self._getValue() );
                        self.trigger( 'change' );
                    });
        this._changeData();
        this._changeWait();
        this._changeVisible();
        this._changeDisabled();
    },

    /** Renders the classic multiple selection box */
    _renderClassic: function() {
        var self = this;
        this.$el.addClass( 'ui-select-multiple' )
                .append( this.$select      = $( '<select/>' ) )
                .append( this.$resize      = $( '<div/>' )
                .append( this.$resize_icon = $( '<i/>' ) ) );
        this.$resize_icon.addClass( 'fa fa-angle-double-right fa-rotate-45' );
        this.$resize.removeClass()
                    .addClass( 'icon-resize' )
                    .off( 'mousedown' ).on( 'mousedown', function( event ) {
                        var currentY = event.pageY;
                        var currentHeight = self.$select.height();
                        self.minHeight = self.minHeight || currentHeight;
                        $( '#dd-helper' ).show().on( 'mousemove', function( event ) {
                            self.$select.height( Math.max( currentHeight + ( event.pageY - currentY ), self.minHeight ) );
                        }).on( 'mouseup mouseleave', function() {
                            $( '#dd-helper' ).hide().off();
                        });
                    });
    },

    /** Renders the default select2 field */
    _renderSearchable: function() {
        var self = this;
        this.$el.append( this.$select   = $( '<div/>' ) )
                .append( this.$dropdown = $( '<div/>' ) );
        this.$dropdown.hide();
        if ( !this.model.get( 'multiple' ) ) {
            this.$dropdown.show().on( 'click', function() {
                self.$select.select2 && self.$select.select2( 'open' );
            });
        }
        this.all_button = null;
        if ( this.model.get( 'multiple' ) && this.model.get( 'searchable' ) ) {
            this.all_button = new Buttons.ButtonCheck({
                onclick: function() {
                    var new_value = [];
                    self.all_button.value() !== 0 && _.each( self.model.get( 'data' ), function( option ) {
                        new_value.push( option.value );
                    });
                    self.value( new_value );
                    self.trigger( 'change' );
                }
            });
            this.$el.prepend( this.all_button.$el );
        }
    },

    /** Updates the selection options */
    _changeData: function() {
        var self = this;
        this.data = [];
        if ( !this.model.get( 'multiple' ) && this.model.get( 'optional' ) ) {
            this.data.push( { value: '__null__', label: self.model.get( 'empty_text' ) } );
        }
        _.each( this.model.get( 'data' ), function( option ) {
            self.data.push( option );
        });
        if ( this.length() == 0 ) {
            this.data.push( { value: '__null__', label: this.model.get( 'error_text' ) } );
        }
        if ( this.model.get( 'searchable' ) ) {
            var data2 = [];
            _.each( this.data, function( option ) {
                data2.push( { id: option.value, text: option.label } );
            });
            this.$select.data( 'select2' ) && this.$select.select2( 'destroy' );
            this.$select.select2( { data: data2, closeOnSelect: !this.model.get( 'multiple' ), multiple: this.model.get( 'multiple' ) } );
            this.$( '.select2-container .select2-search input' ).off( 'blur' );
        } else {
            this.$select.find( 'option' ).remove();
            _.each( this.data, function( option ) {
                self.$select.append( $( '<option/>' ).attr( 'value', option.value ).html( _.escape( option.label ) ) );
            });
        }
        this.model.set( 'disabled', this.length() == 0 );
        this._changeValue();
    },

    /** Handles field enabling/disabling, usually used when no options are available */
    _changeDisabled: function() {
        if ( this.model.get( 'searchable' ) ) {
            this.$select.select2( this.model.get( 'disabled' ) ? 'disable' : 'enable' );
        } else {
            this.$select.prop( 'disabled', this.model.get( 'disabled' ) );
        }
    },

    /** Searchable fields may display a spinner e.g. while waiting for a server response */
    _changeWait: function() {
        if ( this.model.get( 'searchable' ) ) {
            this.$dropdown.removeClass()
                          .addClass( 'icon-dropdown fa' )
                          .addClass( this.model.get( 'wait' ) ? 'fa-spinner fa-spin' : 'fa-caret-down' );
        }
    },

    /** Handles field visibility */
    _changeVisible: function() {
        this.$el[ this.model.get( 'visible' ) ? 'show' : 'hide' ]();
        this.$select[ this.model.get( 'visible' ) ? 'show' : 'hide' ]();
    },

    /** Synchronizes the model value with the actually selected field value */
    _changeValue: function() {
        this._setValue( this.model.get( 'value' ) || null );
        if ( this.model.get( 'searchable' ) ) {
            if ( this._getValue() === null && !this.model.get( 'multiple' ) && !this.model.get( 'optional' ) ) {
                this._setValue( this.first() );
            }
            var value = this._getValue();
            this.all_button && this.all_button.value( $.isArray( value ) ? value.length : 0, this.length() );
        }
    },

    /** Return/Set current selection */
    value: function ( new_value ) {
        new_value !== undefined && this.model.set( 'value', new_value );
        return this._getValue();
    },

    /** Return the first select option */
    first: function() {
        return this.data.length > 0 ? this.data[ 0 ].value : null;
    },

    /** Check if a value is an existing option */
    exists: function( value ) {
        return _.findWhere( this.data, { value: value } );
    },

    /** Return the label/text of the current selection */
    text: function () {
        var v = this._getValue();
        var d = this.exists( $.isArray( v ) ? v[ 0 ] : v );
        return d ? d.label : '';
    },

    /** Show the select field */
    show: function() {
        this.model.set( 'visible', true );
    },

    /** Hide the select field */
    hide: function() {
        this.model.set( 'visible', false );
    },

    /** Show a spinner indicating that the select options are currently loaded */
    wait: function() {
        this.model.set( 'wait', true );
    },

    /** Hide spinner indicating that the request has been completed */
    unwait: function() {
        this.model.set( 'wait', false );
    },

    /** Returns true if the field is disabled */
    disabled: function() {
        return this.model.get( 'disabled' );
    },

    /** Enable the select field */
    enable: function() {
        this.model.set( 'disabled', false );
    },

    /** Disable the select field */
    disable: function() {
        this.model.set( 'disabled', true );
    },

    /** Update all available options at once */
    add: function( options, sorter ) {
        _.each( this.model.get( 'data' ), function( v ) {
            !_.findWhere( options, v ) && options.push( v );
        });
        sorter && options && options.sort( sorter );
        this.model.set( 'data', options );
    },

    /** Update available options */
    update: function( options ) {
        this.model.set( 'data', options );
    },

    /** Set the custom onchange callback function */
    setOnChange: function( callback ) {
        this.model.set( 'onchange', callback );
    },

    /** Number of available options */
    length: function() {
        return $.isArray( this.model.get( 'data' ) ) ? this.model.get( 'data' ).length : 0;
    },

    /** Set value to dom */
    _setValue: function( new_value ) {
        if ( new_value !== undefined ) {
            new_value = new_value !== null ? new_value : '__null__';
            if ( this.model.get( 'searchable' ) ) {
                this.$select.select2( 'val', this.model.get( 'multiple' ) && !$.isArray( new_value ) ? [ new_value ] : new_value );
            } else {
                this.$select.val( new_value );
            }
        }
    },

    /** Get value from dom */
    _getValue: function() {
        var val = this.model.get( 'searchable' ) ? this.$select.select2( 'val' ) : this.$select.val();
        return Utils.isEmpty( val ) || val == '' ? null : val;
    }
});

return {
    View: View
}

});
