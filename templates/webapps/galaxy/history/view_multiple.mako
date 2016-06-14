
<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client"/>

<%def name="title()">
    ${_( 'Histories' )}
</%def>

## ----------------------------------------------------------------------------
<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <style type="text/css">
    /* reset */
    html, body {
        margin: 0px;
        padding: 0px;
    }
    </style>
</%def>


## ----------------------------------------------------------------------------
<%def name="center_panel()"></%def>

<%def name="javascript_app()">
<script type="text/javascript">
define( 'app', function(){
    require([
        'mvc/history/history-model',
        'mvc/history/multi-panel'
    ], function( HISTORY_MODEL, MULTI_HISTORY ){
        $(function(){
            histories = new HISTORY_MODEL.HistoryCollection( [], {
                includeDeleted      : bootstrapped.includingDeleted,
                order               : bootstrapped.order,
                limitOnFirstFetch   : bootstrapped.limit,
                limitPerFetch       : bootstrapped.limit,
                // lastFetched         : bootstrapped.limit,
                currentHistoryId    : bootstrapped.current_history_id,
            });

            multipanel = new MULTI_HISTORY.MultiPanelColumns({
                el                          : $( '#center' ).get(0),
                histories                   : histories,
            })
            histories.fetchFirst({ silent: true })
                .done( function(){
                    multipanel.createColumns();
                    multipanel.render( 0 );
                });
        });
    });
});
</script>
${ galaxy_client.load( app='app', current_history_id=current_history_id,
    includingDeleted=include_deleted_histories, order=order, limit=limit ) }
##${ galaxy_client.load( app='app', histories=histories,
##    includingDeleted=include_deleted_histories, order=order, limit=limit ) }
</%def>
