<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import os %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        %if repository.includes_tools:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='set_tool_versions', id=trans.security.encode_id( repository.id ) )}">Set tool versions</a>
        %endif
        %if repository.missing_tool_dependencies:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='install_missing_tool_dependencies', id=trans.security.encode_id( repository.id ) )}">Install missing tool dependencies</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or Uninstall</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name} repository's tool dependencies</div>
    <div class="toolFormBody">
        <div class="form-row">
            <table class="grid">
                %for tool_dependency in repository.tool_dependencies:
                    <%
                        name = tool_dependency.name
                        version = tool_dependency.version
                        type = tool_dependency.type
                        installed_changeset_revision = tool_dependency.installed_changeset_revision
                        uninstalled = tool_dependency.uninstalled
                        install_dir = os.path.abspath( os.path.join( trans.app.config.tool_dependency_dir,
                                                                     name,
                                                                     version,
                                                                     repository.owner,
                                                                     repository.name,
                                                                     installed_changeset_revision ) )
                    %>
                        <tr><td bgcolor="#D8D8D8"><b>Name</b></td><td bgcolor="#D8D8D8">${name}</td></tr>
                        <tr><th>Version</th><td>${version}</td></tr>
                        <tr><th>Type</th><td>${type}</td></tr>
                        <tr>
                            <th>Install directory</th>
                            <td>
                                %if uninstalled:
                                    This dependency is not currently installed
                                %else:
                                    <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='browse_tool_dependency', id=trans.security.encode_id( tool_dependency.id ), repository_id=trans.security.encode_id( repository.id ) )}">
                                        ${install_dir}
                                    </a>
                                %endif
                            </td>
                        </tr>
                        <tr><th>Installed changeset revision</th><td>${installed_changeset_revision}</td></tr>
                        <tr><th>Uninstalled</th><td>${uninstalled}</td></tr>
                %endfor
            </table>
            <div style="clear: both"></div>
        </div>
    </div>
</div>
