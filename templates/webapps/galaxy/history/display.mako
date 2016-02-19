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
        .history-panel {
            margin-top: 8px;
        }
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

<div id="history-${ history_dict[ 'id' ] }" class="history-panel">
</div>
<script type="text/javascript">
    var historyJSON  = ${h.dumps( history_dict )},
        contentsJSON = ${h.dumps( content_dicts )};

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}",
        urlArgs: 'v=${app.server_starttime}'
    })([
        'mvc/history/history-view-annotated',
        'mvc/history/copy-dialog',
    ], function( panelMod, historyCopyDialog ){
        // history module is already in the dpn chain from the panel. We can re-scope it here.
        var historyModel = require( 'mvc/history/history-model' ),
            history = new historyModel.History( historyJSON, contentsJSON, {});

        $( '.history-copy-link' ).click( function( ev ){
            historyCopyDialog( history, { useImport: true, allowAll: false })
                .done( function(){
                    var mainWindow = ( window && ( window !== window.parent ) )? window.top : window;
                    mainWindow.location.href = Galaxy.root;
                });
        });

        window.historyView = new panelMod.AnnotatedHistoryView({
            show_deleted    : false,
            show_hidden     : false,
            el              : $( "#history-" + historyJSON.id ),
            model           : history
        }).render();
    });
</script>
</%def>
