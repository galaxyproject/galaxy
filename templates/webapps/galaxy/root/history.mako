<%inherit file="/base.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client" />

<%def name="title()">
    ${ _( 'Galaxy History' ) }
</%def>

<%def name="stylesheets()">
${ parent.stylesheets() }
<style>
.historyPage {
    background: #DFE5F9;
    color: #333;
    margin: 5px;
    border: 0;
    padding: 0;
}

</style>
</%def>

## -----------------------------------------------------------------------------
<%def name="javascripts()">
${ parent.javascripts() }
<script type="text/javascript">
$(function(){
    $( 'body' ).addClass( 'historyPage' ).addClass( 'history-panel' )
        .css({ margin: '0px', padding: '0px' });
});
</script>
</%def>

<%def name="javascript_app()">
<script type="text/javascript">
define( 'app', function(){
    require([
        'mvc/history/history-panel-edit'
    ], function( historyPanel ){
        $(function(){
            // history module is already in the dpn chain from the panel. We can re-scope it here.
            var historyModel    = require( 'mvc/history/history-model' );
            window.panel = new historyPanel.HistoryPanelEdit({
                show_deleted    : bootstrapped.show_deleted,
                show_hidden     : bootstrapped.show_hidden,
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                model           : new historyModel.History( bootstrapped.history, bootstrapped.contents )
            });
            panel.render().$el.appendTo( 'body' );
        });
    });
});
</script>
${ galaxy_client.load( app='app', history=history, contents=contents,
    show_deleted=show_deleted, show_hidden=show_hidden ) }
</%def>
