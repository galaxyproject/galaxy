<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%def name="title()">Edit Library Item Info Template</%def>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if library_item_info_template:
<div class="toolForm">
    <div class="toolFormTitle">Edit Library Item Info Template</div>
    <div class="toolFormBody">
        <form name="library_item_info_template_edit" action="${h.url_for( controller='admin', action='library_item_info_template' )}" method="post" >
            <input type="hidden" name="id" value="${library_item_info_template.id}"/>
            <input type="hidden" name="set_element_count" value="${new_element_count}"/>
            
            
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${library_item_info_template.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="${library_item_info_template.description}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            
      </div>
      </div>
      <div class="toolForm">
      <div class="toolFormBody">

            
            
            %for template_element in library_item_info_template.elements:
            <div class="toolFormTitle">Edit Element</div>
            <input type="hidden" name="element_ids" value="${template_element.id}"/>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="element_name_${template_element.id}" value="${template_element.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="element_description_${template_element.id}" value="${template_element.description}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            %endfor
            
            %for element_count in range( new_element_count ):
            <div class="form-row">
                <div class="toolFormTitle">Create Element ${1+element_count}</div>
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
            </div>
            %endfor
            <div class="form-row">
                <label>Add additional elements:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="new_element_count" value="0" size="3"/>
                </div>
                <div style="clear: both"></div>
            </div>

            
            <input type="submit" name="library_item_info_template_edit_button" value="Save"/>
        </form>
    </div>
</div>

<p/>
%else:
<div class="toolForm">
    <div class="toolFormTitle">Create Library Item Info Template</div>
    <div class="toolFormBody">
        <form name="library_item_info_template_new" action="${h.url_for( controller='admin', action='library_item_info_template' )}" method="post" >
            %if library_id:
                <input type="hidden" name="library_id" value="${library_id}"/>
            %elif library_dataset_id:
                <input type="hidden" name="library_dataset_id" value="${library_dataset_id}"/>
            %elif folder_id:
                <input type="hidden" name="folder_id" value="${folder_id}"/>
            %elif library_dataset_dataset_association_id:
                <input type="hidden" name="library_dataset_dataset_association_id" value="${library_dataset_dataset_association_id}"/>
            %endif
            <input type="hidden" name="set_element_count" value="${new_element_count}"/>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            
      </div>
      </div>
      <div class="toolForm">
      <div class="toolFormBody">
            
            
            %for element_count in range( new_element_count ):
            <div class="form-row">
                <div class="toolFormTitle">Create Element ${1+element_count}</div>
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
            </div>
            %endfor
            <div class="form-row">
                <label>Add additional elements:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="new_element_count" value="0" size="3"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="library_item_info_template_create_button" value="Save"/>
        </form>
    </div>
</div>

<p/>


%endif