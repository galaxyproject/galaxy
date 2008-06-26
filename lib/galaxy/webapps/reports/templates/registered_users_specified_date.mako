<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">User Registrations for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</h3>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="30%" class="colored">
      %if len( users ) == 0:
        <tr><td colspan="2">There are no user registrations for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</td></tr>
      %else:
        <tr class="header">
          <td>Email</td>
        </tr>
        <% ctr = 0 %>
        %for user in users:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td>${user}</td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
