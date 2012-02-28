<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Choose the tool panel section to contain the installed tools (optional)</div>
    <div class="toolFormBody">
        <form name="reselect_tool_panel_section" id="reselect_tool_panel_section" action="${h.url_for( controller='admin_toolshed', action='reinstall_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                ${no_changes_check_box.get_html()}
                <label style="display: inline;">No changes</label>
                <div class="toolParamHelp" style="clear: both;">
                    Uncheck and select a different tool panel section to load the tools into a different section in the tool panel.
                </div>
            </div>
            <div class="form-row">
                <label>Add new tool panel section:</label>
                <input name="new_tool_panel_section" type="textfield" value="" size="40"/>
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
            </div>
        </form>
    </div>
</div>
