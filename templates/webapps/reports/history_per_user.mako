<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
<div class="reportBody">
    <h3 align="center">Histories per User</h3>
    <h4 align="center">Listed in
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by
    %if sorting == 0:
        Users
    %else:
        Number
    %endif
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="history_per_user">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
                        <select value="${sorting}" size="3" name="sorting">
                            <option value="User"> by username </option>
                            <option value="Number"> by number </option>
                        </select>
                        <select value="${descending}" size="3" name="descending">
                            <option value="desc"> descending </option>
                            <option value="asc"> ascending </option>
                        </select>
                        </br>
                        <button name="action" value="commit">Go</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if histories:
            <tr class="header">
                <td>User</td>
                <td>Number of History</td>
            </tr>
            <% ctr = 0 %>
            %for history in histories:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${history[0]}</td>
                    <td>${history[1]}</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        %endif
    </table>
</div>
</div>
