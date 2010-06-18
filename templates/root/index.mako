<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="late_javascripts()">
    ${parent.late_javascripts()}
    <script type="text/javascript">
    $(function(){
        // Init history options.
        $("#history-options-button").css( "position", "relative" );
        make_popupmenu( $("#history-options-button"), {
            "History Lists": null,
            "Saved Histories": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list')}";
            },
            "Histories Shared with Me": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list_shared')}";
            },
            "Current History": null,
            "Create New": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history_new' )}";
            },
            "Clone": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='clone')}";
            },
            "Share or Publish": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='sharing' )}";
            },
            "Extract Workflow": function() {
                galaxy_main.location = "${h.url_for( controller='workflow', action='build_from_current_history' )}";
            },
            "Dataset Security": function() {
                galaxy_main.location = "${h.url_for( controller='root', action='history_set_default_permissions' )}";
            },
            "Show Deleted Datasets": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history', show_deleted=True)}";
            },
            "Show structure": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='display_structured' )}";
            },
            "Export to File": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='export_archive' )}";
            },
            "Delete": function()
            {
                if ( confirm( "Really delete the current history?" ) )
                {
                    galaxy_main.location = "${h.url_for( controller='history', action='delete_current' )}";
                }
            },
            "Other Actions": null,
            "Import from File": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='import_archive' )}";
            }
        });
        
        // Init tool options.
        %if trans.app.toolbox_search.enabled:
            make_popupmenu( $("#tools-options-button"), {
                    "Search Tools": function() {
                    // Show/hide menu and update user preference for menu visibility.
                    var tool_menu_frame = $("#galaxy_tools").contents();
                    var menu = tool_menu_frame.find('#tool-search');
                    if (menu.is(":visible"))
                    {
                        // Hide menu.
                        pref_value = "False";
                        menu_option_text = "Search Tools";
                        menu.toggle();
                
                        // Reset search.
                        reset_tool_search(true);
                    }
                    else
                    {
                        // Show menu.
                        pref_value = "True";
                        menu_option_text = "Hide Search";
                        menu.toggle();
                    }
            
                    // Update menu option.
                    $("#tools-options-button-menu").find("li").first().text(menu_option_text);
            
                    // TODO: Set user preference.
                    /*
                    TODO: uncomment this when this method is working.
                    $.ajax({
                        url: "${h.url_for( controller='/user', action='set_user_pref_async' )}",
                        data: { "pref_name" : "show_tool_search",
                                "pref_value" : pref_value
                              },
                        error: function() { 
                            alert( "Failed to set user preference." );
                        },
                    });
                    */
                }
            });
        %endif        
    });
    </script>
</%def>

<%def name="init()">
<%
	if trans.app.config.cloud_controller_instance:
		self.has_left_panel=False
		self.has_right_panel=False
		self.active_view="cloud"
	else:
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
        <div class='unified-panel-header-inner'>
            <div style="float: right">
                <a class='panel-header-button popup' id="tools-options-button" href="#">${_('Options')}</a>
            </div>
            ${n_('Tools')}
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_tools" id="galaxy_tools" src="${h.url_for( controller='root', action='tool_menu' )}" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%; width: 100%;"> </iframe>
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
    elif trans.app.config.cloud_controller_instance:
    	center_url = h.url_for( controller='cloud', action='list' )
    else:
        center_url = h.url_for( '/static/welcome.html' )
    %>
    
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>

</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a id="history-options-button" class='panel-header-button popup' href="${h.url_for( controller='root', action='history_options' )}" target="galaxy_main">${_('Options')}</a>
            </div>
            <div class="panel-header-text">${_('History')}</div>
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%;" src="${h.url_for( controller='root', action='history' )}"></iframe>
    </div>
</%def>
