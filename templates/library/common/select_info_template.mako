<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select a form on which to base the template for the ${library_item_desc} '${library_item_name}'</div>
    <form name="new_info_template" action="${h.url_for( controller='library_common', action='add_info_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}" method="post" >
        <div class="toolFormBody">
            <div class="form-row">
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
