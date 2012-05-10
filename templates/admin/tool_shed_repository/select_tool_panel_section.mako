<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    The core Galaxy development team does not maintain the contents of many Galaxy tool shed repositories.  Some repository tools
    may include code that produces malicious behavior, so be aware of what you are installing.  
    <p/>
    If you discover a repository that causes problems after installation, contact <a href="http://wiki.g2.bx.psu.edu/Support" target="_blank">Galaxy support</a>,
    sending all necessary information, and appropriate action will be taken.
    <p/>
    <a href="http://wiki.g2.bx.psu.edu/Tool%20Shed#Contacting_the_owner_of_a_repository" target="_blank">Contact the repository owner</a> for general questions 
    or concerns.
</div>
<br/>
<div class="warningmessage">
    Installation may take a while, depending upon the size of the repository contents.  Wait until a message is displayed in your 
    browser after clicking the <b>Install</b> button below.
</div>
<br/>

<div class="toolForm">
    <div class="toolFormTitle">Choose the tool panel section to contain the installed tools (optional)</div>
    <div class="toolFormBody">
        <form name="select_tool_panel_section" id="select_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='install_repository', tool_shed_url=tool_shed_url, repo_info_dict=repo_info_dict, includes_tools=includes_tools )}" method="post" >
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
            <div class="form-row">
                <pre>${readme_text}</pre>
            </div>
        </div>
    </div>
%endif
