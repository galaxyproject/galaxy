<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%
   from galaxy.tools import Tool
   from galaxy.tools.toolbox import ToolSection
%>

<script type="text/javascript">
$().ready(function() {
%if tool_id:
    var focus_el = $("input[name=reload_tool_button]");
%else:
    var focus_el = $("select[name=tool_id]");
%endif
    focus_el.focus();
});
$().ready(function() {
    $("#reload_toolbox").click(function(){
        $.ajax({
            url: "${h.url_for(controller="/api/configuration", action="toolbox")}",
            type: 'PUT'
        });
    });
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reload Tool</div>
    <div class="toolFormBody">
    <form name="reload_tool" id="reload_tool" action="${h.url_for( controller='admin', action='reload_tool' )}" method="post" >
        <div class="form-row">
            <label>
                Tool to reload:
            </label>
            <select name="tool_id">
                %for val in toolbox.tool_panel_contents( trans ):
                    %if isinstance( val, Tool ):
                        <option value="${val.id|h}">${val.name|h}</option>
                    %elif isinstance( val, ToolSection ):
                        <optgroup label="${val.name|h}">
                        <% section = val %>
                        %for section_key, section_val in section.elems.items():
                            %if isinstance( section_val, Tool ):
                                <% selected_str = "" %>
                                %if section_val.id == tool_id:
                                     <% selected_str = " selected=\"selected\"" %>
                                %endif
                                <option value="${section_val.id|h}"${selected_str}>${section_val.name|h}</option>
                            %endif
                        %endfor
                    %endif
                %endfor
            </select>
        </div>
        <div class="form-row">
            <input type="submit" name="reload_tool_button" value="Reload"/>
        </div>
    </form>
    </div>
</div>
<p>
<div class="toolForm">
    <div class="toolFormTitle">Reload Toolbox</div>
    <div class="toolFormBody">
    <form name="reload_toolbox_form" id="reload_toolbox_form" action="" method="" >
        <div class="form-row">
        Clicking <a href="#" id="reload_toolbox">here</a> will reload
        the Galaxy toolbox. This will cause newly discovered tools
        to be added, tools now missing from tool confs to be removed,
        and items in the panel reordered. Individual tools, even ones
        with modified tool descriptions willl not be reloaded.
        </div>
    </form>
    </div>
</div>
