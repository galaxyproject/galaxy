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
<%
import json
metadata_json = json.dumps(repository['metadata'])
%>
    $(document).ready(function() {
        $('#install_repository').click(function() {
            var params = {};
            params['tool_shed_url'] = $("#tool_shed_url").val();
            params['install_tool_dependencies'] = $("#install_tool_dependencies").val();
            params['install_repository_dependencies'] = $("#install_repository_dependencies").val();
            params['tool_panel_section_id'] = $("#tool_panel_section_id").val();
            params['new_tool_panel_section_label'] = $("#new_tool_panel_section").val();
            params['changeset'] = $("#changeset").val();
            params['repo_dict'] = '${encoded_repository}';
            url = $('#repository_installation').attr('action');
            console.log(url);
            $.post(url, params, function(data) {
                window.location.href = data;
            });

        });
        $('#changeset').change(function() {
            var metadata = ${metadata_json};
            metadata_key = $(this).find("option:selected").text();
            console.log(metadata[metadata_key]['tools'])
        });
    });
</script>
<h1>${repository['name']}</h1>
<form id="repository_installation" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">
    <label for="install_tool_dependencies">Install tool dependencies</label>
    <input type="checkbox" checked id="install_tool_dependencies" />
    <label for="install_tool_dependencies">Install repository dependencies</label>
    <input type="checkbox" checked id="install_repository_dependencies" />
    <input type="hidden" id="tsr_id" name="tsr_id" value="${repository['id']}" />
    <input type="hidden" id="tool_shed_url" name="tool_shed_url" value="${tool_shed_url}" />
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
        <label>Tool panel section:</label>
        ${tool_panel_section_select_field.get_html()}
    </div>
    <div class="form-row">
        <label>Add new tool panel section:</label>
        <input id="new_tool_panel_section" name="new_tool_panel_section_label" type="textfield" value="" size="40"/>
        <div class="toolParamHelp" style="clear: both;">
            Add a new tool panel section to contain the installed tools (optional).
        </div>
    </div>
    <select id="changeset" name="changeset">
        %for changeset in sorted( repository['metadata'].keys(), key=lambda changeset: int( changeset.split( ':' )[ 0 ] ), reverse=True ):
            <option value="${changeset.split(':')[1]}">${changeset}</option>
        %endfor
    </select>
    <div class="toolForm">
        <div class="toolFormTitle">Contents of this repository</div>
        <div class="toolFormBody">
            <table class="tables container-table" id="valid_tools" border="0" cellpadding="2" cellspacing="2" width="100%">
                <tbody>
                    <tr id="folder-ed01147b4aa1e8de" class="folderRow libraryOrFolderRow expanded" bgcolor="#D8D8D8">
                        <td colspan="3" style="padding-left: 0px;">
                            <span class="expandLink folder-ed01147b4aa1e8de-click">
                                <div style="float: left; margin-left: 2px;" class="expandLink folder-ed01147b4aa1e8de-click">
                                    <a class="folder-ed01147b4aa1e8de-click" href="javascript:void(0);">
                                        Valid tools<i> - click the name to preview the tool and use the pop-up menu to inspect all metadata</i>
                                    </a>
                                </div>
                            </span>
                        </td>
                    </tr>
                    <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">
                        <th style="padding-left: 40px;">Name</th>
                        <th>Description</th>
                        <th>Version</th>
                    </tr>
                    <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-c9715d71689bf781">
                            <td style="padding-left: 40px;">
                                <div style="float:left;" class="menubutton split popup" id="tool-c9715d71689bf781-popup">
                                    <a class="view-info">Kraken</a>
                                </div>
                            </td>
                        <td>assign taxonomic labels to sequencing reads</td>
                        <td>1.1.2</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    <input type="button" id="install_repository" name="install_repository" value="Install" />
</form>
