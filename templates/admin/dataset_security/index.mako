<%inherit file="/base.mako"/>

<%def name="title()">Dataset Security</%def>
<div class="toolForm">
  <div class="toolFormTitle">Dataset Security</div>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td><a href="${h.url_for( controller='admin', action='groups' )}">Groups</a></td></tr>
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </table>
</div>
