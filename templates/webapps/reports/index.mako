<%inherit file="/webapps/reports/base_panels.mako"/>

<%def name="init()">
    ${parent.init()}
    <%
        self.has_left_panel=True
        self.has_right_panel=False
        self.active_view="reports"
    %>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

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
        <div class='unified-panel-header-inner'><span>Reports</span>
            <a target="galaxy_main" href="${h.url_for( controller='home', action='run_stats' )}" class="float-right">
                <span class="fa fa-home"></span>
            </a>
        </div>
    </div>
    <div class="unified-panel-body">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Jobs</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=datetime.utcnow().strftime( "%Y-%m-%d" ), sort_id='default', order='default' )}">Today's jobs</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_month_all', sort_id='default', order='default' )}">Jobs per day this month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_month_in_error', sort_id='default', order='default' )}">Jobs in error per day this month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='specified_date_handler', operation='unfinished', sort_id='default', order='default' )}">All unfinished jobs</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_month_all', sort_id='default', order='default' )}">Jobs per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_month_all', by_destination=True, sort_id='default', order='default' )}">Jobs per month by user / node type</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_month_in_error', sort_id='default', order='default' )}">Jobs in error per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_user', sort_id='default', order='default' )}">Jobs per user</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_user', by_destination=True, sort_id='default', order='default' )}">Jobs per user / node type</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='per_tool', sort_id='default', order='default' )}">Jobs per tool</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='jobs', action='errors_per_tool', sort_id='default', order='default', spark_time='')}">Errors per tool</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Histories</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='history', action='history_and_dataset_per_user' )}">Histories and Datasets per User</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='history', action='history_and_dataset_type' )}">States of Datasets per History</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Tools</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='tools', action='tools_and_job_state' )}">States of Jobs per Tool</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='tools', action='tool_execution_time' )}">Execution Time per Tool</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                    <span>Workflows</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='workflows', action='per_workflow', sort_id='default', order='default' )}">Runs per Workflows</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='workflows', action='per_month_all', sort_id='default', order='default' )}">Workflows per month</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='workflows', action='per_user', sort_id='default', order='default' )}">Workflows per user</a></div>
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
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='last_access_date', sort_id='default', order='default' )}">Date of last login</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='user_disk_usage', sort_id='default', order='default' )}">User disk usage</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='users', action='history_per_user', sort_id='default', order='default' )}">Number of History per user</a></div>
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
    <% center_url = h.url_for( controller='home', action='run_stats' ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
