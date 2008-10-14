<%inherit file="/base.mako"/>

<%def name="title()">Permitted Actions on Datasets</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <h3 align="center">Manage Permitted Actions on Datasets for Group '${group.name}'</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td colspan="3"><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td colspan="3">&nbsp;</td>
    %if len( group.datasets ) == 0:
      <tr><td colspan="3">The group you selected has no associated datasets.</td></tr>
    %else:
      <tr class="header">
        <td>Association Names/Info</td>
        <td>Permitted Actions</td>
      </tr>
      <% ctr = 0 %>
      <form name="group_dataset_permitted_actions_edit" action="${h.url_for( controller='admin', 
                                                                             action='group_dataset_permitted_actions_edit',
                                                                             group_id=group.id )}" method="post" >
        <input type="hidden" name="gdas" value="${ ','.join( [ str(gda.id) for gda in gdas ] ) }"/>
        %for gda in gdas:
          <% permissions = trans.app.security_agent.get_dataset_permissions( gda, group.id ) %>
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif 
            <td>
              %if gda.dataset.library_associations:
                <strong>Library name(s):</strong><br/>
              %endif
              <ul>
              %for da in gda.dataset.library_associations:
                <li>${da.name} (${da.info})</li>
              %endfor
              </ul>
              %if gda.dataset.history_associations:
                <strong>History name(s):</strong><br/>
              %endif
              <ul>
              %for da in gda.dataset.history_associations:
                <li>${da.name} (${da.info})</li>
              %endfor
              </ul>
            </td>
            <td>
              %for pa in trans.app.model.Dataset.permitted_actions:
                <% pa_val = trans.app.security_agent.permitted_actions.__dict__[pa] %>
                <input type="checkbox" name="gda_actions_${gda.id}" value="${pa}"
                %if pa_val in permissions[1]:
                  checked
                %endif
                />
                ${pa_val}<br/>${trans.app.security_agent.get_permitted_action_description(pa)}<br/>
                <br/>
              %endfor
              <br/>
            </td>
          </tr>
          <% ctr += 1 %>
        %endfor
        <tr><td colspan="3"><center><button name="group_dataset_permitted_actions_edit_button" value="group_dataset_permitted_actions_edit">Update</button></center></td></tr>
      </form>
    %endif
  </table>
</div>
