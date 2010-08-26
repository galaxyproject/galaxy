<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new folder</div>
    <div class="toolFormBody">
        <form name="folder" action="${h.url_for( controller='library_common', action='create_folder', cntrller=cntrller, parent_id=trans.security.encode_id( folder.id ), library_id=library_id, show_deleted=show_deleted )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="New Folder" size="40"/>
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
            <div class="form-row">
                <input type="submit" name="new_folder_button" value="Create"/>
            </div>
        </form>
    </div>
</div>
