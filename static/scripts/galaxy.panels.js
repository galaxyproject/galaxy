var hidden_width = 7;
var border_tweak = jQuery.browser.msie ? 14 : 9;

function make_left_panel( panel_el, center_el, border_el ) {
    var jq = jQuery;
    var hidden = false;
    var saved_size = null;
    // Functions for managing panel
    resize = function( x ) {
        var oldx = x;
        if ( x < 0 ) x = 0;
        jq( panel_el ).css( "width", x );
        jq( border_el ).css( "left", oldx );
        jq( center_el ).css( "left", x+7 );
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
                ui.draggable.pos[0] = x;
                ui.draggable.pos[1] = ui.options.co.top;
            },
            click: function() {
                toggle();
            }
        }
    ).find( "div" ).show();;
    
};

function make_right_panel( panel_el, center_el, border_el ) {
    var jq = jQuery;
    var hidden = false;
    var hidden_by_tool = false;
    var saved_size = null;    
    var resize = function( x ) {
        jq( panel_el ).css( "width", x );
        jq( center_el ).css( "right", x+9 );
        jq( border_el ).css( "right", x ).css( "left", "" )
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
        var space = q( center_el ).width() - ( hidden ? saved_size : 0 );
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
                ui.draggable.pos[0] = x;
                ui.draggable.pos[1] = ui.options.co.top;
            }
        }
    ).find( "div" ).show();;
};
