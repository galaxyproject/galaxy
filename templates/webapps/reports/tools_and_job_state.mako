<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
<div class="reportBody">
    <h3 align="center">States of Jobs per Tool</h3>
    <h4 align="center">Listed in
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by
    %if sorting == 0:
        Tool
    %elif sorting == 1:
        state Ok
    %elif sorting == 2:
        state error
    %endif
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="tools_and_job_state">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
                        <select value="${sorting}" size="3" name="sorting">
                            <option value="tool"> by Tool </option>
                            <option value="ok"> state ok </option>
                            <option value="error"> state error </option>
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
                <td>Tool</td>
                <td>Jobs ok</td>
                <td>Job in error</td>
            </tr>
            <% odd = False%>
            %for tool in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                <td>
                %if data[tool][0] + data[tool][1] != "--":
                    <a href=tools_and_job_state_per_month?tool=${tool}>${tool}</a>
                %else:
                    ${tool}
                %endif
                </td>
                <td>${data[tool][0]}</td>
                <td>
                %if data[tool][1] != '-':
                    <a href=tool_error_messages?tool=${tool}>${data[tool][1]}</a>
                %else:
                    -
                %endif
                </td>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
</div>
