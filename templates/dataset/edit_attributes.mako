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
  <div class="toolFormTitle">Edit Attributes</div>
  <div class="toolFormBody">
      <form name="edit_attributes" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="id" value="${data.id}">
          <div class="form-row">
            <label>
                Name:
            </label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                <input type="text" name="name" value="${data.name}" size="40">
            </div>
            <div style="clear: both"></div>
          </div>
          <div class="form-row">
            <label>
                Info:
            </label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                <input type="text" name="info" value="${data.info}" size="40">
            </div>
            <div style="clear: both"></div>
          </div> 
          %for element in metadata:
              <div class="form-row">
                <label>
                    ${element.spec.desc}:
                </label>
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
      <form name="auto_detect" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="id" value="${data.id}">
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

  <p />
  
  <% converters = data.get_converter_types() %>
  %if len( converters ) > 0:
      <div class="toolForm">
      <div class="toolFormTitle">Convert to new format</div>
      <div class="toolFormBody">
          <form name="convert_data" action="${h.url_for( action='edit' )}" method="post">
              <input type="hidden" name="id" value="${data.id}">
              <div class="form-row">
                <label>
                    Convert to:
                </label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <select name="target_type">
                      %for key, value in converters.items():
                        <option value="${key}">${value.name[8:]}</option>
                      %endfor
                    </select>
                </div>

                <div class="toolParamHelp" style="clear: both;">
                    This will create a new dataset with the contents of this
                    dataset converted to a new format. 
                </div>
                <div style="clear: both"></div>
              </div>
              <div class="form-row">
                  <input type="submit" name="convert_data" value="Convert">
              </div>
          </form>
      </div>
      </div>
      
      <p />
  %endif


  <div class="toolForm">
  <div class="toolFormTitle">Change data type</div>
  <div class="toolFormBody">
      <form name="change_datatype" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="id" value="${data.id}">
          <div class="form-row">
            <label>
                New Type:
            </label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${datatype( data, datatypes )}
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

<p />

%if trans.app.config.enable_beta_features and trans.user and ( trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset = data ) ):
  <div class="toolForm">
  <div class="toolFormTitle">Change Permitted Actions</div>
  <div class="toolFormBody">
      <form name="change_permission_form" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="id" value="${data.id}">
          <div class="form-row">
            <label>
                Private Dataset:
            </label>
            <% checked = "" %>
            %if not trans.app.security_agent.dataset_has_group( data.id, trans.app.model.Group.get_public_group().id ):
                <% checked = " checked" %>
            %endif
            <div style="float: left; width: 250px; margin-right: 10px;">
                <input type="checkbox" name="private_dataset"${checked}>
            </div>
            <div style="clear: both"></div>
            <div class="toolParamHelp" style="clear: both;">
                This will prevent other users from viewing or utilizing this dataset, even if you share your history with them.
            </div>
            <div style="clear: both"></div>
          </div>
          <div class="form-row">
              <input type="submit" name="change_permission" value="Save">
          </div>
      </form>
  </div>
  </div>
%endif
