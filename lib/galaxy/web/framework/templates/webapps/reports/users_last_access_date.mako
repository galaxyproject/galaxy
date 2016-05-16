<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<div class="report">
    <h3 align="center">Date of Last Galaxy Login</h3>
    <h4 align="center">
        Listed in descending order by access date ( oldest date first )
    </h4>
    <table class="lastAccessForm colored" >
        <tr>
            <td>
                <form method="post"
                      controller="users"
                      action="last_access_date">
                    <p>
                        %if users:
                            ${len( users ) }
                        %else:
                            0
                        %endif
                        &nbsp;users have not logged in to Galaxy for
                        <input type="textfield"
                               value="${days_not_logged_in}"
                               size="3"
                               name="days_not_logged_in">
                        days.
                        <input type="hidden" value=${sort_id} name="sort_id">
                        <input type="hidden" value=${order} name="order">
                        &nbsp;
                        <button name="action" value="days_not_logged_in">
                            Go
                        </button>
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <table class="lastAccessForm colored">
        %if users:
            <tr class="header">
                <td class="half_width">
                    ${get_sort_url(sort_id, order, 'zero', 'users', 'last_access_date', 'Email', days_not_logged_in=days_not_logged_in)}
                    <span class='dir_arrow zero'>${arrow}</span>
                </td>
                <td class="half_width">
                    ${get_sort_url(sort_id, order, 'one', 'users', 'last_access_date', 'Date of last Login', days_not_logged_in=days_not_logged_in)}
                    <span class='dir_arrow one'>${arrow}</span>
                </td>
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
            <tr>
                <td>
                    All users have logged in to Galaxy within the past
                    ${days_not_logged_in} days
                </td>
            </tr>
        %endif
    </table>
</div>
