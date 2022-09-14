<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />

<%
   import datetime
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

${get_css()}

<!--jobs_per_month_by_user_and_destination.mako-->
<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'jobs', 'per_month_all')}
                </td>
                <td>
                    <h4 align="center">Jobs Per Month by User/Node type</h4>
                    <h5 align="center">
                        Click Month to view details.
                        Graph goes from the 1st to the last of the month.
                    </h5>
                </td>
                <td align="right">
                    ${get_entry_selector("jobs", "per_month_all", page_specs.entries, sort_id, order, by_destination=True)}
                </td>
            </tr>
        </table>

        <table align="center" width="80%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="7">There are no jobs.</td></tr>
            %else:
                <tr class="header">
                    <td class="seventh_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'per_month_all', 'Month', page=page, offset=offset, entries=entries, by_destination=True)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td class="seventh_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'per_month_all', 'User', page=page, offset=offset, entries=entries, by_destination=True)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td class="seventh_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'per_month_all', 'Node Type', page=page, offset=offset, entries=entries, by_destination=True)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
					<td class="seventh_width">
                        ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_month_all', 'Jobs', page=page, offset=offset, entries=entries, by_destination=True)}
                        <span class='dir_arrow total_jobs'>${arrow}</span>
                    </td>
                    <td class="seventh_width">
                         Total Execution Time: seconds
                    </td>
                    <td class="seventh_width">
                         Total Execution Time: hh:mm:ss
                    </td>
                    <td></td>
                </tr>
                <%
                    ctr = 0
                    entries = 1
                %>
                %for job in jobs:
                    <% key = str(job[2]) + str(job[3]) %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>
                            <a href="${h.url_for( controller='jobs', action='specified_month_all', specified_date=job[0]+'-01', sort_id='default', order='default', by_destination=True )}">
                                ${job[2]} ${job[3]}
                            </a>
                        </td>
                        <td>${job[4]}</td>
                        <td>${job[5]}</td>
                        <td>${job[1]}</td>
                        <td id="${key}">${job[6].seconds}</td>
                        <td id="${key}">${datetime.timedelta(seconds=job[6].seconds)}</td>
                        %try:
                            ${make_sparkline(key, trends[key], "bar", "/ day")}
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
<!--jobs_per_month_by_user_and_destination.mako-->
