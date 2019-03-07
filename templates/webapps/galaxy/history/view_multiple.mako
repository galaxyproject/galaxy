<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client"/>

<%def name="title()">
    ${_( 'Histories' )}
</%def>

<%def name="center_panel()"></%def>

<%def name="javascript_app()">

    ${galaxy_client.load(
        app='app',
        current_history_id=current_history_id,
        includingDeleted=include_deleted_histories,
        order=order,
        limit=limit
    )}

    <script type="text/javascript">
        config.addInitialization(function(galaxy, config) {
            // Hmm relies on python-printed variable defined elsewhere?
            // That's not great, but the rxjs debouncer should allow
            // the required config to be written before the init runs.
            if ("bootstrapped" in config) {
                window.bundleEntries.multiHistory(config.bootstrapped);
            } else {
                console.warn("Missing config object for multiHistory");
            }
        });
    </script>

</%def>
