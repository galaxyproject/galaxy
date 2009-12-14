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
    // Make popup menus.
    make_popup_menus();
});

function make_popup_menus() 
{
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
        b.addClass( "popup" ).show();
    });
}

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
    var menu_element = $( "<ul id='" + button_element.attr('id') + "-menu'></ul>" );
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

// Returns the number of keys (elements) in an array/dictionary.
var array_length = function(an_array)
{
    if (an_array.length)
        return an_array.length;

    var count = 0;
    for (element in an_array)   
        count++;
    return count;
};

//
// Replace dbkey select box with text input box & autocomplete.
//
var replace_dbkey_select = function() 
{
    var select_elt = $('select[name=dbkey]');
    var start_value = select_elt.attr('value');
    if (select_elt.length != 0)
    {
        //
        // Set up text input + autocomplete element.
        //
        var text_input_elt = $("<input id='dbkey-input' type='text'></input>");
        text_input_elt.attr('size', 40);
        text_input_elt.attr('name', select_elt.attr('name'));
        text_input_elt.click( function()
        {
                // Show all. Also provide note that load is happening since this can be slow.
                var cur_value = $(this).attr('value');
                $(this).attr('value', 'Loading...');
                $(this).showAllInCache();
                $(this).attr('value', cur_value);
                $(this).select();
        });

        // Get options for dbkey for autocomplete.
        var dbkey_options = new Array();
        var dbkey_mapping = new Object();
        select_elt.children('option').each( function() 
        {
            // Get text, value for option.
            var text = $(this).text();    
            var value = $(this).attr('value');
    
            // Ignore values that are '?'
            if (value == '?')
                return;
    
            // Set options and mapping.
            dbkey_options.push( text );
            dbkey_mapping[ text ] = value;
    
            // If this is the start value, set value of input element.
            if ( value == start_value )
                text_input_elt.attr('value', text);
        });
        if ( text_input_elt.attr('value') == '' ) 
            text_input_elt.attr('value', 'Click to Search or Select Build');

        // Do autocomplete.
        var autocomplete_options = { selectFirst: false, autoFill: false, mustMatch: false, matchContains: true, max: 1000, minChars : 0, hideForLessThanMinChars : false };
        text_input_elt.autocomplete(dbkey_options, autocomplete_options);
        
        // Replace select with text input.
        select_elt.replaceWith(text_input_elt);   
        
        //
        // When form is submitted, change the text entered into the input to the corresponding value. If text doesn't correspond to value, remove it.
        //
        $('form').submit( function() 
        {
            var dbkey_text_input = $('#dbkey-input');
            if (dbkey_text_input.length != 0)
            {
                // Try to convert text to value.
                var cur_value = dbkey_text_input.attr('value');
                var new_value = dbkey_mapping[cur_value];
                if (new_value != null && new_value != undefined)
                    dbkey_text_input.attr('value', new_value);
                else
                {
                    // If there is a non-empty start value, use that; otherwise unknown.
                    if (start_value != "")
                        dbkey_text_input.attr('value', start_value);
                    else
                        dbkey_text_input.attr('value', '?');
                }
            }
        });
    }
} // end replace_dbkey_select()
