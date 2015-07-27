<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

## Default title
<%def name="title()">Galaxy Administration</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}    
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base", "autocomplete_tagging", "tool_menu" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

    <style type="text/css">
        body { margin: 0; padding: 0; overflow: hidden; }
        #left {
            background: #C1C9E5 url(${h.url_for('/static/style/menu_bg.png')}) top repeat-x;
        }

        .unified-panel-body {
            overflow: auto;
        }
        .toolMenu {
            margin: 8px 0 0 10px;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
    <%
        self.has_left_panel=True
        self.has_right_panel=False
        self.active_view="admin"
    %>
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Administration</div>
    </div>
    <div class="unified-panel-body">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionTitle">Server</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='view_datatypes_registry' )}" target="galaxy_main">Data types registry</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='view_tool_data_tables' )}" target="galaxy_main">Data tables registry</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='display_applications' )}" target="galaxy_main">Display applications</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='jobs' )}" target="galaxy_main">Manage jobs</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Tools and Tool Shed</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">                        
                    %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_tool_sheds' )}" target="galaxy_main">Search Tool Shed</a></div>
                    %endif
                    %if installing_repository_ids:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='monitor_repository_installation', tool_shed_repository_ids=installing_repository_ids )}" target="galaxy_main">Monitor installing repositories</a></div>
                    %endif
                    %if is_repo_installed:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_repositories' )}" target="galaxy_main">Manage installed tools</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='reset_metadata_on_selected_installed_repositories' )}" target="galaxy_main">Reset metadata</a></div>
                    %endif
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='package_tool' )}" target="galaxy_main">Download local tool</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='tool_versions' )}" target="galaxy_main">Tool lineage</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='reload_tool' )}" target="galaxy_main">Reload a tool's configuration</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='review_tool_migration_stages' )}" target="galaxy_main">Review tool migration stages</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='tool_errors' )}" target="galaxy_main">View Tool Error Logs</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='sanitize_whitelist' )}" target="galaxy_main">Manage Display Whitelist</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Security</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='users' )}" target="galaxy_main">Users</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='groups' )}" target="galaxy_main">Groups</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='roles' )}" target="galaxy_main">Roles</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='userskeys', action='all_users' )}" target="galaxy_main">API keys</a></div>
                        %if trans.app.config.allow_user_impersonation:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin', action='impersonate' )}" target="galaxy_main">Impersonate a user</a></div>
                        %endif
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Data</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        %if trans.app.config.enable_quotas:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin', action='quotas' )}" target="galaxy_main">Quotas</a></div>
                        %endif
                        <div class="toolTitle"><a href="${h.url_for( controller='library_admin', action='browse_libraries' )}" target="galaxy_main">Data libraries</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='data_manager' )}" target="galaxy_main">Local data</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Form Definitions</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='forms', action='browse_form_definitions' )}" target="galaxy_main">Form definitions</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Sample Tracking</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='external_service', action='browse_external_services' )}" target="galaxy_main">Sequencers and external services</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='request_type', action='browse_request_types' )}" target="galaxy_main">Request types</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_admin', action='browse_requests' )}" target="galaxy_main">Sequencing requests</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_common', action='find_samples', cntrller='requests_admin' )}" target="galaxy_main">Find samples</a></div>
                    </div>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <% center_url = h.url_for( controller='admin', action='center', message=message, status=status ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
