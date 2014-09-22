<%namespace file="/galaxy.masthead.mako" import="get_user_json" />

## ----------------------------------------------------------------------------
<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
%>
</%def>

## ----------------------------------------------------------------------------
<%def name="body()">
    ${center_panel()}
</%def>

## ----------------------------------------------------------------------------
<%def name="title()">
    ${history[ 'name' ]}
</%def>

## ----------------------------------------------------------------------------
<%def name="stylesheets()">
${parent.stylesheets()}
<style>
%if not use_panels:
    body, html {
        margin: 0px;
        padding: 0px;
    }
%endif
#header {
    background-color: white;
    border-bottom: 1px solid #DDD;
    width: 100%;
    height: 48px;
}
#history-view-controls {
    margin: 10px 10px 10px 10px;
}
.history-panel {
    /* this and the height of #header above are way too tweaky */
    margin-top: 18px;
}
.history-title {
    font-size: 120%;
}
.history-title input {
    font-size: 100%;
}
a.btn {
    text-decoration: none;
}
</style>
</%def>

## ----------------------------------------------------------------------------
<%def name="javascripts()">
${parent.javascripts()}

</%def>

## ----------------------------------------------------------------------------
<%def name="center_panel()">
<%
    imp_with_deleted_url = h.url_for( controller='history', action='imp', id=history[ 'id' ], all_datasets=True )
    imp_without_deleted_url = h.url_for( controller='history', action='imp', id=history[ 'id' ] )

    structure_url = h.url_for( controller='history', action='display_structured', id=history[ 'id' ] )

    switch_to_url = h.url_for( controller='history', action='switch_to_history', hist_id=history[ 'id' ] )

    show_deleted = context.get( 'show_deleted', None )
    show_hidden  = context.get( 'show_hidden',  None )

    user_is_owner_json = 'true' if user_is_owner else 'false'
    show_deleted_json  = h.dumps( show_deleted )
    show_hidden_json   = h.dumps( show_hidden )
%>

<div id="header" class="clear">
    <div id="history-view-controls">
        <div class="pull-left">
            %if not history[ 'purged' ]:
                %if user_is_owner:
                    <button id="switch" class="btn btn-default">${ _( 'Switch to this history' ) }</button>
                %else:
                    <button id="import" class="btn btn-default"></button>
                %endif
                <a id="structure" href="${ structure_url }" class="btn btn-default">${ _( 'Show structure' ) }</a>
            %endif
        </div>
        <div class="pull-right">
            <button id="toggle-deleted" class="btn btn-default"></button>
            <button id="toggle-hidden" class="btn btn-default"></button>
        </div>
    </div>
</div>

<div id="history-${ history[ 'id' ] }" class="history-panel unified-panel-body" style="overflow: auto;"></div>

<script type="text/javascript">

    function setUpBehaviors(){

        $( '#toggle-deleted' ).modeButton({
            initialMode : "${ 'showing_deleted' if show_deleted else 'not_showing_deleted' }",
            modes: [
                { mode: 'showing_deleted',      html: _l( 'Exclude deleted' ) },
                { mode: 'not_showing_deleted',  html: _l( 'Include deleted' ) }
            ]
        }).click( function(){
            // allow the 'include/exclude deleted' button to control whether the 'import' button includes deleted
            //  datasets when importing or not; when deleted datasets are shown, they'll be imported
            $( '#import' ).modeButton( 'setMode',
                $( this ).modeButton( 'current' ) === 'showing_deleted'? 'with_deleted': 'without_deleted' );
        });

        $( '#toggle-hidden' ).modeButton({
            initialMode : "${ 'showing_hidden' if show_hidden else 'not_showing_hidden' }",
            modes: [
                { mode: 'showing_hidden',     html: _l( 'Exclude hidden' ) },
                { mode: 'not_showing_hidden', html: _l( 'Include hidden' ) }
            ]
        });

        $( '#switch' ).click( function( ev ){
            ##HACK:ity hack hack
            ##TODO: remove when out of iframe
            var hpanel = Galaxy.currHistoryPanel
                      || ( top.Galaxy && top.Galaxy.currHistoryPanel )? top.Galaxy.currHistoryPanel : null;
            if( hpanel ){
                hpanel.switchToHistory( "${ history[ 'id' ] }" );
            } else {
                window.location = "${ switch_to_url }";
            }
        });
        
        $( '#import' ).modeButton({
            switchModesOnClick : false,
            initialMode : "${ 'with_deleted' if show_deleted else 'without_deleted' }",
            modes: [
                { mode: 'with_deleted', html: _l( 'Import with deleted datasets and start using history' ),
                    onclick: function importWithDeleted(){
                        window.location = '${imp_with_deleted_url}';
                    }
                },
                { mode: 'without_deleted', html: _l( 'Import and start using history' ),
                    onclick: function importWithoutDeleted(){
                        window.location = '${imp_without_deleted_url}';
                    }
                }
            ]
        });
    }

    var userIsOwner  = ${'true' if user_is_owner else 'false'},
        historyJSON  = ${h.dumps( history )},
        hdaJSON      = ${h.dumps( hdas )};
        panelToUse   = ( userIsOwner )?
//TODO: change class names
            ({ location: 'mvc/history/history-panel-edit',  className: 'HistoryPanelEdit' }):
            ({ location: 'mvc/history/history-panel',       className: 'HistoryPanel' });

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}"
    })([ 'mvc/user/user-model', panelToUse.location, 'utils/localization' ], function( user, panelMod, _l ){
        $(function(){
            setUpBehaviors();
     
            var panelClass = panelMod[ panelToUse.className ],
                // history module is already in the dpn chain from the panel. We can re-scope it here.
                historyModel = require( 'mvc/history/history-model' ),
                history = new historyModel.History( historyJSON, hdaJSON );

            window.historyPanel = new panelClass({
                show_deleted    : ${show_deleted_json},
                show_hidden     : ${show_hidden_json},
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                el              : $( "#history-" + historyJSON.id ),
                model           : history
            }).render();

            $( '#toggle-deleted' ).on( 'click', function(){
                historyPanel.toggleShowDeleted();
            });
            $( '#toggle-hidden' ).on( 'click', function(){
                historyPanel.toggleShowHidden();
            });
        });
    });
</script>

</%def>
