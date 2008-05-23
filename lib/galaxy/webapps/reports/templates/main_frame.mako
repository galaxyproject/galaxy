<%inherit file="/base.mako"/>
<html>
  <head>
    <title>Galaxy Reports</title>
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
  </head>
  <body>
    <div class="body">
      <h3 align="center">Galaxy Reports</h3>
      <table align="center" width="40%" class="colored">
        <tr><td><div class="reportTitle">Job Information</div></td></tr>
		<tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='index' )}">Current Month</a></div></td></tr>
      </table>
      <br clear="left"/><br/><br/><br/>
      <table align="center" width="40%" class="colored">
        <tr><td><div class="reportTitle">System Information</div></td></tr>
		<tr><td><div class="reportBody"><a href="${h.url_for( controller='system', action='index' )}">Disk space, old histories and datasets</a></div></td></tr>
      </table>
    </div>
  </body>
</html>
