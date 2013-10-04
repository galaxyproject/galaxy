<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs Per Month</h4>
        <h5 align="center">Click Month to view details.</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="4">There are no jobs.</td></tr>
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
                        <td><a href="${h.url_for( controller='jobs', action='specified_month_all', specified_date=job[0]+'-01' )}">${job[2]} ${job[3]}</a></td>
                        <td>${job[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
