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
metadata_json = json.dumps(repository['metadata'])
tool_panel_section_dict = { 'name': tool_panel_section_select_field.name,
                            'id': tool_panel_section_select_field.field_id,
                            'sections': [] }
for name, id, _ in tool_panel_section_select_field.options:
    tool_panel_section_dict['sections'].append( '<option value="%s">%s</option>' % ( id, name ) )
%>
var tool_panel_sections_json = ${json.dumps(tool_panel_section_dict['sections'])};
function global_select_tps_template() {
    var tps_selection_template = _.template([
        '<div class="form-row" id="select_tps">',
            '${tool_panel_section_select_field.get_html().replace('\n', '')}',
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
        '<tr id="libraryItem" class="tool_row" style="display: table-row;">',
            '<td style="padding-left: 40px;">',
                '<div id="tool" class="menubutton split popup" style="float: left;">',
                    '<a class="view-info"><\%- tool_name %></a>',
                '</div>',
            '</td>',
            '<td><\%- tool_description %></td>',
            '<td><\%- tool_version %></td>',
            '<td>',
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
        '<div id="select_tps_<\%- clean_name %>" class="form-row">',
            '<select data-toolguid="<\%- tool_guid %>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<\%- clean_name %>">',
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
function repository_dependency_row(name, revision, owner, prior) {
    rd_html = ['<tr class="datasetRow repository_dependency_row" style="display: table-row;">',
               '<td><p>Repository <b><\%- name %></b> revision <b><\%- revision %></b> owned by <b><\%- owner %></b>']
    if (prior) {
        rd_html.push(' (<em>prior installation required</em>)');
    }
    rd_html.push('</p></td></tr>');
    return _.template(rd_html.join(''))({name: name, revision: revision, owner: owner});
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
function check_tool_dependencies(metadata) {
    if (metadata['includes_tool_dependencies']) {
        $(".tool_dependency_row").remove();
        dependency_metadata = metadata['tool_dependencies'];
        for (var dependency_key in dependency_metadata) {
            dep = dependency_metadata[dependency_key];
            dependency_html = tool_dependency_row(dep['name'], dep['version'], dep['type']);
            $("#tool_deps").append(dependency_html);
        }
        $("#tool_dependencies").show();
        $("#install_tool_dependencies").prop('disabled', false);
    }
    else {
        $("#tool_dependencies").hide();
        $("#install_tool_dependencies").prop('disabled', true);
    }
}
function check_repository_dependencies(metadata) {
    $(".repository_dependency_row").remove();
    if (metadata['has_repository_dependencies']) {
        dependency_metadata = metadata['repository_dependencies'];
        for (var dependency_key in dependency_metadata) {
            if (dependency_key != 'root_key' && dependency_key != 'description') {
                for (var dependency in dependency_metadata[dependency_key]) {
                    dep = dependency_metadata[dependency_key][dependency];
                    $("#repository_deps").append(repository_dependency_row(dep[1], dep[3], dep[2], dep[4]));
                }
            }
        }
        $("#repository_dependencies").show();
        $("#install_repository_dependencies").prop('disabled', false);
    }
    else {
        $("#repository_dependencies").hide();
        $("#install_repository_dependencies").prop('disabled', true);
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
    var metadata = ${metadata_json}[metadata_key];
    check_repository_dependencies(metadata);
    check_tool_dependencies(metadata);
    if (metadata !== undefined && metadata['has_repository_dependencies']) {
        $("#repository_dependencies").show();
        $("#install_repository_dependencies_checkbox").show();
    }
    else {
        $("#repository_dependencies").hide();
        $("#install_repository_dependencies_checkbox").hide();
    }
    if (metadata !== undefined && metadata['includes_tool_dependencies']) {
        $("#tool_dependencies").show();
        $("#install_tool_dependencies_checkbox").show();
    }
    else {
        $("#tool_dependencies").hide();
        $("#install_tool_dependencies_checkbox").hide();
    }
    $(".tool_row").remove();
    $.each(metadata['tools']['valid_tools'], function(idx) {
        tool = metadata['tools']['valid_tools'][idx];
        clean_name = clean_tool_name(tool['name']);
        new_html = tool_row_template(tool.name, tool.description, tool.version, clean_name, tool.guid);
        create_html = create_tps_template(clean_name);
        $("#tools_in_repo").append(new_html);
        $('#select_tps_button_' + clean_name).click(show_select_html);
    });
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
        params.repo_dict = '${encoded_repository}';
        console.log(params);
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
</style>
<h2 style="font-weight: normal;">Installing repository <strong>${repository['name']}</strong> from <strong>${repository['owner']}</strong></h2>
<form id="repository_installation" method="post" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">
    <input type="hidden" id="tsr_id" name="tsr_id" value="${repository['id']}" />
    <input type="hidden" id="tool_shed_url" name="tool_shed_url" value="${tool_shed_url}" />
    <div class="toolForm">
        <div class="toolFormTitle">Changeset</div>
        <div class="toolFormBody">
            <select id="changeset" name="changeset">
                %for changeset in sorted( repository['metadata'].keys(), key=lambda changeset: int( changeset.split( ':' )[ 0 ] ), reverse=True ):
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
                <table class="tables container-table" id="repository_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">
                    <tbody id="repository_deps">
                        <tr class="repository_dependency_row"><p>Repository installation requires the following:</p></tr>
                    </tbody>
                </table>
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
