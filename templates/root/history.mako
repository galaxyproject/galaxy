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
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link href="${h.url_for('/static/style/history.css')}" rel="stylesheet" type="text/css" />

## <!--[if lt IE 7]>
## <script defer type="text/javascript" src="/static/scripts/ie_pngfix.js"></script>
## <![endif]-->

<script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
<script type="text/javascript" src="${h.url_for('/static/scripts/jquery.cookie.js')}"></script>
<script type="text/javascript" src="${h.url_for('/static/scripts/cookie_set.js')}"></script>

<script type="text/javascript">
    $( document ).ready( function() {
        initShowHide();
        setupHistoryItem( $("div.historyItemWrapper") );
        // Collapse all
        $("#top-links").append( "|&nbsp;" ).append( $("<a href='#'>${_('collapse all')}</a>").click( function() {
            $( "div.historyItemBody:visible" ).each( function() {
                if ( $.browser.mozilla )
                {
                    $(this).find( "pre.peek" ).css( "overflow", "hidden" );
                }
                $(this).slideUp( "fast" );
            })
            var state = new CookieSet( "galaxy.history.expand_state" );
            state.removeAll().save();
        return false;
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
	})
    })
    //' Functionized so AJAX'd datasets can call them
    // Get shown/hidden state from cookie
    function initShowHide() {
        $( "div.historyItemBody" ).hide();
        // Load saved state and show as neccesary
        var state = new CookieSet( "galaxy.history.expand_state" );
    for ( id in state.store ) { $( "#" + id ).children( "div.historyItemBody" ).show(); }
        // If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        if ( $.browser.mozilla ) {
            $( "div.historyItemBody" ).each( function() {
                if ( ! $(this).is( ":visible" ) ) $(this).find( "pre.peek" ).css( "overflow", "hidden" );
            })
        }
        delete state;
    }
    // Add show/hide link and delete link to a history item
    function setupHistoryItem( query ) {
        query.each( function() {
            var id = this.id;
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).children( ".historyItemTitleBar" ).find( ".historyItemTitle" ).wrap( "<a href='#'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ) }
                    body.slideUp( "fast" );
                    ## other instances of this could be editing the cookie, refetch
                    var state = new CookieSet( "galaxy.history.expand_state" );
                    state.remove( id ); state.save();
                    delete state;
                } 
                else {
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    var state = new CookieSet( "galaxy.history.expand_state" );
                    state.add( id ); state.save();
                    delete state;
                }
        return false;
            });
            // Delete link
            $(this).find( "a.historyItemDelete" ).each( function() {
        var data_id = this.id.split( "-" )[1];
        $(this).click( function() {
            $( '#progress-' + data_id ).show();
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
                $( "div#historyItemContainer-" + data_id ).remove();
                if ( $( "div.historyItemContainer" ).length < 1 ) {
                    q ( "div#emptyHistoryMessage" ).show();
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
            $( '#progress-' + data_id ).show();
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
                        delete tracked_datasets[ parseInt(id) ];
                    } else {
                        tracked_datasets[ parseInt(id) ] = val.state;
                    }
                });
                // Keep going (if there are still any items to track)
                updater( tracked_datasets );
            },
            error: function() {
                // Just retry, like the old method, should try to be smarter
                updater( tracked_datasets );
            }
        });
    };
</script>

<![if gte IE 7]>
<script type="text/javascript">
    $( document ).ready( function() {
        // Add rollover effect to any image with a 'rollover' attribute
        preload_images = {}
        $( "img[@rollover]" ).each( function() {
            var r = $(this).attr('rollover');
            var s = $(this).attr('src');
            preload_images[r] = true;
            $(this).hover( 
                function() { $(this).attr( 'src', r ) },
                function() { $(this).attr( 'src', s ) }
            )
        })
        for ( r in preload_images ) { $( "<img>" ).attr( "src", r ) }
    })
</script>
<![endif]>

</head>

<body class="historyPage">
    
<div id="top-links" class="historyLinks">
    <a href="${h.url_for('history', show_deleted=show_deleted)}">${_('refresh')}</a> 
    %if show_deleted:
    | <a href="${h.url_for('history', show_deleted=False)}">${_('hide deleted')}</a> 
    %endif
</div>
    
<div id="history-name-area" class="historyLinks" style="color: gray; font-weight: bold;">
    <div style="float: right"><a id="history-rename" target="galaxy_main" href="${h.url_for( controller='history', action='rename' )}"><img src="${h.url_for('/static/images/pencil_icon.png')}"></a></div>
    <div id="history-name">${history.name}</div>
</div>

%if history.deleted:
    <div class="warningmessagesmall">
        ${_('You are currently viewing a deleted history!')}
    </div>
    <p></p>
%endif

<%namespace file="history_common.mako" import="render_dataset" />

<% activatable_datasets = history.activatable_datasets %>

%if ( show_deleted and not activatable_datasets ) or ( not show_deleted and not history.active_datasets ):
    <div class="infomessagesmall" id="emptyHistoryMessage">
%else:    
    <%
    if show_deleted:
        #all datasets
        datasets_to_show = activatable_datasets
    else:
        #active (not deleted)
        datasets_to_show = history.active_datasets
    %>
    ## Render requested datasets, ordered from newest to oldest
    %for data in reversed( datasets_to_show ):
        %if data.visible:
            <div class="historyItemContainer" id="historyItemContainer-${data.id}">
                ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted )}
            </div>
        %endif
    %endfor
    <script type="text/javascript">
    var tracked_datasets = {};
    %for data in reversed( history.active_datasets ):
        %if data.visible and data.state not in [ "deleted", "empty", "error", "ok" ]:
            tracked_datasets[ ${data.id} ] = "${data.state}";
        %endif
    %endfor
    updater( tracked_datasets );
    </script>
    <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
%endif
        ${_("Your history is empty. Click 'Get Data' on the left pane to start")}
    </div>

</body>
</html>
