<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Jobs Per Domain</h3>
        <h4 align="center">This report does not account for unauthenticated users.</h4>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs</td></tr>
            %else:
                <tr class="header">
                    <td>Domain</td>
                    <td>Total Jobs</td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${job[0]}</td>
                        <td>${job[1]}</td>
                    </tr>
                <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
