<%namespace file="/display_common.mako" import="*" />

<%
    import_href = h.url_for( controller='visualization', action='imp', id=encoded_visualization_id )
    display_href = h.url_for( controller='visualization', action='display_by_username_and_slug',
        username=item.user.username, slug=item.slug )
%>
<div id="visualization-${encoded_visualization_id}" class='embedded-item display visualization'>
    <div class='title'>
        <div style="float: left">
            <a class="expand-content-btn icon-button toggle-expand" href="${display_href}"
               title="Show or hide visualization"></a>
        </div>
        <div style="float: right;">
            <a title="Import" class="icon-button import" href="${import_href}"></a>
            <a title="View" class="icon-button go-to-full-screen" href="${display_href}"></a>
        </div>
        <h4>
            <a class="toggle-embed" href="${display_href}" title="Show or hide visualization">
                Galaxy Visualization | ${get_item_name( item )}
            </a>
        </h4>
        %if hasattr( item, "annotation") and item.annotation:
        <div class="annotation">${item.annotation}</div>
        %endif
    </div>
    <div class='expanded-content'>
        <div class='item-content'>
        </div>
    </div>
</div>

<script type="text/javascript">
// Embedding the same visualization more than once will confuse DOM ids.
//  In order to handle this, find this script and cache the previous node (the div above).
//  (Since we need thisScript to be locally scoped or it will get overwritten, enclose in self-calling function)
(function(){
    var scripts = document.getElementsByTagName( 'script' ),
        // this is executed immediately, so the last script will be this script
        thisScript = scripts[ scripts.length - 1 ],
        $embeddedObj = $( thisScript ).prev();

    /** check for an existing iframe for this visualization, adding one to the item-content if needed */
    function addVisualizationIFrame(){
        var $embeddedObj = $( thisScript ).prev(),
            $itemContent = $embeddedObj.find( '.expanded-content .item-content' ),
            $iframe = $itemContent.find( 'iframe' );
        if( $iframe.size() ){ return $iframe; }
        return $itemContent.html([
                '<iframe frameborder="0" width="100%" height="100%" ',
                        'sandbox="allow-forms allow-same-origin allow-scripts" ',
                        'src="/visualization/saved?id=${encoded_visualization_id}&embedded=True">',
                '</iframe>'
            ].join('')).find( 'iframe' );
    }

    /** 4 elements change when expanding - toggle them all, add the iframe and prevent the url change */
    function toggleExpanded( ev ){
        var $embeddedObj = $( thisScript ).prev();
        $embeddedObj.find( '.expand-content-btn' ).toggleClass( 'toggle-expand' ).toggleClass( 'toggle' ).show();
        $embeddedObj.find( ".summary-content" ).slideToggle( "fast" );
        $embeddedObj.find( ".annotation" ).slideToggle( "fast" );
        $embeddedObj.find( ".expanded-content" ).slideToggle( "fast" );
        addVisualizationIFrame();
        ev.preventDefault();
    }

    // add expansion to +/- btn and title
    $(function(){
        var $embeddedObj = $( thisScript ).prev();
        // clear the handlers (w/ off) created in page/display/mako for visualizations
        $embeddedObj.find( '.expand-content-btn' ).off().click( toggleExpanded );
        $embeddedObj.find( '.toggle-embed' ).off().click( toggleExpanded );
    });
})();
</script>
