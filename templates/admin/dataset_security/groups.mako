<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<%def name="title()">Groups</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='users' )}">Users</a>
  </div>
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='create_group' )}">Create a new group</a>
    <br/>
    <a href="${h.url_for( controller='admin', action='deleted_groups' )}">Manage deleted groups</a>
    <br/>
  </div>
  <h3 align="center">Groups</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td colspan="5"><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    %if len( groups ) == 0:
      <tr><td colspan="5">There are no Galaxy groups</td></tr>
    %else:
      <tr class="header">
        <td>Group</td>
        <td>Priority</td>
        <td>Members</td>
        <td>Datasets</td>
        <td>Group Permitted Actions on Datasets</td>
        <td>&nbsp;</td>
      </tr>
      <% ctr = 0 %>
      %for group in groups:
        <% group_name = unescape( group[1], unentities ) %>
        %if ctr % 2 == 1:
          <tr class="odd_row">
        %else:
          <tr class="tr">
        %endif
          <td>${group_name}</td>
          <td>${group[2]}</td>
          <td><a href="${h.url_for( controller='admin', action='group_members', group_id=group[0], group_name=group[1] )}">${group[3]}</a></td>
          %if group[4] > 0:
            <td><a href="${h.url_for( controller='admin', action='group_dataset_permitted_actions', group_id=group[0], group_name=group[1] )}">${group[4]}</a></td>
          %else:
            <td>${group[4]}</td>
          %endif
          <td>
            %if len( group[5] ) == 1:
              ${group[5][0]}
            %elif len( group[5] ) > 1:
              %for da in group[5]:
                ${da}<br/>  
              %endfor
            %endif
          </td>
          <td><a href="${h.url_for( controller='admin', action='mark_group_deleted', group_id=group[0] )}">Mark group deleted</a></td>
        </tr>
        <% ctr += 1 %>
      %endfor
    %endif
  </table>
</div>
