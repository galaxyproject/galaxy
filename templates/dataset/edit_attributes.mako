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

<%
if isinstance( data, trans.app.model.HistoryDatasetAssociation ):
    id_name = 'id'
elif isinstance( data, trans.app.model.LibraryFolderDatasetAssociation ):
    id_name = 'lid'
%>

%if ( id_name == 'id' or trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_EDIT_METADATA, dataset = data ) ):
  <div class="toolForm">
  <div class="toolFormTitle">Edit Attributes</div>
  <div class="toolFormBody">
      <form name="edit_attributes" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="${id_name}" value="${data.id}">
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
          <input type="hidden" name="${id_name}" value="${data.id}">
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
  
  %if id_name == 'id':
    <% converters = data.get_converter_types() %>
    %if len( converters ) > 0:
        <div class="toolForm">
        <div class="toolFormTitle">Convert to new format</div>
        <div class="toolFormBody">
            <form name="convert_data" action="${h.url_for( action='edit' )}" method="post">
                <input type="hidden" name="${id_name}" value="${data.id}">
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
  %endif


  <div class="toolForm">
  <div class="toolFormTitle">Change data type</div>
  <div class="toolFormBody">
      <form name="change_datatype" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="${id_name}" value="${data.id}">
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
%else:
  <div class="toolForm">
  <div class="toolFormTitle">View Attributes</div>
  <div class="toolFormBody">
      <div class="form-row">
        <strong>Name:</strong> ${data.name}
        <div style="clear: both"></div>
        <strong>Info:</strong> ${data.info}
        <div style="clear: both"></div>
        <strong>Data Format:</strong> ${data.ext}
        <div style="clear: both"></div>
      %for element in metadata:
        <strong>${element.spec.desc}:</strong> ${element.value[0]}
        <div style="clear: both"></div>
      %endfor
      </div> 
  </div>
  </div>

<p />
%endif

%if trans.user and ( trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset = data ) ):
  <script type="text/javascript">
    var q = jQuery.noConflict();
    q( document ).ready( function () {
        // initialize state
        q("input.groupCheckbox").each( function() {
            if ( ! q(this).is(":checked") ) q("div#" + this.name).hide();
        });
        // handle events
        q("input.groupCheckbox").click( function() {
            if ( q(this).is(":checked") ) {
                q("div#" + this.name).slideDown("fast");
            } else {
                q("div#" + this.name).slideUp("fast");
            }
        });
    });
  </script>
  <div class="toolForm">
  <div class="toolFormTitle">Change Dataset Access Permissions</div>
  <div class="toolFormBody">
      <form name="change_permission_form" action="${h.url_for( action='edit' )}" method="post">
          <input type="hidden" name="${id_name}" value="${data.id}">
          <div class="form-row">
              <% user_groups = [ assoc.group for assoc in trans.user.groups ] %>
              <% dataset_group_ids = [ assoc.group.id for assoc in data.dataset.groups ] %>
              <div class="toolParamHelp" style="clear: both;">
                Check each group which should have access to this dataset.
              </div>
              %for group in user_groups:
                %if group.id in dataset_group_ids:
                  <% assoc = filter( lambda x: x.group_id == group.id, data.dataset.groups )[0] %>
                %else:
                  <% assoc = None %>
                %endif
                <input type="checkbox" name="group_${group.id}" class="groupCheckbox"
                %if assoc is not None:
                  checked
                %endif
                  /> ${group.name} <br/>
                <div class="permissionContainer" id="group_${group.id}">
                %for k, v in trans.app.security_agent.permitted_actions.items():
                  <input type="checkbox" name="group_${group.id}_${k}"
                  %if assoc is not None and v in assoc.permitted_actions:
                    checked
                  %endif
                  /> ${trans.app.security_agent.get_permitted_action_description(k)} <br/>
                %endfor
                </div>
              %endfor
              <input type="submit" name="change_permission" value="Save">
          </div>
      </form>
  </div>
  </div>
%elif trans.user and ( trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data ) ):
  <div class="toolForm">
  <div class="toolFormTitle">Dataset Access Permissions</div>
  <div class="toolFormBody">
    <div class="form-row">
      <label>The following groups may perform the actions listed on this dataset:</label>
      <br/>
      %for assoc in data.dataset.groups:
          ${assoc.group.name}
          <ul>
          %for action in assoc.permitted_actions:
              <li>${trans.app.security_agent.get_permitted_action_description(action)}</li>
          %endfor
          </ul>
      %endfor
      <div class="toolParamHelp" style="clear: both;">
        You do not have permission to edit this dataset's permissions.
      </div>
    </div>
  </div>
  </div>
%endif
