<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">Jobs in Error for ${month_label}&nbsp;${year_label} ( includes jobs deleted before finishing )</h3>
    <h4 align="center">Click Jobs in Error to view jobs in error for that day</h4>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr><td colspan="3">There are no jobs in error for ${month_label}&nbsp;${year_label}</td></tr>
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
            <td>${month_label}&nbsp;${job[3]},&nbsp;${year_label}</td>
            <td><a href="${h.url_for( controller='jobs', action='specified_date_in_error', specified_date=job[1], day_label=job[0], month_label=month_label, year_label=year_label, day_of_month=job[3] )}">${job[2]}</a></td>
          </tr>
          <% ctr += 1 %>
        %endfor
      %endif
    </table>
  </div>
</%def>
