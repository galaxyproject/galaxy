<%inherit file="/base.mako"/>
<%def name="title()">Manage Library</%def>


<div class="toolForm">
    <div class="toolFormTitle">Edit a Library: ${library.name}</div>
    <div class="toolFormBody">
    <form name="end_library" action="${h.url_for( 'manage_library' )}" method="post" >
            <input type="hidden" name="library_id" value="${library.id}">
            <div class="form-row">

              <label>
                  Name:
              </label>
              <div style="float: left; width: 250px; margin-right: 10px;">
                  <input type="text" name="name" value="${library.name}" size="40">
              </div>


              <div style="clear: both"></div>

            </div>

            
            <div class="form-row">
              <label>
                  Description:
              </label>
              <div style="float: left; width: 250px; margin-right: 10px;">
                  <input type="text" name="description" value="${library.description}" size="40">
              </div>


              <div style="clear: both"></div>

            </div>
      <tr><td></td><td><input type="submit" value="Save">
      </table>
  </form>

  </div>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <a href="${h.url_for( 'manage_folder', id = library.root_folder.id )}">manage root folder</a>
      </div>
</div>

