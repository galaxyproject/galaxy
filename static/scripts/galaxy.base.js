jQuery(document).ready( function() {
    // Links with confirmation
    jQuery( "a[@confirm]" ).click( function() {
        return confirm( jQuery(this).attr( "confirm"  ) )
    });
    jQuery( "div[@popupmenu]" ).each( function() {
        var options = {};
        $(this).find( "a" ).each( function() {
            var confirmtext = $(this).attr( "confirm" ),
                href = $(this).attr( "href" ),
                target = $(this).attr( "target" );
            options[ $(this).text() ] = function() {
                if ( !confirmtext || confirm( confirmtext ) ) {
                    var f = window;
                    if ( target == "_parent" ) {
                        f = window.parent;
                    }
                    f.location = href;
                }
            };
        });
        var b = $( "#" + $(this).attr( 'popupmenu' ) );
        make_popupmenu( b, options );
        $(this).remove();
        b.show();
    });
});

function ensure_popup_helper() {
    // And the helper below the popup menus
    if ( $( "#popup-helper" ).length == 0 ) {
        var e = $("<div id='popup-helper' style='background: white; opacity: 0.00; top: 0; left: 0; width: 100%; height: 100%; position: absolute; z-index: 15000;'></div>");
        if ( $.browser.ie ) {
            // Element will not capture drags in ie without nonzero opacity,
            // but causes flashing in firefox with nonzero opacity
            e.css( "opacity", "0.01" );
        }
        e.appendTo("body").hide();
    }
}

function make_popupmenu( button_element, options ) {
    ensure_popup_helper();
    var menu_element = $( "<div class='popupmenu'></div>" ).appendTo( "body" );
    $.each( options, function( k, v ) {
        $( "<div class='popupmenu-item' />" ).html( k ).click( v ).appendTo( menu_element );
    });
    var clean = function() {
        $(menu_element).unbind().hide();
        $("#popup-helper").unbind().hide();
    };
    var click = function( e ) {
        var o = $(button_element).offset();
        $("#popup-helper").mousedown( clean ).show();
        $( menu_element ).click( clean ).css( { top: -1000 } ).show().css( {
            top: e.pageY - 2,
            left: e.pageX - 2 // + $(button_element).width() - $(menu_element).width()
        } );
        return false;
    };
    $( button_element ).click( click );
};