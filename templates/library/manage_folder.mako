<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=folder ):
<div class="toolForm">
    <div class="toolFormTitle">Edit folder name and description</div>
    <div class="toolFormBody">
        <form name="folder" action="${h.url_for( controller='library', action='folder' )}" method="post" >
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
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="rename" value="submitted" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="folder_id" value="${folder.id}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="rename_folder_button" value="Save"/>
        </form>
    </div>
</div>

<p/>
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=folder ):
    ${render_permission_form( folder, folder.name, h.url_for( action='folder' ), 'folder_id', folder.id, trans.user.all_roles() )}
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=folder ):
<div class="toolForm">
    <div class="toolFormTitle">Add a subfolder</div>
    <div class="toolFormBody">
        <form name="add_to_folder" action="${h.url_for( controller='library', action='folder' )}" method="post" >
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
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="folder_id" value="${folder.id}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="create_new_folder_button" value="Create New Folder"/>
        </form>
    </div>
</div>
<p/>
Click <a href="${h.url_for( controller='library', action='dataset', folder_id=folder.id )}">here</a> to add a dataset.
<p/> 
%endif

