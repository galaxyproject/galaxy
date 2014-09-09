##<%inherit file="/embed_base.mako"/>
<%namespace file="/display_common.mako" import="*" />

## Some duplication with embed_base here, needed a way to override the main embedded-item html for histories
<%
    encoded_history_id = trans.security.encode_id( item.id )
    import_href = h.url_for( controller='history', action='imp', id=encoded_history_id )
    display_href = h.url_for( controller='history', action='display_by_username_and_slug',
        username=item.user.username, slug=item.slug )
%>
<div id="history-${encoded_history_id}" class='embedded-item display history'>
    <div class='title'>
        <div style="float: left">
            <a class="expand-content-btn icon-button toggle-expand" href="${display_href}"
               title="Show or hide history contents"></a>
        </div>
        <div style="float: right;">
            <a title="Import history" class="icon-button import" href="${import_href}"></a>
            <a title="View history" class="icon-button go-to-full-screen" href="${display_href}"></a>
        </div>
        <h4>
            <a class="toggle-embed" href="${display_href}" title="Show or hide history contents">
                Galaxy History | ${get_item_name( item )}
            </a>
        </h4>
        %if hasattr( item, "annotation") and item.annotation:
        <div class="annotation">${item.annotation}</div>
        %endif
    </div>
    <div class='summary-content'>
        ## currently, no summary content for history
    </div>
    <div class='expanded-content'>
        <div class='item-content'>
            <div class='history-panel'></div>
        </div>
    </div>
</div>

<script type="text/javascript">
// Embedding the same history more than once will confuse DOM ids.
//  In order to handle this, find this script and cache the previous node (the div above).
//  (Since we need thisScript to be locally scoped or it will get overwritten, enclose in self-calling function)
(function(){
    var scripts = document.getElementsByTagName( 'script' ),
        // this is executed immediately, so the last script will be this script
        thisScript = scripts[ scripts.length - 1 ],
        $embeddedHistory = $( thisScript ).prev();

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}"
    });
    require([ 'mvc/history/history-panel-annotated' ], function( panelMod ){

        function toggleExpanded( ev ){
            var $embeddedHistory = $( thisScript ).prev();
            $embeddedHistory.find( '.expand-content-btn' ).toggleClass( 'toggle-expand' ).toggleClass( 'toggle' );
            $embeddedHistory.find( ".summary-content" ).slideToggle( "fast" );
            $embeddedHistory.find( ".annotation" ).slideToggle( "fast" );
            $embeddedHistory.find( ".expanded-content" ).slideToggle( "fast" );
            ev.preventDefault();
        }

        $(function(){
            var historyModel = require( 'mvc/history/history-model' ),
                panel = new panelMod.AnnotatedHistoryPanel({
                    el      : $embeddedHistory.find( ".history-panel" ),
                    model   : new historyModel.History(
                        ${h.dumps( history_dict )},
                        ${h.dumps( hda_dicts )}
                    )
                }).render();

            $embeddedHistory.find( '.expand-content-btn' ).click( toggleExpanded );
            $embeddedHistory.find( '.toggle-embed' ).click( toggleExpanded );
        });
    });
})();
</script>
