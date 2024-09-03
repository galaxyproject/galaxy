<%inherit file="/webapps/tool_shed/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
    ${parent.init()}
    <%
        self.has_left_panel=True
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
    <div style="padding: 0.5rem;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionTitle">
                    Repositories
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_categories' )}">Browse by category</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='browse_repositories' )}">Browse all repositories</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='reset_metadata_on_selected_repositories_in_tool_shed' )}">Reset selected metadata</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='browse_repository_metadata' )}">Browse metadata</a>
                        </div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    Categories
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='manage_categories' )}">Manage categories</a>
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
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='users' )}">Manage users</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='groups' )}">Manage groups</a>
                        </div>
                        <div class="toolTitle">
                            <a target="galaxy_main" href="${h.url_for( controller='admin', action='roles' )}">Manage roles</a>
                        </div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    Statistics
                </div>
                <div class="toolSectionBody">
                    <div class="toolTitle">
                        <a target="galaxy_main" href="${h.url_for( controller='admin', action='regenerate_statistics' )}">View shed statistics</a>
                    </div>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <%
        center_url = h.url_for(controller='admin', action='center' )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 75%; height: 100%;" src="${center_url}"> </iframe>
</%def>
