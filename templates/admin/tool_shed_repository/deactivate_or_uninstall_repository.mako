<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        <form name="deactivate_or_uninstall_repository" id="deactivate_or_uninstall_repository" action="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Description:</label>
                ${repository.description}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${repository.changeset_revision}</a>
            </div>
            <div class="form-row">
                <label>Tool shed:</label>
                ${repository.tool_shed}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.owner}
            </div>
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted}
            </div>
            <div class="form-row">
                <%
                    can_deactivate_repository = repository.can_deactivate
                    can_uninstall_repository = repository.can_uninstall( trans.app )
                %>
                %if can_deactivate_repository and can_uninstall_repository:
                    <% deactivate_uninstall_button_text = "Deactivate or Uninstall" %>
                    ${remove_from_disk_check_box.get_html()}
                    <label for="repository" style="display: inline;font-weight:normal;">Check to uninstall or leave blank to deactivate</label>
                    <br/><br/>
                %elif can_deactivate_repository:
                    <% deactivate_uninstall_button_text = "Deactivate" %>
                %else:
                    <% deactivate_uninstall_button_text = "Uninstall" %>
                    ##hack to mimic check box
                    <input type="hidden" name="remove_from_disk" value="true"/><input type="hidden" name="remove_from_disk" value="true"/>
                %endif
                %if not can_uninstall_repository:
                    <%
                        irm = trans.app.installed_repository_manager

                        # Get installed repositories that require this repository.
                        installed_repository_dependencies = []
                        installed_runtime_dependent_tool_dependencies = []
                        for r in irm.installed_repository_dependencies_of_installed_repositories:
                            if r.id == repository.id:
                                installed_repository_dependencies = irm.installed_repository_dependencies_of_installed_repositories[ r ]
                                break

                        # Get this repository's installed tool dependencies.
                        installed_tool_dependencies = []
                        for r in irm.installed_tool_dependencies_of_installed_repositories:
                            if r.id == repository.id:
                                installed_tool_dependencies = irm.installed_tool_dependencies_of_installed_repositories[ r ]
                                break

                        # Get installed runtime dependent tool dependencies of this repository's installed tool dependencies.
                        installed_runtime_dependent_tool_dependencies = []
                        for itd in installed_tool_dependencies:
                            for td in irm.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies:
                                if td.id == itd.id:
                                    installed_dependent_tds = \
                                        irm.installed_runtime_dependent_tool_dependencies_of_installed_tool_dependencies[ td ]
                                    if installed_dependent_tds:
                                        installed_runtime_dependent_tool_dependencies.extend( installed_dependent_tds )
                    %>
                    %if installed_repository_dependencies or installed_runtime_dependent_tool_dependencies:
                        <table width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                                <td bgcolor="#D8D8D8">
                                    <label>This repository cannot be uninstalled because it is required by the following installed items:</label>
                                </td>
                            </tr>
                        </table>
                        %if installed_repository_dependencies:
                            <label>Dependent repositories:</label>
                            <ul>
                            %for installed_repository_dependency in installed_repository_dependencies:
                                <%
                                    changeset_revision = installed_repository_dependency.changeset_revision
                                    name = installed_repository_dependency.name
                                    owner = installed_repository_dependency.owner
                                %>
                                <li>Revision <b>${ changeset_revision | h}</b> of repository <b>${name | h}</b> owned by <b>${owner | h}</b></li>
                            %endfor
                            </ul>
                        %endif
                        %if installed_runtime_dependent_tool_dependencies:
                            <label>Runtime dependent tool dependencies of this repository's tool dependencies:</label>
                            <ul>
                                %for td in installed_runtime_dependent_tool_dependencies:
                                    <%
                                        containing_repository = irm.get_containing_repository_for_tool_dependency( td )
                                        repository_name = containing_repository.name
                                        changeset_revision = containing_repository.changeset_revision
                                        owner = containing_repository.owner
                                    %>
                                    <li>
                                        Version <b>${td.version}</b> of ${td.type} <b>${td.name}</b> contained in revision 
                                        <b>${changeset_revision | h}</b> of repository <b>${repository_name | h}</b> owned by <b>${owner}</b>
                                    </li>
                                %endfor
                            </ul>
                        %endif
                        <br/>
                    %endif
                %endif
                %if can_deactivate_repository:
                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                            <td bgcolor="#D8D8D8">
                                <label>Deactivating this repository will result in the following:</label>
                            </td>
                        </tr>
                    </table>
                    <div class="toolParamHelp" style="clear: both;">
                            * The repository and all of it's contents will remain on disk.
                    </div>
                    %if repository.includes_tools_for_display_in_tool_panel:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's tools will not be loaded into the tool panel.
                        </div>
                    %endif
                    %if repository.includes_tool_dependencies:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's installed tool dependencies will remain on disk.
                        </div>
                    %endif
                    %if repository.includes_datatypes:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's datatypes, datatype converters and display applications will be eliminated from the datatypes registry.
                        </div>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository record's deleted column in the tool_shed_repository database table will be set to True.
                    </div>
                    <br/>
                %endif
                %if can_uninstall_repository:
                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                            <td bgcolor="#D8D8D8">
                                <label>Uninstalling this repository will result in the following:</label>
                            </td>
                        </tr>
                    </table>
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository and all of it's contents will be removed from disk.
                    </div>
                    %if repository.includes_tools_for_display_in_tool_panel:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's tool tag sets will be removed from the tool config file in which they are defined.
                        </div>
                    %endif
                    %if repository.includes_tool_dependencies:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's installed tool dependencies will be removed from disk.
                        </div>
                        <div class="toolParamHelp" style="clear: both;">
                            * Each associated tool dependency record's status column in the tool_dependency database table will be set to 'Uninstalled'.
                        </div>
                    %endif
                    %if repository.includes_datatypes:
                        <div class="toolParamHelp" style="clear: both;">
                            * The repository's datatypes, datatype converters and display applications will be eliminated from the datatypes registry.
                        </div>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository record's deleted column in the tool_shed_repository database table will be set to True.
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        * The repository record's uninstalled column in the tool_shed_repository database table will be set to True.
                    </div>
                    <div style="clear: both"></div>
                    <br/>
                %endif
            </div>
            <div class="form-row">
                <input type="submit" name="deactivate_or_uninstall_repository_button" value="${deactivate_uninstall_button_text}"/>
            </div>
        </form>
    </div>
</div>
