<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new information template for ${library_item_desc} '${library_item_name}'</div>
    <form name="new_info_template" action="${h.url_for( controller='admin', action='info_template', new_template=True )}" method="post" >
        <div class="toolFormBody">
            <input type="hidden" name="library_id" value="${library_id}"/>
            %if library_dataset_id:
                <input type="hidden" name="library_dataset_id" value="${library_dataset_id}"/>
            %elif folder_id:
                <input type="hidden" name="folder_id" value="${folder_id}"/>
            %elif ldda_id:
                <input type="hidden" name="ldda_id" value="${ldda_id}"/>
            %endif
            <input type="hidden" name="set_num_fields" value="${num_fields}"/>
            <div class="form-row">
                <label>Template name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Template description (optional):</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
        </div>
        <div class="toolFormTitle">Fill in the template field labels and help text</div>
        <div class="toolFormBody">
            %for element_count in range( num_fields ):
                <div class="form-row">
                    <b>${1+element_count}) Field label:</b>
                    <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                    <b>Field help text (optional):</b>
                    <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                </div>
                <div style="clear: both"></div>
            %endfor
        </div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Add additional template fields:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="num_fields" value="0" size="3"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="new_info_template_button" value="Save"/>
        </div>
    </form>
</div>
