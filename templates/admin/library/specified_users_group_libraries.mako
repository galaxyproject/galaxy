<%inherit file="/base.mako"/>

<% 
  from galaxy.web.controllers.admin import entities, unentities
  from xml.sax.saxutils import escape, unescape 
%>

<%def name="title()">Specified Users Group Libraries{</%def>
<% 
  gn = unescape( group_name, unentities ) 
  email = unescape( user_email, unentities ) 
%>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='users' )}">Users</a>
  </div>
  <div class="toolFormTitle">Libraries containing datasets associated with group '${gn}' that user '${email}' can access</div>
  <div class="toolFormBody">
    %for library in libraries:
      <div class="form-row">
        <a href="${h.url_for( controller='admin', action='library', id=library.id )}">${library.name}</a>
      </div>
    %endfor
  </div>
</div>
