define([
    'jquery',
], function( jQuery ){

"use strict";
// ============================================================================
var $ = jQuery;

// Panels
var MIN_PANEL_WIDTH = 160,
    MAX_PANEL_WIDTH = 800;

/**   */
var Panel = function( options ) {
    this.$panel = options.panel;
    this.$center = options.center;
    this.$drag = options.drag;
    this.$toggle = options.toggle;
    this.left = !options.right;
    this.hidden = false;
    this.hidden_by_tool = false;
    this.saved_size = null;
    this.init();
};

$.extend( Panel.prototype, {

    /**   */
    resize: function( x ) {
        this.$panel.css( "width", x );
        if ( this.left ) {
            this.$center.css( "left", x );
        } else {
            this.$center.css( "right", x );
        }
        // ie7-recalc.js
        if ( document.recalc ) { document.recalc(); }
    },

    /**   */
    do_toggle: function() {
        var self = this;
        if ( this.hidden ) {
            this.$toggle.removeClass( "hidden" );
            if ( this.left ) {
                this.$panel.css( "left", - this.saved_size ).show().animate( { "left": 0 }, "fast", function () {
                    self.resize( self.saved_size );
                });
            } else {
                this.$panel.css( "right", - this.saved_size ).show().animate( { "right": 0 }, "fast", function () {
                    self.resize( self.saved_size );
                });
            }
            self.hidden = false;
        } else {
            self.saved_size = this.$panel.width();
            if ( document.recalc ) { document.recalc(); }
            // Hide border
            if ( this.left ) {
                this.$panel.animate( { left: - this.saved_size }, "fast" );
            } else {
                this.$panel.animate( { right: - this.saved_size }, "fast" );
            }
            // self.resize(0);
            if ( this.left ) {
                this.$center.css( "left", 0 );
            } else {
                this.$center.css( "right", 0 );
            }

            self.hidden = true;
            self.$toggle.addClass( "hidden" );
        }
        this.hidden_by_tool = false;
    },

    /**   */
    handle_minwidth_hint: function( x ) {
        var space = this.$center.width() - ( this.hidden ? this.saved_size : 0 );
        if ( space < x )
        {
            if ( ! this.hidden ) {
                this.do_toggle();
                this.hidden_by_tool = true;
            }
        } else {
            if ( this.hidden_by_tool ) {
                this.do_toggle();
                this.hidden_by_tool = false;
            }
        }
    },

    /**   */
    force_panel: function( op ) {
        if ( ( this.hidden && op == 'show' ) || ( ! this.hidden && op == 'hide' ) ) {
            this.do_toggle();
        }
    },

    /**   */
    init: function() {
        var self = this,
            prevX;
        // Pull the collapse element out to body level so it is visible when panel is hidden
        self.$toggle.remove().appendTo( "body" );
        // Hide/show using toggle element
        self.$toggle.on( "click", function() { self.do_toggle(); } );

        // Resizing using drag element
        function move( e ){
            var delta = e.pageX - prevX;
            prevX = e.pageX;

            var oldWidth = self.$panel.width(),
                newWidth = ( self.left )?( oldWidth + delta ):( oldWidth - delta );
            // Limit range
            newWidth = Math.min( MAX_PANEL_WIDTH, Math.max( MIN_PANEL_WIDTH, newWidth ) );
            self.resize( newWidth );
        }
        this.$drag.on( "mousedown", function( e ) {
            prevX = e.pageX;
            $( '#DD-helper' ).show()
                .on( 'mousemove', move )
                .one( 'mouseup', function( e ){
                    $( this ).hide().off( 'mousemove', move );
                });
        });
        // TODO: remove global
        window.force_left_panel = function( x ) { self.force_panel( x ); };
        window.handle_minwidth_hint = function( x ) { self.handle_minwidth_hint( x ); };
    }
});

// ============================================================================
    return Panel;
});
