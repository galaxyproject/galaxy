<%inherit file="/webapps/community/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

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
    <div class="page-container" style="padding: 10px;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    Search
                </div>
                <div class="toolSectionBody">
                    <div class="toolTitle">
                        <a target="galaxy_main" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
                    </div>
                    <div class="toolTitle">
                        <a target="galaxy_main" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    All Repositories
                </div>
                <div class="toolTitle">
                    <a target="galaxy_main" href="${h.url_for( controller='repository', action='browse_categories' )}">Browse by category</a>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    Available Actions
                </div>
                <div class="toolTitle">
                    <a target="galaxy_main" href="${h.url_for( controller='/user', action='login' )}">Login to create a repository</a>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <%
        if trans.app.config.require_login and not trans.user:
            center_url = h.url_for( controller='user', action='login' )
        elif repository_id:
            center_url = h.url_for( controller='repository', action='view_citable_repository', repository_id=repository_id )
        else:
            center_url = h.url_for( controller='repository', action='view_citable_repositories_by_owner', user_id=user_id )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
