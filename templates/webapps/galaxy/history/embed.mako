<%namespace file="/display_common.mako" import="*" />

## Some duplication with embed_base here, needed a way to override the main embedded-item html for histories
<%
    encoded_history_id = trans.security.encode_id( item.id )
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
            <a title="Import history" class="icon-button import" href="javascript:void(0)"></a>
            <a title="View history" class="icon-button go-to-full-screen" href="${display_href}"></a>
        </div>
        <h4>
            <a class="toggle-embed" href="${display_href}" title="Show or hide history contents">
                Galaxy History | ${get_item_name( item ) | h}
            </a>
        </h4>
        %if hasattr( item, "annotation") and item.annotation:
        <div class="annotation">${ item.annotation | h }</div>
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
    var scripts = document.getElementsByTagName( 'script' );
        // this is executed immediately, so the last script will be this script
    var thisScript = scripts[ scripts.length - 1 ];
    var $embeddedHistory = $( thisScript ).prev();

    var $embeddedHistory = $( thisScript ).prev();
    $embeddedHistory.find( '.item-content' ).addClass( 'flex-vertical-container' );

    $(function(){
        var HistoryContentsWithAnnotations = window.bundleEntries.HistoryContents.extend({
            _buildFetchData : function( options ){
                console.log( '_buildFetchData:' );
                options = options || {};
                if( !options.keys && !options.view ){
                    options.view = 'summary';
                    options.keys = 'annotation,tags';
                }
                return window.bundleEntries.HistoryContents.prototype._buildFetchData.call( this, options );
            }
        });
        var HistoryWithAnnotations = window.bundleEntries.History.extend({
            contentsClass : HistoryContentsWithAnnotations
        });

        var historyJSON = ${h.dumps( history_dict )};
        var historyModel = new HistoryWithAnnotations( historyJSON, null, {
            order           : 'hid-asc',
        });

        var historyView = new window.bundleEntries.HistoryViewAnnotated.AnnotatedHistoryView({
            el          : $embeddedHistory.find( ".history-panel" ),
            className   : window.bundleEntries.HistoryViewAnnotated.AnnotatedHistoryView.prototype.className + ' wide',
            model       : historyModel
        });

        historyView.trigger( 'loading' );
        historyModel.fetchContents({ silent: true })
            .fail( function(){ alert( 'Galaxy history failed to load' ); })
            .done( function(){
                historyView.trigger( 'loading-done' );
                historyView.render();
            });

        function toggleExpanded( ev ){
            ev.preventDefault();
            $embeddedHistory.find( '.expand-content-btn' ).toggleClass( 'toggle-expand' ).toggleClass( 'toggle' );
            $embeddedHistory.find( ".summary-content" ).slideToggle( "fast" );
            $embeddedHistory.find( ".annotation" ).slideToggle( "fast" );
            $embeddedHistory.find( ".expanded-content" ).slideToggle( "fast" );
        }

        $embeddedHistory.find( '.expand-content-btn' ).click( toggleExpanded );
        $embeddedHistory.find( '.toggle-embed' ).click( toggleExpanded );

        function showConfirmationModal( name ){
            var body = [
                    '<div class="donemessagelarge">',
                        _l( 'History imported' ), ': ', _.escape( historyModel.get( 'name' ) ),
                    '</div>'
                ].join('');
            Galaxy.modal.show({
                title : _l( 'Success!' ),
                body : $( body ),
                buttons : {
                    'Return to the published page' : function(){
                        Galaxy.modal.hide();
                    },
                    'Start using the history' : function(){
                        window.location = Galaxy.root;
                    },
                }
            });
            Galaxy.modal.$( '.modal-header' ).hide();
            Galaxy.modal.$( '.modal-body' ).css( 'padding-bottom', 0 );
            Galaxy.modal.$( '.modal-footer' ).css({ border : 0, 'padding-top': 0 });
        }

        $embeddedHistory.find( '.import' ).click( function( ev ){
            var dialogOptions = { useImport: true, allowAll: false, autoClose: false };
            window.bundleEntries.HistoryCopyDialog( historyModel, dialogOptions ).done( showConfirmationModal );
        })
    });
})();
</script>
