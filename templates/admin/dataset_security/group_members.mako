<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<% gn = unescape( group_name, unentities ) %>

%if msg:
<div class="donemessage">${msg}</div>
%endif

<h2>Members of Group '${gn}'</h2>

%if not deleted:
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='group_members_edit', group_id=group_id, group_name=group_name )}">
            Manage group membership
        </a>
    </li>
</ul>

%endif
  
%if len( members ) == 0:

  Group '${gn}' contains no members
  
%else:
  
  <table cellpadding="0" cellspacing="0" width="100%" class="colored">
      <tr class="header"><td>User Name</td></tr>
      <% ctr = 0 %>
      %for member in members:
        <% email = unescape( member[1], unentities ) %>
        %if ctr % 2 == 1:
          <tr class="odd_row">
        %else:
          <tr class="tr">
        %endif
          <td><a href="${h.url_for( controller='admin', 
                                    action='user_groups_roles', 
                                    user_id=member[0], 
                                    user_email=member[1] )}">${email}</a></td>
        </tr>
        <% ctr += 1 %>
      %endfor
  </table>

%endif
