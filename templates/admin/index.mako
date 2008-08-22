<%inherit file="/base.mako"/>

<div class="body">
  <h3 align="center">Galaxy Administration</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td><a href="${h.url_for( controller='admin', action='dataset_security' )}">Dataset Security</a></td></tr>
    <tr><td><a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a></td></tr>
    <tr><td><a href="${h.url_for( controller='admin', action='reload_tool' )}">Reload a tool while the Galaxy server is running</a></td></tr>
  </table>
</div>
