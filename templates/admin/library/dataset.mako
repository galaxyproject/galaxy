<%inherit file="/base.mako"/>

<%def name="title()">Edit Dataset Attributes</%def>

<%def name="datatype( dataset, datatypes )">
  <select name="datatype">
    ## $datatypes.sort()
    %for ext in datatypes:
      %if dataset.ext == ext:
        <option value="${ext}" selected="yes">${ext}</option>
      %else:
        <option value="${ext}">${ext}</option>
      %endif
    %endfor
  </select>
</%def>

<div class="toolForm">
  <div class="toolFormTitle">Dataset Permissions</div>
  <div class="toolFormBody">
    <form name="edit_group_associations" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
      <input type="hidden" name="id" value="${dataset.id}">
      <div class="form-row">
          <% dataset_gdas = [ assoc for assoc in dataset.dataset.groups ] %>
          <div class="toolParamHelp" style="clear: both;">
            Choose the permissions each user or group should have on this dataset.
          </div>
          %for gda in dataset_gdas:
            <input type="checkbox" name="group_${gda.group.id}" class="groupCheckbox" checked readonly /> ${gda.group.name.replace( ' private group', '' )} <br/>
            <div class="permissionContainer" id="group_${gda.group.id}">
            %for k, v in trans.app.security_agent.permitted_actions.items():
              <input type="checkbox" name="actions" value="${gda.group.id},${v}"
              %if v in gda.permitted_actions:
                checked
              %endif
              /> ${trans.app.security_agent.get_permitted_action_description(k)} <br/>
            %endfor
            </div>
          %endfor
      </div>
      <div class="form-row"><input type="submit" name="change_permitted_actions" value="Save"></div>
    </form>
  </div>
</div>
<p/>
<div class="toolForm">
  <div class="toolFormTitle">Edit Attributes</div>
  <div class="toolFormBody">
    <form name="edit_attributes" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
      <input type="hidden" name="id" value="${dataset.id}">
      <div class="form-row">
        <label>Name:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="text" name="name" value="${dataset.name}" size="40">
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Info:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="text" name="info" value="${dataset.info}" size="40">
        </div>
        <div style="clear: both"></div>
      </div> 
      %for element in metadata:
        <div class="form-row">
          <label>${element.spec.desc}:</label>
          <div style="float: left; width: 250px; margin-right: 10px;">
            ${element.get_html()}
          </div>
          <div style="clear: both"></div>
        </div>
      %endfor
      <div class="form-row">
        <input type="submit" name="save" value="Save">
      </div>
    </form>
    <form name="auto_detect" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
      <input type="hidden" name="id" value="${dataset.id}">
      <div style="float: left; width: 250px; margin-right: 10px;">
        <input type="submit" name="detect" value="Auto-detect">
      </div>
      <div class="toolParamHelp" style="clear: both;">
        This will inspect the dataset and attempt to correct the above column values
        if they are not accurate.
      </div>
    </form>
  </div>
</div>
<p/>
<div class="toolForm">
  <div class="toolFormTitle">Change data type</div>
  <div class="toolFormBody">
    <form name="change_datatype" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
      <input type="hidden" name="id" value="${dataset.id}">
      <div class="form-row">
        <label>New Type:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          ${datatype( dataset, datatypes )}
        </div>
        <div class="toolParamHelp" style="clear: both;">
          This will change the datatype of the existing dataset
          but <i>not</i> modify its contents. Use this if Galaxy
          has incorrectly guessed the type of your dataset.
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <input type="submit" name="change" value="Save">
      </div>
    </form>
  </div>
</div>
<a href="${h.url_for( controller='admin', action='folder', id=dataset.folder.id )}">manage containing folder</a>
<p/>
