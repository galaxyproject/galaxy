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

    $(function(){
        options = {
            hasMasthead: ${ 'true' if use_panels else 'false' },
            userIsOwner: ${ 'true' if user_is_owner else 'false' },
            isCurrent: ${ 'true' if history_is_current else 'false' },
            historyJSON: ${ h.dumps( history ) },
            showDeletedJson: ${ show_deleted_json },
            showHiddenJson: ${ show_hidden_json },
            initialModeDeleted: "${ 'showing_deleted' if show_deleted else 'not_showing_deleted' }",
            initialModeHidden: "${ 'showing_hidden' if show_hidden else 'not_showing_hidden' }",
            allowUserDatasetPurge: ${ 'true' if trans.app.config.allow_user_dataset_purge else 'false' }
        };
        options.viewToUse = options.userIsOwner ?
                ({ location: 'mvc/history/history-view-edit',  className: 'HistoryViewEdit' }):
                ({ location: 'mvc/history/history-view',       className: 'HistoryView' });
        window.bundleEntries.history(options);
    });
</script>

</%def>
