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
var html = '                    <tr style="display: table-row;" class="tool_row" parent="0" id="libraryItem">\
                            <td style="padding-left: 40px;">\
                                <div style="float:left;" class="menubutton split popup" id="tool">\
                                    <a class="view-info">__TOOL_NAME__</a>\
                                </div>\
                            </td>\
                        <td>__DESCRIPTION__</td>\
                        <td>__VERSION__</td>\
                    </tr>\
';
    function check_tool_dependencies(metadata) {
        if (metadata['includes_tool_dependencies']) {
            $("#tool_dependencies").show();
            $("#install_tool_dependencies").prop('disabled', false);
        }
        else {
            $("#tool_dependencies").hide();
            $("#install_tool_dependencies").prop('disabled', true);
        }
    }
    function check_repository_dependencies(metadata) {
        if (metadata['has_repository_dependencies']) {
            $("#repository_dependencies").show();
            $("#install_repository_dependencies").prop('disabled', false);
        }
        else {
            $("#repository_dependencies").hide();
            $("#install_repository_dependencies").prop('disabled', true);
        }
    }
    function repository_metadata() {
        metadata_key = $('#changeset').find("option:selected").text();
        var metadata = ${metadata_json}[metadata_key];
        if (!metadata['has_repository_dependencies'] && !metadata['includes_tool_dependencies']) {
            $("#dependencies").hide();
        }
        else {
            $("#dependencies").show();
        }
        check_tool_dependencies(metadata);
        check_repository_dependencies(metadata);
        console.log(metadata);
        $(".tool_row").remove();
        $.each(metadata['tools']['valid_tools'], function(idx) {
            new_html = html.replace('__TOOL_NAME__', metadata['tools']['valid_tools'][idx]['name']);
            new_html = new_html.replace('__DESCRIPTION__', metadata['tools']['valid_tools'][idx]['description']);
            new_html = new_html.replace('__VERSION__', metadata['tools']['valid_tools'][idx]['version']);
            $("#tools_in_repo").append(new_html);
        });
    }
    $(document).ready(function() {
        repository_metadata();
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
        $('#changeset').change(repository_metadata);
    });
</script>
<!--<pre>${json.dumps(repository['metadata'], indent=2)}</pre>-->
<h1>${repository['owner']}/${repository['name']}</h1>
<form id="repository_installation" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">
    <div class="toolForm">
        <div class="toolFormTitle">Changeset</div>
        <div class="toolFormBody">
    <select id="changeset" name="changeset">
        %for changeset in sorted( repository['metadata'].keys(), key=lambda changeset: int( changeset.split( ':' )[ 0 ] ), reverse=True ):
            <option value="${changeset.split(':')[1]}">${changeset}</option>
        %endfor
    </select>
    </div>
    </div>
    <input type="hidden" id="tsr_id" name="tsr_id" value="${repository['id']}" />
    <input type="hidden" id="tool_shed_url" name="tool_shed_url" value="${tool_shed_url}" />
    <div class="toolForm" id="dependencies">
        <div class="toolFormTitle">Dependencies of this repository</div>
        <div class="toolFormBody">
            <table class="tables container-table" id="repository_dependencies" border="0" cellpadding="2" cellspacing="2" width="100%">
                <tbody id="repository_deps">
                    <tr id="folder-529fd61ab1c6cc36" class="folderRow libraryOrFolderRow expanded" bgcolor="#D8D8D8">
                        <td style="padding-left: 0px;">
                            <label for="install_repository_dependencies">Install repository dependencies</label>
                            <input type="checkbox" checked id="install_repository_dependencies" /><br />
                            <span class="expandLink folder-529fd61ab1c6cc36-click">
                                <div style="float: left; margin-left: 2px;" class="expandLink folder-529fd61ab1c6cc36-click">
                                    <a class="folder-529fd61ab1c6cc36-click" href="javascript:void(0);">
                                        Repository dependencies<i> - installation of these additional repositories is required</i>
                                    </a>
                                </div>
                            </span>
                        </td>
                    </tr>
                    <tr style="display: table-row;" class="datasetRow" parent="1" id="libraryItem-rrd-adb5f5c93f827949">
                        <td style="padding-left: 60px;">
                            Repository <b>package_ncurses_5_9</b> revision <b>14ee17fc7640</b> owned by <b>iuc</b> <i>(prior install required)</i>
                        </td>
                    </tr>
                </tbody>
            </table>
            <table class="tables container-table" id="tool_dependencies" border="0" cellpadding="2" cellspacing="2" width="100%">
                <tbody id="tool_deps">
                    <tr id="folder-2234cb1fd1df4331" class="folderRow libraryOrFolderRow expanded" bgcolor="#D8D8D8">
                        <td colspan="4" style="padding-left: 0px;">
                            <label for="install_tool_dependencies">Install tool dependencies</label>
                            <input type="checkbox" checked id="install_tool_dependencies" /><br />
                            <span class="expandLink folder-2234cb1fd1df4331-click">
                                <div style="float: left; margin-left: 2px;" class="expandLink folder-2234cb1fd1df4331-click">
                                    <a class="folder-2234cb1fd1df4331-click" href="javascript:void(0);">
                                        Tool dependencies<i> - repository tools require handling of these dependencies</i>
                                    </a>
                                </div>
                            </span>
                        </td>
                    </tr>
                    <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rtd-adb5f5c93f827949">
                        <th style="padding-left: 40px;">Name</th>
                        <th>Version</th>
                        <th>Type</th>
                    </tr>
                    <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rtd-529fd61ab1c6cc36">
                        <td style="padding-left: 40px;">samtools</td>
                        <td>1.2</td>
                        <td>package</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    %if shed_tool_conf_select_field:
    <div class="toolForm">
        <div class="toolFormTitle">Shed tool configuration file:</div>
        <div class="toolFormBody">
        <%
            if len( shed_tool_conf_select_field.options ) == 1:
                select_help = "Your Galaxy instance is configured with 1 shed-related tool configuration file, so repositories will be "
                select_help += "installed using its <b>tool_path</b> setting."
            else:
                select_help = "Your Galaxy instance is configured with %d shed-related tool configuration files, " % len( shed_tool_conf_select_field.options )
                select_help += "so select the file whose <b>tool_path</b> setting you want used for installing repositories."
        %>
        <div class="form-row">
            ${shed_tool_conf_select_field.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                ${select_help}
            </div>
        </div>
        <div style="clear: both"></div>
        </div>
    </div>
    %endif
    <div class="toolForm">
        <div class="toolFormTitle">Tool panel section:</div>
        <div class="toolFormBody">
    <div class="form-row">
        ${tool_panel_section_select_field.get_html()}
    </div>
    <div class="form-row">
        <input id="new_tool_panel_section" name="new_tool_panel_section_label" type="textfield" value="" size="40"/>
        <div class="toolParamHelp" style="clear: both;">
            Add a new tool panel section to contain the installed tools (optional).
        </div>
    </div>
    </div>
    </div>
    <div class="toolForm">
        <div class="toolFormTitle">Contents of this repository</div>
        <div class="toolFormBody">
            <table class="tables container-table" id="valid_tools" border="0" cellpadding="2" cellspacing="2" width="100%">
                <tbody id="tools_in_repo">
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
                </tbody>
            </table>
        </div>
    </div>
    <input type="button" id="install_repository" name="install_repository" value="Install" />
</form>
