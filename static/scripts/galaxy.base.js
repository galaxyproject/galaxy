$.fn.makeAbsolute = function(rebase) {
    return this.each(function() {
        var el = $(this);
        var pos = el.position();
        el.css({
            position: "absolute",
            marginLeft: 0, marginTop: 0,
            top: pos.top, left: pos.left,
            right: $(window).width() - ( pos.left + el.width() )
        });
        if (rebase) {
            el.remove().appendTo("body");
        }
    });
}

jQuery(document).ready( function() {
    // Links with confirmation
    jQuery( "a[confirm]" ).click( function() {
        return confirm( jQuery(this).attr( "confirm"  ) )
    });
    jQuery( "div[popupmenu]" ).each( function() {
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
        $( "<div id='popup-helper'/>" ).css( {
            background: 'white', opacity: 0, zIndex: 15000,
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' 
        } ).appendTo( "body" ).hide();
    }
}

function make_popupmenu( button_element, options ) {
    ensure_popup_helper();
    var container_element = $(button_element);
    // if ( container_element.parent().hasClass( "combo-button" ) ) {
    //    container_element = container_element.parent();
    // }
    // ontainer_element).css( "position", "relative" );
    var menu_element = $( "<ul id='" + button_element.attr('id') + "-menu'></div>" );
    $.each( options, function( k, v ) {
        if ( v ) {
            $( "<li/>" ).html( k ).click( v ).appendTo( menu_element );
        } else {
            $( "<li class='head'/>" ).html( k ).appendTo( menu_element );
        }
    });
    var wrapper = $( "<div class='popmenu-wrapper'>" );
    wrapper.append( menu_element )
           .append( "<div class='overlay-border'>" )
           .css( "position", "absolute" )
           .appendTo( "body" )
           .hide();
    attach_popupmenu( button_element, wrapper );
};

function attach_popupmenu( button_element, wrapper ) {
    var clean = function() {
        wrapper.unbind().hide();
        $("#popup-helper").unbind( "click.popupmenu" ).hide();
        // $(document).unbind( "click.popupmenu" ); 
    };
    var click = function( e ) {
        var o = $(button_element).offset();
        $("#popup-helper").bind( "click.popupmenu", clean ).show();
        // $(document).bind( "click.popupmenu", clean );
        // Show off screen to get size right
        wrapper.click( clean ).css( { left: 0, top: -1000 } ).show();
        // console.log( e.pageX, $(document).scrollLeft() + $(window).width(), $(menu_element).width() );
        var x = e.pageX - wrapper.width() / 2 
        x = Math.min( x, $(document).scrollLeft() + $(window).width() - $(wrapper).width() - 20 );
        x = Math.max( x, $(document).scrollLeft() + 20 );
        // console.log( e.pageX, $(document).scrollLeft() + $(window).width(), $(menu_element).width() );
        
        
        wrapper.css( {
            top: e.pageY - 5,
            left: x
        } );
        return false;
    };
    $( button_element ).click( click );
};
