<%inherit file="/base.mako"/>
<%def name="title()">Galaxy Administration</%def>

<table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
  <tr>
    <td>
      <h3 align="center">Galaxy Administration</h3>
      %if msg:
        <p class="ok_bgr">${msg}</p>
      %endif
    </td>
  </tr>
  <tr>
    <td>
      <form method="post" action="admin">
        <p>Admin password: <input type="password" name="passwd" size="8"></p>
        <p>
          Reload tool: 
          <select name="tool_id">
            %for i, section in enumerate( toolbox.sections ):
              <optgroup label="${section.name}">
              %for t in section.tools:
                <option value="${t.id}">${t.name}</option>
              %endfor
            %endfor
          </select>
          <button name="action" value="tool_reload">Reload</button>
        </p>
      </form>
    </td>
  </tr>
  <tr>
    <td>
      <a href="${h.url_for( '/library/manage_libraries' )}">Manage Libraries</a>
    </td>
  </tr>
  <tr>
</table>

