<%inherit file="/base.mako"/>

<%def name="title()">Library</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='users' )}">Users</a>
  </div>
  <div class="toolFormTitle">Manage Library '${library.name}'</div>
  <div class="toolFormBody">
  <form name="end_library" action="${h.url_for( controller='admin', action='library' )}" method="post" >
    <input type="hidden" name="library_id" value="${library.id}">
    <div class="form-row">
      <label>Name:</label>
      <div style="float: left; width: 250px; margin-right: 10px;">
        <input type="text" name="name" value="${library.name}" size="40">
      </div>
      <div style="clear: both"></div>
    </div>
    <div class="form-row">
      <label>Description:</label>
      <div style="float: left; width: 250px; margin-right: 10px;">
        <input type="text" name="description" value="${library.description}" size="40">
      </div>
      <div style="clear: both"></div>
    </div>
    <table>
      <tr><td>&nbsp;</td><td><input type="submit" value="Save"></td></tr>
    </table>
  </form>
</div>
<div style="float: left; width: 250px; margin-right: 10px;">
  <a href="${h.url_for( 'folder', id = library.root_folder.id )}">Manage Root Folder</a>
</div>
