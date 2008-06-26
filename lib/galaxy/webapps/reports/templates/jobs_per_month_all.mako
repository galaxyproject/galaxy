<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">Jobs Per Month</h3>
    <h4 align="center">Click Month to view the number of jobs for each day of that month</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr><td colspan="4">There are no jobs</td></tr>
      %else:
        <tr class="header">
          <td>Month</td>
          <td>User Jobs</td>
          <td>Monitor Jobs</td>
          <td>Total</td>
        </tr>
        <% ctr = 0 %>
        %for job in jobs:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td><a href="${h.url_for( controller='jobs', action='specified_month_all', month=job[0], month_label=job[4].strip(), year_label=job[5] )}">${job[4]}&nbsp;${job[5]}</a></td>
            <td>${job[1]}</td>
            <td>${job[2]}</td>
            <td>${job[3]}</td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
