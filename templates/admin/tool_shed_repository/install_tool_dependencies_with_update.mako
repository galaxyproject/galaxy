<%inherit file="/base.mako"/>
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />

<% import os %>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        The updates to the <b>${repository.name}</b> repository require the following packages.  Click the <b>Install</b> button to install them.
        Installing some packages may take a while, but you can continue to use Galaxy during installation.
    </p> 
</div>
  
<div class="card">
    <div class="card-body">
        <form name="install_tool_dependencies_with_update" id="install_tool_dependencies_with_update" action="${h.url_for( controller='admin_toolshed', action='install_tool_dependencies_with_update' )}" method="post" >
            <input type="hidden" name="updating_repository_id" value="${updating_repository_id|h}"/>
            <input type="hidden" name="updating_to_ctx_rev" value="${updating_to_ctx_rev|h}"/>
            <input type="hidden" name="updating_to_changeset_revision" value="${updating_to_changeset_revision|h}"/>
            <input type="hidden" name="encoded_updated_metadata" value="${encoded_updated_metadata|h}"/>
            <input type="hidden" name="encoded_relative_install_dir" value="${encoded_relative_install_dir|h}"/>
            <input type="hidden" name="encoded_tool_dependencies_dict" value="${encoded_tool_dependencies_dict|h}"/>
            %if tool_dependencies_dict:
                <div class="form-row">
                    <table class="grid">
                        <tr><td colspan="4" bgcolor="#D8D8D8"><b>New tool dependencies included in update</b></td></tr>
                        <tr>
                            <th>Name</th>
                            <th>Version</th>
                            <th>Install directory</th>
                        </tr>
                        %for key, requirements_dict in tool_dependencies_dict.items():
                            <%
                                readme_text = None
                                if key == 'set_environment':
                                    key_name = ', '.join( [ environment_variable[ 'name' ] for environment_variable in requirements_dict ] )
                                    key_version = ''
                                    install_dir = ''
                                else:
                                    key_items = key.split( '/' )
                                    key_name = key_items[ 0 ]
                                    key_version = key_items[ 1 ]
                                    readme_text = requirements_dict.get( 'readme', None )
                                    install_dir = os.path.join( trans.app.tool_dependency_dir,
                                                                key_name,
                                                                key_version,
                                                                repository.owner,
                                                                repository.name,
                                                                repository.installed_changeset_revision )
                            %>
                            %if not os.path.exists( install_dir ):
                                <tr>
                                    <td>${key_name|h}</td>
                                    <td>${key_version|h}</td>
                                    <td>${install_dir|h}</td>
                                </tr>
                                %if readme_text:
                                    <tr><td colspan="4" bgcolor="#FFFFCC">${key_name|h} ${key_version|h} requirements and installation information</td></tr>
                                    <tr><td colspan="4"><pre>${readme_text}</pre></td></tr>
                                %endif
                            %endif
                        %endfor
                    </table>
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <input type="submit" name="install_tool_dependencies_with_update_button" value="Install"/>
            </div>
        </form>
    </div>
</div>
