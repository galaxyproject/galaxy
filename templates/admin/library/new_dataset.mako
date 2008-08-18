<%inherit file="/base.mako"/>

<%def name="title()">Create New Library Dataset</%def>
<div class="toolForm" id="new_dataset">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <div class="toolFormTitle">Create a new Library Dataset</div>
  <div class="toolFormBody">
    <form name="tool_form" action="${h.url_for( controller='admin', action='dataset' )}" enctype="multipart/form-data" method="post">
      <input type="hidden" name="folder_id" value="${folder_id}">
      <div class="form-row">
        <label>File:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><input type="file" name="file_data"></div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>URL/Text:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><textarea name="url_paste" rows="5" cols="35"></textarea></div>
        <div class="toolParamHelp" style="clear: both;">
          Here you may specify a list of URLs (one per line) or paste the contents of a file.
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Convert spaces to tabs:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><div><input type="checkbox" name="space_to_tab" value="Yes">Yes</div></div>
        <div class="toolParamHelp" style="clear: both;">
          Use this option if you are entering intervals by hand.
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>File Format:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <select name="extension">
            <option value="auto" selected>Auto-detect</option>
            %for file_format in file_formats:
              <option value="${file_format}">${file_format}</option>
            %endfor
          </select>
        </div>
        <div class="toolParamHelp" style="clear: both;">
          Which format? See help below
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Genome:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <select name="dbkey">
            %for dbkey in dbkeys:
              %if dbkey[1] == last_used_build:
                <option value="${dbkey[1]}" selected>${dbkey[0]}</option>
              %else:
                <option value="${dbkey[1]}">${dbkey[0]}</option>
              %endif
            %endfor
          </select>
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Associate with Groups:</label>
        <help>Multi-select list - hold the appropriate key while clicking to select multiple columns</help>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <select name="groups" multiple="true" size="5">
            %for group in groups:
              <option value="${group[0]}">${group[1]}</option>
            %endfor
          </select>
        </div>
      </div>
      <div style="clear: both"></div>
      <div class="form-row">
        <input type="submit" class="primary-button" name="create_dataset" value="Add Dataset to Folder">
      </div>
    </form>
  </div>
</div>
