<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

<%
    from galaxy import util
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}
    
<%
   _email = util.restore_text( email )
%>

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Workflows per month for user "${_email}"</h3>
        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="2">There are no workflows for user "${_email}"</td></tr>
            %else:
                <tr class="header">
                    <td>
                        ${get_sort_url(sort_id, order, 'date', 'workflows', 'user_per_month', 'Month', email=util.sanitize_text( email ))}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td>
                        ${get_sort_url(sort_id, order, 'total_workflows', 'workflows', 'user_per_month', 'Total', email=util.sanitize_text( email ))}
                        <span class='dir_arrow total_workflows'>${arrow}</span>
                    </td>
                </tr>
                <% ctr = 0 %>
                %for workflow in workflows:
                    <%
                        month = workflow[0]
                        total = workflow[1]
                    %>
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${month}</td>
                        <td>${total}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
