<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery", "json2", "jquery.jstore-all", "jquery.autocomplete", "autocomplete_tagging" )}
    <script type="text/javascript">
    $(function() {
        // Load jStore for local storage
        $.extend(jQuery.jStore.defaults, { project: 'galaxy', flash: '/static/jStore.Flash.html' })
        $.jStore.load(); // Auto-select best storage

        $.jStore.ready(function(engine) {
            engine.ready(function() {
                // Init stuff that requires the local storage to be running
                //initShowHide();
                setupHistoryItem( $("div.historyItemWrapper") ); 
                
                // Hide all for now.
                $( "div.historyItemBody:visible" ).each( function() {
                    if ( $.browser.mozilla ) {
                        $(this).find( "pre.peek" ).css( "overflow", "hidden" );
                    }
                    $(this).slideUp( "fast" );
                });

            });
        });
        
        // Setup embedded content:
        //  (a) toggles for showing/hiding embedded content;
        //  (b) ...
        $('.embedded-item').each( function() 
        {
            // Setup toggle expand.
            var container = $(this);
            var toggle_expand = $(this).find('.toggle-expand');
            toggle_expand.click( function() 
            {
                var ajax_url = container.find("input[type=hidden]").val();
                // Only get item content if it's not already there.
                var item_content = $.trim(container.find(".item-content").text());
                if (item_content == "")
                    $.ajax({
                        type: "GET",
                        url: ajax_url,
                        error: function() { alert("Getting item content failed."); },
                        success: function( item_content ) {
                            container.find(".summary-content").hide("fast");
                            container.find(".item-content").html(item_content).show("fast");
                            container.find(".toggle-expand").hide();
                            container.find(".toggle-contract").show();
                        }
                    });
                else
                {
                    container.find(".summary-content").hide("fast");
                    container.find(".item-content").show("fast");
                    container.find(".toggle-expand").hide();
                    container.find(".toggle-contract").show();
                }
                return false;
            });
            // Setup toggle contract.
            var toggle_contract = $(this).find('.toggle-contract');
            toggle_contract.click( function() 
            {
                container.find(".item-content").hide("fast");
                container.find(".summary-content").show("fast");
                container.find(".toggle-contract").hide();
                container.find(".toggle-expand").show();
                return false;
            });
            
            
        });
    });
    // Functionized so AJAX'd datasets can call them
    function initShowHide() {

        // Load saved state and show as necessary
        try {
            var stored = $.jStore.store("history_expand_state");
            if (stored) {
                var st = JSON.parse(stored);
                for (var id in st) {
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
    }
    // Add show/hide link and delete link to a history item
    function setupHistoryItem( query ) {
        query.each( function() {
            var id = this.id;
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).children( ".historyItemTitleBar" ).find( ".historyItemTitle" ).wrap( "<a href='#'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    // Hiding stuff here
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ) }
                    body.slideUp( "fast" );

                    // Save setting
                    var stored = $.jStore.store("history_expand_state")
                    var prefs = stored ? JSON.parse(stored) : null
                    if (prefs) {
                        delete prefs[id];
                        $.jStore.store("history_expand_state", JSON.stringify(prefs));
                    }
                } else {
                    // Showing stuff here
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });

                    // Save setting
                    var stored = $.jStore.store("history_expand_state")
                    var prefs = stored ? JSON.parse(stored) : new Object;
                    prefs[id] = true;
                    $.jStore.store("history_expand_state", JSON.stringify(prefs));
                }
                return false;
            });
            // Delete link
            $(this).find( "div.historyItemButtons > .delete" ).each( function() {
                var data_id = this.id.split( "-" )[1];
                $(this).click( function() {
                    $( '#historyItem-' + data_id + "> div.historyItemTitleBar" ).addClass( "spinner" );
                    $.ajax({
                        url: "${h.url_for( action='delete_async', id='XXX' )}".replace( 'XXX', data_id ),
                        error: function() { alert( "Delete failed" ) },
                        success: function() {
                            %if show_deleted:
                            var to_update = {};
                            to_update[data_id] = "none";
                            updater( to_update );
                            %else:
                            $( "#historyItem-" + data_id ).fadeOut( "fast", function() {
                                $( "#historyItemContainer-" + data_id ).remove();
                                if ( $( "div.historyItemContainer" ).length < 1 ) {
                                    $( "#emptyHistoryMessage" ).show();
                                }
                            });
                            %endif
                        }
                    });
                    return false;
                });
            });
            // Undelete link
            $(this).find( "a.historyItemUndelete" ).each( function() {
                var data_id = this.id.split( "-" )[1];
                $(this).click( function() {
                    $( '#historyItem-' + data_id + " > div.historyItemTitleBar" ).addClass( "spinner" );
                    $.ajax({
                        url: "${h.url_for( controller='dataset', action='undelete_async', id='XXX' )}".replace( 'XXX', data_id ),
                        error: function() { alert( "Undelete failed" ) },
                        success: function() {
                            var to_update = {};
                            to_update[data_id] = "none";
                            updater( to_update );
                        }
                    });
                    return false;
                });
            });
        });
    };


    //TODO: this function is a duplicate of array_length defined in galaxy.base.js ; not sure why it needs to be redefined here (due to streaming?).
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
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base", "history", "autocomplete_tagging" )}
    <style type="text/css">
        .toggle-contract { display: none; }
        .item-content { overflow: auto; }
    </style>
</%def>

<%def name="render_item_header( item )">
    ## No header for pages.
</%def>

<%def name="render_item_links( page )">
</%def>

<%def name="render_item( page, page_data=None )">
    ${page_data}
</%def>