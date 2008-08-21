<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<% email = unescape( user_email, unentities ) %>

<%def name="title()">Create Group</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <h3 align="center">Groups of which '${email}' is a member</h3>
  <table align="center" class="colored">
    %if msg:
      <tr><td colspan="5"><p class="ok_bgr">${msg}</p></td></tr>
    %endif
    %if len( groups ) == 0:
      <tr><td colspan="5">User '${email}' belongs to no groups</td></tr>
    %else:
      <tr class="header">
        <td>Group</td>
        <td>Priority</td>
        <td>Datasets</td>
        <td>Permitted Actions on Datasets</td>
        <td>Containing Libraries</td>
      </tr>
      <% ctr = 0 %>
      %for group in groups:
        <% 
          gn = unescape( group[1], unentities )
          library_ids = ''
          for library_id in group[5]:
            library_ids += "%s," % library_id
          library_ids = library_ids.rstrip( ',' )
        %>
        %if ctr % 2 == 1:
          <tr class="odd_row">
        %else:
          <tr class="tr">
        %endif
          <td>${gn}</td>
          <td>${group[2]}</td>
          %if group[3] > 0:
            <td><a href="${h.url_for( controller='admin', action='group_dataset_permitted_actions', group_id=group[0], group_name=group[1] )}">${group[3]}</a></td>
          %else:
            <td>${group[3]}</td>
          %endif
          <td>
            %for da in group[4]:
              ${da}<br/>  
            %endfor
          </td>
          <td>
            %if len( group[5] ) > 0:
              <a href="${h.url_for( controller='admin', action='specified_users_group_libraries', user_email=user_email, group_name=group[1], library_ids=library_ids )}">${len( group[5] )}</a>
            %else:
              ${len( group[5] )}
            %endif
          </td>
        </tr>
        <% ctr += 1 %>
      %endfor
    %endif
  </table>
</div>
