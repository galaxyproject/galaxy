<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs for ${month_label}&nbsp;${year_label}</h4>
        <h5 align="center">Click Jobs to see their details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="5">There are no jobs for ${month_label}&nbsp;${year_label}</td></tr>
            %else:
                <tr class="header">
                    <td>Day</td>
                    <td>Date</td>
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
                        <td>${job[0]}</td>
                        <td>${month_label}&nbsp;${job[1]},&nbsp;${year_label}</td>
                        <td><a href="${h.url_for( controller='jobs', action='specified_date_handler', specified_date=job[3], webapp='reports' )}">${job[2]}</a></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
