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
${h.js( "galaxy.base", "jquery", "json2", "jquery.jstore-all", "jquery.autocomplete", "autocomplete_tagging" )}

<script type="text/javascript">
$(function() {
    // Load jStore for local storage
    $.extend(jQuery.jStore.defaults, { project: 'galaxy', flash: '${h.url_for("/static/jStore.Flash.html")}' })
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
    
    // Rename async.
    async_save_text("history-rename", "history-name", "${h.url_for( controller="/history", action="rename_async", id=trans.security.encode_id(history.id) )}", "new_name");
    
    // Annotation async.
    // Tag async. Simply have the workflow tag element generate a click on the tag element to activate tagging.
    $('#workflow-tag').click( function() 
    {
        $('.tag-area').click();
        return false;
    });
                    
    // Annotate async.
    async_save_text("history-annotate", "history-annotation", "${h.url_for( controller="/history", action="annotate_async", id=trans.security.encode_id(history.id) )}", "new_annotation", true, 4);
    
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
</script>

<style>
.historyItemBody {
    display: none;
}
div.form-row {
    padding: 5px 5px 5px 0px;
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

<%namespace file="../tagging_common.mako" import="render_individual_tagging_element" />
<%namespace file="history_common.mako" import="render_dataset" />

%if trans.get_user() is not None:
    <div style="margin: 0px 0px 5px 10px">
        <a href="#" onclick="$('#tags-and-annotation').toggle('fast')">Edit Tags and Annotation/Notes</a>
        <div id="tags-and-annotation" style="display: none">    
            ## Tagging elt.
            <div class="form-row">
                <label>Tags:</label>
                <div style="float: right"><a id="workflow-tag" title="Tag" class="icon-button edit" target="galaxy_main" href="${h.url_for( controller='workflow', action='annotate_async' )}"></a></div>
                <style>
                    .tag-area {
                        border: none;
                    }
                </style>
                ${render_individual_tagging_element(user=trans.get_user(), tagged_item=history, elt_context="history.mako", use_toggle_link=False, input_size="20", render_add_tag_button=False)}
                <div style="clear: both"></div>
            </div>
        
            ## Annotation elt.
            <div id="history-annotation-area" class="form-row">
<<<<<<< local
                <label>Annotation / Notes:</label>
                <div style="float: right"><a id="history-annotate" title="Annotate" class="icon-button edit" target="galaxy_main" href="${h.url_for( controller='history', action='annotate_async' )}"></a></div>
                <div id="history-annotation">${annotation}</div>
=======
       	        <label>Annotation / Notes:</label>
    		    <div style="float: right"><a id="history-annotate" title="Annotate" class="icon-button edit" target="galaxy_main" href="${h.url_for( controller='history', action='annotate_async' )}"></a></div>
    		    %if annotation:
                        <div id="history-annotation">${h.escape(annotation)}</div>
                    %else:
                        <div id="history-annotation"></div>
                    %endif
>>>>>>> other
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
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
