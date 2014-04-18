<%inherit file="/base.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client" />

<%def name="title()">
    ${ _( 'Galaxy History' ) }
</%def>

## -----------------------------------------------------------------------------
<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <style>
        body.historyPage {
            margin: 0px;
            padding: 0px;
        }
    </style>
</%def>

## -----------------------------------------------------------------------------
<%def name="javascripts()">
${ parent.javascripts() }

<script type="text/javascript">
$(function(){
    $( 'body' ).addClass( 'historyPage' ).addClass( 'history-panel' );
});

window.app = function(){
    require([
        'mvc/history/current-history-panel'
    ], function( historyPanel ){
        $(function(){
            // history module is already in the dpn chain from the panel. We can re-scope it here.
            var historyModel    = require( 'mvc/history/history-model' );
            window.panel = new historyPanel.CurrentHistoryPanel({
                show_deleted    : bootstrapped.show_deleted,
                show_hidden     : bootstrapped.show_hidden,
                el              : $( "body" ),
                model           : new historyModel.History( bootstrapped.history, bootstrapped.hdas ),
                onready         : function(){
                    this.render( 0 );
                }
            });
        });
    });
}
</script>
${ galaxy_client.load( 'app', history=history, hdas=hdas, show_deleted=show_deleted, show_hidden=show_hidden ) }

</%def>
