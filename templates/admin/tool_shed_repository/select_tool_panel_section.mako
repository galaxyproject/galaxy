<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_dependencies_section" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_readme_section" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

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
%>

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
<div class="toolForm">
    <div class="toolFormBody">
        <form name="select_tool_panel_section" id="select_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='prepare_for_install', tool_shed_url=tool_shed_url, encoded_repo_info_dicts=encoded_repo_info_dicts, includes_tools=includes_tools, includes_tool_dependencies=includes_tool_dependencies )}" method="post" >
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
            %if can_display_repository_dependencies or can_display_tool_dependencies:
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Confirm dependency installation</th>
                    </table>
                </div>
                ${render_dependencies_section( install_repository_dependencies_check_box, install_tool_dependencies_check_box, containers_dict )}
                <div style="clear: both"></div>
            %endif
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
