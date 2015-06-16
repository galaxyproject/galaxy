<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}
    
<!--jobs_per_tool.mako-->
<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs Per Tool</h4>
        <h5 align="center">Click Tool ID to view details</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs.</td></tr>
            %else:
                <tr class="header">
                    <td>
                        ${get_sort_url(sort_id, order, 'tool_id', 'jobs', 'per_tool', 'Tool ID')}
                        <span class='dir_arrow tool_id'>${arrow}</span>
                    </td>
                    %if is_user_jobs_only:
                        <td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_tool', 'User Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
					%else:
                        <td>
                            ${get_sort_url(sort_id, order, 'total_jobs', 'jobs', 'per_tool', 'User and Monitor Jobs')}
                            <span class='dir_arrow total_jobs'>${arrow}</span>
                        </td>
	                %endif
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='tool_per_month', tool_id=job[0], sort_id='default', order='default' )}">${job[0]}</a></td>
                        <td>${job[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
<!--End jobs_per_tool.mako-->
