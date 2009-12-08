<% _=n_ %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>

<head>
<title>${_('Galaxy History')}</title>

## This is now only necessary for tests
%if bool( [ data for data in history.active_datasets if data.state in ['running', 'queued', '', None ] ] ):
<!-- running: do not change this comment, used by TwillTestCase.wait -->
%endif

<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Pragma" content="no-cache">

${h.css( "base", "history", "autocomplete_tagging" )}
${h.js( "jquery", "json2", "jquery.jstore-all", "jquery.autocomplete", "autocomplete_tagging" )}

<script type="text/javascript">
$(function() {
    // Load jStore for local storage
    $.extend(jQuery.jStore.defaults, { project: 'galaxy', flash: '/static/jStore.Flash.html' })
    $.jStore.load(); // Auto-select best storage

    $.jStore.ready(function(engine) {
        engine.ready(function() {
            // Init stuff that requires the local storage to be running
            initShowHide();
            setupHistoryItem( $("div.historyItemWrapper") ); 
        });
    });
    
    // Generate 'collapse all' link
    $("#top-links").append( "|&nbsp;" ).append( $("<a href='#'>${_('collapse all')}</a>").click( function() {
        $( "div.historyItemBody:visible" ).each( function() {
            if ( $.browser.mozilla ) {
                $(this).find( "pre.peek" ).css( "overflow", "hidden" );
            }
            $(this).slideUp( "fast" );
        });
        $.jStore.remove("history_expand_state");
    }));
    
    $("#history-rename").click( function() {
        var old_name = $("#history-name").text()
        var t = $("<input type='text' value='" + old_name + "'></input>" );
        t.blur( function() {
            $(this).remove();
            $("#history-name").show();
        });
        t.keyup( function( e ) {
            if ( e.keyCode == 27 ) {
                // Escape key
                $(this).trigger( "blur" );
            } else if ( e.keyCode == 13 ) {
                // Enter key
                new_value = this.value;
                $(this).trigger( "blur" );
                $.ajax({
                    url: "${h.url_for( controller='history', action='rename_async', id=history.id )}",
                    data: { "_": true, new_name: new_value },
                    error: function() { alert( "Rename failed" ) },
                    success: function() {
                        $("#history-name").text( new_value );
                    }
                });
            }
        });
        $("#history-name").hide();
        $("#history-name-area").append( t );
        t.focus();
        return false;
    });
    // Updater
    updater({
        <% updateable = [data for data in reversed( datasets ) if data.visible and data.state not in [ "deleted", "empty", "error", "ok" ]] %>
        ${ ",".join( map(lambda data: "\"%s\" : \"%s\"" % (data.id, data.state), updateable) ) }
    });
    
    // Navigate to a dataset.
    %if hda_id:
        self.location = "#${hda_id}";
    %endif
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
// Looks for changes in dataset state using an async request. Keeps
// calling itself (via setTimeout) until all datasets are in a terminal
// state.
var updater = function ( tracked_datasets ) {
    // Check if there are any items left to track
    var empty = true;
    for ( i in tracked_datasets ) {
        empty = false;
        break;
    }
    if ( ! empty ) {
        // console.log( "Updater running in 3 seconds" );
        setTimeout( function() { updater_callback( tracked_datasets ) }, 3000 );
    } else {
        // console.log( "Updater finished" );
    }
};
var updater_callback = function ( tracked_datasets ) {
    // Build request data
    var ids = []
    var states = []
    var force_history_refresh = false
    $.each( tracked_datasets, function ( id, state ) {
        ids.push( id );
        states.push( state );
    });
    // Make ajax call
    $.ajax( {
        type: "POST",
        url: "${h.url_for( controller='root', action='history_item_updates' )}",
        dataType: "json",
        data: { ids: ids.join( "," ), states: states.join( "," ) },
        success : function ( data ) {
            $.each( data, function( id, val ) {
                // Replace HTML
                var container = $("#historyItemContainer-" + id);
                container.html( val.html );
                setupHistoryItem( container.children( ".historyItemWrapper" ) );
                initShowHide();
                // If new state was terminal, stop tracking
                if (( val.state == "ok") || ( val.state == "error") || ( val.state == "empty") || ( val.state == "deleted" ) || ( val.state == "discarded" )) {
                    if ( val.force_history_refresh ){
                        force_history_refresh = true;
                    }
                    delete tracked_datasets[ parseInt(id) ];
                } else {
                    tracked_datasets[ parseInt(id) ] = val.state;
                }
            });
            if ( force_history_refresh ) {
                parent.frames.galaxy_history.location.reload();
            } else {
                // Keep going (if there are still any items to track)
                updater( tracked_datasets ); 
            }
        },
        error: function() {
            // Just retry, like the old method, should try to be smarter
            updater( tracked_datasets );
        }
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
 
    //
    // Function provides text for tagging toggle link.
    //
    var get_toggle_link_text = function(tags)
    {
        var text = "";
        var num_tags = array_length(tags);
        if (num_tags != 0)
          {
            text = num_tags + (num_tags != 1 ? " Tags" : " Tag");
          }
        else
          {
            // No tags.
            text = "Add tags to history";
          }
        return text;
    };
</script>

<style>
.historyItemBody {
    display: none;
}
</style>

<noscript>
<style>
.historyItemBody {
    display: block;
}
</style>
</noscript>

</head>

<body class="historyPage">
    
<div id="top-links" class="historyLinks">
    <a href="${h.url_for('history', show_deleted=show_deleted)}">${_('refresh')}</a> 
    %if show_deleted:
    | <a href="${h.url_for('history', show_deleted=False)}">${_('hide deleted')}</a> 
    %endif
</div>
    
<div id="history-name-area" class="historyLinks" style="color: gray; font-weight: bold;">
    <div style="float: right"><a id="history-rename" title="Rename" class="icon-button edit" target="galaxy_main" href="${h.url_for( controller='history', action='rename' )}"></a></div>
    <div id="history-name">${history.get_display_name()}</div>
</div>

%if history.deleted:
    <div class="warningmessagesmall">
        ${_('You are currently viewing a deleted history!')}
    </div>
    <p></p>
%endif

<%namespace file="../tagging_common.mako" import="render_tagging_element" />
<%namespace file="history_common.mako" import="render_dataset" />

%if trans.get_user() is not None:
    <style>
        .tag-element {
            margin-bottom: 0.5em;
        }
    </style>
    ${render_tagging_element( tagged_item=history, elt_context='history.mako', get_toggle_link_text_fn='get_toggle_link_text' )}
%endif

%if not datasets:

    <div class="infomessagesmall" id="emptyHistoryMessage">

%else:    

    ## Render requested datasets, ordered from newest to oldest
    %for data in reversed( datasets ):
        %if data.visible:
            <div class="historyItemContainer" id="historyItemContainer-${data.id}">
                ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted, user_owns_dataset = True )}
            </div>
        %endif
    %endfor

    <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
%endif
        ${_("Your history is empty. Click 'Get Data' on the left pane to start")}
    </div>

</body>
</html>
