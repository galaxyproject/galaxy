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
    <div class="toolFormTitle">Edit template '${liit.name}'
        <a id="liit-${liit.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="liit-${liit.id}-popup">
            <a class="action-button" href="${h.url_for( controller='admin', action='info_template', library_id=library_id, id=liit.id, permissions=True )}">Edit this template's permissions</a>
        </div>
    </div>
    <form name="edit_info_template" action="${h.url_for( controller='admin', action='info_template', library_id=library_id, edit_template=True )}" method="post" >
        <div class="toolFormBody">
            <input type="hidden" name="id" value="${liit.id}"/>
            <input type="hidden" name="set_num_fields" value="${num_fields}"/>
            <div class="form-row">
                <b>Template name:</b>
                <input type="text" name="name" value="${liit.name}" size="40"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <b>Template description (optional):</b>
                <input type="text" name="description" value="${liit.description}" size="40"/>
                <div style="clear: both"></div>
            </div>
        </div>
        <div class="toolFormTitle">Edit the template field labels and help text</div>
        <div class="toolFormBody">
            %for template_element in liit.elements:
                <input type="hidden" name="element_ids" value="${template_element.id}"/>
                <div class="form-row">
                    <b>Field label:</b>
                    <input type="text" name="element_name_${template_element.id}" value="${template_element.name}" size="40"/>
                    <b>Field help text (optional):</b>
                    <input type="text" name="element_description_${template_element.id}" value="${template_element.description}" size="40"/>
                    <div style="clear: both"></div>
                </div>
            %endfor
            %for element_count in range( num_fields ):
                <div class="form-row">
                    <div class="toolFormTitle">Additional field ${1+element_count}</div>
                    <div class="form-row">
                        <b>Field label:</b>
                        <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                        <b>Field help text (optional):</b>
                        <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                        <div style="clear: both"></div>
                    </div>
                </div>
            %endfor
            <div class="form-row">
                <label>Add additional fields:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="num_fields" value="0" size="3"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="edit_info_template_button" value="Save"/>
        </div>
    </form>
</div>
