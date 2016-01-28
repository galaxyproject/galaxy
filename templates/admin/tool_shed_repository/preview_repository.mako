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
${javascripts()}

%if message:
    ${render_msg( message, status )}
%endif
<script type="text/javascript">
<%
import json
tool_panel_section_dict = { 'name': tool_panel_section_select_field.name,
                            'id': tool_panel_section_select_field.field_id,
                            'sections': [] }
for name, id, _ in tool_panel_section_select_field.options:
    tool_panel_section_dict['sections'].append( '<option value="%s">%s</option>' % ( id, name ) )
%>
var tool_panel_sections_json = ${json.dumps(tool_panel_section_dict['sections'])};
var repository_information = ${json.dumps(toolshed_data)};
var valid_tool_dependencies = Array();
var valid_tools = Array();
Array.prototype.containsDict = function(val) {
    for (var i in this) {
        needle = this[i];
        var found = true;
        for (var key in val) {
            if (needle[key] != val[key]) {
                found = false;
            }
        }
        if (found) { return true; }
    }
    return false;
}
function global_select_tps_template() {
    var tps_selection_template = _.template([
        '<div class="form-row" id="select_tps">',
            '${tool_panel_section_select_field.get_html(extra_attr={'style':'width:30em;'}).replace('\n', '')}',
            '<input class="menubutton" type="button" id="create_new" value="Create new" />',
            '<div class="toolParamHelp" style="clear: both;">',
                'Select an existing tool panel section to contain the installed tools (optional).',
            '</div>',
        '</div>'
    ].join(''));
    return tps_selection_template();
}
function global_create_tps_template() {
    tps_creation_template = _.template([
        '<div class="form-row" id="new_tps">',
            '<input id="new_tool_panel_section" name="new_tool_panel_section" type="textfield" value="" size="40"/>',
            '<input class="menubutton" type="button" id="select_existing" value="Select existing" />',
            '<div class="toolParamHelp" style="clear: both;">',
                'Add a new tool panel section to contain the installed tools (optional).',
            '</div>',
        '</div>'
    ].join(''));
    return tps_creation_template();
}
function tool_row_template(name, description, version, clean_name, tool_guid) {
    var tool_row = _.template([
        '<tr id="libraryItem" class="tool_row" style="display: table-row;" style="width: 15%">',
            '<td style="padding-left: 40px;">',
                '<div id="tool" class="menubutton split popup" style="float: left;">',
                    '<a class="view-info"><\%- tool_name %></a>',
                '</div>',
            '</td>',
            '<td><\%- tool_description %></td>',
            '<td style="width: 15%"><\%- tool_version %></td>',
            '<td style="width: 35%">',
                '<div class="toolFormBody" id="per_tool_tps_container">',
                    '<span id="show_tps_picker">',
                        '<input class="menubutton" id="select_tps_button_<\%- clean_name %>" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" type="button" value="Specify panel section" />',
                    '</span>',
                '</div>',
            '</td>',
        '</tr>'].join(''));
    return tool_row({tool_name: name, tool_description: description, tool_version: version, clean_name: clean_name, tool_guid: tool_guid});
}
function tps_picker_template(clean_name, tool_guid) {
    var tps_picker = _.template([
        '<span id="show_tps_picker">',
            '<input class="menubutton" id="select_tps_button_<\%- clean_name %>" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" type="button" value="Specify panel section" />',
        '</span>',
        ].join(''));
    return tps_picker({clean_name: clean_name, tool_guid: tool_guid});
}
function select_tps_template(clean_name, tool_guid) {
    var underscore_template = _.template([
        '<div id="select_tps_<\%- clean_name %>" class="form-row" style="padding: 0 !important;">',
            '<select style="width: 30em;" data-toolguid="<\%- tool_guid %>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<\%- clean_name %>">',
            tool_panel_sections_json,
            '</select>',
            '<input class="menubutton" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" value="Create new" id="create_new_<\%- clean_name %>" type="button">',
            '<input class="menubutton" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" value="Cancel" id="cancel_<\%- clean_name %>" type="button">',
            '<div style="clear: both;" class="toolParamHelp"></div>',
        '</div>'].join(''));
    return underscore_template({clean_name: clean_name, tool_guid: tool_guid});
}
function create_tps_template(clean_name, tool_guid) {
    var underscore_template = _.template([
            '<div id="new_tps_<\%- clean_name %>" class="form-row">',
                '<input data-toolguid="<\%- tool_guid %>" class="tool_panel_section_picker" size="40" name="new_tool_panel_section" id="new_tool_panel_section_<\%- clean_name %>" type="text">',
                '<input class="menubutton" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" value="Select existing" id="select_existing_<\%- clean_name %>" type="button">',
                '<input class="menubutton" data-toolguid="<\%- tool_guid %>" data-toolname="<\%- clean_name %>" value="Cancel" id="cancel_<\%- clean_name %>" type="button">',
            '</div>'
        ].join(''));
    return underscore_template({clean_name: clean_name, tool_guid: tool_guid});
}
function repository_dependency_row(dependency_id, name, revision, owner, prior) {
    rd_html = ['<li id="metadata_<\%- id %>" class="datasetRow repository_dependency_row" style="display: table-row;">',
               'Repository <b><\%- name %></b> revision <b><\%- revision %></b> owned by <b><\%- owner %></b>']
    if (prior) {
        rd_html.push(' (<em>prior installation required</em>)');
    }
    rd_html.push('</li>');
    return _.template(rd_html.join(''))({id: dependency_id, name: name, revision: revision, owner: owner});
}
function tool_dependency_row(name, version, type) {
    var td_row = _.template([
        '<tr class="datasetRow tool_dependency_row" style="display: table-row;">',
            '<td style="padding-left: 40px;">',
            '<\%- name %></td>',
            '<td><\%- version %></td>',
            '<td><\%- type %></td>',
        '</tr>'
        ].join(''));
    return td_row({name: name, version: version, type: type})
}
function clean_tool_name(name) {
    return name.replace(/[^a-zA-Z0-9]+/g, "_").toLowerCase();
}
function process_dependencies(metadata, selector) {
    if (metadata.has_repository_dependencies) {
        for (var item in metadata.repository_dependencies) {
            var dependency = metadata.repository_dependencies[item];
            var repository = dependency.repository;
            if (repository != null) {
                var dependency_html = repository_dependency_row(dependency.id, repository.name, dependency.changeset_revision, repository.owner, dependency.prior_installation_required)
                if (selector == null) {
                    $("#repository_deps").append(dependency_html);
                }
                else {
                    $(selector).append('<ul>' + dependency_html + '</ul>');
                }
                if (dependency.has_repository_dependencies) {
                    process_dependencies(dependency, '#metadata_' + dependency.id);
                }
            }
        }
    }
    if (metadata.includes_tool_dependencies) {
        for (var item in metadata.tool_dependencies) {
            var dependency = metadata.tool_dependencies[item];
            var tool_dependency = {name: dependency.name, version: dependency.version, type: dependency.type};
            if (!valid_tool_dependencies.containsDict(tool_dependency)) {
                valid_tool_dependencies.push(tool_dependency);
            }
        }
    }
    if (metadata.includes_tools) {
        for (var entry in metadata.tools) {
            var tool = metadata.tools[entry];
            valid_tool = {clean_name: clean_tool_name(tool.name), name: tool.name, version: tool.version, description: tool.description, guid: tool.guid};
            if (!valid_tools.containsDict(valid_tool) && tool.add_to_tool_panel) {
                valid_tools.push(valid_tool);
            }
        }
    }
}
function tool_panel_section() {
    var tps_selection = $('#tool_panel_section_select').find("option:selected").text();
    if (tps_selection == 'Create New') {
        $("#new_tool_panel_section").prop('disabled', false);
        $("#new_tps").show();
    }
    else {
        $("#new_tool_panel_section").prop('disabled', true);
        $("#new_tps").hide();
    }
}
function show_select_html() {
    clean_name = $(this).attr('data-toolname');
    tool_guid = $(this).attr('data-toolguid');
    containing_element = $(this).parent().parent();
    containing_element.children().each(function(){$(this).remove()});
    select_html = select_tps_template(clean_name, tool_guid);
    containing_element.append(select_html);
    $('#create_new_' + clean_name).click(show_create_html);
    $('#cancel_' + clean_name).click(show_picker_button);
}
function show_picker_button() {
    clean_name = $(this).attr('data-toolname');
    tool_guid = $(this).attr('data-toolguid');
    containing_element = $(this).parent().parent();
    containing_element.children().each(function(){$(this).remove()});
    picker_html = tps_picker_template(clean_name, tool_guid);
    containing_element.append(picker_html);
    $('#select_tps_button_' + clean_name).click(show_select_html);
}
function show_create_html() {
    clean_name = $(this).attr('data-toolname');
    tool_guid = $(this).attr('data-toolguid');
    containing_element = $(this).parent().parent();
    containing_element.children().each(function(){$(this).remove()});
    create_html = create_tps_template(clean_name, tool_guid);
    containing_element.append(create_html);
    $('#select_existing_' + clean_name).click(show_select_html);
    $('#cancel_' + clean_name).click(show_picker_button);
}
function changeset_metadata() {
    metadata_key = $('#changeset').find("option:selected").text();
    $("#current_changeset").text(metadata_key);
    var repository_metadata = repository_information.metadata[metadata_key];
    if (repository_metadata !== undefined && repository_metadata['has_repository_dependencies']) {
        $("#repository_dependencies").show();
        $("#install_repository_dependencies_checkbox").show();
    }
    else {
        $("#repository_dependencies").hide();
        $("#install_repository_dependencies_checkbox").hide();
    }
    $(".repository_dependency_row").remove();
    $(".tool_dependency_row").remove();
    process_dependencies(repository_metadata);
    valid_tools.sort(function(a,b){return a.clean_name.localeCompare(b.clean_name);});
    valid_tool_dependencies.sort(function(a,b){return a.name.toUpperCase().localeCompare(b.name.toUpperCase());});
    $('.tool_row').remove();
    for (var tool_idx = 0; tool_idx < valid_tools.length; tool_idx++) {
        tool = valid_tools[tool_idx];
        if (tool.name != 'undefined') {
            new_html = tool_row_template(tool.name, tool.description, tool.version, tool.clean_name, tool.guid);
            $("#tools_in_repo").append(new_html);
            $('#select_tps_button_' + tool.clean_name).click(show_select_html);
        }
    }
    if (valid_tool_dependencies.length > 0) {
        for (var td_index = 0; td_index < valid_tool_dependencies.length; td_index++) {
            tool_dependency = valid_tool_dependencies[td_index];
            dependency_html = tool_dependency_row(tool_dependency.name, tool_dependency.version, tool_dependency.type);
            $("#tool_deps").append(dependency_html);
        }
        $("#tool_dependencies").show();
        $("#install_tool_dependencies").prop('disabled', false);
        $("#install_tool_dependencies_checkbox").show();
    }
    else {
        $("#tool_dependencies").hide();
        $("#install_tool_dependencies").prop('disabled', true);
        $("#install_tool_dependencies_checkbox").hide();
    }
}
function toggle_folder(folder) {
    target_selector = '#' + folder.attr('data_target');
    $(target_selector).toggle();
}
function select_tps(params) {
    var tool_panel_section = {};
    if ($('#tool_panel_section_select').length) {
        params.tool_panel_section_id = $('#tool_panel_section_select').find("option:selected").val();
    }
    else {
        params.new_tool_panel_section = $("#new_tool_panel_section").val();
    }
    $('.tool_panel_section_picker').each(function() {
        element_name = $(this).attr('name');
        tool_guid = $(this).attr('data-toolguid');
        if (element_name == 'tool_panel_section_id') {
            tool_panel_section[tool_guid] = { tool_panel_section: $(this).find("option:selected").val(), action: 'append' }
        }
        else {
            tool_panel_section[tool_guid] = { tool_panel_section: $(this).val(), action: 'create' }
        }
    });
    return tool_panel_section;
}
function show_global_tps_select() {
    $('#tool_panel_section').children().each(function(){$(this).remove()});
    $('#tool_panel_section').append(global_select_tps_template());
    $('#create_new').click(show_global_tps_create);
}
function show_global_tps_create() {
    $('#tool_panel_section').children().each(function(){$(this).remove()});
    $('#tool_panel_section').append(global_create_tps_template());
    $('#select_existing').click(show_global_tps_select);
}
$(function() {
    changeset_metadata();
    require(["libs/jquery/jstree"], function() {
        $('#repository_dependencies_table').jstree();
    });
    show_global_tps_select();
    $('#changeset').change(changeset_metadata);
    $("#tool_panel_section_select").change(tool_panel_section);
    $('.toggle_folder').click(function() {
        toggle_folder($(this));
    });
    $('#repository_installation').submit(function(form) {
        form.preventDefault();
        var params = {};
        params.tool_shed_url = $("#tool_shed_url").val();
        params.install_tool_dependencies = $("#install_tool_dependencies").val();
        params.install_repository_dependencies = $("#install_repository_dependencies").val();
        params.tool_panel_section = JSON.stringify(select_tps(params));
        params.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        params.changeset = $("#changeset").val();
        url = $('#repository_installation').attr('action');
        $.post(url, params, function(data) {
            window.location.href = data;
        });
    });
});
</script>
<style type="text/css">
div.expandLink {
    float: left;
    padding-left: 2px;
    background-color: #d8d8d8;
    width: 100%;
}
div.changeset {
    padding: 5px 10px 5px 10px;
}
</style>
<!-- <pre>${json.dumps(toolshed_data, indent=2)}</pre> -->
<h2 style="font-weight: normal;">Installing repository <strong>${toolshed_data['name']}</strong> from <strong>${toolshed_data['owner']}</strong></h2>
<form id="repository_installation" method="post" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">
    <input type="hidden" id="tsr_id" name="tsr_id" value="${toolshed_data['id']}" />
    <input type="hidden" id="tool_shed_url" name="tool_shed_url" value="${tool_shed_url}" />
    <div class="toolForm">
        <div class="toolFormTitle">Changeset</div>
        <div class="toolFormBody changeset">
            <select id="changeset" name="changeset">
                %for changeset in sorted( toolshed_data['metadata'].keys(), key=lambda changeset: int( changeset.split( ':' )[ 0 ] ), reverse=True ):
                    <option value="${changeset.split(':')[1]}">${changeset}</option>
                %endfor
            </select>
            <input type="submit" id="install_repository" name="install_repository" value="Install this revision" />
        </div>
        %if shed_tool_conf_select_field:
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
        %endif
        <div class="toolFormTitle">Tool panel section:</div>
        <div class="toolFormBody" id="tool_panel_section">
        </div>
        <div class="toolFormTitle">Contents of this repository at revision <strong id="current_changeset"></strong></div>
        <div class="toolFormBody">
            <p id="install_repository_dependencies_checkbox">
                <input type="checkbox" checked id="install_repository_dependencies" />
                <label for="install_repository_dependencies">Install repository dependencies</label>
            </p>
            <p id="install_tool_dependencies_checkbox">
                <input type="checkbox" checked id="install_tool_dependencies" />
                <label for="install_tool_dependencies">Install tool dependencies</label>
            </p>
            <div class="tables container-table" id="repository_dependencies">
                <div class="expandLink">
                    <a class="toggle_folder" data_target="repository_dependencies_table">
                        Repository dependencies &ndash; <em>installation of these additional repositories is required</em>
                    </a>
                </div>
                <div class="tables container-table" id="repository_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">
                    <ul id="repository_deps">
                        <li class="repository_dependency_row"><p>Repository installation requires the following:</p></li>
                    </ul>
                </div>
            </div>
            <div class="tables container-table" id="tool_dependencies">
                <div class="expandLink">
                    <a class="toggle_folder" data_target="tool_dependencies_table">
                        Tool dependencies &ndash; <em>repository tools require handling of these dependencies</em>
                    </a>
                </div>
                <table class="tables container-table" id="tool_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">
                    <tbody id="tool_deps">
                        <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">
                            <th style="padding-left: 40px;">Name</th>
                            <th>Version</th>
                            <th>Type</th>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="tables container-table" id="tools_toggle">
                <div class="expandLink">
                    <a class="toggle_folder" data_target="valid_tools">
                        Valid tools &ndash; <em>click the name to preview the tool and use the pop-up menu to inspect all metadata</em>
                    </a>
                </div>
                <table class="tables container-table" id="valid_tools" border="0" cellpadding="2" cellspacing="2" width="100%">
                    <tbody id="tools_in_repo">
                        <tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">
                            <th style="padding-left: 40px;">Name</th>
                            <th>Description</th>
                            <th>Version</th>
                            <th>Tool Panel Section</th>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</form>
