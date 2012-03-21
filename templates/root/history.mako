<%namespace file="/message.mako" import="render_msg" />

<% _=n_ %>
<!DOCTYPE HTML>

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
${h.js( "jquery", "jquery.tipsy", "galaxy.base", "json2", "jstorage", "jquery.autocomplete", "autocomplete_tagging" )}

<script type="text/javascript">

<% TERMINAL_STATES = ["ok", "error", "empty", "deleted", "discarded", "failed_metadata"] %>
TERMINAL_STATES = ${ h.to_json_string(TERMINAL_STATES) };

// Tag handling.
function tag_handling(parent_elt) {
    $(parent_elt).find("a.icon-button.tags").each( function() {
        // Use links parameters but custom URL as ajax URL.
        $(this).click( function() {
            // Get tag area, tag element.
            var history_item = $(this).parents(".historyItem");
            var tag_area = history_item.find(".tag-area");
            var tag_elt = history_item.find(".tag-elt");

            // Show or hide tag area; if showing tag area and it's empty, fill it.
            if ( tag_area.is( ":hidden" ) ) {
                if (!tag_elt.html()) {
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
                } else {
                    // Tag element is filled; show.
                    tag_area.slideDown("fast");
                }
            } else {
                // Hide.
                tag_area.slideUp("fast");
            }
            return false;        
        });
    });
};

// Annotation handling.
function annotation_handling(parent_elt) {
    $(parent_elt).find("a.icon-button.annotate").each( function() {
        // Use links parameters but custom URL as ajax URL.
        $(this).click( function() {
            // Get tag area, tag element.
            var history_item = $(this).parents(".historyItem");
            var annotation_area = history_item.find(".annotation-area");
            var annotation_elt = history_item.find(".annotation-elt");

            // Show or hide annotation area; if showing annotation area and it's empty, fill it.
            if ( annotation_area.is( ":hidden" ) ) {
                if (!annotation_elt.html()) {
                    // Need to fill annotation element.
                    var href_parms = $(this).attr("href").split("?")[1];
                    var ajax_url = "${h.url_for( controller='dataset', action='get_annotation_async' )}?" + href_parms;
                    $.ajax({
                        url: ajax_url,
                        error: function() { alert( "Annotations failed" ) },
                        success: function(annotation) {
                            if (annotation == "") {
                                annotation = "<em>Describe or add notes to dataset</em>";
                            }
                            annotation_elt.html(annotation);
                            annotation_area.find(".tooltip").tipsy( { gravity: 's' } );
                            async_save_text(
                                annotation_elt.attr("id"), annotation_elt.attr("id"),
                                "${h.url_for( controller='/dataset', action='annotate_async')}?" + href_parms,
                                "new_annotation", 18, true, 4);
                            annotation_area.slideDown("fast");
                        }
                    });
                } else {
                    // Annotation element is filled; show.
                    annotation_area.slideDown("fast");
                }
            } else {
                // Hide.
                annotation_area.slideUp("fast");
            }
            return false;        
        });
    });
};

// Update the message for async operations
function render_message(message, status) {
    $("div#message-container").html( "<div class=\"" + status + "message\">" + message + "</div><br/>" );
}

$(function() {
    var historywrapper = $("div.historyItemWrapper");
    init_history_items(historywrapper);
    historywrapper.each( function() {
        // Delete link
        $(this).find("div.historyItemButtons > .delete" ).each( function() {
            var data_id = this.id.split( "-" )[1];
            $(this).click( function() {
                $( '#historyItem-' + data_id + "> div.historyItemTitleBar" ).addClass( "spinner" );
                $.ajax({
                    url: "${h.url_for( controller='dataset', action='delete_async', dataset_id='XXX' )}".replace( 'XXX', data_id ),
                    error: function() { render_message( "Dataset deletion failed", "error" ); },
                    success: function(msg) {
                        if (msg === "OK") {
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
                            $(".tipsy").remove();
                        } else {
                            render_message( "Dataset deletion failed", "error" );
                        }
                    }
                });
                return false;
            });
        });
        
        // Check to see if the dataset data is cached or needs to be pulled in
        // via objectstore
        $(this).find("a.display").each( function() {
            var history_item = $(this).parents(".historyItem")[0];
            var history_id = history_item.id.split( "-" )[1];
            $(this).click(function() {
                check_transfer_status($(this), history_id);
            });
        });
        
        // If dataset data is not cached, keep making ajax calls to check on the
        // data status and update the dataset UI element accordingly
        function check_transfer_status(link, history_id) {
            $.getJSON("${h.url_for( controller='dataset', action='transfer_status', dataset_id='XXX' )}".replace( 'XXX', link.attr("dataset_id") ), 
                function(ready) {
                    if (ready === false) {
                        // $("<div/>").text("Data is loading from S3... please be patient").appendTo(link.parent());
                        $( '#historyItem-' + history_id).removeClass( "historyItem-ok" );
                        $( '#historyItem-' + history_id).addClass( "historyItem-running" );
                        setTimeout(function(){check_transfer_status(link, history_id)}, 1000);
                    } else {
                        $( '#historyItem-' + history_id).removeClass( "historyItem-running" );
                        $( '#historyItem-' + history_id).addClass( "historyItem-ok" );
                    }
                }
            );
        }

        // Undelete link
        $(this).find("a.historyItemUndelete").each( function() {
            var data_id = this.id.split( "-" )[1];
            $(this).click( function() {
                $( '#historyItem-' + data_id + " > div.historyItemTitleBar" ).addClass( "spinner" );
                $.ajax({
                    url: "${h.url_for( controller='dataset', action='undelete_async', dataset_id='XXX' )}".replace( 'XXX', data_id ),
                    error: function() { render_message( "Dataset undeletion failed", "error" ); },
                    success: function() {
                        var to_update = {};
                        to_update[data_id] = "none";
                        updater( to_update );
                    }
                });
                return false;
            });
        });
        
        // Purge link
        $(this).find("a.historyItemPurge").each( function() {
            var data_id = this.id.split( "-" )[1];
            $(this).click( function() {
                $( '#historyItem-' + data_id + " > div.historyItemTitleBar" ).addClass( "spinner" );
                $.ajax({
                    url: "${h.url_for( controller='dataset', action='purge_async', dataset_id='XXX' )}".replace( 'XXX', data_id ),
                    error: function() { render_message( "Dataset removal from disk failed", "error" ) },
                    success: function() {
                        var to_update = {};
                        to_update[data_id] = "none";
                        updater( to_update );
                    }
                });
                return false;
            });
        });
        
        // Show details icon -- Disabled since it often gets stuck, etc
        /* $(this).find("a.show-details").bind("mouseenter.load-detail", function(e) {
            var anchor = $(this);
            $.get($(this).attr("href"), function(data) {
                anchor.attr("title", data);
                anchor.tipsy( { html: true, gravity: 's', opacity: 1.0, delayOut: 300 } );
                anchor.unbind("mouseenter.load-detail");
                anchor.trigger("mouseenter");
            });
            return false;
        });
        
        // Disable clickthrough
        $(this).find("a.show-details").bind("click", function() { return false; });
        */
        
        tag_handling(this);
        annotation_handling(this);
    });
    
    // Trackster links
    function init_trackster_links() {
        // Add to trackster browser functionality
        $(".trackster-add").live("click", function() {
            var dataset = this,
                dataset_jquery = $(this);
            $.ajax({
                url: dataset_jquery.attr("data-url"),
                dataType: "html",
                error: function() { alert( "Could not add this dataset to browser." ); },
                success: function(table_html) {
                    var parent = window.parent;
                    
                    parent.show_modal("View Data in a New or Saved Visualization", "", {
                        "Cancel": function() {
                            parent.hide_modal();
                        },
                        "View in saved visualization": function() {
                            // Show new modal with saved visualizations.
                            parent.hide_modal();
                            parent.show_modal("Add Data to Saved Visualization", table_html, {
                                "Cancel": function() {
                                    parent.hide_modal();
                                },
                                "Add to visualization": function() {
                                    $(parent.document).find('input[name=id]:checked').each(function() {
                                        var vis_id = $(this).val();
                                        parent.location = dataset_jquery.attr("action-url") + "&id=" + vis_id;
                                    });
                                }, 
                            });
                        },
                        "View in new visualization": function() {
                            parent.location = dataset_jquery.attr("new-url");
                        }
                    });
                }
            });
        });
    }
    
    init_trackster_links();
    
    // History rename functionality.
    async_save_text("history-name-container", "history-name", "${h.url_for( controller="/history", action="rename_async", id=trans.security.encode_id(history.id) )}", "new_name", 18);
    
    // History tagging functionality.
    var historyTagArea = $('#history-tag-area');
    $('#history-tag').click( function() {
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
    updater(
        ${ h.to_json_string( dict([(trans.app.security.encode_id(data.id), data.state) for data in reversed( datasets ) if data.visible and data.state not in TERMINAL_STATES]) ) }
    );
    
    // Navigate to a dataset.
    %if hda_id:
        self.location = "#${hda_id}";
    %endif

    // Update the Quota Meter
    $.ajax( {
        type: "POST",
        url: "${h.url_for( controller='root', action='user_get_usage' )}",
        dataType: "json",
        success : function ( data ) {
            $.each( data, function( type, val ) {
                quota_meter_updater( type, val );
            });
        }
    });
});

// Updates the Quota Meter
var quota_meter_updater = function ( type, val ) {
    if ( type == "usage" ) {
        $("#quota-meter-bar", window.top.document).css( "width", "0" );
        $("#quota-meter-text", window.top.document).text( "Using " + val );
    } else if ( type == "percent" ) {
        $("#quota-meter-bar", window.top.document).removeClass("quota-meter-bar-warn quota-meter-bar-error");
        if ( val >= 100 ) {
            $("#quota-meter-bar", window.top.document).addClass("quota-meter-bar-error");
            $("#quota-message-container").slideDown();
        } else if ( val >= 85 ) {
            $("#quota-meter-bar", window.top.document).addClass("quota-meter-bar-warn");
            $("#quota-message-container").slideUp();
        } else {
            $("#quota-message-container").slideUp();
        }
        $("#quota-meter-bar", window.top.document).css( "width", val + "px" );
        $("#quota-meter-text", window.top.document).text( "Using " + val + "%" );
    }
}

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
    if ( !empty ) {
        setTimeout( function() { updater_callback( tracked_datasets ) }, 4000 );
    }
};
var updater_callback = function ( tracked_datasets ) {
    // Build request data
    var ids = [],
        states = [],
        force_history_refresh = false,
        check_history_size = false;
        
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
                init_history_items( $("div.historyItemWrapper"), "noinit" );
                tag_handling(container);
                annotation_handling(container);
                // If new state is terminal, stop tracking
                if (TERMINAL_STATES.indexOf(val.state) !== -1) {
                    if ( val.force_history_refresh ){
                        force_history_refresh = true;
                    }
                    delete tracked_datasets[id];
                    // When a dataset becomes terminal, check for changes in history disk size
                    check_history_size = true;
                } else {
                    tracked_datasets[id] = val.state;
                }
            });
            if ( force_history_refresh ) {
                parent.frames.galaxy_history.location.reload();
            } else {
                if ( check_history_size ) {
                    $.ajax( {
                        type: "POST",
                        url: "${h.url_for( controller='root', action='history_get_disk_size' )}",
                        dataType: "json",
                        success: function( data ) {
                            $.each( data, function( type, val ) {
                                if ( type == "history" ) {
                                    $("#history-size").text( val );
                                } else if ( type == "global_usage" ) {
                                    quota_meter_updater( "usage", val );
                                } else if ( type == "global_percent" ) {
                                    quota_meter_updater( "percent", val );
                                }
                            });
                        }
                    });
                    check_history_size = false;
                }
                // Keep going (if there are still any items to track)
                updater( tracked_datasets ); 
            }
            make_popup_menus();
        },
        error: function() {
            // Just retry, like the old method, should try to be smarter
            updater( tracked_datasets );
        }
    });
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
    color: gray;
    font-weight: bold;
}
#history-name {
    word-wrap: break-word;
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
    <a title='${_('collapse all')}' class='icon-button toggle tooltip' href='#' style="display: none"></a>
    
    %if trans.get_user():
    <div style="width: 40px; float: right; white-space: nowrap;">
        <a id="history-tag" title="Edit history tags" class="icon-button tags tooltip" target="galaxy_main" href="${h.url_for( controller='history', action='tag' )}"></a>
        <a id="history-annotate" title="Edit history annotation" class="icon-button annotate tooltip" target="galaxy_main" href="${h.url_for( controller='history', action='annotate' )}"></a>
    </div>
    %endif
</div>

<div class="clear"></div>

%if show_deleted:
<div class="historyLinks">
    <a href="${h.url_for('history', show_deleted=False)}">${_('hide deleted')}</a>
</div>
%endif

%if show_hidden:
<div class="historyLinks">
    <a href="${h.url_for('history', show_hidden=False)}">${_('hide hidden')}</a>
</div>
%endif

<div id="history-name-area" class="historyLinks">
    
    <div id="history-name-container" style="position: relative;">
        %if trans.get_user():
            <div id="history-size" style="position: absolute; top: 3px; right: 0px;">${history.get_disk_size(nice_size=True)}</div>
            <div id="history-name" style="margin-right: 50px;" class="tooltip editable-text" title="Click to rename history">${history.get_display_name() | h}</div>
            
        %else:
            <div id="history-size">${history.get_disk_size(nice_size=True)}</div>
        %endif
    </div>                     
</div>
<div style="clear: both;"></div>

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
            <strong>Annotation / Notes:</strong>
            <div id="history-annotation-container">
            <div id="history-annotation" class="tooltip editable-text" title="Click to edit annotation">
                %if annotation:
                    ${h.to_unicode( annotation ) | h}
                %else:
                    <em>Describe or add notes to history</em>
                %endif
            </div>
            </div>
        </div>
        
    </div>
%endif

<div id="message-container">
    %if message:
        ${render_msg( message, status )}
    %endif
</div>

%if over_quota:
<div id="quota-message-container">
%else:
<div id="quota-message-container" style="display: none;">
%endif
    <div id="quota-message" class="errormessage">
        You are over your disk quota.  Tool execution is on hold until your disk usage drops below your allocated quota.
    </div>
    <br/>
</div>

%if not datasets:

    <div class="infomessagesmall" id="emptyHistoryMessage">

%else:    

    ## Render requested datasets, ordered from newest to oldest
    <div>
    %for data in reversed( datasets ):
        %if data.visible or show_hidden:
            <div class="historyItemContainer" id="historyItemContainer-${trans.app.security.encode_id(data.id)}">
                ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted, for_editing = True )}
            </div>
        %endif
    %endfor
    </div>

    <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
%endif
        ${_("Your history is empty. Click 'Get Data' on the left pane to start")}
    </div>

</body>
</html>
