<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/spark_base.mako" import="jqs_style, make_sparkline" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${jqs_style()}

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
                    <% key = str(job[2]) + str(job[3]) %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='specified_month_all', specified_date=job[0]+'-01' )}">${job[2]} ${job[3]}</a></td>
                        <td>${job[1]}</td>
                        ${make_sparkline(key, job[4], "bar", "/ day")}
                        <td id="${key}"></td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
