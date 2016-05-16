<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}


<!--jobs_tool_per_month.mako-->
<div class="report">
    <div class="reportBody">
        <h4 align="center">Jobs per month for tool "${tool_id}"</h4>
        <h5 align="center">
            <p>Click Jobs to view details.</p>
            <p>Graph goes from first of the month to the last</p>
        </h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr>
                    <td colspan="2">
                        There are no jobs for tool "${tool_id}"
                    </td>
                </tr>
            %else:
                <tr class="header">
                    <td class="third_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'tool_per_month', 'Month', tool_id=tool_id)}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td class="third_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'tool_per_month', 'User Jobs', tool_id=tool_id)}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td class="third_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'tool_per_month', 'User and Monitor Jobs', tool_id=tool_id)}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                    <td></td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    <% key = job[2] + job[3] %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[2]}&nbsp;${job[3]}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='tool_for_month', tool_id=tool_id, specified_date=job[0] )}">${job[1]}</a></td>
                        ${make_sparkline(key, trends[key], "bar", "/ day")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_tool_per_month.mako-->
