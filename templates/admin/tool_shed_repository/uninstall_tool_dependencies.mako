<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import os %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if has_readme:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='view_readme', id=trans.security.encode_id( repository.id ) )}">View README</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get repository updates</a>
        %if repository.tool_dependencies:
            <% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Uninstall tool dependencies</div>
    <div class="toolFormBody">
        <form name="uninstall_tool_dependenceies" id="uninstall_tool_dependenceies" action="${h.url_for( controller='admin_toolshed', action='uninstall_tool_dependencies' )}" method="post" >       
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th>Name</th>
                        <th>Version</th>
                        <th>Type</th>
                        <th>Install directory</th>
                    </tr>
                    %for tool_dependency in tool_dependencies:
                        <input type="hidden" name="tool_dependency_ids" value="${trans.security.encode_id( tool_dependency.id )}"/>
                        <%
                            if tool_dependency.type == 'package':
                                install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                            tool_dependency.name,
                                                            tool_dependency.version,
                                                            tool_dependency.tool_shed_repository.owner,
                                                            tool_dependency.tool_shed_repository.name,
                                                            tool_dependency.tool_shed_repository.installed_changeset_revision )
                            elif tool_dependency.type == 'set_environment':
                                install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                            'environment_settings',
                                                            tool_dependency.name,
                                                            tool_dependency.tool_shed_repository.owner,
                                                            tool_dependency.tool_shed_repository.name,
                                                            tool_dependency.tool_shed_repository.installed_changeset_revision )
                        %>
                        %if os.path.exists( install_dir ):
                            <tr>
                                <td>${tool_dependency.name}</td>
                                <td>${tool_dependency.version}</td>
                                <td>${tool_dependency.type}</td>
                                <td>${install_dir}</td>
                            </tr>
                        %endif
                    %endfor
                </table>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="uninstall_tool_dependencies_button" value="Uninstall"/>
                <div class="toolParamHelp" style="clear: both;">
                    Click to uninstall the tool dependencies listed above.
                </div>
            </div>
        </form>
    </div>
</div>
