<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">Jobs In Error Per Month</h3>
    <h4 align="center">Click Year-Month to view the number of jobs in error for each day of that month</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr class="header"><td colspan="5">There are no jobs in error</td></tr>
      %else:
        <tr class="header">
          <td>Year-Month</td>
          <td>Jobs In Error</td>
        </tr>
        <% ctr = 0 %>
        %for job in jobs:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td><a href="${h.url_for( controller='jobs', action='specified_month_in_error', id=job[0] )}">${job[0]}</a></td>
            <td>${job[1]}</td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
