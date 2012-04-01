// IE doesn't implement Array.indexOf
if (!Array.indexOf) {
    Array.prototype.indexOf = function(obj) {
        for (var i = 0, len = this.length; i < len; i++) {
            if (this[i] == obj) {
                return i;
            }
        }
        return -1;
    };
}

// Returns the number of keys (elements) in an array/dictionary.
function obj_length(obj) {
    if (obj.length !== undefined) {
        return obj.length;
    }

    var count = 0;
    for (var element in obj) {
        count++;
    }
    return count;
}

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

function make_popupmenu(button_element, initial_options) {
    
    /*  Use the $.data feature to store options with the link element.
        This allows options to be changed at a later time 
    */
    var element_menu_exists = (button_element.data("menu_options"));
    button_element.data("menu_options", initial_options);
    // If element already has menu, nothing else to do since HTML and actions are already set.
    if (element_menu_exists) { return; }
    button_element.bind("click.show_popup", function(e) {
        // Close existing visible menus
        $(".popmenu-wrapper").remove();
        
        // Need setTimeouts so clicks don't interfere with each other        
        setTimeout( function() {
            // Dynamically generate the wrapper holding all the selectable options of the menu.
            var menu_element = $( "<ul class='dropdown-menu' id='" + button_element.attr('id') + "-menu'></ul>" );
            var options = button_element.data("menu_options");
            if (obj_length(options) <= 0) {
                $("<li>No Options.</li>").appendTo(menu_element);
            }
            $.each( options, function( k, v ) {
                if (v) {
                    menu_element.append( $("<li></li>").append( $("<a href='#'></a>").html(k).click(v) ) );
                } else {
                    menu_element.append( $("<li></li>").addClass( "head" ).append( $("<a href='#'></a>").html(k) ) );
                }
            });
            var wrapper = $( "<div class='popmenu-wrapper' style='position: absolute;left: 0; top: -1000;'></div>" ).append( menu_element ).appendTo( "body" );
                   
            var x = e.pageX - wrapper.width() / 2 ;
            x = Math.min( x, $(document).scrollLeft() + $(window).width() - $(wrapper).width() - 5 );
            x = Math.max( x, $(document).scrollLeft() + 5 );

            wrapper.css( {
               top: e.pageY,
               left: x
            } );
        }, 10);
        
        setTimeout( function() {
            // Bind click event to current window and all frames to remove any visible menus
            // Bind to document object instead of window object for IE compat
            var close_popup = function(el) {
                $(el).bind("click.close_popup", function() {
                    $(".popmenu-wrapper").remove();
                    el.unbind("click.close_popup");
                });
            };
            close_popup( $(window.document) ); // Current frame
            close_popup( $(window.top.document) ); // Parent frame
            for (var frame_id = window.top.frames.length; frame_id--;) { // Sibling frames
                var frame = $(window.top.frames[frame_id].document);
                close_popup(frame);
            }
        }, 50);
        
        return false;
    });
    
}

function make_popup_menus() {
    jQuery( "div[popupmenu]" ).each( function() {
        var options = {};
        var menu = $(this);
        menu.find( "a" ).each( function() {
            var link = $(this),
                link_dom = link.get(0);
            var confirmtext = link_dom.getAttribute( "confirm" ),
                href = link_dom.getAttribute( "href" ),
                target = link_dom.getAttribute( "target" );
            if (!href) {
                options[ link.text() ] = null;
            } else {
                options[ link.text() ] = function() {
                    if ( !confirmtext || confirm( confirmtext ) ) {
                        var f;
                        if ( target == "_parent" ) {
                            window.parent.location = href;
                        } else if ( target == "_top" ) {
                            window.top.location = href;
                        } else if ( target == "demo" ) {
                            // Http request target is a window named
                            // demolocal on the local box
                            if ( f == undefined || f.closed ) {
                                f = window.open( href,target );
                                f.creator = self;
                            };
                        } else {
                            window.location = href;
                        };
                    };
                };
            };
        });
        var box = $( "#" + menu.attr( 'popupmenu' ) );
        
        // For menus with clickable link text, make clicking on the link go through instead
        // of activating the popup menu
        box.find("a").bind("click", function(e) {
            e.stopPropagation(); // Stop bubbling so clicking on the link goes through
            return true;
        });
        
        make_popupmenu(box, options);
        box.addClass("popup");
        menu.remove();
    });
}

// Alphanumeric/natural sort fn
function naturalSort(a, b) {
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
    if ( yD ) {
        if ( xD < yD ) { return -1; }
        else if ( xD > yD ) { return 1; }
    }
    // natural sorting through split numeric strings and default strings
    var oFxNcL, oFyNcL;
    for ( var cLoc = 0, numS = Math.max(xN.length, yN.length); cLoc < numS; cLoc++ ) {
        oFxNcL = parseFloat(xN[cLoc]) || xN[cLoc];
        oFyNcL = parseFloat(yN[cLoc]) || yN[cLoc];
        if (oFxNcL < oFyNcL) { return -1; }
        else if (oFxNcL > oFyNcL) { return 1; }
    }
    return 0;
}

// Replace select box with a text input box + autocomplete.
function replace_big_select_inputs(min_length, max_length) {
    // To do replace, jQuery's autocomplete plugin must be loaded.
    if (!jQuery().autocomplete) {
        return;
    }
    
    // Set default for min_length and max_length
    if (min_length === undefined) {
        min_length = 20;
    }
    if (max_length === undefined) {
        max_length = 3000;
    }
    
    $('select').each( function() {
        var select_elt = $(this);
        // Make sure that options is within range.
        var num_options = select_elt.find('option').length;
        if ( (num_options < min_length) || (num_options > max_length) ) {
            return;
        }
            
        // Skip multi-select because widget cannot handle multi-select.
        if (select_elt.attr('multiple') === 'multiple') {
            return;
        }
            
        if (select_elt.hasClass("no-autocomplete")) {
            return;
        }
        
        // Replace select with text + autocomplete.
        var start_value = select_elt.attr('value');
        
        // Set up text input + autocomplete element.
        var text_input_elt = $("<input type='text' class='text-and-autocomplete-select'></input>");
        text_input_elt.attr('size', 40);
        text_input_elt.attr('name', select_elt.attr('name'));
        text_input_elt.attr('id', select_elt.attr('id'));
        text_input_elt.click( function() {
            // Show all. Also provide note that load is happening since this can be slow.
            var cur_value = $(this).val();
            $(this).val('Loading...');
            $(this).showAllInCache();
            $(this).val(cur_value);
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
        if ( start_value === '' || start_value === '?') {
            text_input_elt.attr('value', 'Click to Search or Select');
        }
        
        // Sort dbkey options list only.
        if (select_elt.attr('name') == 'dbkey') {
            select_options = select_options.sort(naturalSort);
        }
        
        // Do autocomplete.
        var autocomplete_options = { selectFirst: false, autoFill: false, mustMatch: false, matchContains: true, max: max_length, minChars : 0, hideForLessThanMinChars : false };
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
            } else {
                // If there is a non-empty start value, use that; otherwise unknown.
                if (start_value !== "") {
                    text_input_elt.attr('value', start_value);
                } else {
                    // This is needed to make the DB key work.
                    text_input_elt.attr('value', '?');
                }
            }
        };
        text_input_elt.parents('form').submit( function() { submit_hook(); } );
        
        // Add custom event so that other objects can execute name --> value conversion whenever they want.
        $(document).bind("convert_to_values", function() { submit_hook(); } );
        
        // If select is refresh on change, mirror this behavior.
        if (select_elt.attr('refresh_on_change') == 'true') {
            // Get refresh vals.
            var ref_on_change_vals = select_elt.attr('refresh_on_change_values'),
                last_selected_value = select_elt.attr("last_selected_value");
            if (ref_on_change_vals !== undefined) {
                ref_on_change_vals = ref_on_change_vals.split(',');
            }
            // Function that attempts to refresh based on the value in the text element.
            var try_refresh_fn = function() {
                // Get new value and see if it can be matched.
                var new_value = select_mapping[text_input_elt.attr('value')];
                if (last_selected_value !== new_value && new_value !== null && new_value !== undefined) {
                    if (ref_on_change_vals !== undefined && $.inArray(new_value, ref_on_change_vals) === -1 && $.inArray(last_selected_value, ref_on_change_vals) === -1) {
                        return;
                    }
                    text_input_elt.attr('value', new_value);
                    $(window).trigger("refresh_on_change");
                    text_input_elt.parents('form').submit();
                }
            };
            
            // Attempt refresh if (a) result event fired by autocomplete (indicating autocomplete occurred) or (b) on keyup (in which
            // case a user may have manually entered a value that needs to be refreshed).
            text_input_elt.bind("result", try_refresh_fn);
            text_input_elt.keyup( function(e) {
                if (e.keyCode === 13) { // Return key
                    try_refresh_fn();
                }
            });
            
            // Disable return key so that it does not submit the form automatically. This is done because element should behave like a 
            // select (enter = select), not text input (enter = submit form).
            text_input_elt.keydown( function(e) {
                if (e.keyCode === 13) { // Return key
                    return false;
                }
            });
        }
    });
}

/**
 * Make an element with text editable: (a) when user clicks on text, a textbox/area 
 * is provided for editing; (b) when enter key pressed, element's text is set and on_finish
 * is called.
 */
// TODO: use this function to implement async_save_text (implemented below).
$.fn.make_text_editable = function(config_dict) {
    // Get config options.
    var num_cols = ("num_cols" in config_dict ? config_dict.num_cols : 30),
        num_rows = ("num_rows" in config_dict ? config_dict.num_rows : 4),
        use_textarea = ("use_textarea" in config_dict ? config_dict.use_textarea : false),
        on_finish = ("on_finish" in config_dict ? config_dict.on_finish : null),
        help_text = ("help_text" in config_dict ? config_dict.help_text : null);
        
    
    // Add element behavior.
    var container = $(this);
    container.addClass("editable-text").click(function(e) {
        // If there's already an input element, editing is active, so do nothing.
        if ($(this).children(":input").length > 0) {
            return;
        }
        
        container.removeClass("editable-text");
        
        // Handler for setting element text.
        var set_text = function(new_text) {
            container.find(":input").remove();
            
            if (new_text != "") {
                container.text(new_text);
            }
            else {
                // No text; need a line so that there is a click target.
                container.html("<br>");
            }
            container.addClass("editable-text");

            if (on_finish) {
                on_finish(new_text);
            }
        };
        
        // Create input element(s) for editing.
        var cur_text = container.text(),
            input_elt, button_elt;
            
        if (use_textarea) {
            input_elt = $("<textarea/>").attr({ rows: num_rows, cols: num_cols }).text($.trim(cur_text)).keyup(function(e) {
                if (e.keyCode === 27) {
                    // Escape key.
                    set_text(cur_text);
                }
            });
            button_elt = $("<button/>").text("Done").click(function() {
                set_text(input_elt.val());
                // Return false so that click does not propogate to container.
                return false;
            });
        }
        else {
            input_elt = $("<input type='text'/>").attr({ value: $.trim(cur_text), size: num_cols })
            .blur(function() {
                set_text(cur_text);
            }).keyup(function(e) {
                if (e.keyCode === 27) {
                    // Escape key.
                    $(this).trigger("blur");
                } else if (e.keyCode === 13) {
                    // Enter key.
                    set_text($(this).val());
                }
            });
        }               
                                
        // Replace text with input object(s) and focus & select.
        container.text("");
        container.append(input_elt);
        if (button_elt) {
            container.append(button_elt);
        }
        input_elt.focus();
        input_elt.select();
        
        // Do not propogate to elements below b/c that blurs input and prevents it from being used.
        e.stopPropagation();
    });
    
    // Add help text if there some.
    if (help_text) {
        container.attr("title", help_text).tipsy( { gravity: 's' } );
    }
    
    return container;
}

/** 
 * Edit and save text asynchronously.
 */
function async_save_text(click_to_edit_elt, text_elt_id, save_url, text_parm_name, num_cols, use_textarea, num_rows, on_start, on_finish) {
    // Set defaults if necessary.
    if (num_cols === undefined) {
        num_cols = 30;
    }
    if (num_rows === undefined) {
        num_rows = 4;
    }
    
    // Set up input element.
    $("#" + click_to_edit_elt).live("click", function() {
        // Check if this is already active
        if ( $("#renaming-active").length > 0) {
            return;
        }
        var text_elt = $("#" + text_elt_id),
            old_text = text_elt.text(),
            t;
            
        if (use_textarea) {
            t = $("<textarea></textarea>").attr({ rows: num_rows, cols: num_cols }).text( $.trim(old_text) );
        } else {
            t = $("<input type='text'></input>").attr({ value: $.trim(old_text), size: num_cols });
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
                        if (processed_text !== "") {
                            text_elt.text(processed_text);
                        } else {
                            text_elt.html("<em>None</em>");
                        }
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
        t.insertAfter(text_elt);
        t.focus();
        t.select();
        
        return;
    });
}

function init_history_items(historywrapper, noinit, nochanges) {

    var action = function() {
        // Load saved state and show as necessary
        try {
            var stored = $.jStorage.get("history_expand_state");
            if (stored) {
                for (var id in stored) {
                    $("#" + id + " div.historyItemBody" ).show();
                }
            }
        } catch(err) {
            // Something was wrong with values in storage, so clear storage
            $.jStorage.deleteKey("history_expand_state");
        }

        // If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        if ( $.browser.mozilla ) {
            $( "div.historyItemBody" ).each( function() {
                if ( !$(this).is(":visible") ) { $(this).find( "pre.peek" ).css( "overflow", "hidden" ); }
            });
        }
        
        historywrapper.each( function() {
            var id = this.id,
                body = $(this).children( "div.historyItemBody" ),
                peek = body.find( "pre.peek" );
            $(this).find( ".historyItemTitleBar > .historyItemTitle" ).wrap( "<a href='javascript:void(0);'></a>" ).click( function() {
                var prefs;
                if ( body.is(":visible") ) {
                    // Hiding stuff here
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ); }
                    body.slideUp( "fast" );
                    
                    if (!nochanges) { // Ignore embedded item actions
                        // Save setting
                        prefs = $.jStorage.get("history_expand_state");
                        if (prefs) {
                            delete prefs[id];
                            $.jStorage.set("history_expand_state", prefs);
                        }
                    }
                } else {
                    // Showing stuff here
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    
                    if (!nochanges) {
                        // Save setting
                        prefs = $.jStorage.get("history_expand_state");
                        if (!prefs) { prefs = {}; }
                        prefs[id] = true;
                        $.jStorage.set("history_expand_state", prefs);
                    }
                }
                return false;
            });
        });
        
        // Generate 'collapse all' link
        $("#top-links > a.toggle").click( function() {
            var prefs = $.jStorage.get("history_expand_state");
            if (!prefs) { prefs = {}; }
            $( "div.historyItemBody:visible" ).each( function() {
                if ( $.browser.mozilla ) {
                    $(this).find( "pre.peek" ).css( "overflow", "hidden" );
                }
                $(this).slideUp( "fast" );
                if (prefs) {
                    delete prefs[$(this).parent().attr("id")];
                }
            });
            $.jStorage.set("history_expand_state", prefs);
        }).show();
    };
    
    action();
}

function commatize( number ) {
    number += ''; // Convert to string
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(number)) {
        number = number.replace(rgx, '$1' + ',' + '$2');
    }
    return number;
}

// Reset tool search to start state.
function reset_tool_search( initValue ) {
    // Function may be called in top frame or in tool_menu_frame; 
    // in either case, get the tool menu frame.
    var tool_menu_frame = $("#galaxy_tools").contents();
    if (tool_menu_frame.length === 0) {
        tool_menu_frame = $(document);
    }
        
    // Remove classes that indicate searching is active.
    $(this).removeClass("search_active");
    tool_menu_frame.find(".toolTitle").removeClass("search_match");
    
    // Reset visibility of tools and labels.
    tool_menu_frame.find(".toolSectionBody").hide();
    tool_menu_frame.find(".toolTitle").show();
    tool_menu_frame.find(".toolPanelLabel").show();
    tool_menu_frame.find(".toolSectionWrapper").each( function() {
        if ($(this).attr('id') != 'recently_used_wrapper') {
            // Default action.
            $(this).show();
        } else if ($(this).hasClass("user_pref_visible")) {
            $(this).show();
        }
    });
    tool_menu_frame.find("#search-no-results").hide();
    
    // Reset search input.
    tool_menu_frame.find("#search-spinner").hide();
    if (initValue) {
        var search_input = tool_menu_frame.find("#tool-search-query");
        search_input.val("search tools");
    }
}

// Create GalaxyAsync object.
var GalaxyAsync = function(log_action) {
    this.url_dict = {};
    this.log_action = (log_action === undefined ? false : log_action);
};

GalaxyAsync.prototype.set_func_url = function( func_name, url ) {
    this.url_dict[func_name] = url;
};

// Set user preference asynchronously.
GalaxyAsync.prototype.set_user_pref = function( pref_name, pref_value ) {
    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({                   
        url: url,
        data: { "pref_name" : pref_name, "pref_value" : pref_value },
        error: function() { return false; },
        success: function() { return true; }                                           
    });
};

// Log user action asynchronously.
GalaxyAsync.prototype.log_user_action = function( action, context, params ) {
    if (!this.log_action) { return; }
        
    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({                   
        url: url,
        data: { "action" : action, "context" : context, "params" : params },
        error: function() { return false; },
        success: function() { return true; }                                           
    });
};

$(document).ready( function() {
    $("select[refresh_on_change='true']").change( function() {
        var select_field = $(this),
            select_val = select_field.val(),
            refresh = false,
            ref_on_change_vals = select_field.attr("refresh_on_change_values");
        if (ref_on_change_vals) {
            ref_on_change_vals = ref_on_change_vals.split(',');
            var last_selected_value = select_field.attr("last_selected_value");
            if ($.inArray(select_val, ref_on_change_vals) === -1 && $.inArray(last_selected_value, ref_on_change_vals) === -1) {
                return;
            }
        }
        $(window).trigger("refresh_on_change");
        $(document).trigger("convert_to_values"); // Convert autocomplete text to values
        select_field.get(0).form.submit();
    });
    
    // checkboxes refresh on change
    $(":checkbox[refresh_on_change='true']").click( function() {
        var select_field = $(this),
            select_val = select_field.val(),
            refresh = false,
            ref_on_change_vals = select_field.attr("refresh_on_change_values");
        if (ref_on_change_vals) {
            ref_on_change_vals = ref_on_change_vals.split(',');
            var last_selected_value = select_field.attr("last_selected_value");
            if ($.inArray(select_val, ref_on_change_vals) === -1 && $.inArray(last_selected_value, ref_on_change_vals) === -1) {
                return;
            }
        }
        $(window).trigger("refresh_on_change");
        select_field.get(0).form.submit();
    });
    
    // Links with confirmation
    $( "a[confirm]" ).click( function() {
        return confirm( $(this).attr("confirm") );
    });
    // Tooltips
    if ( $.fn.tipsy ) {
        // FIXME: tipsy gravity cannot be updated, so need classes that specify N/S gravity and 
        // initialize each separately.
        $(".tooltip").tipsy( { gravity: 's' } );
    }
    // Make popup menus.
    make_popup_menus();
    
    // Replace big selects.
    replace_big_select_inputs(20, 1500);
    
    // If galaxy_main frame does not exist and link targets galaxy_main, 
    // add use_panels=True and set target to self.
    $("a").click( function() {
        var anchor = $(this);
        var galaxy_main_exists = (parent.frames && parent.frames.galaxy_main)
        if ( ( anchor.attr( "target" ) == "galaxy_main" ) && ( !galaxy_main_exists ) ) {
            var href = anchor.attr("href");
            if (href.indexOf("?") == -1) {
                href += "?";
            }
            else {
                href += "&";
            }
            href += "use_panels=True";
            anchor.attr("href", href);
            anchor.attr("target", "_self");
        }
        return anchor;
    });

});
