<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="render_tool_dependency_section" />
<%namespace file="/webapps/community/common/common.mako" import="render_readme" />

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
    %if includes_tool_dependencies and trans.app.config.use_tool_dependencies:
        <div class="toolFormTitle">Confirm tool dependency installation</div>
    %else:
        <div class="toolFormTitle">Choose the tool panel section to contain the installed tools (optional)</div>
    %endif
    <div class="toolFormBody">
        <form name="select_tool_panel_section" id="select_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='prepare_for_install', tool_shed_url=tool_shed_url, encoded_repo_info_dicts=encoded_repo_info_dicts, includes_tools=includes_tools, includes_tool_dependencies=includes_tool_dependencies )}" method="post" >
            <div style="clear: both"></div>
            %if includes_tool_dependencies and trans.app.config.use_tool_dependencies:
                ${render_tool_dependency_section( install_tool_dependencies_check_box, repo_info_dicts )}
                <div style="clear: both"></div>
                <div class="form-row">
                    <table class="colored" width="100%">
                        <th bgcolor="#EBD9B2">Choose the tool panel section to contain the installed tools (optional)</th>
                    </table>
                </div>
            %endif
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
    ${render_readme( readme_text )}
%endif
