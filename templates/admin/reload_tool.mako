<%inherit file="/base.mako"/>

<div class="body">
  <h3 align="center">Reload a Tool</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr>
      <td>
        <form name="tool_reload" action="${h.url_for( controller='admin', action='tool_reload' )}" method="post" >
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
  </table>
</div>
