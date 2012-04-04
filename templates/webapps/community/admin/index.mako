<%inherit file="/webapps/community/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">   
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
        self.active_view="tools"
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
        <div class='unified-panel-header-inner'>Administration</div>
    </div>
    <div class="page-container" style="padding: 10px;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionTitle">
                    Repositories
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_categories', webapp='community' )}">Browse by category</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='browse_repositories', webapp='community' )}">Browse all repositories</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='reset_all_repository_metadata', webapp='community' )}">Reset all metadata</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='browse_repository_metadata', webapp='community' )}">Browse metadata</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_invalid_tools', cntrller='admin', webapp='community' )}">Browse invalid tools</a>
                        </div>
                    </div>
                </div>
                <div class="toolSectionTitle">
                    Categories
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='manage_categories', webapp='community' )}">Manage categories</a>
                        </div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    Security
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='users', webapp='community' )}">Manage users</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='groups', webapp='community' )}">Manage groups</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='roles', webapp='community' )}">Manage roles</a>
                        </div>
                    </div>
                </div>
                <div class="toolSectionTitle">
                    Statistics
                </div>
                    <div class="toolTitle">
                        <a target="galaxy_main" href="${h.url_for( controller='admin', action='regenerate_statistics', webapp='community' )}">View shed statistics</a>
                    </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <%
        center_url = h.url_for( action='center', webapp='community' )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
