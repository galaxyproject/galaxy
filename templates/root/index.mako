<%inherit file="/base_panels.mako"/>

<%def name="late_javascripts()">
    ${parent.late_javascripts()}
    <script type="text/javascript">
    $(function(){
        $("#history-options-button").css( "position", "relative" );
        make_popupmenu( $("#history-options-button"), {
            "List your histories": null,
            "Stored by you": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list')}";
            },
            "Current History": null,
            "Create new": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history_new' )}";
            },
            "Clone": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='clone')}";
            },
            "Share": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='share' )}";
            },
            "Extract workflow": function() {
                galaxy_main.location = "${h.url_for( controller='workflow', action='build_from_current_history' )}";
            },
            "Dataset security": function() {
                galaxy_main.location = "${h.url_for( controller='root', action='history_set_default_permissions' )}";
            },
            "Show deleted datasets": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history', show_deleted=True)}";
            },
            "Delete": function()
            {
                if ( confirm( "Really delete the current history?" ) )
                {
                    galaxy_main.location = "${h.url_for( controller='history', action='delete_current' )}";
                }
            },
            "Manage shared histories": null,
            "Shared by you": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list', operation='sharing' )}";
            },
            "Shared with you": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list_shared')}";
            }
        });
    });
    </script>
</%def>

<%def name="init()">
<%
    self.has_left_panel=True
    self.has_right_panel=True
    self.active_view="analysis"
%>
%if trans.app.config.require_login and not trans.user:
    <script type="text/javascript">
        if ( window != top ) {
            top.location.href = location.href;
        }
    </script>
%endif
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>${n_('Tools')}</div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_tools" src="${h.url_for( controller='root', action='tool_menu' )}" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%; width: 100%;"> </iframe>
    </div>
</%def>

<%def name="center_panel()">

    ## If a specific tool id was specified, load it in the middle frame
    <%
    if trans.app.config.require_login and not trans.user:
        center_url = h.url_for( controller='user', action='login' )
    elif tool_id is not None:
        center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True )
    elif workflow_id is not None:
        center_url = h.url_for( controller='workflow', action='run', id=workflow_id )
    elif m_c is not None:
        center_url = h.url_for( controller=m_c, action=m_a )
    else:
        center_url = h.url_for( '/static/welcome.html' )
    %>
    
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>

</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a id="history-options-button" class='panel-header-button' href="${h.url_for( controller='root', action='history_options' )}" target="galaxy_main"><span>${_('Options')}<span>&#9660;</span></span></a>
            </div>
            <div class="panel-header-text">${_('History')}</div>
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%;" src="${h.url_for( controller='root', action='history' )}"></iframe>
    </div>
</%def>
