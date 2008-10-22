<%inherit file="/base.mako"/>
<%def name="title()">History Item Attributes</%def>


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
          %for name, spec in data.metadata.spec.items():
              %if spec.visible:
                <div class="form-row">
                  <label>
                      ${spec.desc}:
                  </label>
                  <div style="float: left; width: 250px; margin-right: 10px;">
                      ${data.metadata.get_html_by_name( name )}
                  </div>
                  <div style="clear: both"></div>
                </div>
              %endif
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
      %if data.missing_meta():
          <div class="errormessagesmall">Required metadata values are missing. Some of these values may not be editable by the user. Selecting "Auto-detect" will attempt to fix these values.</div>
      %endif
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

  <p>
  <div class="toolForm">
  <div class="toolFormTitle">Copy History Item</div>
  <div class="toolFormBody">
      Click <a href="${h.url_for( controller='dataset', action='copy_datasets', source_dataset_ids=data.id, target_history_ids=data.history_id )}" target="galaxy_main">here</a> to make a copy of this history item.
  </div>
  </div>
  </p>
