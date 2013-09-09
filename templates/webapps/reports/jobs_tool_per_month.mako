<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs per month for tool "${tool_id}"</h4>
        <h5 align="center">Click Jobs to view details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs for tool "${tool_id}"</td></tr>
            %else:
                <tr class="header">
                    <td>Month</td>
                    %if is_user_jobs_only:
    					<td>User Jobs</td>
					%else:
	                    <td>User + Monitor Jobs</td>
	                %endif
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[2]}&nbsp;${job[3]}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', operation='tool_for_month', tool_id=tool_id, specified_date=job[0] )}">${job[1]}</a></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
