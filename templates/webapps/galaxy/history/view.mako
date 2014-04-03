<%namespace file="/history/history_panel.mako" import="history_panel_javascripts" />
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

<%def name="center_panel()">
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
${history_panel_javascripts()}

%if not use_panels:
<script type="text/javascript">
window.Galaxy = {};
</script>
%endif

</%def>

## ----------------------------------------------------------------------------
<%def name="center_panel()">
<%
    show_deleted = context.get( 'show_deleted', None )
    show_hidden  = context.get( 'show_hidden',  None )

    user_is_owner_json = 'true' if user_is_owner else 'false'
    show_deleted_json  = h.to_json_string( show_deleted )
    show_hidden_json   = h.to_json_string( show_hidden )

    imp_with_deleted_url = h.url_for( controller='history', action='imp', id=history['id'], all_datasets=True )
    imp_without_deleted_url = h.url_for( controller='history', action='imp', id=history['id'] )
%>

<div id="header" class="clear">
    <div id="history-view-controls" class="pull-right">
        %if not user_is_owner and not history[ 'purged' ]:
            <button id="import" class="btn btn-default"></button>
        %endif
        <button id="toggle-deleted" class="btn btn-default"></button>
        <button id="toggle-hidden" class="btn btn-default"></button>
    </div>
</div>

<div id="history-${ history[ 'id' ] }" class="history-panel unified-panel-body" style="overflow: auto;"></div>

<script type="text/javascript">
    $(function(){
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
                $( this ).modeButton( 'current' ) === 'showing_deleted'? 'with_deleted': 'without_deleted' )
        });

        $( '#toggle-hidden' ).modeButton({
            initialMode : "${ 'showing_hidden' if show_hidden else 'not_showing_hidden' }",
            modes: [
                { mode: 'showing_hidden',     html: _l( 'Exclude hidden' ) },
                { mode: 'not_showing_hidden', html: _l( 'Include hidden' ) }
            ]
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
                },
            ]
        });
    });

    var debugging    = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false,
        userIsOwner  = ${'true' if user_is_owner else 'false'},
        historyJSON  = ${h.to_json_string( history )},
        hdaJSON      = ${h.to_json_string( hdas )};
        panelToUse   = ( userIsOwner )?
            ({ location: 'mvc/history/history-panel',           className: 'HistoryPanel' }):
            ({ location: 'mvc/history/readonly-history-panel',  className: 'ReadOnlyHistoryPanel' });

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}"
    })([ 'mvc/user/user-model', panelToUse.location ], function( user, panelMod ){
        $(function(){
            if( !Galaxy.currUser ){
                Galaxy.currUser = new user.User( ${h.to_json_string( get_user_json() )} );
            }
     
            var panelClass = panelMod[ panelToUse.className ],
                // history module is already in the dpn chain from the panel. We can re-scope it here.
                historyModel = require( 'mvc/history/history-model' ),
                hdaBaseView  = require( 'mvc/dataset/hda-base' ),
                history = new historyModel.History( historyJSON, hdaJSON, {
                    logger: ( debugging )?( console ):( null )
                });

            window.historyPanel = new panelClass({
                show_deleted    : ${show_deleted_json},
                show_hidden     : ${show_hidden_json},
                el              : $( "#history-" + historyJSON.id ),
                model           : history,
                onready         : function(){
                    var panel = this;
                    $( '#toggle-deleted' ).on( 'click', function(){
                        panel.toggleShowDeleted();
                    });
                    $( '#toggle-hidden' ).on( 'click', function(){
                        panel.toggleShowHidden();
                    });
                    this.render();
                }
            });
        });
    });
</script>

</%def>
