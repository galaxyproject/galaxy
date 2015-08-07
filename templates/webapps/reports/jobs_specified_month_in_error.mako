<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs in Error for ${month_label}&nbsp;${year_label}</h4>
        <h5 align="center">Click job count to see the day's details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="3">There are no jobs in the error state for ${month_label}&nbsp;${year_label}</td></tr>
            %else:
                <tr class="header">
                    <td class="quarter_width">Day</td>
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'specified_month_in_error', 'Date')}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_in_error', 'User Jobs in Error')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'specified_month_in_error', 'User and Monitor Jobs in Error')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                    <td></td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    <% key = job[1] %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[0]}</td>
                        <td>${month_label}&nbsp;${job[1]},&nbsp;${year_label}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='specified_date_in_error', specified_date=job[3] )}">${job[2]}</a></td>
                        ${make_sparkline(key, trends[key], "bar", "/ hour")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
