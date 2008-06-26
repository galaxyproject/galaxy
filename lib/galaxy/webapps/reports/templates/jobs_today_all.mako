<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">All Jobs for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</h3>
    <h4 align="center">Click Total Jobs to see jobs for today</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr><td colspan="5">There are no jobs for ${day_label},&nbsp;${month_label}&nbsp;${day_of_month},&nbsp;${year_label}</td></tr>
      %else:
        <tr class="header">
          <td>Day</td>
          <td>Date</td>
          <td>User Jobs</td>
          <td>Monitor Jobs</td>
          <td>Total Jobs</td>
        </tr>
        <% ctr = 0 %>
        %for job in jobs:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td>${job[0]}</td>
            <td>${month_label}&nbsp;${job[5]},&nbsp;${year_label}</td>
            <td>${job[2]}</td>
            <td>${job[3]}</td>
            <td><a href="${h.url_for( controller='jobs', action='specified_date_all', specified_date=job[1], day_label=job[0], month_label=month_label, year_label=year_label, day_of_month=job[5] )}">${job[4]}</a></td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
