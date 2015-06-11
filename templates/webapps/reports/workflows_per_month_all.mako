<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Workflows Per Month</h3>
        <table align="center" width="60%" class="colored">
            %if len( workflows ) == 0:
                <tr><td colspan="4">There are no workflows</td></tr>
            %else:
                <tr class="header">
                    <td>
                        ${get_sort_url(sort_id, order, 'date', 'workflows', 'per_month_all', 'Month')}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td>
                        ${get_sort_url(sort_id, order, 'total_workflows', 'workflows', 'per_month_all', 'Total')}
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
