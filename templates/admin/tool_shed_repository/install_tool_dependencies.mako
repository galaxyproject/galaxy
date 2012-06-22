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
        <form name="install_tool_dependenceies" id="install_tool_dependenceies" action="${h.url_for( controller='admin_toolshed', action='install_tool_dependencies' )}" method="post" >
            <div class="form-row">
                <table class="grid">
                    <tr><td colspan="4" bgcolor="#D8D8D8"><b>Tool dependencies</b></td></tr>
                    <tr>
                        <th>Name</th>
                        <th>Version</th>
                        <th>Type</th>
                        <th>Install directory</th>
                    </tr>
                    <% tool_shed_repository = None %>
                    %for tool_dependency in tool_dependencies:
                        <input type="hidden" name="tool_dependency_ids" value="${trans.security.encode_id( tool_dependency.id )}"/>
                        <%
                            readme_text = None
                            if tool_shed_repository is None:
                                tool_shed_repository = tool_dependency.tool_shed_repository
                                metadata = tool_shed_repository.metadata
                                tool_dependencies_dict = metadata[ 'tool_dependencies' ]
                            for key, requirements_dict in tool_dependencies_dict.items():
                                key_items = key.split( '/' )
                                key_name = key_items[ 0 ]
                                key_version = key_items[ 1 ]
                                if key_name == tool_dependency.name and key_version == tool_dependency.version:
                                    readme_text = requirements_dict.get( 'readme', None )
                            install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                        tool_dependency.name,
                                                        tool_dependency.version,
                                                        tool_shed_repository.owner,
                                                        tool_shed_repository.name,
                                                        tool_shed_repository.installed_changeset_revision )
                        %>
                        %if not os.path.exists( install_dir ):
                            <tr>
                                <td>${tool_dependency.name}</td>
                                <td>${tool_dependency.version}</td>
                                <td>${tool_dependency.type}</td>
                                <td>${install_dir}</td>
                            </tr>
                            %if readme_text:
                                <tr><td colspan="4" bgcolor="#FFFFCC">${tool_dependency.name} ${tool_dependency.version} requirements and installation information</td></tr>
                                <tr><td colspan="4"><pre>${readme_text}</pre></td></tr>
                            %endif
                        %endif
                    %endfor
                </table>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="install_tool_dependencies_button" value="Install"/>
            </div>
        </form>
    </div>
</div>
