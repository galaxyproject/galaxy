/** This class creates/wraps a drill down element. */
define([ 'utils/utils', 'mvc/ui/ui-options' ], function( Utils, Options ) {

var View = Options.BaseIcons.extend({
    initialize: function( options ) {
        options.type     = options.display || 'checkbox';
        options.multiple = ( options.type == 'checkbox' );
        Options.BaseIcons.prototype.initialize.call( this, options );
    },

    /** Set states for selected values */
    _setValue: function ( new_value ) {
        Options.BaseIcons.prototype._setValue.call( this, new_value );
        if ( new_value !== undefined && new_value !== null && this.header_index ) {
            var self = this;
            var values = $.isArray( new_value ) ? new_value : [ new_value ];
            _.each( values, function( v ) {
                var list = self.header_index[ v ];
                _.each( list, function( element ) {
                    self._setState( element, true );
                });
            });
        }
    },

    /** Expand/collapse a sub group */
    _setState: function ( header_id, is_expanded ) {
        var $button = this.$( '.button-' + header_id );
        var $subgroup = this.$( '.subgroup-' + header_id );
        $button.data( 'is_expanded', is_expanded );
        if ( is_expanded ) {
            $subgroup.show();
            $button.removeClass( 'fa-plus-square' ).addClass( 'fa-minus-square' );
        } else {
            $subgroup.hide();
            $button.removeClass( 'fa-minus-square' ).addClass( 'fa-plus-square' );
        }
    },

    /** Template to create options tree */
    _templateOptions: function() {
        var self = this;
        this.header_index = {};

        // attach event handler
        function attach( $el, header_id ) {
            var $button = $el.find( '.button-' + header_id );
            $button.on( 'click', function() {
                self._setState( header_id, !$button.data( 'is_expanded' ) );
            });
        }

        // recursive function which iterates through options
        function iterate ( $tmpl, options, header ) {
            header = header || [];
            for ( i in options ) {
                var level = options[ i ];
                var has_options = level.options && level.options.length > 0;
                var new_header = header.slice( 0 );
                self.header_index[ level.value ] = new_header.slice( 0 );
                var $group = $( '<div/>' );
                if ( has_options ) {
                    var header_id = Utils.uid();
                    var $button = $( '<span/>' ).addClass( 'button-' + header_id ).addClass( 'ui-drilldown-button fa fa-plus-square' );
                    var $subgroup = $( '<div/>' ).addClass( 'subgroup-' + header_id ).addClass( 'ui-drilldown-subgroup' );
                    $group.append( $( '<div/>' )
                                        .append( $button )
                                        .append( self._templateOption( { label: level.name, value: level.value } ) ) );
                    new_header.push( header_id );
                    iterate ( $subgroup, level.options, new_header );
                    $group.append( $subgroup );
                    attach( $group, header_id );
                } else {
                    $group.append( self._templateOption( { label: level.name, value: level.value } ) );
                }
                $tmpl.append( $group );
            }
        }

        // iterate through options and create dom
        var $tmpl = $( '<div/>' );
        iterate( $tmpl, this.model.get( 'data' ) );
        return $tmpl;
    },

    /** Template for drill down view */
    _template: function() {
        return $( '<div/>' ).addClass( 'ui-options-list drilldown-container' ).attr( 'id', this.model.id );
    }
});

return {
    View: View
}

});
