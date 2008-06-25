<%inherit file="/base_panels.mako"/>
<%def name="main_body()">
  ## Display the available reports
  <div class="body">
    <h3 align="center">Galaxy Reports</h3>
    <table align="center" width="40%" class="colored">
      <tr><td><div class="reportTitle">Job Information</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='specified_month_all' )}">Number of jobs per day for current month</a> - displays days of the current month with the total number of jobs for each day</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='specified_month_in_error' )}">Number of jobs in error per day for current month</a> - displays days of the current month with the total number of jobs in error for each day</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='all_unfinished' )}">All unfinished jobs</a> - displays jobs that are currently in a "new" state, a "queued" state or a "running" state</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='per_month_all' )}">Number of jobs per month</a> - displays a list of months with the total number of jobs for each month</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='per_month_in_error' )}">Number of jobs in error per month</a> - displays a list of months with the total number of jobs in error for each month</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='per_user' )}">Number of jobs per user</a> - displays users sorted in descending order by the number of jobs they have submitted</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='jobs', action='per_tool' )}">Number of jobs per tool</a> - displays tools sorted in alphabetical order by tool id and the number of jobs created by the tool</div></td></tr>
    </table>
    <br clear="left"/><br/><br/><br/>
    <table align="center" width="40%" class="colored">
      <tr><td><div class="reportTitle">System Information</div></td></tr>
      <tr><td><div class="reportBody"><a href="${h.url_for( controller='system', action='index' )}">Disk space, old histories and datasets</a> - displays history and dataset information including disk space allocation where datasets are stored</div></td></tr>
    </table>
  </div>
</%def>
