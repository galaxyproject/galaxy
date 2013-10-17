<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h4 align="center">Jobs Per User</h4>
        <h5 align="center">Click User to view details.</h5>
        <table align="center" width="60%" class="colored">
            %if len( jobs ) == 0:
                <tr><td colspan="2">There are no jobs.</td></tr>
            %else:
                <tr class="header">
                    <td>User</td>
                    <td>Total Jobs</td>
                </tr>
                <% ctr = 0 %>
                %for job in jobs:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='jobs', action='user_per_month', email=job[0] )}">${job[0]}</a></td>
                        <td>${job[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
