$(document).ready(function() {
    replace_big_select_inputs();
});

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
};

function ensure_popup_helper() {
    // And the helper below the popup menus
    if ( $( "#popup-helper" ).length === 0 ) {
        $( "<div id='popup-helper'/>" ).css( {
            background: 'white', opacity: 0, zIndex: 15000,
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' 
        } ).appendTo( "body" ).hide();
    }
}

function attach_popupmenu( button_element, wrapper ) {
    var clean = function() {
        wrapper.unbind().hide();
        $("#popup-helper").unbind( "click.popupmenu" ).hide();
        // $(document).unbind( "click.popupmenu" ); 
    };
    var click = function( e ) {
        // var o = $(button_element).offset();
        $("#popup-helper").bind( "click.popupmenu", clean ).show();
        // $(document).bind( "click.popupmenu", clean );
        // Show off screen to get size right
        wrapper.click( clean ).css( { left: 0, top: -1000 } ).show();
        // console.log( e.pageX, $(document).scrollLeft() + $(window).width(), $(menu_element).width() );
        var x = e.pageX - wrapper.width() / 2 ;
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
}

function make_popupmenu( button_element, options ) {
    ensure_popup_helper();
    // var container_element = $(button_element);
    // if ( container_element.parent().hasClass( "combo-button" ) ) {
    //    container_element = container_element.parent();
    // }
    // container_element).css( "position", "relative" );
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
}

function make_popup_menus() {
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
                    } else if ( target == "_top" ) {
                        f = window.top;
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

// Returns the number of keys (elements) in an array/dictionary.
function array_length(an_array) {
    if (an_array.length) {
        return an_array.length;
    }

    var count = 0;
    for (var element in an_array) {
        count++;
    }
    return count;
}

// Alphanumeric/natural sort fn
function naturalSort(a, b){
    // setup temp-scope variables for comparison evauluation
    var re = /(-?[0-9\.]+)/g,
        x = a.toString().toLowerCase() || '',
        y = b.toString().toLowerCase() || '',
        nC = String.fromCharCode(0),
        xN = x.replace( re, nC + '$1' + nC ).split(nC),
        yN = y.replace( re, nC + '$1' + nC ).split(nC),
        xD = (new Date(x)).getTime(),
        yD = xD ? (new Date(y)).getTime() : null;
    // natural sorting of dates
    if ( yD )
        if ( xD < yD ) return -1;
        else if ( xD > yD ) return 1;
    // natural sorting through split numeric strings and default strings
    for( var cLoc = 0, numS = Math.max(xN.length, yN.length); cLoc < numS; cLoc++ ) {
        oFxNcL = parseFloat(xN[cLoc]) || xN[cLoc];
        oFyNcL = parseFloat(yN[cLoc]) || yN[cLoc];
        if (oFxNcL < oFyNcL) return -1;
        else if (oFxNcL > oFyNcL) return 1;
    }
    return 0;
}

// Replace select box with a text input box + autocomplete.
// TODO: make work with selects where refresh_on_change=True and refresh_on_change_values="..."
function replace_big_select_inputs(min_length) {
    // To do replace, jQuery's autocomplete plugin must be loaded.
    if (typeof jQuery().autocomplete == "undefined")
        return;
    
    // Set default for min_length.
    if (min_length === undefined)
        min_length = 20;
    
    $('select').each( function() {
        var select_elt = $(this);
        // Skip if # of options < min length.
        if (select_elt.find('option').length < min_length)
            return;

        // Replace select with text + autocomplete.
        var start_value = select_elt.attr('value');
        
        // Set up text input + autocomplete element.
        var text_input_elt = $("<input type='text' class='text-and-autocomplete-select'></input>");
        text_input_elt.attr('size', 40);
        text_input_elt.attr('name', select_elt.attr('name'));
        text_input_elt.attr('id', select_elt.attr('id'));
        text_input_elt.click( function() {
            // Show all. Also provide note that load is happening since this can be slow.
            var cur_value = $(this).attr('value');
            $(this).attr('value', 'Loading...');
            $(this).showAllInCache();
            $(this).attr('value', cur_value);
            $(this).select();
        });

        // Get options for select for autocomplete.
        var select_options = [];
        var select_mapping = {};
        select_elt.children('option').each( function() {
            // Get text, value for option.
            var text = $(this).text();
            var value = $(this).attr('value');

            // Set options and mapping. Mapping is (i) [from text to value] AND (ii) [from value to value]. This
            // enables a user to type the value directly rather than select the text that represents the value. 
            select_options.push( text );
            select_mapping[ text ] = value;
            select_mapping[ value ] = value;

            // If this is the start value, set value of input element.
            if ( value == start_value ) {
                text_input_elt.attr('value', text);
            }
        });
        
        // Set initial text if it's empty.
        if ( start_value == '' || start_value == '?') {
            text_input_elt.attr('value', 'Click to Search or Select');
        }
        
        // Sort option list
        select_options = select_options.sort(naturalSort);
        
        // Do autocomplete.
        var autocomplete_options = { selectFirst: false, autoFill: false, mustMatch: false, matchContains: true, max: 1000, minChars : 0, hideForLessThanMinChars : false };
        text_input_elt.autocomplete(select_options, autocomplete_options);

        // Replace select with text input.
        select_elt.replaceWith(text_input_elt);
        
        // Set trigger to replace text with value when element's form is submitted. If text doesn't correspond to value, default to start value.
        var submit_hook = function() {
            // Try to convert text to value.
            var cur_value = text_input_elt.attr('value');
            var new_value = select_mapping[cur_value];
            if (new_value !== null && new_value !== undefined) {
                text_input_elt.attr('value', new_value);
            } 
            else {
                // If there is a non-empty start value, use that; otherwise unknown.
                if (start_value != "") {
                    text_input_elt.attr('value', start_value);
                } else {
                    // This is needed to make the DB key work.
                    text_input_elt.attr('value', '?');
                }
            }
        };
        text_input_elt.parents('form').submit( function() { submit_hook(); } );
        
        // Add custom event so that other objects can execute name --> value conversion whenever they want.
        $(document).bind("convert_dbkeys", function() { submit_hook(); } );
        
        // If select is refresh on change, mirror this behavior.
        if (select_elt.attr('refresh_on_change') == 'true')
        {
            // Get refresh vals.
            var refresh_vals = select_elt.attr('refresh_on_change_values');
            if (refresh_vals !== undefined)
                refresh_vals = refresh_vals.split(",")
            text_input_elt.keyup( function( e ) 
            {
                if ( ( e.keyCode == 13 ) && // Return Key
                     ( return_key_pressed_for_autocomplete == true ) ) // Make sure return key was for autocomplete.
                {
                    //
                    // If value entered can be matched to value, do so and refresh by submitting parent form.
                    //
                    
                    // Get new value and see if it can be matched.
                    var cur_value = text_input_elt.attr('value');
                    var new_value = select_mapping[cur_value];
                    if (new_value !== null && new_value !== undefined) 
                    {
                        // Do refresh if new value is refresh value or if there are no refresh values.
                        refresh = false;
                        if (refresh_vals !== undefined)
                        {
                            for (var i= 0; i < refresh_vals.length; i++ )
                                if (new_value == refresh_vals[i])
                                {
                                    refresh = true;
                                    break;
                                }
                        }
                        else
                            // Refresh for all values.
                            refresh = true;

                        if (refresh)
                        {
                            text_input_elt.attr('value', new_value);
                            text_input_elt.parents('form').submit();
                        }
                    }
                }
            });
        }
    });
}

// Edit and save text asynchronously.
function async_save_text(click_to_edit_elt, text_elt_id, save_url, text_parm_name, num_cols, use_textarea, num_rows, on_start, on_finish) {
    // Set defaults if necessary.
    if (num_cols === undefined) {
        num_cols = 30;
    }
    if (num_rows === undefined) {
        num_rows = 4;
    }
    
    // Set up input element.
    $("#" + click_to_edit_elt).live( "click", function() {
        // Check if this is already active
        if ( $("#renaming-active").length > 0) {
            return;
        }
        var text_elt = $("#" + text_elt_id),
            old_text = text_elt.text(),
            t;
            
        if (use_textarea) {
            t = $("<textarea></textarea>").attr({ rows: num_rows, cols: num_cols }).text( old_text );
        } else {
            t = $("<input type='text'></input>").attr({ value: old_text, size: num_cols });
        }
        t.attr("id", "renaming-active");
        t.blur( function() {
            $(this).remove();
            text_elt.show();
            if (on_finish) {
                on_finish(t);
            }
        });
        t.keyup( function( e ) {
            if ( e.keyCode === 27 ) {
                // Escape key
                $(this).trigger( "blur" );
            } else if ( e.keyCode === 13 ) {
                // Enter key submits
                var ajax_data = {};
                ajax_data[text_parm_name] = $(this).val();
                $(this).trigger( "blur" );
                $.ajax({
                    url: save_url,
                    data: ajax_data,
                    error: function() { 
                        alert( "Text editing for elt " + text_elt_id + " failed" );
                        // TODO: call finish or no? For now, let's not because error occurred.
                    },
                    success: function(processed_text) {
                        // Set new text and call finish method.
                        text_elt.text( processed_text );
                        if (on_finish) {
                            on_finish(t);
                        }
                    }
                });
            }
        });
        
        if (on_start) {
            on_start(t);
        }
        // Replace text with input object and focus & select.
        text_elt.hide();
        t.insertAfter( text_elt );
        t.focus();
        t.select();
        
        return;
    });
}

function init_history_items(historywrapper, noinit, nochanges) {

    var action = function() {
        // Load saved state and show as necessary
        try {
            var stored = $.jStore.store("history_expand_state");
            if (stored) {
                for (var id in stored) {
                    $("#" + id + " div.historyItemBody" ).show();
                }
            }
        } catch(err) {
            // Something was wrong with values in storage, so clear storage
            $.jStore.remove("history_expand_state");
        }

        // If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        if ( $.browser.mozilla ) {
            $( "div.historyItemBody" ).each( function() {
                if ( ! $(this).is( ":visible" ) ) $(this).find( "pre.peek" ).css( "overflow", "hidden" );
            })
        }
        
        historywrapper.each( function() {
            var id = this.id;
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).find( ".historyItemTitleBar > .historyItemTitle" ).wrap( "<a href='javascript:void(0);'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    // Hiding stuff here
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ); }
                    body.slideUp( "fast" );
                    
                    if (!nochanges) { // Ignore embedded item actions
                        // Save setting
                        var prefs = $.jStore.store("history_expand_state");
                        if (prefs) {
                            delete prefs[id];
                            $.jStore.store("history_expand_state", prefs);
                        }
                    }
                } else {
                    // Showing stuff here
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    
                    if (!nochanges) {
                        // Save setting
                        var prefs = $.jStore.store("history_expand_state");
                        if (prefs === undefined) { prefs = {}; }
                        prefs[id] = true;
                        $.jStore.store("history_expand_state", prefs);
                    }
                }
                return false;
            });
        });
        
        // Generate 'collapse all' link
        $("#top-links > a.toggle").click( function() {
            var prefs = $.jStore.store("history_expand_state");
            if (prefs === undefined) { prefs = {}; }
            $( "div.historyItemBody:visible" ).each( function() {
                if ( $.browser.mozilla ) {
                    $(this).find( "pre.peek" ).css( "overflow", "hidden" );
                }
                $(this).slideUp( "fast" );
                if (prefs) {
                    delete prefs[$(this).parent().attr("id")];
                }
            });
            $.jStore.store("history_expand_state", prefs);
        }).show();
    }
    
    if (noinit) {
        action();
    } else {
        // Load jStore for local storage
        $.jStore.init("galaxy"); // Auto-select best storage
        $.jStore.engineReady(function() {
            action();
        });
    }
}

$(document).ready( function() {
    // Links with confirmation
    $( "a[confirm]" ).click( function() {
        return confirm( $(this).attr("confirm") );
    });
    // Tooltips
    if ( $.fn.tipsy ) {
        $(".tooltip").tipsy( { gravity: 's' } );
    }
    // Make popup menus.
    make_popup_menus();
});
