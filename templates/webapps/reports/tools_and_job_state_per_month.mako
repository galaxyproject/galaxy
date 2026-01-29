<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
<div class="reportBody">
    <h3 align="center">States of Jobs for ${tool}</h3>
    <h4 align="center">Listed in descending by month</h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if data:
            <tr class="header">
                <td>Month</td>
                <td>Ok</td>
                <td>Error</td>
            </tr>
            <% odd = False%>
            %for month in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                <td>${month}</td>
                <td>
                %if data[month][0] == 0:
                    -
                %else:
                    ${data[month][0]}
                %endif
                </td>
                <td>
                %if data[month][1] == 0:
                    -
                %else:
                    ${data[month][1]}
                %endif
                </td>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
</div>
