<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">User Registrations for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</h3>
        <table align="center" width="30%" class="colored">
            %if len( users ) == 0:
                <tr><td colspan="2">There are no user registrations for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</td></tr>
            %else:
                <tr class="header">
                    <td>Email</td>
                </tr>
                <% ctr = 0 %>
                %for user in users:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>${user}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
