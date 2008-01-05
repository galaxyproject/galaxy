<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>

<head>
<title>Galaxy History</title>

## This is now only necessary for tests
%if bool( [ data for data in history.active_datasets if data.state in ['running', 'queued', '', None ] ] ):
<!-- running: do not change this comment, used by TwillTestCase.wait -->
%endif

<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
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
    var q = jQuery.noConflict();
    q( document ).ready( function() {
        initShowHide();
        setupHistoryItem( q("div.historyItemWrapper") );
        // Collapse all
        q("#top-links").append( "|&nbsp;" ).append( q("<a href='#'>collapse all</a>").click( function() {
            q( "div.historyItemBody:visible" ).each( function() {
                if ( q.browser.mozilla )
                {
                    q(this).find( "pre.peek" ).css( "overflow", "hidden" );
                }
                q(this).slideUp( "fast" );
            })
            var state = new CookieSet( "galaxy.history.expand_state" );
            state.removeAll().save();
        }))
        // Add footer show / hide 
        q( "div.footerheader" ).each( function() {
            var menu = q(this).next();
            menu.hide();
            q(this).append( q("<a href='#'>options...</a>").click( function() {
                if ( menu.is( ":visible" ) ) { menu.slideUp( "fast" ) }
                else { menu.slideDown( "fast" ) } 
            }))
        })
        // Links with confirmation
        q( "a[@confirm]" ).click( function() {
            return confirm( q(this).attr( "confirm"  ) )
        })
    })
    // Functionized so AJAX'd datasets can call them
    // Get shown/hidden state from cookie
    function initShowHide() {
        q( "div.historyItemBody" ).hide();
        // Load saved state and show as neccesary
        var state = new CookieSet( "galaxy.history.expand_state" );
	for ( id in state.store ) { q( "#" + id ).children( "div.historyItemBody" ).show(); }
        // If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        if ( q.browser.mozilla ) {
            q( "div.historyItemBody" ).each( function() {
                if ( ! q(this).is( ":visible" ) ) q(this).find( "pre.peek" ).css( "overflow", "hidden" );
            })
        }
        delete state;
    }
    // Add show/hide link and delete link to a history item
    function setupHistoryItem( query ) {
        query.each( function() {
            var id = this.id;
            var body = q(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            q(this).children( ".historyItemTitleBar" ).find( ".historyItemTitle" ).wrap( "<a href='#'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    if ( q.browser.mozilla ) { peek.css( "overflow", "hidden" ) }
                    body.slideUp( "fast" );
                    ## other instances of this could be editing the cookie, refetch
                    var state = new CookieSet( "galaxy.history.expand_state" );
                    state.remove( id ); state.save();
                    delete state;
                } 
                else {
                    body.slideDown( "fast", function() { 
                        if ( q.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    var state = new CookieSet( "galaxy.history.expand_state" );
                    state.add( id ); state.save();
                    delete state;
                }
            })
	    // Delete link
	    q(this).find( "a.historyItemDelete" ).each( function() {
		var data_id = this.id.split( "-" )[1];
		q(this).click( function() {
		    q( '#progress-' + data_id ).show();
		    q.ajax({
			url: "${h.url_for( action='delete_async', id='XXX' )}".replace( 'XXX', data_id ),
			error: function() { alert( "Delete failed" ) },
			success: function() {
			    q( "#historyItem-" + data_id ).fadeOut( "fast", function() {
				q( "div#historyItemContainer-" + data_id ).remove();
				if ( q( "div.historyItemContainer" ).length < 1 ) {
				    q ( "div#emptyHistoryMessage" ).show();
				}
			    });
			}
		    });
		    return false;
		});
	    });
        });
    }
    // lifted from prototype.js
    function array_from(iterable) {
        if (!iterable) return [];
        if (iterable.toArray) {
            return iterable.toArray();
        } else {
            var results = [];
            for (var i = 0, length = iterable.length; i < length; i++)
                results.push(iterable[i]);
            return results;
        }
    }
    Function.prototype.bind = function() {
        var __method = this, args = array_from(arguments), object = args.shift();
        return function() {
            return __method.apply(object, args.concat(array_from(arguments)));
        }
    }
    function updater( id, state_url, code_url, orig_state ) {
        this.id = id;
        this.state_url = state_url;
        this.code_url = code_url;
        this.old_state = orig_state;
    }
    updater.prototype.go = function() {
        //Apparently IE doesn't do Array.indexOf...
        //stop_states = new Array( "ok", "error" );
        this.interval = setInterval( function() {
            q.get(this.state_url, function(new_state) {
                //if (stop_states.indexOf(new_state) >= 0) { clearInterval( this.interval ); }
                if ((new_state == "ok") || (new_state == "error") || (new_state == "empty")) {
                    clearInterval( this.interval );
                }
                if (this.old_state != new_state) {
		    var id = 'div#historyItemContainer-' + this.id;
                    q( id ).load(this.code_url, {}, function() {
			setupHistoryItem( q( id ).children( ".historyItemWrapper" ) );
			// FIXME: Inefficient
			initShowHide();
		    });
                }
                this.old_state = new_state;
            }.bind(this) );
        }.bind(this), 3000 );
    }
    updater.prototype.stop = function() {
        clearInterval( this.interval );
    }
</script>

<![if gte IE 7]>
<script type="text/javascript">
    q( document ).ready( function() {
        // Add rollover effect to any image with a 'rollover' attribute
        preload_images = {}
        q( "img[@rollover]" ).each( function() {
            var r = q(this).attr('rollover');
            var s = q(this).attr('src');
            preload_images[r] = true;
            q(this).hover( 
                function() { q(this).attr( 'src', r ) },
                function() { q(this).attr( 'src', s ) }
            )
        })
        for ( r in preload_images ) { q( "<img>" ).attr( "src", r ) }
    })
</script>
<![endif]>

<style type="text/css">
#footer {
    /* Netscape 4, IE 4.x-5.0/Win and other lesser browsers will use this */
    position: absolute; left: 0px; bottom: 0px;
}
body > div#footer {
    /* used by Opera 5+, Netscape6+/Mozilla, Konqueror, Safari, OmniWeb 4.5+, iCab, ICEbrowser */
    position: fixed;
}
</style>

<!--[if gte IE 5.5]>
<![if lt IE 7]>
<style type="text/css">
div#footer {
    /* IE5.5+/Win - this is more specific than the IE 5.0 version */
    width:100%;
    right: auto; bottom: auto;
    left: expression( ( -5 - footer.offsetWidth + ( document.documentElement.clientWidth ? document.documentElement.clientWidth : document.body.clientWidth ) + ( ignoreMe2 = document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft ) ) + 'px' );
    top: expression( ( - footer.offsetHeight + ( document.documentElement.clientHeight ? document.documentElement.clientHeight : document.body.clientHeight ) + ( ignoreMe = document.documentElement.scrollTop ? document.documentElement.scrollTop : document.body.scrollTop ) ) + 'px' );
}
</style>
<![endif]>
<![endif]-->

</head>

<body class="historyPage">

<div id="top-links" class="historyLinks">
    <a href="${h.url_for('history')}">refresh</a> 
</div>

%if history.deleted:
    <div class="warningmessagesmall">
        You are currently viewing a deleted history!
    </div>
    <p></p>
%endif

<%namespace file="history_common.mako" import="render_dataset" />

%if len(history.active_datasets) < 1:
    <div class="infomessagesmall" id="emptyHistoryMessage">
%else:    
    ## Render all active (not deleted) datasets, ordered from newest to oldest
    %for data in reversed( history.active_datasets ):
        %if data.visible:
            <div class="historyItemContainer" id="historyItemContainer-${data.id}">
                ${render_dataset( data, data.hid )}
            </div>
        %endif
    %endfor
    <script type="text/javascript">
    %for data in reversed( history.active_datasets ):
        %if data.visible and data.state not in [ "empty", "error", "ok" ]:
            var updater_${data.id} = new updater( ${data.id},
		'${h.url_for( action='dataset_state', id=data.id )}',
		'${h.url_for( action='dataset_code', id=data.id, hid=data.hid )}',
		'data.state' );
            updater_${data.id}.go();
        %endif
    %endfor
    </script>
    <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
%endif
        Your history is empty. Click 'Get Data' on the left pane to start
    </div>

</body>

## <div style="height: 20px"></div>
## <div id="footer" >
##     <div class="footerheader">
##         <b>History</b> 
##     </div>
##     <div>
##         <div class="footermenu">
##             #if $t.user
##                 <div style="padding-top: 5px;">
##                     #if $history.user
##                         <div class="footermenuitem">currently stored as "<a href="$h.url_for('/history_rename', id=$history.id )" target="galaxy_main">$history.name</a>"</div>
##                     #else
##                         <div class="footermenuitem"><a href="$h.url_for('/history_store')" target="galaxy_main">store</a> this history for later</div>
##                     #end if
##                     <div class="footermenuitem"><a href="$h.url_for('/history_available')" target="galaxy_main">view</a> previously stored histories</div>
##                     #if $len( $history.active_datasets ) > 0 and $history.user not in [ None , "" ]:
##                         <div class="footermenuitem"><a href="$h.url_for('/history_new')">create</a> a new empty history</div>
##                     #end if
##                 </div>
##             #else
##                 <div class="footermenumessage">
##                     <div class="infomark">You must be <a target="galaxy_main" href="$h.url_for('/user/login')">logged in</a> to store or switch histories.</div>
##                 </div>
##             #end if
##             <div class="footermenuitem"><a href="$h.url_for('/history_share')" target="galaxy_main">share</a> current history</div>
##             <div class="footermenuitem"><a href="$h.url_for('/history_delete', id=$history.id )" confirm="Are you sure you want to delete the current history?">delete</a> current history</div>
##         </div>
##     </div>
## </div>

</html>
