<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
<div class="reportBody">
    <h3 align="center">Histories and Datasets per User</h3>
    <h4 align="center">Listed in
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by
    %if sorting == 0:
        Users
    %elif sorting == 1:
        number of History
    %elif sorting == 2:
        number of Dataset
    %else:
        History Space
    %endif
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="history_and_dataset_per_user">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
                        <select value="${sorting}" size="4" name="sorting">
                            <option value="User"> by username </option>
                            <option value="size"> by history space </option>
                            <option value="HSort"> by number of history </option>
                            <option value="DSort"> by number of dataset </option>
                        </select>
                        <select value="${descending}" size="3" name="descending">
                            <option value="desc"> descending </option>
                            <option value="asc"> ascending </option>
                        </select>
                        </br>
                        <button name="action" value="commit">Sort my Data!</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if data:
            <tr class="header">
                <td>User</td>
                <td>Number of History</td>
                <td>Number of Dataset</td>
            </tr>
            <% odd = False%>
            %for user in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                <td><a href="history_and_dataset_type?user_selection=${user}">${user}</a></td>
                <td>${data[user][0]}</td>
                <td>${data[user][1]}</td>
                </tr>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
</div>
