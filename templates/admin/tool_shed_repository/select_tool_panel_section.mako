<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import os %>

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        The core Galaxy development team does not maintain the contents of many Galaxy tool shed repositories.  Some repository tools
        may include code that produces malicious behavior, so be aware of what you are installing.  
    </p>
    <p>
        If you discover a repository that causes problems after installation, contact <a href="http://wiki.g2.bx.psu.edu/Support" target="_blank">Galaxy support</a>,
        sending all necessary information, and appropriate action will be taken.
    </p>
    <p>
        <a href="http://wiki.g2.bx.psu.edu/Tool%20Shed#Contacting_the_owner_of_a_repository" target="_blank">Contact the repository owner</a> for 
        general questions or concerns.
    </p>
</div>
<br/>

<div class="toolForm">
    <div class="toolFormTitle">Confirm tool dependency installation</div>
    <div class="toolFormBody">
        <form name="select_tool_panel_section" id="select_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='install_repository', tool_shed_url=tool_shed_url, repo_info_dict=repo_info_dict, includes_tools=includes_tools, includes_tool_dependencies=includes_tool_dependencies )}" method="post" >
            <div style="clear: both"></div>
            %if includes_tool_dependencies:
                <div class="form-row">
                    <div class="toolParamHelp" style="clear: both;">
                        <p>
                            These tool dependencies can be automatically installed with the repository.  Installing them provides significant benefits and 
                            Galaxy includes various features to manage them.
                        </p>
                        <p>
                            Each of these dependencies may require their own build requirements (e.g., CMake, g++, etc).  Galaxy will not attempt to install
                            these build requirements, so tool dependency installation may partially fail if any are missing from your environment, but the
                            repository and all of it's contents will be installed.  You can install the missing build requirements and have Galaxy attempt 
                            to install the tool dependencies again if tool dependency installation fails in any way.
                        </p>
                    </div>
                </div>
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
                            <% description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple %>
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
                                    tool_dependency_readme_text = requirements_dict.get( 'readme', None )
                                %>
                                %if not os.path.exists( install_dir ):
                                    <tr>
                                        <td>${name}</td>
                                        <td>${version}</td>
                                        <td>${type}</td>
                                        <td>${install_dir}</td>
                                    </tr>
                                    %if tool_dependency_readme_text:
                                        <tr><td colspan="4" bgcolor="#FFFFCC">${name} ${version} requirements and installation information</td></tr>
                                        <tr><td colspan="4"><pre>${tool_dependency_readme_text}</pre></td></tr>
                                    %endif
                                %endif
                            %endfor
                        %endfor
                    </table>
                    <div style="clear: both"></div>
                </div>
            %endif
            <div style="clear: both"></div>
            <div class="form-row">
                <table class="colored" width="100%">
                    <th bgcolor="#EBD9B2">Choose the tool panel section to contain the installed tools (optional)</th>
                </table>
            </div>
            %if shed_tool_conf_select_field:
                <div class="form-row">
                    <label>Shed tool configuration file:</label>
                    ${shed_tool_conf_select_field.get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        Your Galaxy instance is configured with ${len( shed_tool_conf_select_field.options )} shed tool configuration files, 
                        so choose one in which to configure the installed tools.
                    </div>
                </div>
                <div style="clear: both"></div>
            %else:
                <input type="hidden" name="shed_tool_conf" value="${shed_tool_conf}"/>
            %endif
            <div class="form-row">
                <label>Add new tool panel section:</label>
                <input name="new_tool_panel_section" type="textfield" value="${new_tool_panel_section}" size="40"/>
                <div class="toolParamHelp" style="clear: both;">
                    Add a new tool panel section to contain the installed tools (optional).
                </div>
            </div>
            <div class="form-row">
                <label>Select existing tool panel section:</label>
                ${tool_panel_section_select_field.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Choose an existing section in your tool panel to contain the installed tools (optional).  
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="select_tool_panel_section_button" value="Install"/>
                <div class="toolParamHelp" style="clear: both;">
                    Clicking <b>Install</b> without selecting a tool panel section will load the installed tools into the tool panel outside of any sections.
                </div>
            </div>
        </form>
    </div>
</div>
%if readme_text:
    <div class="toolForm">
        <div class="toolFormTitle">Repository README file (may contain important installation or license information)</div>
        <div class="toolFormBody">
            <input type="hidden" name="readme_text" value="${readme_text}"/>
            <div class="form-row">
                <pre>${readme_text}</pre>
            </div>
        </div>
    </div>
%endif
