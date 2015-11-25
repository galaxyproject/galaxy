<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif
<script type="text/javascript">
    $(document).ready(function() {
        $('#install_repository').click(function() {
            var params = {};
            params['tool_shed_url'] = $("#toolshed_url").val();
            params['install_tool_dependencies'] = $("#install_tool_dependencies").val();
            params['install_repository_dependencies'] = $("#install_repository_dependencies").val();
            params['tool_panel_section_id'] = $("#tool_panel_section_id").val();
            params['new_tool_panel_section_label'] = $("#new_tool_panel_section").val();
            params['changeset'] = $("#changeset").val();
            url = $('#repository_installation').attr('action');
            console.log(url);
            $.post(url, params, function(data) {
                console.log(data);
            });

        });
    });
</script>
<pre>${repository}</pre>
<h1>${repository['name']}</h1>
<form id="repository_installation" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">
    <label for="install_tool_dependencies">Install tool dependencies</label>
    <input type="checkbox" checked id="install_tool_dependencies" />
    <label for="install_tool_dependencies">Install repository dependencies</label>
    <input type="checkbox" checked id="install_repository_dependencies" />
    <input type="hidden" name="tsr_id" value="${repository['id']}" />
    <input type="hidden" name="toolshed_url" value="${toolshed_url}" />
    %if shed_tool_conf_select_field:
        <div class="form-row">
            <table class="colored" width="100%">
                <th bgcolor="#EBD9B2">Choose the tool panel section to contain the installed tools (optional)</th>
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
                ${select_help|h}
            </div>
        </div>
        <div style="clear: both"></div>
    %endif
    <div class="form-row">
        <label>Add new tool panel section:</label>
        <input id="new_tool_panel_section" name="new_tool_panel_section_label" type="textfield" value="" size="40"/>
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
    <select id="changeset" name="changeset">
        %for changeset in repository['metadata'].keys():
            <option value="${changeset}">${changeset}</option>
        %endfor
    </select>
    <input type="button" id="install_repository" name="install_repository" value="Install" />
</form>
