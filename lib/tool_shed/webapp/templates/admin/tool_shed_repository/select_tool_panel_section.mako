<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_dependencies_section" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_readme_section" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${container_javascripts()}
</%def>

<%
    # Handle the case where an uninstalled repository encountered errors during the process of being reinstalled.  In
    # this case, the repository metadata is an empty dictionary, but one or both of has_repository_dependencies
    # and includes_tool_dependencies may be True.  If either of these are True but we have no metadata, we cannot install
    # repository dependencies on this pass.
    if has_repository_dependencies:
        repository_dependencies = containers_dict[ 'repository_dependencies' ]
        missing_repository_dependencies = containers_dict[ 'missing_repository_dependencies' ]
        if repository_dependencies or missing_repository_dependencies:
            can_display_repository_dependencies = True
        else:
            can_display_repository_dependencies = False
    else:
        can_display_repository_dependencies = False
    if includes_tool_dependencies:
        tool_dependencies = containers_dict[ 'tool_dependencies' ]
        missing_tool_dependencies = containers_dict[ 'missing_tool_dependencies' ]
        if tool_dependencies or missing_tool_dependencies:
            can_display_tool_dependencies = True
        else:
            can_display_tool_dependencies = False
    else:
        can_display_tool_dependencies = False
    can_display_resolver_installation = install_resolver_dependencies_check_box is not None
%>

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <p>
        The Galaxy development team does not maintain the contents of many Galaxy Tool Shed repositories.  Some
        repository tools may include code that produces malicious behavior, so be aware of what you are installing.
    </p>
    <p>
        If you discover a repository that causes problems after installation, contact <a href="https://galaxyproject.org/support" target="_blank">Galaxy support</a>,
        sending all necessary information, and appropriate action will be taken.
    </p>
    <p>
        <a href="https://galaxyproject.org/toolshed/repository-features/#contact-repository-owner" target="_blank">Contact the repository owner</a> for
        general questions or concerns.
    </p>
</div>
<div class="card">
    <div class="card-body">
        <form name="select_tool_panel_section" id="select_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='prepare_for_install' )}" method="post" >
            <div class="form-row">
                <input type="hidden" name="includes_tools" value="${includes_tools}" />
                <input type="hidden" name="includes_tool_dependencies" value="${includes_tool_dependencies}" />
                <input type="hidden" name="requirements_status" value="${requirements_status}" />
                <input type="hidden" name="includes_tools_for_display_in_tool_panel" value="${includes_tools_for_display_in_tool_panel}" />
                <input type="hidden" name="tool_shed_url" value="${tool_shed_url}" />
                <input type="hidden" name="encoded_repo_info_dicts" value="${encoded_repo_info_dicts}" />
                <input type="hidden" name="updating" value="${updating}" />
                <input type="hidden" name="updating_repository_id" value="${updating_repository_id}" />
                <input type="hidden" name="updating_to_ctx_rev" value="${updating_to_ctx_rev}" />
                <input type="hidden" name="updating_to_changeset_revision" value="${updating_to_changeset_revision}" />
                <input type="hidden" name="encoded_updated_metadata" value="${encoded_updated_metadata}" />
            </div>
            <div style="clear: both"></div>
            <% readme_files_dict = containers_dict.get( 'readme_files', None ) %>
            %if readme_files_dict:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Repository README file - may contain important installation or license information</th>
                    </table>
                </div>
                ${render_readme_section( containers_dict )}
                <div style="clear: both"></div>
            %endif
            <%
                if requirements_status and install_resolver_dependencies_check_box or includes_tool_dependencies:
                    display_dependency_confirmation = True
                else:
                    display_dependency_confirmation = False
            %>
            %if requirements_status:
                %if not install_resolver_dependencies_check_box and not includes_tool_dependencies:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <head>
                            <th>
                                <img src="${h.url_for('/static')}/images/icon_error_sml.gif" title='Cannot install dependencies'/>
                                This repository requires dependencies that cannot be installed through the Tool Shed
                            </th>
                        </head>
                    </table>
                </div>
                <div class="form-row">
                     <p>This repository defines tool requirements that cannot be installed through the Tool Shed.</p>
                     <p>Please activate Conda dependency resolution, activate Docker dependency resolution, setup Environment Modules
or manually satisfy the dependencies listed below.</p>
                     <p>For details see <a target="_blank" href="https://docs.galaxyproject.org/en/master/admin/dependency_resolvers.html">the dependency resolver documentation.</a></p>
                </div>
                %endif
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">The following tool dependencies are required by the current repository</th>
                    </table>
                </div>
                <div class="form-row">
                    ${render_tool_dependency_resolver( requirements_status, prepare_for_install=True )}
                </div>
                <div style="clear: both"></div>
            %endif
            %if can_display_repository_dependencies or display_dependency_confirmation:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Confirm dependency installation</th>
                    </table>
                </div>
                ${render_dependencies_section( install_resolver_dependencies_check_box, install_repository_dependencies_check_box, install_tool_dependencies_check_box, containers_dict, revision_label=None, export=False, requirements_status=requirements_status )}
                <div style="clear: both"></div>
            %endif
            %if shed_tool_conf_select_field:
                %if includes_tools_for_display_in_tool_panel:
                    <div class="form-row">
                        <table class="colored" width="100%">
                            <th bgcolor="#EBD9B2">Choose the tool panel section to contain the installed tools (optional)</th>
                        </table>
                    </div>
                <div class="detail-section">
                %endif
                <%
                    if len( shed_tool_conf_select_field.options ) == 1:
                        select_help = "Your Galaxy instance is configured with 1 shed-related tool configuration file, so repositories will be "
                        select_help += "installed using its <b>tool_path</b> setting."
                    else:
                        select_help = "Your Galaxy instance is configured with %d shed-related tool configuration files, " % len( shed_tool_conf_select_field.options )
                        select_help += "so select the file whose <b>tool_path</b> setting you want used for installing repositories."
                %>
                <div class="form-row">
                    <label>Shed tool configuration file:</label>
                    ${render_select(shed_tool_conf_select_field)}
                    <div class="toolParamHelp" style="clear: both;">
                        ${select_help|h}
                    </div>
                </div>
                <div style="clear: both"></div>
                </div>
            %else:
                <input type="hidden" name="shed_tool_conf" value="${shed_tool_conf|h}"/>
            %endif
            %if includes_tools_for_display_in_tool_panel:
                <div class="form-row">
                    <label>Add new tool panel section:</label>
                    <input name="new_tool_panel_section_label" type="textfield" value="${new_tool_panel_section_label|h}" size="40"/>
                    <div class="toolParamHelp" style="clear: both;">
                        Add a new tool panel section to contain the installed tools (optional).
                    </div>
                </div>
                <div class="form-row">
                    <label>Select existing tool panel section:</label>
                    ${render_select(tool_panel_section_select_field)}
                    <div class="toolParamHelp" style="clear: both;">
                        Choose an existing section in your tool panel to contain the installed tools (optional).
                    </div>
                </div>
            %endif
            <div class="form-row">
                <input type="submit" name="select_tool_panel_section_button" value="Install"/>
                <div class="toolParamHelp" style="clear: both;">
                    %if includes_tools_for_display_in_tool_panel:
                        Clicking <b>Install</b> without selecting a tool panel section will load the installed tools into the tool panel outside of any sections.
                    %endif
                </div>
            </div>
        </form>
    </div>
</div>
