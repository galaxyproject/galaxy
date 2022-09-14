<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline, make_spark_settings" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />

<%!
    import re
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}
<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

<!--jobs_per_user.mako-->
<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                  ${get_pages(sort_id, order, page_specs, 'jobs', 'per_user', spark_time=time_period)}
                </td>
                <td>
                    <h4 align="center">Jobs Per User</h4>
                    <h5 align="center">
                        Click User to view details.
                        Graph goes from present to past
                        ${make_spark_settings("jobs", "per_user", spark_limit, sort_id, order, time_period, page=page, offset=offset, entries=entries)}
                    </h5>
                </td>
                <td align="right">
                  ${get_entry_selector("jobs", "per_user", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs.</td></tr>
            %else:
                <tr class="header">
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'user_email', 'jobs', 'per_user', 'User', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow user_email'>${arrow}</span>
                    </td>
                    <td class="third_width">
                        ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_user', 'Total Jobs', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow total_jobs'>${arrow}</span>
                    </td>
                    <td></td>
                </tr>
                <%
                   ctr = 0
                   entries = 1
                %>
                %for job in jobs:
                    <% key = re.sub(r'\W+', '', job[0]) %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>
                            <a href="${h.url_for( controller='jobs', action='user_per_month', email=job[0], sort_id='default', order='default' )}">
                                ${job[0]}
                            </a>
                        </td>
                        <td>${job[1]}</td>
                        %try:
                            ${make_sparkline(key, trends[key], "bar", "/ " + time_period[:-1])}
                        %except KeyError:
                        %endtry
                        <td id="${key}"></td>
                    </tr>
                    <%
                       ctr += 1
                       entries += 1
                    %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_per_user.mako-->

