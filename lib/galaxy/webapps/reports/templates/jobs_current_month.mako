<%inherit file="/base.mako"/>
<html>
  <head>
    <title>Jobs for current month</title>
    <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
  </head>
  <body>
    <h3 align="center">Jobs for Current Month</h3>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      <tr><td colspan="5"><div class="reportTitle">Jobs for Current Month</div></td></tr>
      %if len( jobs ) == 0:
        <tr class="header"><td colspan="5">There are no jobs for the current month</td></tr>
      %else:
        <tr class="header">
          <td>Day</td>
          <td>Date</td>
          <td>User Jobs</td>
          <td>Monitor Jobs</td>
          <td>Total</td>
        </tr>
        <%
          ctr = 0
        %>
        %for job in jobs:
          %if len( jobs ) > 2 and ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td>${job[0]}</td>
            <td>${job[1]}</td>
            <td>${job[2]}</td>
            <td>${job[3]}</td>
            <td>${job[4]}</td>
          </tr>
          <%
            ctr += 1
          %>
        %endfor
      %endif
    </table>
  </body>
</html>
