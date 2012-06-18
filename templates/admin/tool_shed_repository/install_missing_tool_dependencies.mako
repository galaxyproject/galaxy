<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import os %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        %if repository.includes_tools:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='set_tool_versions', id=trans.security.encode_id( repository.id ) )}">Set tool versions</a>
        %endif
        %if repository.tool_dependencies:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', id=trans.security.encode_id( repository.id ) )}">Manage tool dependencies</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        Galaxy will attempt to install the missing tool dependencies listed below.  Each of these dependencies may require their own build
        requirements (e.g., CMake, g++, etc).  Galaxy will not attempt to install these build requirements, so if any are missing from your
        environment tool dependency installation may partially fail.  If this happens, you can install the missing build requirements and
        have Galaxy attempt to install the tool dependencies again.
    </p> 
</div>
<br/>
<div class="warningmessage">
    <p>
        Installation may take a while.  <b>Always wait until a message is displayed in your browser after clicking the <b>Go</b> button below.</b>
        If you get bored, watching your Galaxy server's paster log will help pass the time.
    </p>
    <p>
        Information about the tool dependency installation process will be saved in various files named with a ".log" extension in the directory: 
        ${trans.app.config.tool_dependency_dir}/<i>package name</i>/<i>package version</i>/${repository.owner}/${repository.name}/${repository.changeset_revision}
    </p>
</div>
<br/>

<div class="toolForm">
    <div class="toolFormBody">
        <form name="install_missing_tool_dependencies" id="install_missing_tool_dependencies" action="${h.url_for( controller='admin_toolshed', action='install_missing_tool_dependencies', id=trans.security.encode_id( repository.id ), tool_panel_section=tool_panel_section, new_tool_panel_section=new_tool_panel_section, reinstalling=reinstalling )}" method="post" >
            <div style="clear: both"></div>
            <div class="form-row">
                <label>Install missing tool dependencies?</label>
                ${install_tool_dependencies_check_box.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Un-check to skip installation of these missing tool dependencies.
                </div>
                ## Fake the no_changes_check_box value.
                %if no_changes_checked:
                    <input type="hidden" id="no_changes" name="no_changes" value="true" checked="checked"><input type="hidden" name="no_changes" value="true">
                %else:
                    <input type="hidden" name="no_changes" value="true">
                %endif
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <table class="grid">
                    <tr><td colspan="4" bgcolor="#D8D8D8"><b>Missing tool dependencies</b></td></tr>
                    <tr>
                        <th>Name</th>
                        <th>Version</th>
                        <th>Type</th>
                        <th>Install directory</th>
                    </tr>
                    %for dependency_key, requirements_dict in tool_dependencies.items():
                        <%
                            name = requirements_dict[ 'name' ]
                            version = requirements_dict[ 'version' ]
                            type = requirements_dict[ 'type' ]
                            install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                                        name,
                                                        version,
                                                        repository.owner,
                                                        repository.name,
                                                        repository.changeset_revision )
                            readme_text = requirements_dict.get( 'readme', None )
                        %>
                        %if not os.path.exists( install_dir ):
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
                        %endif
                    %endfor
                </table>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="install_missing_tool_dependencies_button" value="Go"/>
            </div>
        </form>
    </div>
</div>
