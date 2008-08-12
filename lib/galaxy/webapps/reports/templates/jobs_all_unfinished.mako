<%inherit file="/base_panels.mako"/>

<%def name="main_body()">
  <div class="reportBody">
    <h3 align="center">All Unfinished Jobs</h3>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="60%" class="colored">
      %if len( jobs ) == 0:
        <tr><td colspan="5">There are no unfinished jobs</td></tr>
      %else:
        %for job in jobs:
          <% 
            state = job[0]
            if state == 'new':
              rowdef = '<tr class="headernew">'
            elif state == 'queued':
              rowdef = '<tr class="headerqueued">'
            elif state == 'running':
              rowdef = '<tr class="headerrunning">'
          %>
          ${rowdef}
            <td>State</td>
            <td>Job Id</td>
            <td>Create Time</td>
            <td>Update Time</td>
            <td>Session Id</td>
          </tr>
          <tr>
            <td>${job[0]}</td>
            <td>${job[1]}</td>
            <td>${job[2]}</td>
            <td>${job[3]}</td>
            <td>${job[4]}</td>
          </tr>
          <tr class="header">
            <td colspan="3">Tool</td>
            <td colspan="2">User</td>
          </tr>
          <tr>
            <td colspan="3">${job[5]}</td>
            <td colspan="2">${job[6]}</td>
          </tr>
          <tr class="header">
            <td colspan="5">Remote Host</td>
          </tr>
          <tr>
            <td colspan="5">${job[7]}</td>
          </tr>
          <tr class="header">
            <td colspan="5">Command Line</td>
          </tr>
          <tr>
            <td colspan="5">${job[8]}</td>
          </tr>
          <tr class="header">
            <td colspan="5">Stderr</td>
          </tr>
          <tr>
            <td colspan="5"><pre>${job[9]}</pre></td>
          </tr>
          <tr class="header">
            <td colspan="5">Stack Trace</td>
          </tr>
          <tr>
            <td colspan="5"><pre>${job[10]}</pre></td>
          </tr>
          <tr class="header">
            <td colspan="5">Info</td>
          </tr>
          <tr>
            <td colspan="5">${job[11]}</td>
          </tr>
          <tr><td colspan="5">&nbsp;</td></tr>
          <tr><td colspan="5">&nbsp;</td></tr>
        %endfor
      %endif
    </table>
  </div>
</%def>
