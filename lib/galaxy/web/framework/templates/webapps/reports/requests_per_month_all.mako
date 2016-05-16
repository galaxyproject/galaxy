<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
    <div class="reportBody">
        <h3 align="center">Sequencing Requests Per Month</h3>
        <table align="center" width="60%" class="colored">
            %if len( requests ) == 0:
                <tr><td colspan="4">There are no requests</td></tr>
            %else:
                <tr class="header">
                    <td class="half_width">Month</td>
                    <td class="half_width">Total</td>
                </tr>
                <% ctr = 0 %>
                %for request in requests:
                    <%
                        month = request[0]
                        total = request[1]
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
