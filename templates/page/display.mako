<%inherit file="/display_base.mako"/>

<%def name="title()">
    <% page = item %>
    Galaxy :: ${page.user.username} :: ${page.title}
</%def>

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
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="get_item_name( page )">
    <% return page.title %>
</%def>

<%def name="render_item_links( page )">
</%def>

<%def name="render_item( page, page_data=None )">
    ${page.latest_revision.content.decode( "utf-8" )}
</%def>