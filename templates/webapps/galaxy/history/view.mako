<%namespace file="/galaxy_client_app.mako" import="get_user_json" />

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
#history-view-controls {
    flex: 0 0 44px;
    background-color: white;
    border-bottom: 1px solid #DDD;
    width: 100%;
    padding: 8px;
}
.history-panel > .controls .title {
    font-size: 120%;
}
.history-panel > .controls .title input {
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
    structure_url = h.url_for( controller='history', action='display_structured', id=history[ 'id' ] )

    switch_to_url = h.url_for( controller='history', action='switch_to_history', hist_id=history[ 'id' ] )

    show_deleted = context.get( 'show_deleted', None )
    show_hidden  = context.get( 'show_hidden',  None )

    user_is_owner_json = 'true' if user_is_owner else 'false'
    show_deleted_json  = h.dumps( show_deleted )
    show_hidden_json   = h.dumps( show_hidden )
%>

<div id="history-view-controls" class="clear">
    <div class="pull-left">
        %if not history[ 'purged' ]:
            %if not user_is_owner:
                <button id="import" class="btn btn-default">${ _( 'Import and start using history' ) }</button>
            %elif not history_is_current:
                <button id="switch" class="btn btn-default">${ _( 'Switch to this history' ) }</button>
            %endif
            <a id="structure" href="${ structure_url }" class="btn btn-default">${ _( 'Show structure' ) }</a>
        %endif
    </div>
    <div class="pull-right">
        <button id="toggle-deleted" class="btn btn-default">
            ${ _( 'Include deleted' ) }
        </button>
        <button id="toggle-hidden" class="btn btn-default">
            ${ _( 'Include hidden' ) }
        </button>
    </div>
</div>

<div id="history-${ history[ 'id' ] }" class="history-panel unified-panel-body" style="overflow: auto;"></div>

<script type="text/javascript">

    // use_panels effects where the the center_panel() is rendered:
    //  w/o it renders to the body, w/ it renders to #center - we need to adjust a few things for scrolling to work
    var hasMasthead  = ${ 'true' if use_panels else 'false' },
        userIsOwner  = ${ 'true' if user_is_owner else 'false' },
        isCurrent    = ${ 'true' if history_is_current else 'false' },
        historyJSON  = ${ h.dumps( history ) },
        viewToUse   = ( userIsOwner )?
//TODO: change class names
            ({ location: 'mvc/history/history-view-edit',  className: 'HistoryViewEdit' }):
            ({ location: 'mvc/history/history-view',       className: 'HistoryView' });

    require.config({
        baseUrl : "${h.url_for( '/static/scripts' )}",
        paths   : {
            'jquery' : 'libs/jquery/jquery'
        },
        urlArgs: 'v=${app.server_starttime}'
    })([
        'mvc/user/user-model',
        viewToUse.location,
        'mvc/history/copy-dialog',
        'utils/localization',
        'ui/mode-button'
    ], function( user, viewMod, historyCopyDialog, _l ){
        +(function setUpBehaviors(){
            $( '#toggle-deleted' ).modeButton({
                initialMode : "${ 'showing_deleted' if show_deleted else 'not_showing_deleted' }",
                modes: [
                    { mode: 'showing_deleted',      html: _l( 'Exclude deleted' ) },
                    { mode: 'not_showing_deleted',  html: _l( 'Include deleted' ) }
                ]
            });

            $( '#toggle-hidden' ).modeButton({
                initialMode : "${ 'showing_hidden' if show_hidden else 'not_showing_hidden' }",
                modes: [
                    { mode: 'showing_hidden',     html: _l( 'Exclude hidden' ) },
                    { mode: 'not_showing_hidden', html: _l( 'Include hidden' ) }
                ]
            });

            $( '#switch' ).click( function( ev ){
                //##HACK:ity hack hack
                //##TODO: remove when out of iframe
                var hview = Galaxy.currHistoryPanel
                         || ( top.Galaxy && top.Galaxy.currHistoryPanel )? top.Galaxy.currHistoryPanel : null;
                if( hview ){
                    hview.switchToHistory( "${ history[ 'id' ] }" );
                } else {
                    window.location = "${ switch_to_url }";
                }
            });

        })();

        $(function(){
            if( hasMasthead ){
                $( '#center' ).addClass( 'flex-vertical-container' );
            }

            var viewClass = viewMod[ viewToUse.className ],
                // history module is already in the dpn chain from the view. We can re-scope it here.
                HISTORY = require( 'mvc/history/history-model' ),
                historyModel = new HISTORY.History( historyJSON );

            // attach the copy dialog to the import button now that we have a history
            $( '#import' ).click( function( ev ){
                historyCopyDialog( historyModel, {
                    useImport   : true,
                    // use default datasets option to match the toggle-deleted button
                    allDatasets : $( '#toggle-deleted' ).modeButton( 'getMode' ).mode === 'showing_deleted',
                }).done( function(){
                    if( window === window.parent ){
                        window.location = Galaxy.root;
                    } else if( Galaxy.currHistoryPanel ){
                        Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                });
            });

            window.historyView = new viewClass({
                el              : $( "#history-" + historyJSON.id ),
                className       : viewClass.prototype.className + ' wide',
                $scrollContainer: hasMasthead? function(){ return this.$el.parent(); } : undefined,
                model           : historyModel,
                show_deleted    : ${show_deleted_json},
                show_hidden     : ${show_hidden_json},
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
            });
            historyView.trigger( 'loading' );
            historyModel.fetchContents({ silent: true })
                .fail( function(){ alert( 'Galaxy history failed to load' ); })
                .done( function(){
                    historyView.trigger( 'loading-done' );
                    historyView.render();
                });

            $( '#toggle-deleted' ).on( 'click', function(){
                historyView.toggleShowDeleted();
            });
            $( '#toggle-hidden' ).on( 'click', function(){
                historyView.toggleShowHidden();
            });
        });
    });
</script>

</%def>
