<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<% gn = unescape( group_name, unentities ) %>

<%def name="title()">Create Group</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='group_members_edit', group_id=group_id, group_name=group_name )}">Manage group membership</a>
    <br/>
  </div>
  <div class="toolFormTitle">Members of Group '${gn}'</div>
  <table align="center" class="colored">
    %if msg:
      <tr><td><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    <tr><td>&nbsp;</td></tr>
    %if len( members ) == 0:
      <tr><td>Group '${gn}' contains no members</td></tr>
    %else:
      <% ctr = 0 %>
      %for member in members:
        <% email = unescape( member[1], unentities ) %>
        %if ctr % 2 == 1:
          <tr class="odd_row">
        %else:
          <tr class="tr">
        %endif
          <td><a href="${h.url_for( controller='admin', 
                                    action='specified_users_groups', 
                                    user_id=member[0], 
                                    user_email=member[1] )}">${email}</a></td>
        </tr>
        <% ctr += 1 %>
      %endfor
    %endif
  </table>
</div>
