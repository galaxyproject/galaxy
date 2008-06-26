<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">User Registrations for ${month_label}&nbsp;${year_label}</h3>
    <h4 align="center">Click Day to see user registrations for that day</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( users ) == 0:
        <tr><td colspan="2">There are no user registrations for ${month_label}&nbsp;${year_label}</td></tr>
      %else:
        <tr class="header">
          <td>Day</td>
          <td>New Registrations</td>
        </tr>
        <% ctr = 0 %>
        %for user in users:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td><a href="${h.url_for( controller='users', action='specified_date', specified_date=user[0], day_label=user[3], month_label=month_label, year_label=year_label, day_of_month=user[1] )}">${user[3]},&nbsp;${month_label}&nbsp;${user[1]},&nbsp;${year_label}</a></td>
            <td>${user[2]}</td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
