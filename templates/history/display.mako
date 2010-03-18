<%inherit file="/display_base.mako"/>
<%namespace file="/root/history_common.mako" import="render_dataset" />

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.jstore-all" )}
    
    ## Set vars so that there's no need to change the code below.
    <% 
        history = published_item 
        datasets = published_item_data
    %> 
    
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
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "history" )}
    <style type="text/css">
        .historyItemBody {
            display: none;
        }
        .column {
            float: left;
        	padding: 10px;
        	margin: 20px;
        	background: #666;
        	border: 5px solid #ccc;
        	width: 300px;
        }
    </style>

    <noscript>
        <style>
            .historyItemBody {
                display: block;
            }
        </style>
    </noscript>
</%def>

<%def name="render_item_links( history )">
    <a href="${h.url_for( controller='/history', action='imp', id=trans.security.encode_id(history.id) )}" class="icon-button import tooltip" title="Import history"></a>
</%def>

<%def name="render_item( history, datasets )">
        %if history.deleted:
            <div class="warningmessagesmall">
                ${_('You are currently viewing a deleted history!')}
            </div>
            <p></p>
        %endif

        %if not datasets:
            <div class="infomessagesmall" id="emptyHistoryMessage">
        %else:    
            ## Render requested datasets, ordered from newest to oldest, including annotations.
            <table class="annotated-item">
                <tr><th>Dataset</th><th class="annotation">Annotation</th></tr>
                %for data in datasets:
                    <tr>
                        %if data.visible:
                            <td>
                                <div class="historyItemContainer visible-right-border" id="historyItemContainer-${data.id}">
                                    ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted, user_owns_dataset=user_owns_history )}
                                </div>
                            </td>
                            <td class="annotation">${data.annotation}</td>
                        %endif
                    </tr>
                %endfor
            </table>
            <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
        %endif
                ${_("This history is empty.")}
            </div>

</%def>