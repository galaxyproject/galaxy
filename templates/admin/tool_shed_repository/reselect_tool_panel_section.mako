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

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <form name="reselect_tool_panel_section" id="reselect_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='reinstall_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <input type="hidden" name="repo_info_dict" value="${encoded_repo_info_dict}" />
            </div>
            <div style="clear: both"></div>
            <% readme_files_dict = containers_dict.get( 'readme_files', None ) %>
            %if readme_files_dict:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Repository README files - may contain important installation or license information</th>
                    </table>
                </div>
                ${render_readme_section( containers_dict )}
                <div style="clear: both"></div>
            %endif
            %if has_repository_dependencies or includes_tool_dependencies:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Confirm dependency installation</th>
                    </table>
                </div>
                ${render_dependencies_section( install_repository_dependencies_check_box, install_tool_dependencies_check_box, containers_dict, revision_label=None, export=False )}
            %endif
            %if shed_tool_conf_select_field:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Choose the configuration file whose tool_path setting will be used for installing repositories</th>
                    </table>
                </div>
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
                        ${select_help}
                    </div>
                </div>
                <div style="clear: both"></div>
            %else:
                <input type="hidden" name="shed_tool_conf" value="${shed_tool_conf}"/>
            %endif
            %if includes_tools_for_display_in_tool_panel:
                <div style="clear: both"></div>
                <div class="form-row">
                    ${no_changes_check_box.get_html()}
                    <label style="display: inline;">No changes</label>
                    <div class="toolParamHelp" style="clear: both;">
                        Uncheck and select a different tool panel section to load the tools into a different section in the tool panel.
                    </div>
                </div>
                <div class="form-row">
                    <label>Add new tool panel section:</label>
                    <input name="new_tool_panel_section_label" type="textfield" value="" size="40"/>
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
            %endif
            <div class="form-row">
                <input type="submit" name="select_tool_panel_section_button" value="Install"/>
            </div>
        </form>
    </div>
</div>
