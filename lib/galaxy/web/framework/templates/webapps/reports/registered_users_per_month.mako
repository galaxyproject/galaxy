<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/sorting_base.mako" import="get_sort_url, get_css" />

%if message:
    ${render_msg( message, 'done' )}
%endif

${get_css()}

<div class="report">
    <div class="reportBody">
        <h3 align="center">User Registrations Per Month</h3>
        <h4 align="center">
            Click Month to view the number of user registrations
            for each day of that month
        </h4>
        <table align="center" width="30%" class="colored">
            %if len( users ) == 0:
                <tr><td colspan="2">There are no registered users</td></tr>
            %else:
                <tr class="header">
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'date', 'users', 'registered_users_per_month', 'Month')}
                        <span class='dir_arrow date'>${arrow}</span>
                    </td>
                    <td class="half_width">
                        ${get_sort_url(sort_id, order, 'num_users', 'users', 'registered_users_per_month', 'Number of Registrations')}
                        <span class='dir_arrow num_users'>${arrow}</span>
                    </td>
                </tr>
                <% ctr = 0 %>
                %for user in users:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td>
                            <a href="${h.url_for( controller='users', action='specified_month', specified_date=user[0]+'-01' )}">
                                ${user[2]}&nbsp;${user[3]}
                            </a>
                        </td>
                        <td>${user[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
