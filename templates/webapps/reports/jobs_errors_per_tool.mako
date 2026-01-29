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

<%
    page = page_specs.page
    offset = page_specs.offset
    entries = page_specs.entries
%>

${get_css()}

<!--jobs_errors_per_tool.mako-->
<div class="report">
    <div class="reportBody">
        <table id="formHeader">
            <tr>
                <td>
                    ${get_pages(sort_id, order, page_specs, 'jobs', 'errors_per_tool', spark_time=time_period)}
                </td>
                <td>
                    <h4 align="center">Jobs In Error Per Tool</h4>
                    <h5 align="center">
                        <p>
                            Click Tool ID to view details.
                            Click error number to view job details.
                        </p>

                        Graph goes from present to past for
                        ${make_spark_settings("jobs", "errors_per_tool", spark_limit, sort_id, order, time_period, page=page, offset=offset, entries=entries)}
                    </h5>
                </td>
                <td align="right">
                    ${get_entry_selector("jobs", "errors_per_tool", page_specs.entries, sort_id, order)}
                </td>
            </tr>
        </table>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr>
                    <td colspan="2">
                        There are no jobs in the error state.
                    </td>
                </tr>
            %else:
                <tr class="header">
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'tool_id', 'jobs', 'errors_per_tool', 'Tool ID', spark_time=time_period, page=page, offset=offset, entries=entries)}
                        <span class='dir_arrow tool_id'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td class="third_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'errors_per_tool', 'User Jobs in Error', spark_time=time_period, page=page, offset=offset, entries=entries)}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td class="third_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'errors_per_tool', 'User and Monitor Jobs in Error', spark_time=time_period, page=page, offset=offset, entries=entries)}
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
                    <% key = re.sub(r'\W+', '', job[1]) %>

                    %if entries > page_specs.entries:
                        <%break%>
                    %endif

                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif

                        <td>
                            <a href="${h.url_for( controller='jobs', action='tool_per_month', tool_id=job[1], sort_id='default', order='default')}">
                                ${job[1]}
                            </a>
                        </td>
                        <td>
                            <a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='specified_tool_in_error', tool_id=job[1])}">
                                ${job[0]}
                            </a>
                        </td>
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
<!--End jobs_errors_per_tool.mako-->
