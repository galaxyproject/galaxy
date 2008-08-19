<%inherit file="/base.mako"/>

<%def name="title()">Libraries You Can Access</%def>
<div class="toolForm">
  <div class="toolFormTitle">Libraries You Can Access</div>
  <div class="toolFormBody">
    %for library in libraries:
      <div class="form-row">
        <a href="${h.url_for( '/library/index', library_id=library.id )}">${library.name}</a>
      </div>
    %endfor
  </div>
</div>
