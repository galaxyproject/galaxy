<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<% gn = unescape( group_name, unentities ) %>

<%def name="title()">Permitted Actions on Datasets</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <h3 align="center">Manage Permitted Actions on Datasets for Group '${gn}'</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td colspan="3"><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td colspan="3">&nbsp;</td>
    %if len( gdas ) == 0:
      <tr><td colspan="3">There is no Galaxy group named '${gn}'</td></tr>
    %else:
      <tr class="header">
        <td>Group</td>
        <td>Priority</td>
        <td>Permitted Actions on Datasets</td>
      </tr>
      <% ctr = 0 %>
      <form name="group_dataset_permitted_actions_edit" action="${h.url_for( controller='admin', 
                                                                             action='group_dataset_permitted_actions_edit',
                                                                             group_id=group_id,
                                                                             group_name=group_name )}" method="post" >
        %for gda in gdas:
          %if ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif 
            <td>${gn}</td>
            <td>${gda[0]}</td>
            <td>
              %for da in dataset_actions:
                <% check = False %>
                %for action in gda[1]:
                  %if action == da:
                    <%
                      check = True
                      break
                    %>
                  %endif
                %endfor
                %if check:
                  <input type="checkbox" name="actions" value="${da}" checked/>
                %else:
                  <input type="checkbox" name="actions" value="${da}"/>
                %endif
                ${da}<br/>
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
