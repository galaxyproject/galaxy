<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
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
.container-table {
    padding-top: 1em;
}
ul.jstree-container-ul {
    margin-top: 1em;
}
</style>
</%def>
<%def name="javascripts()">
    ${parent.javascripts()}
</%def>
<script type="text/javascript">
<%
import json
sheds = []
for name, url in trans.app.tool_shed_registry.tool_sheds.items():
    sheds.append(dict(name=name, url=url))
tool_sheds = json.dumps(sheds)
%>
/*
 *
 * Define some global variables, data, and templates
 *
 */
var has_repo_dependencies = false;
var valid_tool_dependencies = Array();
var valid_tools = Array();
var repository_data = Object();
var tool_sheds = JSON.parse('${tool_sheds}');
repository_details_template = _.template([
    '<h2 style="font-weight: normal;">Repository information for <strong><\%= repository.name \%></strong> from <strong><\%= repository.owner \%></strong></h2>',
    '<form id="repository_installation" method="post" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">',
        '<input type="hidden" id="tsr_id" name="tsr_id" value="ID" />',
        '<input type="hidden" id="tool_shed_url" name="tool_shed_url" value="None" />',
        '<div class="toolForm">',
            '<div class="toolFormTitle">Changeset</div>',
            '<div class="toolFormBody changeset">',
                '<select id="changeset" name="changeset">',
                    '<\% _.each(Object.keys(repository.metadata), function(changeset) { \%>',
                        '<option data-changeset="<\%= changeset \%>" value="<\%= changeset.split(":")[1] \%>"><\%= changeset \%></option>',
                    '<\% }); \%>',
                '</select>',
                '<input class="btn btn-primary" type="submit" id="install_repository" name="install_repository" value="Install this revision now" />',
                '<input class="btn btn-primary" type="button" id="queue_install" name="queue_install" value="Install this revision later" />',
                '<div class="toolParamHelp" style="clear: both;">Please select a revision and review the settings below before installing.</div>',
            '</div>',
            '<div class="toolParamHelp" style="clear: both;">',
            'Please select a revision and review the settings below before installing.',
            '</div>',
        '</div>',
        '<div class="toolFormTitle" id="tps_title">Tool panel section:</div>',
        '<div class="toolFormBody" id="tool_panel_section">',
            '<\%= tps_selection_template(panel_section_dict) \%>',
        '</div>',
        '<div class="toolFormTitle">Contents of this repository at revision <strong id="current_changeset"></strong></div>',
        '<div class="toolFormBody">',
            '<p id="install_repository_dependencies_checkbox">',
                '<input type="checkbox" checked id="install_repository_dependencies" />',
                '<label for="install_repository_dependencies">Install repository dependencies</label>',
            '</p>',
            '<p id="install_tool_dependencies_checkbox">',
                '<input type="checkbox" checked id="install_tool_dependencies" />',
                '<label for="install_tool_dependencies">Install tool dependencies</label>',
            '</p>',
            '<\% if (current_changeset === undefined) { \%>',
                '<\% current_changeset = $("#changeset").find("option:selected").text(); \%>',
            '<\% } \%>',
            '<\% current_metadata = repository.metadata[current_changeset]; \%>',
            '<\% if (current_metadata.has_repository_dependencies) { \%>',
                '<\% current_metadata.repository_dependency_template = repository_dependency_template; \%>',
                '<div class="tables container-table" id="repository_dependencies">',
                    '<div class="expandLink">',
                        '<a class="toggle_folder" data_target="repository_dependencies_table">',
                            'Repository dependencies &ndash; <em>installation of these additional repositories is required</em>',
                        '</a>',
                    '</div>',
                    '<\%= repository_dependencies_template(current_metadata) \%>',
                '</div>',
            '<\% } \%>',
            '<\% if (current_metadata.includes_tool_dependencies) { \%>',
                '<div class="tables container-table" id="tool_dependencies">',
                    '<div class="expandLink">',
                        '<a class="toggle_folder" data_target="tool_dependencies_table">',
                            'Tool dependencies &ndash; <em>repository tools require handling of these dependencies</em>',
                        '</a>',
                    '</div>',
                    '<table class="tables container-table" id="tool_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">',
                        '<tbody id="tool_deps">',
                            '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
                                '<th style="padding-left: 40px;">Name</th>',
                                '<th>Version</th>',
                                '<th>Type</th>',
                            '</tr>',
                            '<\% _.each(tool_dependencies[current_changeset], function(dependency) { \%>',
                                '<tr class="datasetRow tool_dependency_row" style="display: table-row;">',
                                    '<td style="padding-left: 40px;">',
                                    '<\%= dependency.name \%></td>',
                                    '<td><\%= dependency.version \%></td>',
                                    '<td><\%= dependency.type \%></td>',
                                '</tr>',
                            '<\% }); \%>',
                        '</tbody>',
                    '</table>',
                '</div>',
            '<\% } \%>',
            '<\% if (current_metadata.includes_tools_for_display_in_tool_panel) { \%>',
                '<div class="tables container-table" id="tools_toggle">',
                    '<div class="expandLink">',
                        '<a class="toggle_folder" data_target="valid_tools">',
                            'Valid tools &ndash; <em>click the name to preview the tool and use the pop-up menu to inspect all metadata</em>',
                        '</a>',
                    '</div>',
                    '<table class="tables container-table" id="valid_tools" border="0" cellpadding="2" cellspacing="2" width="100%">',
                        '<tbody id="tools_in_repo">',
                            '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
                                '<th style="padding-left: 40px;">Name</th>',
                                '<th>Description</th>',
                                '<th>Version</th>',
                                '<th>Tool Panel Section</th>',
                            '</tr>',
                                '<\% _.each(tools[current_changeset], function(tool) { \%>',
                                    '<tr id="libraryItem" class="tool_row" style="display: table-row;" style="width: 15%">',
                                        '<td style="padding-left: 40px;">',
                                            '<div id="tool" class="menubutton split popup" style="float: left;">',
                                                '<a class="view-info"><\%= tool.name \%></a>',
                                            '</div>',
                                        '</td>',
                                        '<td><\%= tool.description \%></td>',
                                        '<td style="width: 15%"><\%= tool.version \%></td>',
                                        '<td style="width: 35%">',
                                            '<div class="tool_tps_switcher tps_switcher_<\%= tool.clean \%>" id="per_tool_tps_container_<\%= tool.clean \%>">',
                                                '<span id="tps_button_<\%= tool.clean \%>" >',
                                                    '<input class="menubutton show_tool_tps_selector" id="select_tps_button_<\%= tool.clean \%>" data-toolguid="<\%= tool.guid \%>" data-toolname="<\%= tool.clean \%>" type="button" value="Specify panel section" />',
                                                '</span>',
                                            '</div>',
                                        '</td>',
                                    '</tr>',
                                '<\% }); \%>',
                        '</tbody>',
                    '</table>',
                '</div>',
            '<\% } \%>',
        '</div>',
    '</form>',
].join(''));
var tool_dependency_template = _.template([
    '<\% if (has_repository_dependencies) { \%>',
        '<\% _.each(repository_dependencies, function(dependency) { \%>',
            '<\% if (dependency.includes_tool_dependencies) { \%>',
                '<\% dependency.tool_dependency_template = tool_dependency_template \%>',
                '<\%= tool_dependency_template(dependency) \%>',
            '<\% } \%>',
        '<\% }); \%>',
    '<\% } \%>',
].join(''));
repository_dependencies_template = _.template([
    '<div class="tables container-table" id="repository_dependencies_table">',
        '<span class="repository_dependency_row"><p>Repository installation requires the following:</p></span>',
        '<ul id="repository_deps">',
            '<\% if (has_repository_dependencies) { \%>',
                '<\% console.log("dependencies 1"); \%>',
                '<\% _.each(repository_dependencies, function(dependency) { \%>',
                    '<\% dependency.repository_dependency_template = repository_dependency_template; \%>',
                    '<\%= repository_dependency_template(dependency) \%>',
                '<\% }); \%>',
            '<\% } \%>',
        '</ul>',
    '</div>'].join(''));
repository_dependency_template = _.template([
    '<li id="metadata_<\%= id \%>" class="datasetRow repository_dependency_row" style="display: table-row;">',
        'Repository <b><\%= repository.name \%></b> revision <b><\%= changeset_revision \%></b> owned by <b><\%= repository.owner \%></b>',
    '</li>',
    '<\% if (has_repository_dependencies) { \%>',
        '<\% _.each(repository_dependencies, function(dependency) { \%>',
            '<\% dependency.repository_dependency_template = repository_dependency_template; \%>',
            '<ul id="repository_<\%= id \%>">',
                '<\%= repository_dependency_template(dependency) \%>',
            '</ul>',
        '<\% }); \%>',
    '<\% } \%>'
].join(''));
categories_in_shed = _.template([
    '<a href="#">Categories</a>',
    '<div style="clear: both; margin-top: 1em;">',
        '<h2>Repositories by Category</h2>',
        '<table class="grid">',
            '<thead id="grid-table-header">',
                '<tr>',
                    '<th>Name</th>',
                    '<th>Description</th>',
                    '<th>Repositories</th>',
                '</tr>',
            '</thead>',
            '<\% _.each(categories, function(category) { \%>',
                '<tr>',
                    '<td>',
                        '<button class="category-selector" data-categoryid="<\%= category.id \%>" data-shedurl="<\%= shed_url \%>"><\%= category.name \%></button>',
                    '</td>',
                    '<td><\%= category.description \%></td>',
                    '<td><\%= category.repositories \%></td>',
                '</tr>',
            '<\% }); \%>',
        '</table>',
    '</div>'].join(''));
repositories_in_category = _.template([
    '<a href="#">Repositories</a>',
    '<div id="standard-search" style="height: 2em; margin: 1em;">',
        '<span class="ui-widget" >',
            '<input class="search-box-input" id="repository_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />',
        '</span>',
    '</div>',
    '<div style="clear: both; margin-top: 1em;">',
        '<h2>Repositories in <\%= name \%></h2>',
        '<table class="grid">',
            '<thead id="grid-table-header">',
                '<tr>',
                    '<th style="width: 10%;">Owner</th>',
                    '<th style="width: 15%;">Name</th>',
                    '<th>Synopsis</th>',
                    '<th style="width: 10%;">Type</th>',
                    '<th style="width: 5%;">Certified</th>',
                '</tr>',
            '</thead>',
            '<\% _.each(repositories, function(repository) { \%>',
                '<tr>',
                    '<td><\%= repository.owner \%></td>',
                    '<td>',
                        '<button class="repository-selector" data-tsrid="<\%= repository.id \%>"><\%= repository.name \%></button>',
                    '</td>',
                    '<td><\%= repository.description \%></td>',
                    '<td><\%= repository.type \%></td>',
                    '<td><\%= repository.metadata.tools_functionally_correct \%></td>',
                '</tr>',
            '<\% }); \%>',
        '</table>',
    '<div>'].join(''));
tool_sheds_template = _.template([
    '<div class="toolForm">',
        '<div class="toolFormTitle">Accessible Galaxy tool sheds</div>',
        '<div class="toolFormBody">',
            '<div class="form-row">',
                '<table class="grid">',
                    '<\% _.each(tool_sheds, function(shed) { \%>',
                        '<tr class="libraryTitle">',
                            '<td>',
                                '<div style="float: left; margin-left: 1px;" class="menubutton split">',
                                    '<a class="view-info shed-selector" data-shedurl="<\%= shed.url \%>" href="#"><\%= shed.name \%></a>',
                                '</div>',
                            '</td>',
                        '</tr>',
                    '<\% }); \%>',
                '</table>',
            '</div>',
            '<div style="clear: both"></div>',
        '</div>',
    '</div>'].join(''));
show_queue_template = _.template([
    '<li class="nav-tab" role="presentation" id="repository_details" data-toggle="tab"><a href="#">Repository Installation Queue</a></li>'
    ].join(''));
tps_selection_template = _.template([
    '<div class="form-row" id="select_tps">',
        '<select name="<\%= name \%>" id="<\%= id \%>',
            '<\% _.each(sections, function(section) { \%>',
                '<option value="<\%= section.id \%>"><\%= section.name \%>',
            '<\% }); \%>',
        '</select>',
        '<input class="menubutton" type="button" id="create_new" value="Create new" />',
        '<div class="toolParamHelp" style="clear: both;">',
            'Select an existing tool panel section to contain the installed tools (optional).',
        '</div>',
    '</div>'].join(''));
tps_creation_template = _.template([
    '<div class="form-row" id="new_tps">',
        '<input id="new_tool_panel_section" name="new_tool_panel_section" type="textfield" value="" size="40"/>',
        '<input class="menubutton" type="button" id="select_existing" value="Select existing" />',
        '<div class="toolParamHelp" style="clear: both;">',
            'Add a new tool panel section to contain the installed tools (optional).',
        '</div>',
    '</div>'].join(''));
var tps_picker_template = _.template([
    '<span id="tps_button_<\%= tool.clean \%>" >',
        '<input class="menubutton show_tool_tps_selector" id="select_tps_button_<\%= tool.clean \%>" data-toolguid="<\%= tool.guid \%>" type="button" value="Specify panel section" />',
    '</span>',
].join(''));
var select_tps_template = _.template([
    '<div id="select_tps_<\%= tool.clean \%>" class="tps_creator">',
        '<select style="width: 30em;" data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<\%= tool.clean \%>">',
        '</select>',
        '<input id="per_tool_create_<\%= tool.clean \%>" class="menubutton" data-toolguid="<\%= tool.guid \%>" value="Create new" id="create_new_<\%= tool.clean \%>" type="button">',
        '<input id="cancel_<\%= tool.clean \%>" class="menubutton" data-toolguid="<\%= tool.guid \%>" value="Cancel" type="button">',
        '<div style="clear: both;" class="toolParamHelp"></div>',
    '</div>',
].join(''));
var create_tps_template = _.template([
    '<div id="new_tps_<\%= tool.clean \%>" class="form-row">',
        '<input data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" size="40" name="new_tool_panel_section" id="new_tool_panel_section_<\%= tool.clean \%>" type="text">',
        '<input id="per_tool_select_<\%= tool.clean \%>" class="menubutton" data-toolguid="<\%= tool.guid \%>" value="Select existing" id="select_existing_<\%= tool.clean \%>" type="button">',
        '<input id="cancel_<\%= tool.clean \%>" class="menubutton" data-toolguid="<\%= tool.guid \%>" value="Cancel" type="button">',
    '</div>',
].join(''));

function array_contains_dict(array, dict) {
    for (var i in array) {
        needle = array[i];
        var found = true;
        for (var key in dict) {
            if (needle[key] !== dict[key]) {
                found = false;
            }
        }
        if (found) { return true; }
    }
    return false;

}
function process_dependencies(metadata, selector) {
    has_repo_dependencies = false;
    if (metadata.has_repository_dependencies) {
        has_repo_dependencies = true;
        for (var item in metadata.repository_dependencies) {
            var dependency = metadata.repository_dependencies[item];
            if (dependency.has_repository_dependencies) {
                has_repo_dependencies = true;
            }
            var repository = dependency.repository;
            if (repository !== null) {
                template_values = {dependency_id: dependency.id,
                                   name: repository.name,
                                   revision: dependency.changeset_revision,
                                   owner: repository.owner,
                                   prior: ''};
                if (dependency.prior_installation_required) {
                    template_values.prior = ' (<b>Prior installation required</b>)';
                }
                var dependency_html = repository_dependency_template(template_values);
                if (selector === undefined) {
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
            if (item === 'set_environment') {
                for (var i = 0; i < dependency.length; i++) {
                    var tool_dependency = {name: dependency[i].name, version: 'N/A', type: dependency[i].type}
                }
            }
            else {
                var tool_dependency = {name: dependency.name, version: dependency.version, type: dependency.type};
            }
            if (!array_contains_dict(valid_tool_dependencies, tool_dependency)) {
                valid_tool_dependencies.push(tool_dependency);
            }
        }
    }
    if (metadata.includes_tools_for_display_in_tool_panel) {
        $('#tools_toggle').show();
        for (var i = 0; i < metadata.tools.length; i++) {
            var tool = metadata.tools[i];
            valid_tool = {clean_name: tool.clean, name: tool.name, version: tool.version, description: tool.description, guid: tool.guid};
            if (!array_contains_dict(valid_tools, valid_tool) && tool.add_to_tool_panel) {
                valid_tools.push(valid_tool);
            }
        }
    }
    else {
        $('#tools_toggle').hide();
    }
}
function tool_panel_section() {
    var tps_selection = $('#tool_panel_section_select').find("option:selected").text();
    if (tps_selection === 'Create New') {
        $("#new_tool_panel_section").prop('disabled', false);
        $("#new_tps").show();
    }
    else {
        $("#new_tool_panel_section").prop('disabled', true);
        $("#new_tps").hide();
    }
}
function check_if_installed(name, owner, changeset) {
    params = {name: name, owner: owner}
    $.get('${h.url_for(controller='/api/tool_shed_repositories')}', params, function(data) {
        for (var index = 0; index < data.length; index++) {
            var repository = data[index];
            var installed = !repository.deleted && !repository.uninstalled;
            var changeset_match = repository.changeset_revision == changeset ||
                                  repository.installed_changeset_revision == changeset;
            if (repository.name == name && repository.owner == owner && installed && changeset_match) {
                $('#install_repository').prop('disabled', true);
                $('#install_repository').val('This revision is already installed');
            }
            else {
                $('#install_repository').prop('disabled', false);
                $('#install_repository').val('Install this revision');
            }
        }
    });
}
function get_queued_repositories(current_ids = null, processed_ids = null, metadata = null) {
    if (processed_ids === null) {
        processed_ids = Array();
    }
    if (current_ids === null) {
        current_ids = Array();
    }
    if (metadata === null) {
        var changeset = $('#changeset').find("option:selected").text();
        $("#current_changeset").text(changeset);
        var metadata = repository_information.metadata[changeset];
    }
    if (processed_ids.indexOf(metadata.repository.id) === -1) {
        var repo_tuple = Array(metadata.repository.id, metadata.changeset_revision)
        processed_ids.push(metadata.repository.id)
        current_ids.push(repo_tuple)
    }
    if (metadata.has_repository_dependencies) {
        for (var item in metadata.repository_dependencies) {
            var dependency = metadata.repository_dependencies[item];
            var repository = dependency.repository;
            if (processed_ids.indexOf(repository.id) === -1) {
                repo_tuple = Array(repository.id, dependency.changeset_revision)
                current_ids.push(repo_tuple);
                processed_ids.push(repository.id)
            }
            if (dependency.has_repository_dependencies) {
                current_ids = get_queued_repositories(current_ids, processed_ids, dependency);
            }
        }
    }
    return current_ids;
}
function changeset_metadata() {
    var changeset = $('#changeset').find("option:selected").text();
    $("#current_changeset").text(changeset);
    $('#repository_details').empty();
    repository_data.current_changeset = changeset;
    $('#repository_details').append(repository_details_template(repository_data));
    check_if_installed(repository_information.name, repository_information.owner, changeset.split(':')[1]);
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
        if (element_name === 'tool_panel_section_id') {
            tool_panel_section[tool_guid] = { tool_panel_section: $(this).find("option:selected").val(), action: 'append' }
        }
        else {
            tool_panel_section[tool_guid] = { tool_panel_section: $(this).val(), action: 'create' }
        }
    });
    return tool_panel_section;
}
function show_global_tps_select() {
    $('#tool_panel_section').empty();
    $('#tool_panel_section').append(tps_selection_template(repository_data.panel_section_dict));
    $('#create_new').click(show_global_tps_create);
}
function show_global_tps_create() {
    $('#tool_panel_section').empty();
    $('#tool_panel_section').append(tps_creation_template(repository_data.panel_section_dict));
    $('#select_existing').click(show_global_tps_select);
}
function initiate_repository_installation(data) {
    var tsr_ids = data[0];
    var encoded_kwd = data[1];
    $.ajax( {
        type: "POST",
        url: "${h.url_for( controller='admin_toolshed', action='manage_repositories' )}",
        dataType: "html",
        data: { operation: "install", tool_shed_repository_ids: tsr_ids, encoded_kwd: encoded_kwd, reinstalling: false },
        success : function ( data ) {
            console.log( "Initializing repository installation succeeded" );
        },
    });
}
function show_queue() {
    console.log(localStorage.repositories);
}
function check_queue() {
    $('#show_queue').remove();
    if (localStorage.repositories) {
        $('#browse_toolsheds').append(show_queue_template());
    }
    $('#show_queue').click(show_queue);
}
function remove_children(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}
function find_tool_by_guid(tool_guid, changeset) {
    var tools = repository_data.tools[changeset];
    for (var index = 0; index < tools.length; index++) {
        var tool = tools[index];
        if (tool.guid === tool_guid) {
            return tool;
        }
    }
}
function show_panel_button(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(tps_picker_template({tool: tool}));
    $('#select_tps_button_' + tool.clean).click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_selector(tool_guid, changeset);
    });
}
function show_tool_create(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(create_tps_template({tool: tool}));
    $('#per_tool_select_' + tool.clean).click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_select(tool_guid, changeset);
    });
    $('#cancel_' + tool.clean).click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_button(tool_guid, changeset);
    });
}
function show_tool_select(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    console.log({'f': 'show_tool_select', 'tool_guid': tool_guid, 'changeset': changeset});
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(select_tps_template({tool: tool}));
    $('#per_tool_create_' + tool.clean).click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_create(tool_guid, changeset);
    });
    $('#cancel_' + tool.clean).click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_button(tool_guid, changeset);
    });
}
function show_panel_selector(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(select_tps_template({tool: tool}));
    $('#per_tool_create_' + tool.clean).click(function() {
        show_tool_create(tool_guid, changeset);
    });
    $('#cancel_' + tool.clean).click(function() {
        show_panel_button(tool_guid, changeset);
    });
}
function bind_shed_events() {
    $('.category-selector').click(function() {
        $('#browse_toolshed').empty(); // TODO: Remove this when the tabs work. Replace with tab switcher.
        $('#browse_category').empty();
        $('#browse_category').append('<a href="#">Repositories</a><p><img src="/static/images/jstree/throbber.gif" alt="Loading repositories..." /></p>');
        $('#repository_details').attr('data-shedurl', $(this).attr('data-shedurl'));
        category_id = $(this).attr('data-categoryid');
        shed_url = $('#browse_toolshed').attr('data-shedurl');
        api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_category")}'
        $.get(api_url, { tool_shed_url: shed_url, category_id: category_id }, function(data) {
            $('#browse_category').empty();
            $('#browse_category').append(repositories_in_category(data));
            bind_category_events();
        });
    });
}
function bind_category_events() {
    $('.repository-selector').click(function() {
        $('#browse_category').empty(); // TODO: Remove this when the tabs work. Replace with tab switcher.
        console.log('selected repository ' + $(this).attr('data-tsrid'));
        $('#repository_details').empty();
        $('#repository_details').append('<a href="#">Repository</a><p><img src="/static/images/jstree/throbber.gif" alt="Loading repository..." /></p>');
        tsr_id = $(this).attr('data-tsrid');
        shed_url = $('#browse_category').attr('data-shedurl');
        api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_repository")}'
        params = {"tool_shed_url": shed_url, "tsr_id": tsr_id}
        $('#repository_details').attr('data-shedurl', $(this).attr('data-shedurl'));
        $.get(api_url, params, function(data) {
            $('#repository_details').empty();
            data.current_changeset = Object.keys(data.repository.metadata)[0];
            data.repository_dependencies_template = repository_dependencies_template;
            data.repository_dependency_template = repository_dependency_template;
            data.tps_selection_template = tps_selection_template;
            repository_data = data;
            $('#repository_details').append(repository_details_template(data));
            require(["libs/jquery/jstree"], function() {
                $('#repository_deps').jstree();
            });
            bind_repository_events();
        });
        $('#repository_details').attr('data-shedurl', shed_url);
        $('#repository_details').click();
    });
}
function bind_repository_events() {
    $('.show_tool_tps_selector').click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        var tool_guid = $(this).attr('data-toolguid');
        console.log({'f': 'show_tool_tps_selector.click()', 'tool_guid': tool_guid, 'changeset': changeset});
        show_panel_selector(tool_guid, changeset);
    });
    $('#changeset').change(changeset_metadata);
    $('.toggle_folder').click(function() {
        toggle_folder($(this));
    });
    $('#queue_install').click(function() {
        var changeset = $('#changeset').find("option:selected").text();
        $("#current_changeset").text(changeset);
        var repository_metadata = repository_data.metadata[changeset];
        var queue_key = $("#tool_shed_url").val() + ':' + repository_metadata.id + ':' + changeset;
        var queued_repos = new Object();
        if (localStorage.repositories) {
            queued_repos = JSON.parse(localStorage.repositories);
        }
        if (!queued_repos.hasOwnProperty(queue_key)) {
            queued_repos[queue_key] = repository_metadata;
        }
        localStorage.repositories = JSON.stringify(queued_repos);
        console.log(localStorage.repositories);
        check_queue();
    });
    console.log('Binding TPS.');
    $('#create_new').click(show_global_tps_create);
    console.log('Binding submit.');
    $('#repository_installation').submit(function(form) {
        console.log('Installing');
        form.preventDefault();
        var params = {};
        // params.repositories = JSON.stringify(get_queued_repositories());
        params.tool_shed_url = $("#tool_shed_url").val();
        params.install_tool_dependencies = $("#install_tool_dependencies").val();
        params.install_repository_dependencies = $("#install_repository_dependencies").val();
        params.tool_panel_section = JSON.stringify(select_tps(params));
        params.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        params.changeset = $("#changeset").val();
        url = $('#repository_installation').attr('action');
        // $.post(url, params, function(data) {
        //     initiate_repository_installation(JSON.parse(data));
        // });
    });
}

$(function() {
    $('#list_toolsheds').append(tool_sheds_template({tool_sheds: tool_sheds}));
    check_queue();
    $('.shed-selector').click(function() {
        $('#list_toolsheds').empty(); // TODO: Remove this when the tabs work. Replace with tab switcher.
        $('#browse_toolshed').empty();
        $('#browse_toolshed').append('<a href="#">Categories</a><p><img src="/static/images/jstree/throbber.gif" alt="Loading categories..." /></p>');
        $('#browse_category').attr('data-shedurl', $(this).attr('data-shedurl'));
        shed_url = $(this).attr('data-shedurl');
        api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_categories")}'
        $.get(api_url, { tool_shed_url: shed_url }, function(data) {
            $('#browse_toolshed').empty();
            $('#browse_toolshed').append(categories_in_shed(data));
            bind_shed_events();
        });
        $('#browse_toolshed').attr('data-shedurl', shed_url);
    });
});
</script>
<ul class="nav nav-tabs" id="browse_toolsheds">
    <li class="active nav-tab tab_toolsheds" role="presentation" id="list_toolsheds" data-toggle="tab"><a href="#">Toolsheds</a>
    </li>
    <li class="nav-tab tab_categories" role="presentation" id="browse_toolshed" data-toggle="tab"><a href="#">Categories</a>
        <p><img src="/static/images/jstree/throbber.gif" alt="Loading categories..." /></p>
    </li>
    <li class="nav-tab tab_repositories" role="presentation" id="browse_category" data-toggle="tab"><a href="#">Repositories</a>
        <p><img src="/static/images/jstree/throbber.gif" alt="Loading repositories..." /></p>
    </li>
    <li class="nav-tab tab_repository_details" role="presentation" id="repository_details" data-toggle="tab"><a href="#">Repository</a>
        <p><img src="/static/images/jstree/throbber.gif" alt="Loading repository..." /></p>
    </li>
</ul>