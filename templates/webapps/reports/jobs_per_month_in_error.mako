<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="jqs_style, make_sparkline" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${jqs_style()}
${get_css()}

<!--jobs_per_month_in_error.mako-->
<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs In Error Per Month</h4>
        <h5 align="center">Click Month to view details.</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs in the error state.</td></tr>
            %else:
                <tr class="header">
                    <td class="quarter_width">
                        ${get_sort_url(sort_id, order, 'date', 'jobs', 'per_month_in_error', 'Month')}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
    					<td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_month_in_error', 'User Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
	                    <td class="quarter_width">
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_month_in_error', 'User and Monitor Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                    <td></td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    <% key = str(job[2]) + str(job[3]) %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='specified_month_in_error', specified_date=job[0]+'-01', sort_id='default', order='default' )}">${job[2]}&nbsp;${job[3]}</a></td>
                        <td>${job[1]}</td>
                        ${make_sparkline(key, trends[key], "bar", "/ day")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_per_month_in_error.mako-->
