<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_dependencies_section" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_readme_section" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("libs/jquery/jquery.rating", "libs/jquery/jstorage" )}
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
        If you discover a repository that causes problems after installation, contact <a href="https://wiki.galaxyproject.org/Support" target="_blank">Galaxy support</a>,
        sending all necessary information, and appropriate action will be taken.
    </p>
    <p>
        <a href="https://wiki.galaxyproject.org/ToolShedRepositoryFeatures#Contact_repository_owner" target="_blank">Contact the repository owner</a> for 
        general questions or concerns.
    </p>
</div>
<div class="toolForm">
    <div class="toolFormBody">
        <form name="select_shed_tool_panel_config" id="select_shed_tool_panel_config" action="${h.url_for( controller='admin_toolshed', action='prepare_for_install' )}" method="post" >
            <div class="form-row">
                <input type="hidden" name="encoded_repo_info_dicts" value="${encoded_repo_info_dicts}" />
                <input type="hidden" name="updating" value="${updating}" />
                <input type="hidden" name="updating_repository_id" value="${updating_repository_id}" />
                <input type="hidden" name="updating_to_ctx_rev" value="${updating_to_ctx_rev}" />
                <input type="hidden" name="updating_to_changeset_revision" value="${updating_to_changeset_revision}" />
                <input type="hidden" name="encoded_updated_metadata" value="${encoded_updated_metadata}" />
                <input type="hidden" name="includes_tools" value="${includes_tools}" />
                <input type="hidden" name="includes_tool_dependencies" value="${includes_tool_dependencies}" />
                <input type="hidden" name="includes_tools_for_display_in_tool_panel" value="${includes_tools_for_display_in_tool_panel}" />
                <input type="hidden" name="tool_shed_url" value="${tool_shed_url|h}" />
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
            %if can_display_repository_dependencies or can_display_tool_dependencies or can_display_resolver_installation:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Confirm dependency installation</th>
                    </table>
                </div>
                ${render_dependencies_section( install_resolver_dependencies_check_box, install_repository_dependencies_check_box, install_tool_dependencies_check_box, containers_dict, revision_label=None, export=False )}
                <div style="clear: both"></div>
            %endif
            <div class="form-row">
                <table class="colored" width="100%">
                    <th bgcolor="#EBD9B2">Choose the configuration file whose tool_path setting will be used for installing repositories</th>
                </table>
            </div>
            %if shed_tool_conf_select_field:
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
                    ${shed_tool_conf_select_field.get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        ${select_help|h}
                    </div>
                </div>
                <div style="clear: both"></div>
            %else:
                <input type="hidden" name="shed_tool_conf" value="${shed_tool_conf|h}"/>
            %endif
            <div class="form-row">
                <input type="submit" name="select_shed_tool_panel_config_button" value="Install"/>
            </div>
        </form>
    </div>
</div>
