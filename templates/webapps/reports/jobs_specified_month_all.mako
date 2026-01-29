<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%namespace file="/page_base.mako" import="get_pages, get_entry_selector" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

<!--jobs_specified_month_all.mako-->
<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'jobs', 'specified_month_all')}
                </td>
                <td>
                    <h4 align="center">
                        Jobs for ${month_label}&nbsp;${year_label}
                    </h4>
                    <h5 align="center">
                        Click job count to see the day's details.
                    </h5>
                    <h5 align="center">
                        Graph goes from beggining to the end of the day.
                    </h5>
                </td>
                <td align="right">
                    ${get_entry_selector("jobs", "specified_month_all", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr>
                    <td colspan="5">
                        There are no jobs for ${month_label}&nbsp;${year_label}
                    </td>
                </tr>
            %else:
                <tr class="header">
                    <td class="quarter_width">Day</td>
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'specified_month_all', 'Date', page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_all', 'User Jobs', page=page, offset=offset, entries=entries)}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_all', 'User and Monitor Jobs', page=page, offset=offset, entries=entries)}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                    <td></td>
                </tr>
                <%
                   ctr = 0
                   entries = 1
                %>
                %for job in jobs:
                    <% key = job[1] %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>${job[0]}</td>
                        <td>${month_label}&nbsp;${job[1]},&nbsp;${year_label}</td>
                        <td>
                            <a href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=job[3], webapp='reports', sort_id='default', order='default' )}">
                                ${job[2]}
                            </a>
                        </td>
                        ${make_sparkline(key, trends[key], "bar", "/ hour")}
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
<!--End jobs_specified_month_all.mako-->
