<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_admin', action='browse_library', obj_id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select a form on which to base the template for the ${library_item_desc} '${library_item_name}'</div>
    <form name="new_info_template" action="${h.url_for( controller='library_common', action='info_template', cntrller='library_admin' )}" method="post" >
        <div class="toolFormBody">
            <div class="form-row">
                <input type="hidden" name="library_id" value="${library_id}"/>
                %if library_dataset_id:
                    <input type="hidden" name="library_dataset_id" value="${library_dataset_id}"/>
                    <input type="hidden" name="response_action" value="ldda_edit_info"/>
                %elif folder_id:
                    <input type="hidden" name="folder_id" value="${folder_id}"/>
                    <input type="hidden" name="response_action" value="folder"/>
                %elif ldda_id:
                    <input type="hidden" name="ldda_id" value="${ldda_id}"/>
                    <input type="hidden" name="response_action" value="ldda_edit_info"/>
                %endif
                <label>Template:</label>
                <select name="form_id">
                    %for form in forms:
                        <option value="${form.id}">${form.name}</option>
                    %endfor
                </select>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="add_info_template_button" value="Add template to ${library_item_desc}"/>
            </div>
        </div>
    </form>
</div>
