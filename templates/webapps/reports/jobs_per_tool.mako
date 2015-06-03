<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<%
up_arrow = "&#x2191;"
down_arrow = "&#x2193;"
   
id_order = order
total_order = order

id_arrow = " "
total_arrow = " "

if sort == "tool_id":   
    if id_order == "asc":
        id_arrow += down_arrow
        id_order = "desc"
    else:
        id_arrow += up_arrow
        id_order = "asc"
    pass
elif sort == "total_jobs":   
    if total_order == "asc":
        total_arrow += down_arrow
        total_order = "desc"
    else:
        total_arrow += up_arrow
        total_order = "asc"
    pass
%>
    
<!--jobs_per_tool.mako-->
<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs Per Tool</h4>
        <h5 align="center">Click Tool Id to view details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs.</td></tr>
            %else:
                <tr class="header">
                    <td><a href="${h.url_for( controller='jobs', action='per_tool', sort='tool_id', order=id_order )}">Tool id</a>${id_arrow}</td>
                    %if is_user_jobs_only:
                    <td><a href="${h.url_for( controller='jobs', action='per_tool', sort='total_jobs', order=total_order )}">User Jobs</a>${total_arrow}</td>
					%else:
                    <td><a href="${h.url_for( controller='jobs', action='per_tool', sort='total_jobs', order=total_order )}">User + Monitor Jobs</a>${total_arrow}</td>
	                %endif
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='tool_per_month', tool_id=job[0] )}">${job[0]}</a></td>
                        <td>${job[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_per_tool.mako-->
        