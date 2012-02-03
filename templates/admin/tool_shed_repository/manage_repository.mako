<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        %if repository.includes_tools:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='set_tool_versions', id=trans.security.encode_id( repository.id ) )}">Set tool versions</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or Uninstall</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Installed tool shed repository '${repository.name}'</div>
    <div class="toolFormBody">
        <form name="edit_repository" id="edit_repository" action="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Tool shed:</label>
                ${repository.tool_shed}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Name:</label>
                ${repository.name}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <input name="description" type="textfield" value="${description}" size="80"/>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${repository.changeset_revision}
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.owner}
            </div>
            <div class="form-row">
                <label>Location:</label>
                ${repo_files_dir}
            </div>
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted}
            </div>
            <div class="form-row">
                <input type="submit" name="edit_repository_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
<p/>
${render_metadata( repository, can_reset_metadata=True )}
<p/>
