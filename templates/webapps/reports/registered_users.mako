<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Registered Users</h3>
        <h4 align="center">Click Number of Registered Users to see the number of user registrations per month</h4>
        <table align="center" class="colored">
            %if num_users == 0:
                <tr><td>There are no registered users</td></tr>
            %else:
                <tr class="header"><td align="center">Number of Registered Users</td></tr>
                <tr class="tr"><td align="center"><a href="${h.url_for( controller='users', action='registered_users_per_month' )}">${num_users}</a></td></tr>
            %endif
        </table>
    </div>
</div>
