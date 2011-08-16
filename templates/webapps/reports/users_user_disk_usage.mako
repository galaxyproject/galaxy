<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <h3 align="center">Per-user disk usage</h3>
    <h4 align="center">Listed in descending order by usage size</h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="user_disk_usage">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        &nbsp;<button name="action" value="user_cutoff">Go</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if users:
            <tr class="header">
                <td>Email</td>
                <td>Disk Usage:</td>
            </tr>
            <% ctr = 0 %>
            %for user in users:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${user.email}</td>
                    <td>${user.get_disk_usage( nice_size=True )}</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        %endif
    </table>
</div>
