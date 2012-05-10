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
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery", "galaxy.base" )}
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
    <div class="page-container" style="padding: 10px;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionTitle">Security</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='users', webapp=webapp )}" target="galaxy_main">Manage users</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='groups', webapp=webapp )}" target="galaxy_main">Manage groups</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='roles', webapp=webapp )}" target="galaxy_main">Manage roles</a></div>
                        %if trans.app.config.allow_user_impersonation:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin', action='impersonate', webapp=webapp )}" target="galaxy_main">Impersonate a user</a></div>
                        %endif
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Data</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='quotas', webapp=webapp )}" target="galaxy_main">Manage quotas</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='library_admin', action='browse_libraries' )}" target="galaxy_main">Manage data libraries</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='data_admin', action='manage_data' )}" target="galaxy_main">Manage local data</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Server</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='tool_versions' )}" target="galaxy_main">Tool versions</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='reload_tool' )}" target="galaxy_main">Reload a tool's configuration</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='memdump' )}" target="galaxy_main">Profile memory usage</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='jobs' )}" target="galaxy_main">Manage jobs</a></div>
                        %if cloned_repositories:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_repositories' )}" target="galaxy_main">Manage installed tool shed repositories</a></div>
                        %endif
                    </div>
                </div>
                %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                    <div class="toolSectionPad"></div>
                    <div class="toolSectionTitle">Tool sheds</div>
                    <div class="toolSectionBody">
                        <div class="toolSectionBg">                        
                            <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_tool_sheds' )}" target="galaxy_main">Search and browse tool sheds</a></div>
                        </div>
                    </div>
                %endif
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Form Definitions</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='forms', action='browse_form_definitions' )}" target="galaxy_main">Manage form definitions</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Sample Tracking</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='external_service', action='browse_external_services' )}" target="galaxy_main">Manage sequencers and external services</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='request_type', action='browse_request_types' )}" target="galaxy_main">Manage request types</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_admin', action='browse_requests' )}" target="galaxy_main">Sequencing requests</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_common', action='find_samples', cntrller='requests_admin' )}" target="galaxy_main">Find samples</a></div>
                    </div>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <% center_url = h.url_for( controller='admin', action='center', webapp='galaxy', message=message, status=status ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
