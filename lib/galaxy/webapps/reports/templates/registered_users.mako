<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">Registered Users</h3>
    <h4 align="center">Click Number of Registered Users to see the number of user registrations per month</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="25%" class="colored">
      %if num_users == 0:
        <tr><td>There are no registered users</td></tr>
      %else:
        <tr class="header"><td align="center">Number of Registered Users</td></tr>
        <tr class="tr"><td align="center"><a href="${h.url_for( controller='users', action='registered_users_per_month' )}">${num_users}</a></td></tr>
      %endif
    </table>
  </div>
</%def>
