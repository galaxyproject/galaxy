<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">Jobs in Error for ${month}</h3>
    <h4 align="center">Click Jobs in Error to view jobs in error for that day</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr class="header"><td colspan="5">There are no jobs in error for ${month}</td></tr>
      %else:
        <tr class="header">
          <td>Day</td>
          <td>Date</td>
          <td>Jobs in Error</td>
        </tr>
        <% ctr = 0 %>
        %for job in jobs:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td>${job[0]}</td>
            <td>${job[1]}</td>
            <td><a href="${h.url_for( controller='jobs', action='specified_date_in_error', id=job[1] )}">${job[2]}</a></td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
