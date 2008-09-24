<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<% email = unescape( user_email, unentities ) %>

<%def name="title()">Group Membership</%def>

%if msg:
<div class="donemessage">${msg}</div>
%endif

<h2>Groups of which '${email}' is a member</h2>
  
%if len( groups ) == 0:

    User '${email}' belongs to no groups

%else:
  
<table class="colored" cellpadding="0" cellspacing="0" width="100%">

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

  </table>

%endif
