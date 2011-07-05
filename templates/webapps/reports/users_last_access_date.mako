<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <h3 align="center">Date of Last Galaxy Login</h3>
    <h4 align="center">Listed in descending order by access date ( oldest date first )</h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="last_access_date">
                    <p>
                        %if users:
                            ${len( users ) }
                        %else:
                            0
                        %endif 
                        &nbsp;users have not logged in to Galaxy for 
                        <input type="textfield" value="${not_logged_in_for_days}" size="3" name="not_logged_in_for_days"> days.
                        &nbsp;<button name="action" value="not_logged_in_for_days">Go</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if users:
            <tr class="header">
                <td>Email</td>
                <td>Date of last Login</td>
            </tr>
            <% ctr = 0 %>
            %for user in users:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${user[0]}</td>
                    <td>${user[1]}</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        %else:
            <tr><td>All users have logged in to Galaxy within the past ${not_logged_in_for_days} days</td></tr>
        %endif
    </table>
</div>
