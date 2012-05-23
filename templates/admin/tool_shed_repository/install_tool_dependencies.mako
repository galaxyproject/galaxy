<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import os %>

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        The tool dependencies listed below can be automatically installed with the repository.  Installing them provides significant
        benefits and Galaxy includes various features to manage them.
    </p>
    <p>
        Each of these dependencies may require their own build requirements (e.g., CMake, g++, etc).  Galaxy will not attempt to install
        these build requirements, so if any are missing from your environment tool dependency installation may partially fail.  The
        repository and all of it's contents will be installed in any case.
    </p>
    <p>
        If tool dependency installation fails in any way, you can install the missing build requirements and have Galaxy attempt to install
        the tool dependencies again using the <b>Install tool dependencies</b> pop-up menu option on the <b>Manage repository</b> page.
    </p> 
</div>

<div class="toolForm">
    <div class="toolFormBody">
        <form name="install_tool_dependenceies" id="install_tool_dependenceies" action="${h.url_for( controller='admin_toolshed', action='install_repository', tool_shed_url=tool_shed_url, repo_info_dict=repo_info_dict, includes_tools=includes_tools )}" method="post" >
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Install tool dependencies?</label>
                ${install_tool_dependencies_check_box.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Un-check to skip automatic installation of these tool dependencies.
                </div>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <table class="grid">
                    <tr><td colspan="4" bgcolor="#D8D8D8"><b>Tool dependencies</b></td></tr>
                    <tr>
                        <th>Name</th>
                        <th>Version</th>
                        <th>Type</th>
                        <th>Install directory</th>
                    </tr>
                    %for repository_name, repo_info_tuple in dict_with_tool_dependencies.items():
                        <%
                            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
                        %>
                        %for dependency_key, requirements_dict in tool_dependencies.items():
                            <%
                                name = requirements_dict[ 'name' ]
                                version = requirements_dict[ 'version' ]
                                type = requirements_dict[ 'type' ]
                                install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                            name,
                                                            version,
                                                            repository_owner,
                                                            repository_name,
                                                            changeset_revision )
                                readme_text = requirements_dict.get( 'readme', None )
                            %>
                                <tr>
                                    <td>${name}</td>
                                    <td>${version}</td>
                                    <td>${type}</td>
                                    <td>${install_dir}</td>
                                </tr>
                                %if readme_text:
                                    <tr><td colspan="4" bgcolor="#FFFFCC">${name} ${version} requirements and installation information</td></tr>
                                    <tr><td colspan="4"><pre>${readme_text}</pre></td></tr>
                                %endif
                        %endfor
                    %endfor
                </table>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="install_tool_dependenceies_button" value="Continue"/>
            </div>
        </form>
    </div>
</div>
