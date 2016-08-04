/**
 *  Renders tabs e.g. used in the Charts editor, behaves similar to repeat and section rendering
 */
define( [ 'utils/utils' ], function( Utils ) {
var View = Backbone.View.extend({
    initialize : function( options ) {
        var self = this;
        this.visible    = false;
        this.$nav       = null;
        this.$content   = null;
        this.first_tab  = null;
        this.current_id = null;
        this.list       = {};
        this.options = Utils.merge( options, {
            title_new   : '',
            operations  : null,
            onnew       : null,
            max         : null,
            onchange    : null
        });
        this.setElement( $( this._template( this.options ) ) );
        this.$nav           = this.$( '.tab-navigation' );
        this.$content       = this.$( '.tab-content' );
        this.$operations    = this.$nav.find( '.tab-operations' );

        // Renders tab operations
        if ( this.options.operations ) {
            $.each( this.options.operations, function( name, item ) {
                item.$el.prop( 'id', name );
                self.$operations.append( item.$el );
            });
        }

        // Allows user to add new tabs
        this.options.onnew && this.$nav.append( $( this._template_tab_new( this.options ) )
            .tooltip( { title: 'Add a new tab', placement: 'bottom', container: self.$el } )
            .on( 'click', function( e ) { self.options.onnew() } )
        );
        this.$tabnew = this.$nav.find( '.tab-new' );

        // Remove all tooltips on click
        this.$el.on( 'click', function() { $( '.tooltip' ).hide() } );
    },

    /** Returns current number of tabs */
    size: function() {
        return _.size( this.list );
    },

    /** Returns tab id for currently shown tab */
    current: function() {
        return this.$el.find( '.tab-pane.active' ).attr( 'id' );
    },

    /** Adds a new tab */
    add: function( options ) {
        var self = this;
        var id = options.id;
        var $tab_title   = $( this._template_tab( options ) );
        var $tab_content = $( '<div/>' ).attr( 'id', options.id ).addClass( 'tab-pane' );

        // hide new tab if maximum number of tabs has been reached
        this.list[ id ] = true;
        if ( this.options.max && this.size() >= this.options.max ) {
            this.$tabnew.hide();
        }

        // insert tab before new tab or as last tab
        if ( this.options.onnew ) {
            this.$tabnew.before( $tab_title );
        } else {
            this.$nav.append( $tab_title );
        }

        // assing delete callback if provided
        if ( options.ondel ) {
            $tab_title.find( '.tab-delete' ).tooltip( { title: 'Delete this tab', placement: 'bottom', container: self.$el } )
                                            .on( 'click', function() { options.ondel() } );
        } else {
            $tab_title.tooltip( { title: options.tooltip, placement: 'bottom', container: self.$el } );
        }
        $tab_title.on( 'click', function( e ) {
            e.preventDefault();
            options.onclick ? options.onclick() : self.show( id );
        });
        this.$content.append( $tab_content.append( options.$el ) );

        // assign current/first tab
        if ( this.size() == 1 ) {
            $tab_title.addClass( 'active' );
            $tab_content.addClass( 'active' );
            this.first_tab = id;
        }
        if ( !this.current_id ) {
            this.current_id = id;
        }
    },

    /** Delete tab */
    del: function( id ) {
        this.$( '#tab-' + id ).remove();
        this.$( '#' + id ).remove();
        this.first_tab = this.first_tab == id ? null : this.first_tab;
        this.first_tab != null && this.show( this.first_tab );
        this.list[ id ] && delete this.list[ id ];
        if ( this.size() < this.options.max ) {
            this.$el.find( '.ui-tabs-new' ).show();
        }
    },

    /** Delete all tabs */
    delRemovable: function() {
        for ( var id in this.list ) {
            this.del( id );
        }
    },

    /** Show tab view and highlight a tab by id */
    show: function( id ){
        this.$el.fadeIn( 'fast' );
        this.visible = true;
        if ( id ) {
            this.$( '#tab-' + this.current_id ).removeClass('active' );
            this.$( '#' + this.current_id ).removeClass('active' );
            this.$( '#tab-' + id ).addClass( 'active' );
            this.$( '#' + id ).addClass( 'active' );
            this.current_id = id;
        }
        this.options.onchange && this.options.onchange( id );
    },
    
    /** Hide tab view */
    hide: function(){
        this.$el.fadeOut( 'fast' );
        this.visible = false;
    },

    /** Hide operation by id */
    hideOperation: function( id ) {
        this.$nav.find( '#' + id ).hide();
    },

    /** Show operation by id */
    showOperation: function( id ) {
        this.$nav.find( '#' + id ).show();
    },

    /** Reassign an operation to a new callback */
    setOperation: function( id, callback ) {
        this.$nav.find( '#' + id ).off('click').on( 'click', callback );
    },

    /** Set/Get title */
    title: function( id, new_title ) {
        var $el = this.$( '#tab-title-text-' + id );
        new_title && $el.html( new_title );
        return $el.html();
    },

    /** Enumerate titles */
    retitle: function( new_title ) {
        var index = 0;
        for ( var id in this.list ) {
            this.title( id, ++index + ': ' + new_title );
        }
    },

    /** Main template */
    _template: function( options ) {
        return  $( '<div/>' ).addClass( 'ui-tabs tabbable tabs-left' )
                             .append( $( '<ul/>' ).addClass( 'tab-navigation nav nav-tabs' )
                                                  .append( $( '<div/>' ).addClass( 'tab-operations' ) ) )
                             .append( $( '<div/>' ).addClass( 'tab-content' ) );
    },

    /** Default tab templates */
    _template_tab: function( options ) {
        var $tmpl = $( '<li/>' ).addClass( 'tab-element' )
                                .attr( 'id', 'tab-' + options.id )
                                .append( $( '<a/>' ).attr( 'id', 'tab-title-link-' + options.id ) );
        var $href = $tmpl.find( 'a' );
        options.icon && $href.append( $( '<i/>' ).addClass( 'tab-icon fa' ).addClass( options.icon ) );
        $href.append( $( '<span/>' ).attr( 'id', 'tab-title-text-' + options.id )
                                    .addClass( 'tab-title-text' )
                                    .append( options.title ) );
        options.ondel && $href.append( $( '<i/>' ).addClass( 'tab-delete fa fa-minus-circle' ) );
        return $tmpl;
    },

    /** Template for 'new' tab */
    _template_tab_new: function( options ) {
        return  $( '<li/>' ).addClass( 'tab-new' )
                            .append( $( '<a/>' ).attr( 'href', 'javascript:void(0);' )
                                                .append( $( '<i/>' ).addClass( 'tab-icon fa fa-plus-circle' ) )
                                                .append( options.title_new ) );
    }
});

return {
    View : View
}

});
