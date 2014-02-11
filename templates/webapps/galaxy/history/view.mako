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
    ${h.js( 'mvc/user/user-model' )}
%endif

<script type="text/javascript">
    var using_panels = ${ 'false' if not use_panels else 'true' };
    %if not use_panels:
        window.Galaxy = {};
        Galaxy.currUser = new User(${h.to_json_string( get_user_json() )});
    %endif
</script>
</%def>

## ----------------------------------------------------------------------------
<%def name="center_panel()">
<div id="header" class="clear">
    <div id="history-view-controls" class="pull-right">
        <%
            show_deleted = context.get( 'show_deleted', None )
            show_hidden  = context.get( 'show_hidden',  None )

            show_deleted_js = 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' )
            show_hidden_js  = 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' )
        %>
        %if not history[ 'purged' ]:
            <a id="import" class="btn btn-default" style="display: none;"
               href="${h.url_for( controller='history', action='imp', id=history['id'], include_deleted=show_deleted )}">
                ${_('Import and start using history')}
            </a>
        %endif
        <button id="toggle-deleted" class="btn btn-default">
            ${_('Exclude deleted') if show_deleted else _('Include deleted')}
        </button>
        <button id="toggle-hidden" class="btn btn-default">
            ${_('Exclude hidden') if show_hidden else _('Include hidden')}
        </button>
    </div>
</div>

<div id="history-${ history[ 'id' ] }" class="history-panel unified-panel-body" style="overflow: auto;"></div>

<script type="text/javascript">
    var debugging    = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false,
        historyJSON  = ${h.to_json_string( history )},
        hdaJSON      = ${h.to_json_string( hdas )};
    window.hdaJSON = hdaJSON;

    $( '#toggle-deleted' ).modeButton({
        initialMode : (${ show_deleted_js })?( 'exclude' ):( 'include' ),
        modes: [
            { mode: 'exclude', html: _l( 'Exclude deleted' ) },
            { mode: 'include', html: _l( 'Include deleted' ) }
        ]
    }).click( function(){
        // allow the 'include/exclude deleted' button to control whether the 'import' button includes deleted datasets
        //  when importing or not; when deleted datasets are shown, they'll be imported
        var $importBtn = $( '#import' );
        if( $importBtn.size() ){
            // a bit hacky
            var href = $importBtn.attr( 'href' ),
                includeDeleted = $( this ).modeButton()[0].getMode().mode === 'exclude';
            href = href.replace( /include_deleted=True|False/, ( includeDeleted )?( 'True' ):( 'False' ) );
            $importBtn.attr( 'href', href );
            $importBtn.text( includeDeleted ? _l( 'Import with deleted datasets and start using history' )
                                            : _l( 'Import and start using history' ) );
        }
    });

    $( '#toggle-hidden' ).modeButton({
        initialMode : (${ show_hidden_js })?( 'exclude' ):( 'include' ),
        modes: [
            { mode: 'exclude', html: _l( 'Exclude hidden' ) },
            { mode: 'include', html: _l( 'Include hidden' ) }
        ]
    });

    ##TODO: move to mako
    if( Galaxy.currUser.id !== historyJSON.user_id ){
        $( '#import' ).show();
    }

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}"
    });
    require([ "mvc/history/history-panel" ], function( historyPanel ){
        // history module is already in the dpn chain from the panel. We can re-scope it here.
        var historyModel = require( 'mvc/history/history-model' ),
            hdaBaseView  = require( 'mvc/dataset/hda-base' );

        var history = new historyModel.History( historyJSON, hdaJSON, {
            logger: ( debugging )?( console ):( null )
        });

        window.historyPanel = new historyPanel.HistoryPanel({
            HDAViewClass    : ( Galaxy.currUser.id === historyJSON.user_id )?
                                    ( hdaBaseView.HDAEditView ):( hdaBaseView.HDABaseView ),
            show_deleted    : ${show_deleted_js},
            show_hidden     : ${show_hidden_js},
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
</script>

</%def>
