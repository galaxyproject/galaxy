<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="render_readme" />

<%
    if webapp == 'community':
        is_admin = trans.user_is_admin()
        is_new = repository.is_new
        can_contact_owner = trans.user and trans.user != repository.user
        can_push = trans.app.security_agent.can_push( trans.user, repository )
        can_rate = not is_new and trans.user and repository.user != trans.user
        can_upload = can_push
        can_download = not is_new and ( not is_malicious or can_push )
        can_browse_contents = not is_new
        can_view_change_log = not is_new
        can_manage = is_admin or repository.user == trans.user
        if can_push:
            browse_label = 'Browse or delete repository tip files'
        else:
            browse_label = 'Browse repository tip files'
%>

<br/><br/>
<ul class="manage-table-actions">
    %if webapp == 'community':
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_manage:
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, webapp='community' )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">Rate repository</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${browse_label}</a>
            %endif
            %if can_contact_owner:
                <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp=webapp )}">Contact repository owner</a>
            %endif
            %if can_download:
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz', webapp=webapp )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2', webapp=webapp )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip', webapp=webapp )}">Download as a zip file</a>
            %endif
        </div>
    %else:
        %if cntrller=='repository':
            <li><a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_repositories', operation='preview_tools_in_changeset', id=trans.security.encode_id( repository.id ), webapp=webapp )}">Preview tools for install</a></li>       
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories', webapp=webapp )}">Browse valid repositories</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
            </div>
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get repository updates</a>
                %if repository.includes_tools:
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='set_tool_versions', id=trans.security.encode_id( repository.id ) )}">Set tool versions</a>
                %endif
                %if repository.tool_dependencies:
                    <% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
                %endif
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
            </div>
        %endif
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if readme_text:
    ${render_readme( readme_text )}
%endif
