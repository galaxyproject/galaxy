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
    ## Needed to overwide initial width so that link is floated left appropriately.
    %if not user_is_owner:
    <a class="history-copy-link" title="${_('Make a copy of this history and switch to it')}"
       href="javascript:void(0)" style="width: 100%" >
        ${_('Import history')}
    </a>
    %else:
    <a href="${switch_url}" style="width: 100%" title="${_('Make this history your current history')}">
        ${_('Switch to this history')}
    </a>
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

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}",
        urlArgs: 'v=${app.server_starttime}'
    })([
        'mvc/history/history-view-annotated',
        'mvc/history/copy-dialog',
    ], function( panelMod, historyCopyDialog ){
        // history module is already in the dpn chain from the panel. We can re-scope it here.
        var HISTORY = require( 'mvc/history/history-model' );
        var HISTORY_CONTENTS = require( 'mvc/history/history-contents' );

        var HistoryContentsWithAnnotations = HISTORY_CONTENTS.HistoryContents.extend({
            _buildFetchData : function( options ){
                console.log( '_buildFetchData:' );
                options = options || {};
                if( !options.keys && !options.view ){
                    options.view = 'summary';
                    options.keys = 'annotation,tags';
                }
                return HISTORY_CONTENTS.HistoryContents.prototype._buildFetchData.call( this, options );
            }
        });
        var HistoryWithAnnotations = HISTORY.History.extend({
            contentsClass : HistoryContentsWithAnnotations
        });

        var historyModel = new HistoryWithAnnotations( historyJSON, null, {
            order           : 'hid-asc',
        });

        $( '.history-copy-link' ).click( function( ev ){
            historyCopyDialog( historyModel, { useImport: true, allowAll: false })
                .done( function(){
                    var mainWindow = ( window && ( window !== window.parent ) )? window.top : window;
                    mainWindow.location.href = Galaxy.root;
                });
        });

        window.historyView = new panelMod.AnnotatedHistoryView({
            el              : $( "#history-" + historyJSON.id ),
            className       : panelMod.AnnotatedHistoryView.prototype.className + ' wide',
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
