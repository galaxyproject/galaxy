<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


<div class="report">
<div class="reportBody">
    <h3 align="center">Execution Time for ${tool} per Month</h3>
    <h4 align="center">Listed in
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by
    %if sort_by == 0:
        Month
    %elif sort_by == 1:
        min time
    %elif sort_by == 2:
        max time
    %elif sort_by == 3:
        average time
    %endif
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="tool_execution_time_per_month?tool=${tool}">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
                        <select value="${sort_by}" size="4" name="sort_by">
                            <option value="month"> by Month </option>
                            <option value="min"> min time </option>
                            <option value="max"> max time </option>
                            <option value="avg"> average time </option>
                        </select>
                        <select value="${descending}" size="3" name="descending">
                            <option value="desc"> descending </option>
                            <option value="asc"> ascending </option>
                        </select>
                        <input type="checkbox" name="color" value="True">
                            Highlight big times of execution</br>
                        <button name="action" value="commit">Sort my Data!</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        %if data:
            <tr class="header">
                <td>Tool</td>
                <td>Min time of execution</td>
                <td>Max time of execution</td>
                <td>Average time of execution</td>
            </tr>
            <% odd = False%>
            %for month in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                <td>
                ${month}
                </td>
                <td>${data[month][2]}</td>
                <td>${data[month][0]}
                <td>${data[month][1]}</td></td>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
</div>
