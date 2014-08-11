<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="common_misc_javascripts" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${common_misc_javascripts()}
</%def>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Tool shed repository '${repository.name}' tool dependencies</div>
        <%
            can_install = False
            can_uninstall = False
        %>
        <br/><br/>
        <table class="grid">
            <tr><th  bgcolor="#D8D8D8">Name</th><th  bgcolor="#D8D8D8">Version</th><th  bgcolor="#D8D8D8">Type</th><th bgcolor="#D8D8D8">Status</th><th bgcolor="#D8D8D8">Error</th></tr>
            %for tool_dependency in repository.tool_dependencies:
                <%
                    if tool_dependency.error_message:
                        from tool_shed.util.basic_util import to_html_string
                        error_message = to_html_string( tool_dependency.error_message )
                    else:
                        error_message = ''
                    if not can_install:
                        if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                       trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                            can_install = True
                    if not can_uninstall:
                        if tool_dependency.status not in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                           trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                            can_uninstall = True
                %>
                <tr>
                    <td>
                        %if tool_dependency.status not in [ trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                            <a target="galaxy_main" href="${h.url_for( controller='admin_toolshed', action='manage_repository_tool_dependencies', operation='browse', tool_dependency_ids=trans.security.encode_id( tool_dependency.id ), repository_id=trans.security.encode_id( repository.id ) )}">
                                ${tool_dependency.name}
                            </a>
                        %else:
                            ${tool_dependency.name}
                        %endif
                    </td>
                    <td>${tool_dependency.version}</td>
                    <td>${tool_dependency.type}</td>
                    <td>${tool_dependency.status}</td>
                    <td>${error_message}</td>
                </tr>
            %endfor
        </table>
        %if can_install:
            <br/>
            <form name="install_tool_dependencies" id="install_tool_dependencies" action="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', operation='install', repository_id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    Check each tool dependency that you want to install and click <b>Install</b>.
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="checkbox" id="checkAllUninstalled" name="select_all_uninstalled_tool_dependencies_checkbox" value="true" onclick="checkAllUninstalledToolDependencyIdFields(1);"/><input type="hidden" name="select_all_uninstalled_tool_dependencies_checkbox" value="true"/><b>Select/unselect all tool dependencies</b>
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    ${uninstalled_tool_dependencies_select_field.get_html()}
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="submit" name="install_button" value="Install"/></td>
                </div>
            </form>
            <br/>
        %endif
        %if can_uninstall:
            <br/>
            <form name="uninstall_tool_dependencies" id="uninstall_tool_dependencies" action="${h.url_for( controller='admin_toolshed', action='manage_repository_tool_dependencies', operation='uninstall', repository_id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    Check each tool dependency that you want to uninstall and click <b>Uninstall</b>.
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="checkbox" id="checkAllInstalled" name="select_all_installed_tool_dependencies_checkbox" value="true" onclick="checkAllInstalledToolDependencyIdFields(1);"/><input type="hidden" name="select_all_installed_tool_dependencies_checkbox" value="true"/><b>Select/unselect all tool dependencies</b>
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    ${installed_tool_dependencies_select_field.get_html()}
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="submit" name="uninstall_button" value="Uninstall"/></td>
                </div>
            </form>
            <br/>
        %endif
    </div>
</div>
