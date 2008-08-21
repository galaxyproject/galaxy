<%inherit file="/base.mako"/>

<%def name="title()">Libraries</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='users' )}">Users</a>
  </div>
  <div class="form-row"><a href="${h.url_for( controller='admin', action='library' )}">Create a new library</a></div>
  <br/>
  %if msg:
    <p class="ok_bgr">${msg}</p>
  %endif
  <div class="toolFormTitle">Galaxy Libraries</div>
  <div class="toolFormBody">
    %for library in libraries:
      <div class="form-row">
        <a href="${h.url_for( controller='admin', action='library', id=library.id )}">${library.name}</a>
      </div>
    %endfor
  </div>
</div>
