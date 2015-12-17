define(['utils/utils'], function( Utils ) {
var View = Backbone.View.extend({
    visible     : false,
    initialize  : function( options ) {
        var self = this;
        this.options = Utils.merge( options, {
            id              : Utils.uid(),
            title           : '',
            icon            : '',
            buttons         : null,
            body            : null,
            scrollable      : true,
            nopadding       : false,
            operations      : null,
            placement       : 'bottom',
            cls             : 'ui-portlet',
            operations_flt  : 'right',
            collapsible     : false,
            collapsed       : false
        });
        this.setElement( this._template( this.options ) );

        // link content
        this.$body = this.$( '.portlet-body' );
        this.$title = this.$( '.portlet-title-text' );
        this.$header = this.$( '.portlet-header' );
        this.$content = this.$( '.portlet-content' );
        this.$footer = this.$( '.portlet-footer' );

        // set content padding
        if ( this.options.nopadding ) {
            this.$content.css( 'padding', '0px' );
            this.$body.css( 'padding', '0px' );
        }

        // append buttons
        this.$buttons = this.$( '.portlet-buttons' );
        if ( this.options.buttons ) {
            $.each( this.options.buttons, function( name, item ) {
                item.$el.prop( 'id', name );
                self.$buttons.append( item.$el );
            });
        } else {
            this.$buttons.remove();
        }

        // append operations
        this.$operations = this.$( '.portlet-operations' );
        if ( this.options.operations ) {
            $.each( this.options.operations, function( name, item ) {
                item.$el.prop( 'id', name );
                self.$operations.append( item.$el );
            });
        }

        // add body
        this.options.body && this.append( this.options.body );

        // make portlet collapsible
        this.collapsed = false;
        if ( this.options.collapsible ) {
            this.$title.addClass( 'no-highlight' ).css({
                'cursor'            : 'pointer',
                'text-decoration'   : 'underline'
            });
            this.$title.on( 'click', function() {
                if ( self.collapsed ) { self.expand(); } else { self.collapse(); }
            });
            this.options.collapsed && this.collapse();
        }
    },

    // append
    append: function( $el ) {
        this.$body.append( $el );
    },

    // remove all content
    empty: function() {
        this.$body.empty();
    },

    // header
    header: function() {
        return this.$header;
    },

    // body
    body: function() {
        return this.$body;
    },

    // footer
    footer: function() {
        return this.$footer;
    },

    // show
    show: function(){
        this.visible = true;
        this.$el.fadeIn( 'fast' );
    },

    // hide
    hide: function(){
        this.visible = false;
        this.$el.fadeOut( 'fast' );
    },

    // enable buttons
    enableButton: function( id ) {
        this.$buttons.find( '#' + id ).prop( 'disabled', false );
    },

    // disable buttons
    disableButton: function( id ) {
        this.$buttons.find( '#' + id ).prop( 'disabled', true );
    },

    // hide operation
    hideOperation: function( id ) {
        this.$operations.find( '#' + id ).hide();
    },

    // show operation
    showOperation: function( id ) {
        this.$operations.find( '#' + id ).show();
    },

    // set operation
    setOperation: function( id, callback ) {
        var $el = this.$operations.find( '#' + id );
        $el.off( 'click' );
        $el.on( 'click', callback );
    },

    // title
    title: function( new_title ) {
        var $el = this.$title;
        if ( new_title ) {
            $el.html( new_title );
        }
        return $el.html();
    },

    // collapse portlet
    collapse: function() {
        this.collapsed = true;
        this.$content.height( '0%' );
        this.$body.hide();
        this.$footer.hide();
        this.trigger( 'collapsed' );
    },

    // expand portlet
    expand: function() {
        this.collapsed = false;
        this.$content.height( '100%' );
        this.$body.fadeIn( 'fast' );
        this.$footer.fadeIn( 'fast' );
        this.trigger( 'expanded' );
    },

    // disable content access
    disable: function() {
        this.$( '.portlet-backdrop' ).show();
    },

    // enable content access
    enable: function() {
        this.$( '.portlet-backdrop' ).hide();
    },

    // fill regular modal template
    _template: function( options ) {
        var tmpl =  '<div id="' + options.id + '" class="' + options.cls + '">';
        if ( options.title ) {
            tmpl +=     '<div class="portlet-header">' +
                            '<div class="portlet-operations" style="float: ' + options.operations_flt + ';"/>' +
                            '<div class="portlet-title">';
            if ( options.icon ) {
                tmpl +=         '<i class="icon fa ' + options.icon + '">&nbsp;</i>';
            }
            tmpl +=             '<span class="portlet-title-text">' + options.title + '</span>' +
                            '</div>' +
                        '</div>';
        }
        tmpl +=         '<div class="portlet-content">';
        if ( options.placement == 'top' ) {
            tmpl +=         '<div class="portlet-buttons"/>';
        }
        tmpl +=             '<div class="portlet-body"/>';
        if ( options.placement == 'bottom' ) {
            tmpl +=         '<div class="portlet-buttons"/>';
        }
        tmpl +=         '</div>' +
                        '<div class="portlet-footer"/>' +
                        '<div class="portlet-backdrop"/>' +
                    '</div>';
        return tmpl;
    }
});
return {
    View : View
}
});
