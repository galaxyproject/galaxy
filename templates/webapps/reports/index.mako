<%inherit file="/webapps/reports/base_panels.mako"/>

<%def name="init()">
    <%
        self.has_left_panel=True
        self.has_right_panel=False
        self.active_view="reports"
    %>
</%def>

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
                    <span>Sample Tracking</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='sample_tracking', action='per_month_all' )}">Sequencing requests per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='sample_tracking', action='per_user' )}">Sequencing requests per user</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Workflows</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='workflows', action='per_month_all' )}">Workflows per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='workflows', action='per_user' )}">Workflows per user</a></div>
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
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='user_disk_usage' )}">User disk usage</a></div>
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
