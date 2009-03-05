<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />
<%namespace file="/admin/library/common.mako" import="render_existing_library_item_info" />

<% 
    available_templates = folder.get_library_item_info_templates( template_list=[], restrict=False )
    if available_templates:
        available_folder_templates = folder.get_library_item_info_templates( template_list=[], restrict=True )
%>
%if available_templates:
    <b>Add information to this folder using available templates</b>
    <a id="folder-${folder.id}--popup" class="popup-arrow" style="display: none;">&#9660;</a>
    <div popupmenu="folder-${folder.id}--popup">
        %if available_folder_templates:
            <a class="action-button" href="${h.url_for( controller='admin', action='folder', library_id=library_id, id=folder.id, information=True, restrict=True, render_templates=True )}">Display this folder's templates</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin', action='folder', library_id=library_id, id=folder.id, information=True, restrict=False, render_templates=True )}">Display all available templates</a>
        <a class="action-button" href="${h.url_for( controller='admin', action='folder', library_id=library_id, id=folder.id, information=True, restrict=True, render_templates=False )}">Hide templates</a>
    </div>
%endif
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if render_templates not in [ 'False', False ]:
    ${render_available_templates( folder, library_id, restrict=restrict )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit folder name and description</div>
    <div class="toolFormBody">
        <form name="folder" action="${h.url_for( controller='admin', action='folder', information=True, id=folder.id, library_id=library_id )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${folder.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="${folder.description}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="rename_folder_button" value="Save"/>
        </form>
    </div>
</div>

<% folder.refresh() %>
${render_existing_library_item_info( folder, library_id )}
