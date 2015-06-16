<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="jqs_style, make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />
<%!
    import re
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

${jqs_style()}
${get_css()}

<!--jobs_errors_per_tool.mako-->
<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs In Error Per Tool</h4>
        <h5 align="center">
            <p>Click Tool ID to view details. Click error number to view job details.</p>
            <p> Graph goes from present to past(${day_limit} days).</p>
        </h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs in the error state.</td></tr>
            %else:
                <tr class="header">
                    <td>
                        ${get_sort_url(sort_id, order, 'tool_id', 'jobs', 'errors_per_tool', 'Tool ID')}
                        <span class='dir_arrow tool_id'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'errors_per_tool', 'User Jobs in Error')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'errors_per_tool', 'User and Monitor Jobs in Error')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    <% key = re.sub(r'\W+', '', job[1]) %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='tool_per_month', tool_id=job[1], sort_id='default', order='default' )}">${job[1]}</a></td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='specified_tool_in_error', tool_id= job[1] )}">${job[0]}</a></td>
                        ${make_sparkline(key, trends[key], "line", "/ day")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_errors_per_tool.mako-->