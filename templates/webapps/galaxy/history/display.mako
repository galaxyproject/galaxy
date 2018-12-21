<%inherit file="/display_base.mako"/>

## Set vars so that there's no need to change the code below.
<%
    history = published_item
    datasets = published_item_data
%>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">

    </style>
</%def>

<%def name="render_item_links( history )">
<%
    encoded_history_id = history_dict[ 'id' ]
    switch_url = h.url_for( controller='history', action='switch_to_history', hist_id=encoded_history_id )
%>
    %if not user_is_owner:
        <a href="javascript:void(0)" class="history-copy-link btn btn-secondary fa fa-plus float-right" title="Import history"></a>
    %else:
        <a href="${switch_url}" class="btn btn-secondary fa fa-plus float-right" title="${_('Switch to this history')}"></a>
    %endif
</%def>

<%def name="render_item_header( item )">
</%def>

<%def name="render_item( history, datasets )">
<div id="history-${ history_dict[ 'id' ] }" class="history-panel"></div>
<script type="text/javascript">
    var historyJSON  = ${h.dumps( history_dict )};

    $( '.page-body' )
        .css( 'height', '100%' )
        .addClass( 'flex-vertical-container' );

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

        var historyModel = new HistoryWithAnnotations( historyJSON, null, {
            order           : 'hid-asc',
        });

        $( '.history-copy-link' ).click( function( ev ){
            window.bundleEntries.HistoryCopyDialog( historyModel, { useImport: true, allowAll: false })
                .done( function(){
                    var mainWindow = ( window && ( window !== window.parent ) )? window.top : window;
                    mainWindow.location.href = Galaxy.root;
                });
        });

        window.historyView = new window.bundleEntries.HistoryViewAnnotated.AnnotatedHistoryView({
            el              : $( "#history-" + historyJSON.id ),
            className       : window.bundleEntries.HistoryViewAnnotated.AnnotatedHistoryView.prototype.className + ' wide',
            model           : historyModel,
            show_deleted    : false,
            show_hidden     : false,
        });
        historyView.trigger( 'loading' );
        historyModel.fetchContents({ silent: true })
            .fail( function(){ alert( 'Galaxy history failed to load' ); })
            .done( function(){
                historyView.trigger( 'loading-done' );
                historyView.render();
            });
    });
</script>
</%def>
