!function( exports, $ ){

"use strict"

var ensure_dd_helper = function () {
    // Insert div that covers everything when dragging the borders
    if ( $( "#DD-helper" ).length == 0 ) {
        $( "<div id='DD-helper'/>" ).css( {
            background: 'white', opacity: 0, zIndex: 9000,
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' 
        } ).appendTo( "body" ).hide();
    }
}

// Panels

var MIN_PANEL_WIDTH = 150,
    MAX_PANEL_WIDTH = 800;

var Panel = function( options ) {
    this.panel = options.panel;
    this.center = options.center;
    this.drag = options.drag;
    this.toggle = options.toggle;
    this.left = !options.right;
    this.hidden = false;
    this.hidden_by_tool = false;
    this.saved_size = null;
    this.init();
}
$.extend( Panel.prototype, {
    resize: function( x ) {
        $(this.panel).css( "width", x );
        if ( this.left ) {
            $(center).css( "left", x );
        } else {
            $(center).css( "right", x );
        }
        // ie7-recalc.js
        if ( document.recalc ) { document.recalc(); }
    },
    do_toggle: function() {
        var self = this;
        if ( this.hidden ) {
            $(this.toggle).removeClass( "hidden" );
            if ( this.left ) {
                $(this.panel).css( "left", - this.saved_size ).show().animate( { "left": 0 }, "fast", function () {
                    self.resize( self.saved_size );
                });
            } else {
                $(this.panel).css( "right", - this.saved_size ).show().animate( { "right": 0 }, "fast", function () {
                    self.resize( self.saved_size );
                });
            }
            self.hidden = false;
        } else {
            self.saved_size = $(this.panel).width();
            // Move center
            
            // $( center_el ).css( "right", $(border_el).innerWidth() + 1 );

            if ( document.recalc ) { document.recalc(); }
            // Hide border
            if ( this.left ) {
                $(this.panel).animate( { left: - this.saved_size }, "fast" );
            } else {
                $(this.panel).animate( { right: - this.saved_size }, "fast" );
            }
            // self.resize(0);
            if ( this.left ) {
                $(center).css( "left", 0 );
            } else {
                $(center).css( "right", 0 );
            }

            self.hidden = true;
            $(self.toggle).addClass( "hidden" );
        }
        this.hidden_by_tool = false;
    },
    handle_minwidth_hint: function( x ) {
        var space = $(this.center).width() - ( this.hidden ? this.saved_size : 0 );
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
    force_panel: function( op ) {
        if ( ( this.hidden && op == 'show' ) || ( ! this.hidden && op == 'hide' ) ) { 
            this.do_toggle();
        }
    },
    init: function() {
        var self = this;
        // Resizing using drag element
        $(this.drag).on( "dragstart", function( e, d ) {
            $( '#DD-helper' ).show();
            d.width = $(self.panel).width();
        }).on( "dragend", function() {  
            $( '#DD-helper' ).hide();
        }).on( "drag", function( e, d ) {
            var x;
            if ( self.left ) {
                x = d.width + d.deltaX;
            } else {
                x = d.width - d.deltaX;
            }
            // Limit range
            x = Math.min( MAX_PANEL_WIDTH, Math.max( MIN_PANEL_WIDTH, x ) );
            self.resize( x );
        });
        // Hide/show using toggle element
        $(self.toggle).on( "click", function() { self.do_toggle(); } );
    }
});

  
// Modal dialog boxes

function hide_modal() {
    $(".dialog-box-container" ).hide( 0, function() {
        $("#overlay").hide();
		$("#overlay").removeClass( "modal" );
        $( ".dialog-box" ).find( ".body" ).children().remove();
    } );
};

function show_modal() {
	$("#overlay").addClass( "modal" );
	_show_modal.apply( this, arguments );
}

function show_message() {
	_show_modal.apply( this, arguments );
}

function _show_modal( title, body, buttons, extra_buttons, init_fn ) {
    if ( title ) {
        $( ".dialog-box" ).find( ".title" ).html( title );
        $( ".dialog-box" ).find( ".unified-panel-header" ).show(); 
    } else {
        $( ".dialog-box" ).find( ".unified-panel-header" ).hide();   
    }
    var b = $( ".dialog-box" ).find( ".buttons" ).html( "" );
    if ( buttons ) {
        $.each( buttons, function( name, value ) {
            b.append( $( '<button/>' ).text( name ).click( value ) );
            b.append( " " );
        });
        b.show();
    } else {
        b.hide();
    }
    var b = $( ".dialog-box" ).find( ".extra_buttons" ).html( "" );
    if ( extra_buttons ) {
        $.each( extra_buttons, function( name, value ) {
            b.append( $( '<button/>' ).text( name ).click( value ) );
            b.append( " " );
        });
        b.show();
    } else {
        b.hide();
    }
    if ( body == "progress" ) {
        body = $("<img/>").attr("src", image_path + "/yui/rel_interstitial_loading.gif");
    }
    var body_elt = $( ".dialog-box" ).find( ".body" );
    // Clear min-width to allow for modal to take size of new body.
    body_elt.css("min-width", "0px");
    $( ".dialog-box" ).find( ".body" ).html( body );
    if ( ! $(".dialog-box-container").is( ":visible" ) ) {
        $("#overlay").show();
        $(".dialog-box-container").show();
    }
    // Fix min-width so that modal cannot shrink considerably if 
    // new content is loaded.
    body_elt.css("min-width", body_elt.width());
    if ( init_fn ) {
        init_fn();
    }
};

function show_in_overlay( options ) {
    var width = options.width || '600';
    var height = options.height || '400';
    var scroll = options.scroll || 'auto';
    $("#overlay-background").bind( "click.overlay", function() {
        hide_modal();
        $("#overlay-background").unbind( "click.overlay" );
    });
    show_modal( null, $( "<div style='margin: -5px;'><img id='close_button' style='position:absolute;right:-17px;top:-15px;src='" + image_path + "/closebox.png'><iframe style='margin: 0; padding: 0;' src='" + options.url + "' width='" + width + "' height='" + height + "' scrolling='" + scroll + "' frameborder='0'></iframe></div>" ) );
    $("#close_button").bind( "click", function() { hide_modal(); } );
}

function user_changed( user_email, is_admin ) {
    if ( user_email ) {
        $(".loggedin-only").show();
        $(".loggedout-only").hide();
        $("#user-email").text( user_email );
        if ( is_admin ) {
            $(".admin-only").show();
        }
    } else {
        $(".loggedin-only").hide();
        $(".loggedout-only").show();
        $(".admin-only").hide();
    }
}

// Masthead dropdown menus
$(function() {
    var $dropdowns = $("#masthead ul.nav > li.dropdown > .dropdown-menu");
    $("body").on( "click.nav_popups", function( e ) {
        $dropdowns.hide();
        $("#DD-helper").hide();
        // If the target is in the menu, treat normally
        if ( $(e.target).closest( "#masthead ul.nav > li.dropdown > .dropdown-menu" ).length ) {
            return;
        }
        // Otherwise, was the click in a tab
        var $clicked = $(e.target).closest( "#masthead ul.nav > li.dropdown" );
        if ( $clicked.length ) {
            $("#DD-helper").show();
            $clicked.children( ".dropdown-menu" ).show();
            e.preventDefault();
        }
    });
});

// Exports
exports.ensure_dd_helper = ensure_dd_helper;
exports.Panel = Panel;
exports.hide_modal = hide_modal;
exports.show_modal = show_modal;
exports.show_message = show_message;
exports.show_in_overlay = show_in_overlay;
exports.user_changed = user_changed;

}( window, window.jQuery );
