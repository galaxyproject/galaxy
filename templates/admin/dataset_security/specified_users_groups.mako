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
      </tr>
      <% ctr = 0 %>
      %for group in groups:
        <% 
          gn = unescape( group[1], unentities )
        %>
        %if ctr % 2 == 1:
          <tr class="odd_row">
        %else:
          <tr class="tr">
        %endif
          <td>${gn}</td>
        </tr>
        <% ctr += 1 %>
      %endfor

  </table>

%endif
