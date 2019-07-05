<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <h3 align="center">${tool_name} in error's stderr message</h3>
    <h4 align="center">Listed in 
    %if descending == 1:
        descending
    %else:
        ascending
    %endif
    order by number of error of each type
    </h4>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5">
        <tr>
            <td>
                <form method="post" controller="users" action="tool_error_messages?tool=${tool_name}">
                    <p>
                        Top <input type="textfield" value="${user_cutoff}" size="3" name="user_cutoff"> shown (0 = all).
                        </br>
                        Sort:
                        <select value="${descending}" size="2" name="descending">
                            <option value="desc"> descending </option>
                            <option value="asc"> ascending </option>
                        </select>
                        by:
                        <select value="${sort_by}" size="2" name="sort_by">
                            <option value="time"> date of the error </option>
                            <option value="nb"> number of identical error </option>
                        </select>
                        </br>
                        <button name="action" value="commit">Sort my Data!</button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table align="center" width="70%" class="colored" cellpadding="5" cellspacing="5"  style="border-collapse:collapse;">
        %if data:
            <tr class="header">
                <td>Tool error</td>
                <td>Number of error like this</td>
                <td>Date of this error</td>
            </tr>
            <% odd = False%>
            %for error in data:
                %if odd:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                %if len (error.split ('</br>')) < 7:
                    <td>${error}</td>
                %else:
                    <style>
                        .content{
                            height:100px;
                            width:600px;
                            overflow:hidden;
                            text-overflow:ellipsis;}
                        input[type='checkbox'] { visibility: hidden; position: absolute; }
                        input[type='checkbox']:checked + .content { height: auto; width: auto;}
                    </style>
                    <td>
                        <label>
                            <input type="checkbox" />
                            <div class="content">
                                <span class="hidden">
                                    ${error.replace ('</br>'.join (error.split ('</br>')[2:-3]), '...') + \
                                    '</br>' + '-' * 25 + ' Extended error ' + '-' * 25 + '</br>' + \
                                    error + '</br>' + '-' * 66}
                                </span>
                            </div>
                        </label>
                    </td>
                %endif
                <td>${data[error][0]}</td>
                <td>${str(data[error][1])[:11]}</td>
                <% odd = not odd %>
            %endfor
        %endif
    </table>
</div>
