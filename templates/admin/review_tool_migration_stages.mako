<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Tool migrations that can be performed on this Galaxy instance</div>
    <div class="toolFormBody">
        <div class="form-row">
            <p>
                The list of tool migration stages below, displayed most recent to oldest, provides information about the repositories in the
                main Galaxy tool shed that will be cloned at each stage if you run the shell command for that stage.  This enables you to execute
                the migration process for any stage at any time.
            </p>
            <p>
                Keep in mind that tools included in a repository that you want to be displayed in the Galaxy tool panel when the repository is
                installed must be defined in the <b>tool_conf.xml</b> (or equivalent) config file prior to execution of the migration process for a
                stage.  Executing a migration process multiple times will have no affect unless the repositories associated with that stage have been
                uninstalled prior to the execution of the migration process.
            </p>
            <p>
                When you initiate a migration process, the associated repositories will be cloned from the Galaxy tool shed at
                <a href="http://toolshed.g2.bx.psu.edu" target="_blank">http://toolshed.g2.bx.psu.edu</a>.  The location in which the tool repositories
                will be installed is the value of the 'tool_path' attribute in the <tool> tag of the file named ./migrated_tool_conf.xml
                (i.e., <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).  The default location setting is <b>'../shed_tools'</b>, which may be problematic
                for some cluster environments, so make sure to change it before you execute the installation process if appropriate.  The configured location
                must be outside of the Galaxy installation directory or it must be in a sub-directory protected by a properly configured <b>.hgignore</b>
                file if the directory is within the Galaxy installation directory hierarchy.  This is because tool shed repositories will be installed using
                mercurial's clone feature, which creates .hg directories and associated mercurial repository files.  Not having <b>.hgignore</b> properly
                configured could result in undesired behavior when modifying or updating your local Galaxy instance or the tool shed repositories if they are
                in directories that pose conflicts.  See mercurial's .hgignore documentation at
                <a href="http://mercurial.selenic.com/wiki/.hgignore" target="_blank">http://mercurial.selenic.com/wiki/.hgignore</a> for details.
            </p>
        </div>
        <table class="grid">
            <% from tool_shed.util.basic_util import to_html_string %>
            %for stage in migration_stages_dict.keys():
                <%
                    migration_command = 'sh ./scripts/migrate_tools/%04d_tools.sh' % stage
                    install_dependencies = '%s install_dependencies' % migration_command
                    migration_tup = migration_stages_dict[ stage ]
                    migration_info, repo_name_dependency_tups = migration_tup
                    repository_names = []
                    for repo_name_dependency_tup in repo_name_dependency_tups:
                        repository_name, tool_dependencies = repo_name_dependency_tup
                        if repository_name not in repository_names:
                            repository_names.append( repository_name )
                    if repository_names:
                        repository_names.sort()
                        repository_names = ', '.join( repository_names )
                %>
                <tr><td bgcolor="#D8D8D8"><b>Tool migration stage ${stage} - repositories: ${repository_names}</b></td></tr>
                <tr>
                    <td bgcolor="#FFFFCC">
                        <div class="form-row">
                            <p>${to_html_string(migration_info)} <b>Run commands from the Galaxy installation directory!</b></p>
                            <p>
                                %if tool_dependencies:
                                    This migration stage includes tools that have tool dependencies that can be automatically installed.  To install them, run:<br/>
                                    <b>${install_dependencies}</b><br/><br/>
                                    To skip tool dependency installation run:<br/>
                                    <b>${migration_command}</b>
                                %else:
                                    <b>${migration_command}</b>
                                %endif
                            </p>
                        </div>
                    </td>
                </tr>
                %for repo_name_dependency_tup in repo_name_dependency_tups:
                    <% repository_name, tool_dependencies = repo_name_dependency_tup %>
                    <tr>
                        <td bgcolor="#DADFEF">
                            <div class="form-row">
                                <b>Repository:</b> ${repository_name}
                            </div>
                        </td>
                    </tr>
                    %if tool_dependencies:
                        <tr>
                            <td>
                                <div class="form-row">
                                    <b>Tool dependencies</b>
                                </div>
                            </td>
                        </tr>
                        %for tool_dependencies_tup in tool_dependencies:
                            <%
                                tool_dependency_name = tool_dependencies_tup[0]
                                tool_dependency_version = tool_dependencies_tup[1]
                                tool_dependency_type = tool_dependencies_tup[2]
                                installation_requirements = tool_dependencies_tup[3].replace( '\n', '<br/>' )
                            %>
                            <tr>
                                <td>
                                    <div class="form-row">
                                        <b>Name:</b> ${tool_dependency_name} <b>Version:</b> ${tool_dependency_version} <b>Type:</b> ${tool_dependency_type}
                                    </div>
                                    <div class="form-row">
                                        <b>Requirements and installation information:</b><br/>
                                        ${installation_requirements}
                                    </div>
                                </td>
                            </tr>
                        %endfor
                    %else:
                        <tr>
                            <td>
                                <div class="form-row">
                                    No tool dependencies have been defined for this repository.
                                </div>
                            </td>
                        </tr>
                    %endif
                %endfor
            %endfor
        </table>
    </div>
</div>
