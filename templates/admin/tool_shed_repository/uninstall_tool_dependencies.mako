<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<% import os %>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="card">
    <div class="card-header">Uninstall tool dependencies</div>
    <div class="card-body">
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
                            if not os.path.exists( install_dir ):
                                install_dir = "This dependency's installation directory does not exist, click <b>Uninstall</b> to reset for installation."
                        %>
                        <tr>
                            <td>${tool_dependency.name|h}</td>
                            <td>${tool_dependency.version|h}</td>
                            <td>${tool_dependency.type|h}</td>
                            <td>${install_dir|h}</td>
                        </tr>
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
