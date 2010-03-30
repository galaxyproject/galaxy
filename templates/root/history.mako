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
${h.js( "jquery", "jquery.tipsy", "galaxy.base", "json2", "jquery.jstore-all", "jquery.autocomplete", "autocomplete_tagging" )}

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
    $("#top-links > a.toggle").click( function() {
        $( "div.historyItemBody:visible" ).each( function() {
            if ( $.browser.mozilla ) {
                $(this).find( "pre.peek" ).css( "overflow", "hidden" );
            }
            $(this).slideUp( "fast" );
        });
        $.jStore.remove("history_expand_state");
    }).show();
    
    // History rename functionality.
    async_save_text("history-name-container", "history-name", "${h.url_for( controller="/history", action="rename_async", id=trans.security.encode_id(history.id) )}", "new_name", 18);
    
    // History tagging functionality.
    var historyTagArea = $('#history-tag-area');
    $('#history-tag').click( function() 
    {
        if ( historyTagArea.is( ":hidden" ) ) {
            historyTagArea.slideDown("fast");
        } else {
            historyTagArea.slideUp("fast");
        }
        return false;
    });
    
    // History annotation functionality.
    var historyAnnotationArea = $('#history-annotation-area');
    $('#history-annotate').click( function() {
        if ( historyAnnotationArea.is( ":hidden" ) ) {
            historyAnnotationArea.slideDown("fast");
        } else {
            historyAnnotationArea.slideUp("fast");
        }
        return false;
    });
    async_save_text("history-annotation-container", "history-annotation", "${h.url_for( controller="/history", action="annotate_async", id=trans.security.encode_id(history.id) )}", "new_annotation", 18, true, 4);
    
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
// (a) Add show/hide link and delete link to a history item;
// (b) handle tagging and annotation using jquery.
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
        
        // Tag handling.
        $(this).find( "a.icon-button.tags").each( function() 
        {
            // Use links parameters but custom URL as ajax URL.
            $(this).click( function() {
                // Get tag area, tag element.
                var history_item = $(this).parents(".historyItem");
                var tag_area = history_item.find(".tag-area");
                var tag_elt = history_item.find(".tag-elt");
                
                // Show or hide tag area; if showing tag area and it's empty, fill it.
                if ( tag_area.is( ":hidden" ) ) 
                {
                    if (tag_elt.html() == "" )
                    {
                        // Need to fill tag element.
                        var href_parms = $(this).attr("href").split("?")[1];
                        var ajax_url = "${h.url_for( controller='tag', action='get_tagging_elt_async' )}?" + href_parms;
                        $.ajax({
                            url: ajax_url,
                            error: function() { alert( "Tagging failed" ) },
                            success: function(tag_elt_html) {
                                tag_elt.html(tag_elt_html);
                                tag_elt.find(".tooltip").tipsy( { gravity: 's' } );
                                tag_area.slideDown("fast");
                            }
                        });
                    }
                    else
                    {
                        // Tag element is filled; show.
                        tag_area.slideDown("fast");
                    }
                } 
                else 
                {
                    // Hide.
                    tag_area.slideUp("fast");
                }
                return false;        
            });
        });
        
        // Annotation handling.
        $(this).find( "a.icon-button.annotate").each( function() 
        {
            // Use links parameters but custom URL as ajax URL.
            $(this).click( function() {
                // Get tag area, tag element.
                var history_item = $(this).parents(".historyItem");
                var annotation_area = history_item.find(".annotation-area");
                var annotation_elt = history_item.find(".annotation-elt");
                
                // Show or hide annotation area; if showing annotation area and it's empty, fill it.
                if ( annotation_area.is( ":hidden" ) ) 
                {
                    if (annotation_elt.html() == "" )
                    {
                        // Need to fill annotation element.
                        var href_parms = $(this).attr("href").split("?")[1];
                        var ajax_url = "${h.url_for( controller='dataset', action='get_annotation_async' )}?" + href_parms;
                        $.ajax({
                            url: ajax_url,
                            error: function() { alert( "Annotations failed" ) },
                            success: function(annotation) {
                                if (annotation == "")
                                    annotation = "<i>Describe or add notes to dataset</i>";
                                annotation_elt.html(annotation);
                                annotation_area.find(".tooltip").tipsy( { gravity: 's' } );
                                async_save_text(
                                    annotation_elt.attr("id"), annotation_elt.attr("id"),
                                    "${h.url_for( controller="/dataset", action="annotate_async")}?" + href_parms,
                                    "new_annotation", 18, true, 4);
                                annotation_area.slideDown("fast");
                            }
                        });
                    }
                    else
                    {
                        // Annotation element is filled; show.
                        annotation_area.slideDown("fast");
                    }
                } 
                else 
                {
                    // Hide.
                    annotation_area.slideUp("fast");
                }
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
#top-links {
    margin-bottom: 15px;
}
#history-name-container {
    display: inline-block;
    color: gray;
    font-weight: bold;
}
.editable-text {
    border: solid transparent 1px;
    padding: 3px;
    margin: -4px;
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
    
    <a title="${_('refresh')}" class="icon-button arrow-circle tooltip" href="${h.url_for('history', show_deleted=show_deleted)}"></a>
    <a title='${_('collapse all')}' class='icon-button toggle tooltip' href='#' style="display: none;"></a>
    
    %if trans.get_user():
    <div style="width: 40px; float: right; white-space: nowrap;">
        <a id="history-tag" title="Edit history tags" class="icon-button tags tooltip" target="galaxy_main" href="${h.url_for( controller='history', action='tag' )}"></a>
        <a id="history-annotate" title="Edit history annotation" class="icon-button annotate tooltip" target="galaxy_main" href="${h.url_for( controller='history', action='annotate' )}"></a>
    </div>
    %endif

</div>

<div style="clear: both;"></div>

%if show_deleted:
<div class="historyLinks">
    <a href="${h.url_for('history', show_deleted=False)}">${_('hide deleted')}</a>
</div>
%endif

<div id="history-name-area" class="historyLinks">
    
    %if trans.get_user():
    <div id="history-name-container">
        <div id="history-name" class="tooltip editable-text" title="Click to rename history">${history.get_display_name() | h}</div>
    </div>
    %endif
                               
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
    <div style="margin: 0px 5px 10px 5px">
        ## Tagging elt.
        <div id="history-tag-area" style="display: none">
            <b>Tags:</b>
            ${render_individual_tagging_element(user=trans.get_user(), tagged_item=history, elt_context="history.mako", use_toggle_link=False, input_size="20")}
        </div>
    
        ## Annotation elt.
        <div id="history-annotation-area" style="display: none">
   	    <b>Annotation / Notes:</b>
   	    <div id="history-annotation-container">
		<div id="history-annotation" class="tooltip editable-text" title="Click to edit annotation">${annotation or 'None' | h}</div>
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
