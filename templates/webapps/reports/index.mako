<%inherit file="/webapps/reports/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="init()">
    <%
        self.has_left_panel=True
        self.has_right_panel=False
        self.active_view="reports"
    %>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}    
    ## TODO: Clean up these styles and move into panel_layout.css (they are
    ## used here and in the editor).
    <style type="text/css">
    #left {
        background: #C1C9E5 url(${h.url_for('/static/style/menu_bg.png')}) top repeat-x;
    }
    div.toolMenu {
        margin: 5px;
        margin-left: 10px;
        margin-right: 10px;
    }
    div.toolSectionPad {
        margin: 0;
        padding: 0;
        height: 5px;
        font-size: 0px;
    }
    div.toolSectionDetailsInner { 
        margin-left: 5px;
        margin-right: 5px;
    }
    div.toolSectionTitle {
        padding-bottom: 0px;
        font-weight: bold;
    }
    div.toolMenuGroupHeader {
        font-weight: bold;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
        color: #333;
        font-style: italic;
        border-bottom: dotted #333 1px;
        margin-bottom: 0.5em;
    }    
    div.toolTitle {
        padding-top: 5px;
        padding-bottom: 5px;
        margin-left: 16px;
        margin-right: 10px;
        display: list-item;
        list-style: square outside;
    }
    a:link, a:visited, a:active
    {
        color: #303030;
    }
    </style>
</%def>

<%def name="left_panel()">
    <%
        from datetime import datetime
        from time import mktime, strftime, localtime
    %>
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Reports</div>
    </div>
    <div class="page-container" style="padding: 10px;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Jobs</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=datetime.utcnow().strftime( "%Y-%m-%d" ) )}">Today's jobs</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_month_all' )}">Jobs per day this month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_month_in_error' )}">Jobs in error per day this month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_date_handler', operation='unfinished' )}">All unfinished jobs</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_month_all' )}">Jobs per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_month_in_error' )}">Jobs in error per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_user' )}">Jobs per user</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_tool' )}">Jobs per tool</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Users</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='registered_users' )}">Registered users</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='last_access_date' )}">Date of last login</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>System</span>
                </div>
                  <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='system', action='index' )}">Disk space maintenance</a></div>
                    </div>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <% center_url = h.url_for( controller='jobs', action='specified_month_all' ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
