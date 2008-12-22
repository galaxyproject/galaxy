var hidden_width = 7;
var border_tweak = 9;

var jq = jQuery;

function ensure_dd_helper() {
    // Insert div that covers everything when dragging the borders
    if ( jq( "#DD-helper" ).length == 0 ) {
        $( "<div id='DD-helper'/>" ).css( {
            background: 'white', opacity: 0, zIndex: 9000,
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' 
        } ).appendTo( "body" ).hide();
    }
}

function make_left_panel( panel_el, center_el, border_el ) {
    var hidden = false;
    var saved_size = null;
    // Functions for managing panel
    resize = function( x ) {
        var oldx = x;
        if ( x < 0 ) x = 0;
        jq( panel_el ).css( "width", x );
        jq( border_el ).css( "left", oldx );
        jq( center_el ).css( "left", x+7 );
        if ( document.recalc ) { document.recalc() };
    };
    toggle = function() {
        if ( hidden ) {
            jq( border_el ).removeClass( "hover" );
            jq( border_el).animate( {left: saved_size }, "fast" );
            jq( panel_el ).css( "left", - saved_size ).show().animate( { "left": 0 }, "fast", function () {
                resize( saved_size );
                jq( border_el ).removeClass( "hidden" );
            });
            hidden = false;
        } else {
            saved_size = jq( border_el ).position().left;
            // Move center
            jq( center_el ).css( "left", hidden_width );
            if ( document.recalc ) { document.recalc() };
            jq( border_el).removeClass( "hover" );
            jq( panel_el ).animate( { left: - saved_size }, "fast" );
            jq( border_el ).animate( {left: -1 }, "fast", function() {
                jq( this ).addClass( "hidden" );
            });
            hidden = true;
        }
    };
    // Connect to elements
    jq( border_el ).hover( 
        function() { jq( this ).addClass( "hover" ) },
        function() { jq( this ).removeClass( "hover" ) }
    ).draggable( {
            start: function( _, ui ) { 
              jq( '#DD-helper' ).show();
            },
            stop: function( _, ui ) { 
              jq( '#DD-helper' ).hide();
              return false;
            },
            drag: function( _, ui ) {
                x = ui.position.left;
                // Limit range
                x = Math.min( 400, Math.max( 100, x ) );
                // Resize
                if ( hidden ) {
                    jq( panel_el ).css( "left", 0 );
                    jq( border_el ).removeClass( "hidden" );
                    hidden = false;
                }
                resize( x );
                // Constrain helper position
                ui.position.left = x;
                ui.position.top = $(this).data("draggable").originalPosition.top;
            },
            click: function() {
                toggle();
            }
        }
    ).find( "div" ).show();;
    var force_panel = function( op ) {
        if ( ( hidden && op == 'show' ) || ( ! hidden && op == 'hide' ) ) { 
            toggle();
        }
    }
    return { force_panel: force_panel };
};

function make_right_panel( panel_el, center_el, border_el ) {
    var hidden = false;
    var hidden_by_tool = false;
    var saved_size = null;    
    var resize = function( x ) {
        jq( panel_el ).css( "width", x );
        jq( center_el ).css( "right", x+9 );
        jq( border_el ).css( "right", x ).css( "left", "" )
        if ( document.recalc ) { document.recalc() };
    };
    var toggle = function() {
        if ( hidden ) {
            jq( border_el).removeClass( "hover" );
            jq( border_el ).animate( {right: saved_size }, "fast" );
            jq( panel_el ).css( "right", - saved_size ).show().animate( { "right": 0 }, "fast", function () {
                resize( saved_size );
                jq( border_el ).removeClass( "hidden" )
            });
            hidden = false;
        }
        else
        {
            saved_size = jq(document).width() - jq( border_el ).position().left - border_tweak;
            // Move center
            jq( center_el ).css( "right", hidden_width + 1 );
            if ( document.recalc ) { document.recalc() };
            // Hide border
            jq( border_el ).removeClass( "hover" );
            jq( panel_el ).animate( { right: - saved_size }, "fast" );
            jq(  border_el ).animate( { right: -1 }, "fast", function() {
                jq( this ).addClass( "hidden" )
            });
            hidden = true;
        }
        hidden_by_tool = false;
    };
    var handle_minwidth_hint = function( x ) {
        var space = jq( center_el ).width() - ( hidden ? saved_size : 0 );
        if ( space < x )
        {
            if ( ! hidden ) {
                toggle();
                hidden_by_tool = true
            }
        } else {
            if ( hidden_by_tool ) {
                toggle();
                hidden_by_tool = false;
            }
        }
    };
    jq( border_el ).hover( 
        function() { jq( this ).addClass( "hover" ) },
        function() { jq( this ).removeClass( "hover" ) }
    ).draggable( {
            start: function( _, ui ) {
                jq( '#DD-helper' ).show();
            },
            stop: function( _, ui ) {  
                x = ui.position.left;
                w = jq(window).width();
                // Limit range
                x = Math.min( w - 100, x );
                x = Math.max( w - 400, x );
                // Final resize
                resize( w - x - border_tweak );
                jq( '#DD-helper' ).hide();
                return false;
            },
            click: function() {
                toggle();
            },
            drag: function( _, ui ) {
                x = ui.position.left;
                w = jq(window).width(); 
                // Limit range
                x = Math.min( w - 100, x );
                x = Math.max( w - 400, x );
                // Resize
                if ( hidden ) {
                    jq( panel_el ).css( "right", 0 );
                    jq( border_el ).removeClass( "hidden" );
                    hidden = false;
                }
                resize( w - x - border_tweak );
                // Constrain helper position
                ui.position.left = x;
                ui.position.top = $(this).data("draggable").originalPosition.top;
            }
        }
    ).find( "div" ).show();
    var force_panel = function( op ) {
        if ( ( hidden && op == 'show' ) || ( ! hidden && op == 'hide' ) ) { 
            toggle();
        }
    }
    return { handle_minwidth_hint: handle_minwidth_hint, force_panel: force_panel };
};

// Modal dialog boxes

function hide_modal() {
    $(".dialog-box-container" ).fadeOut( function() { $("#overlay").hide(); } );
};

function show_modal( title, body, buttons, extra_buttons ) {
    $( ".dialog-box" ).find( ".title" ).html( title );
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
        body = $( "<img src='../images/yui/rel_interstitial_loading.gif')' />" );
    }
    $( ".dialog-box" ).find( ".body" ).html( body );
    if ( ! $(".dialog-box-container").is( ":visible" ) ) {
        $("#overlay").show();
        $(".dialog-box-container").fadeIn()
    }
};
    
// Popup -- is this up to date?

function make_popupmenu( button_element, options ) {
    var menu_element = $( "<div class='popupmenu'><div class='popupmenu-top'><div class='popupmenu-top-inner'/></div></div>" ).appendTo( "body" );
    $.each( options, function( k, v ) {
        $( "<div class='popupmenu-item' />" ).html( k ).click( v ).appendTo( menu_element );
    });
    var clean = function() {
        $(menu_element).unbind().hide();
        $("#popup-helper").unbind().hide();
    };
    var click = function() {
        var o = $(button_element).offset();
        $("#popup-helper").mousedown( clean ).show();
        $( menu_element ).click( clean ).css( { top: -1000 } ).show().css( {
            top: o.top + $(button_element).height() + 9,
            left: o.left + $(button_element).width() - $(menu_element).width()
        } );
    };
    $( button_element ).click( click );
};
