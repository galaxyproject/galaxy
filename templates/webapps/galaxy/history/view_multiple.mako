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
        bundleEntries.multiHistory(bootstrapped);
    });
</script>

${galaxy_client.load(
    app='app',
    current_history_id=current_history_id,
    includingDeleted=include_deleted_histories,
    order=order,
    limit=limit
)}
</%def>
