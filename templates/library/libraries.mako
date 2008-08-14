<%inherit file="/base.mako"/>

<%def name="title()">View Libraries</%def>
<div class="toolForm">
  <div class="toolFormTitle">View Library</div>
  <div class="toolFormBody">
    %for library in libraries:
      <div class="form-row">
        <a href="${h.url_for( 'index', library_id = library.id )}">${library.name}</a>
      </div>
    %endfor
  </div>
</div>
