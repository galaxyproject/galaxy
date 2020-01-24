<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
<div class="reportBody">
    <h3 align="center">States of Datasets per History</h3>
    <h4 align="center">Listed in
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by History name
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="history_and_dataset_type">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
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
                <td>History name</td>
                <td>Dataset in state 'ok'</td>
                <td>Dataset in state 'upload'</td>
                <td>Dataset paused</td>
                <td>Dataset queued</td>
                <td>Dataset in error</td>
                <td>Dataset discarded</td>

                <!-- <td>Dataset in other status</td>  do you want to show other status?-->

            </tr>
            <% odd = False%>
            %for name in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                <td>${name}</td>
                <td>${data[name][0]}</td>
                <td>${data[name][1]}</td>
                <td>${data[name][2]}</td>
                <td>${data[name][3]}</td>
                <td>${data[name][4]}</td>
                <td>${data[name][5]}</td>

                <!-- <td>${data[name][6]}</td>  do you want to show other status?-->

                </tr>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
</div>
