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
div.container {
    max-width: 100%;
    width: 100%;
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
repository_queue_tab = _.template([
    '<li class="nav-tab" role="presentation" id="repository_installation_queue">',
        '<a href="#repository_queue" data-toggle="tab">Repository Installation Queue</a>',
    '</li>',
].join(''))
repository_queue_template = _.template([
    '<div class="tab-pane" id="repository_queue">',
        '<table id="queued_repositories" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">',
            '<thead id="grid-table-header">',
                '<tr>',
                    '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="install_all" name="install_all" value="Install all" /></th>',
                    '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="clear_queue" name="clear_queue" value="Clear queue" /></th>',
                    '<th class="datasetRow">ToolShed</th>',
                    '<th class="datasetRow">Name</th>',
                    '<th class="datasetRow">Owner</th>',
                    '<th class="datasetRow">Revision</th>',
                '</tr>',
            '</thead>',
            '<tbody>',
                '<\% _.each(repositories, function(repository) { \%>',
                    '<tr id="queued_repository_<\%= repository.id \%>">',
                        '<td class="datasetRow">',
                            '<input class="btn btn-primary install_one" data-repokey="<\%= repository.queue_key \%>" type="submit" id="install_repository_<\%= repository.id \%>" name="install_repository" value="Install now" />',
                        '</td>',
                        '<td class="datasetRow">',
                            '<input class="btn btn-primary remove_one" data-repokey="<\%= repository.queue_key \%>" type="submit" id="unqueue_repository_<\%= repository.id \%>" name="unqueue_repository" value="Remove from queue" />',
                        '</td>',
                        '<td class="datasetRow"><\%= repository.tool_shed_url \%></td>',
                        '<td class="datasetRow"><\%= repository.name \%></td>',
                        '<td class="datasetRow"><\%= repository.owner \%></td>',
                        '<td class="datasetRow"><\%= repository.changeset \%></td>',
                    '</tr>',
                '<\% }); \%>',
            '</tbody>',
        '</table>',
    '</div>',
].join(''));
repository_details_template = _.template([
    '<div class="tab-pane" id="repository_details">',
        '<h2 style="font-weight: normal;">Repository information for <strong><\%= repository.name \%></strong> from <strong><\%= repository.owner \%></strong></h2>',
        '<form id="repository_installation" name="install_repository" method="post" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">',
            '<input type="hidden" id="repositories" name="<\%= current_metadata.repository.id \%>" value="ID" />',
            '<input type="hidden" id="tool_shed_url" name="tool_shed_url" value="<\%= tool_shed_url \%>" />',
            '<div class="toolForm">',
                '<div class="toolFormTitle">Changeset</div>',
                '<div class="toolFormBody changeset">',
                    '<select id="changeset" name="changeset">',
                        '<\% _.each(Object.keys(repository.metadata), function(changeset) { \%>',
                            '<\% if (changeset == current_changeset) { var selected = "selected "; } else { var selected = ""; } \%>',
                            '<option <\%= selected \%>data-changeset="<\%= changeset \%>" value="<\%= changeset.split(":")[1] \%>"><\%= changeset \%></option>',
                        '<\% }); \%>',
                    '</select>',
                    '<input class="btn btn-primary" data-tsrid="<\%= current_metadata.repository.id \%>" type="submit" id="install_repository" name="install_repository" value="Install this revision now" />',
                    '<input class="btn btn-primary" type="button" id="queue_install" name="queue_install" value="Install this revision later" />',
                    '<div class="toolParamHelp" style="clear: both;">Please select a revision and review the settings below before installing.</div>',
                '</div>',
                '<div class="toolParamHelp" style="clear: both;">',
                'Please select a revision and review the settings below before installing.',
                '</div>',
            '</div>',
            '<\%= shed_tool_conf \%>',
            '<\%= tool_panel_section \%>',
            '<div class="toolFormTitle">Contents of this repository at revision <strong id="current_changeset"><\%= current_changeset \%></strong></div>',
            '<div class="toolFormBody">',
                '<\% if (current_metadata.has_repository_dependencies) { \%>',
                    '<p id="install_repository_dependencies_checkbox">',
                        '<input type="checkbox" checked id="install_repository_dependencies" />',
                        '<label for="install_repository_dependencies">Install repository dependencies</label>',
                    '</p>',
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
                    '<p id="install_resolver_dependencies_checkbox">',
                        '<input type="checkbox" checked id="install_resolver_dependencies" />',
                        '<label for="install_resolver_dependencies">Install resolver dependencies</label>',
                    '</p>',
                    '<p id="install_tool_dependencies_checkbox">',
                        '<input type="checkbox" checked id="install_tool_dependencies" />',
                        '<label for="install_tool_dependencies">Install tool dependencies</label>',
                    '</p>',
                    '<div class="tables container-table" id="tool_dependencies">',
                        '<div class="expandLink">',
                            '<a class="toggle_folder" data_target="tool_dependencies_table">',
                                'Tool dependencies &ndash; <em>repository tools require handling of these dependencies</em>',
                            '</a>',
                        '</div>',
                        '<table class="tables container-table" id="tool_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">',
                            '<thead>',
                                '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
                                    '<th style="padding-left: 40px;">Name</th>',
                                    '<th>Version</th>',
                                    '<th>Type</th>',
                                '</tr>',
                            '</thead>',
                            '<tbody id="tool_deps">',
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
                            '<thead>',
                                '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
                                    '<th style="padding-left: 40px;">Name</th>',
                                    '<th>Description</th>',
                                    '<th>Version</th>',
                                    '<th>Tool Panel Section</th>',
                                '</tr>',
                            '</thead>',
                            '<tbody id="tools_in_repo">',
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
                                                        '<input class="btn btn-primary show_tool_tps_selector" id="select_tps_button_<\%= tool.clean \%>" data-toolguid="<\%= tool.guid \%>" data-toolname="<\%= tool.clean \%>" type="button" value="Specify panel section" />',
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
    '</div>',
].join(''));
shed_tool_conf = _.template([
    '<div class="toolFormTitle">Shed tool configuration file:</div>',
    '<div class="toolFormBody">',
    '<div class="form-row">',
        '<\%= stc_html \%>',
        '<div class="toolParamHelp" style="clear: both;">Select the file whose <b>tool_path</b> setting you want used for installing repositories.</div>',
    '</div>',
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
            '<li id="repository_<\%= id \%>_deps">',
                '<\%= repository_dependency_template(dependency) \%>',
            '</li>',
        '<\% }); \%>',
    '<\% } \%>'
].join(''));
categories_in_shed = _.template([
    '<div class="tab-pane" id="list_categories">',
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
                            '<button class="category-selector" data-categoryid="<\%= category.id \%>"><\%= category.name \%></button>',
                        '</td>',
                        '<td><\%= category.description \%></td>',
                        '<td><\%= category.repositories \%></td>',
                    '</tr>',
                '<\% }); \%>',
            '</table>',
        '</div>',
    '</div>',
].join(''));
repositories_in_category = _.template([
    '<div class="tab-pane" id="list_repositories">',
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
        '</div>',
    '</div>',
].join(''));
tool_sheds_template = _.template([
    '<div class="tab-pane" id="list_toolsheds">',
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
    '</div>',
].join(''));
tps_selection_template = _.template([
    '<div class="tab-pane" id="select_tps">',
        '<select name="<\%= name \%>" id="<\%= id \%>',
            '<\% _.each(sections, function(section) { \%>',
                '<option value="<\%= section.id \%>"><\%= section.name \%>',
            '<\% }); \%>',
        '</select>',
        '<input class="btn btn-primary" type="button" id="create_new" value="Create new" />',
        '<div class="toolParamHelp" style="clear: both;">',
            'Select an existing tool panel section to contain the installed tools (optional).',
        '</div>',
    '</div>'].join(''));
tps_creation_template = _.template([
    '<div class="form-row" id="new_tps">',
        '<input id="new_tool_panel_section" name="new_tool_panel_section" type="textfield" value="" size="40"/>',
        '<input class="btn btn-primary" type="button" id="select_existing" value="Select existing" />',
        '<div class="toolParamHelp" style="clear: both;">',
            'Add a new tool panel section to contain the installed tools (optional).',
        '</div>',
    '</div>'].join(''));
var tps_picker_template = _.template([
    '<span id="tps_button_<\%= tool.clean \%>" >',
        '<input class="btn btn-primary show_tool_tps_selector" id="select_tps_button_<\%= tool.clean \%>" data-toolguid="<\%= tool.guid \%>" type="button" value="Specify panel section" />',
    '</span>',
].join(''));
var select_tps_template = _.template([
    '<div id="select_tps_<\%= tool.clean \%>" class="tps_creator">',
        '<select style="width: 30em;" data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<\%= tool.clean \%>">',
        '</select>',
        '<input id="per_tool_create_<\%= tool.clean \%>" class="btn btn-primary" data-toolguid="<\%= tool.guid \%>" value="Create new" id="create_new_<\%= tool.clean \%>" type="button">',
        '<input id="cancel_<\%= tool.clean \%>" class="btn btn-primary" data-toolguid="<\%= tool.guid \%>" value="Cancel" type="button">',
        '<div style="clear: both;" class="toolParamHelp"></div>',
    '</div>',
].join(''));
var create_tps_template = _.template([
    '<div id="new_tps_<\%= tool.clean \%>" class="form-row">',
        '<input data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" size="40" name="new_tool_panel_section" id="new_tool_panel_section_<\%= tool.clean \%>" type="text">',
        '<input id="per_tool_select_<\%= tool.clean \%>" class="btn btn-primary" data-toolguid="<\%= tool.guid \%>" value="Select existing" id="select_existing_<\%= tool.clean \%>" type="button">',
        '<input id="cancel_<\%= tool.clean \%>" class="btn btn-primary" data-toolguid="<\%= tool.guid \%>" value="Cancel" type="button">',
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
function bind_category_events() {
    $('.repository-selector').click(function() {
        $('#repository_details').replaceWith('<div class="tab-pane" id="repository_details"><p><img src="/static/images/jstree/throbber.gif" alt="Loading repository..." /></p></div>');
        tsr_id = $(this).attr('data-tsrid');
        shed_url = $('#tab_contents').attr('data-shedurl');
        api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_repository")}'
        params = {"tool_shed_url": shed_url, "tsr_id": tsr_id}
        $.get(api_url, params, function(data) {
            var changesets = Object.keys(data.repository.metadata);
            data.tool_shed_url = shed_url;
            data.current_changeset = changesets[changesets.length - 1];
            data.current_metadata = data.repository.metadata[data.current_changeset];
            data.repository_dependencies_template = repository_dependencies_template;
            data.repository_dependency_template = repository_dependency_template;
            data.tps_selection_template = tps_selection_template;
            repository_data = data;
            repository_data.shed_tool_conf = shed_tool_conf({'stc_html': repository_data.shed_conf});
            repository_data.tool_panel_section = '';
            if (repository_data.repository.metadata[data.current_changeset].includes_tools_for_display_in_tool_panel) {
                repository_data.tool_panel_section = tps_selection_template(repository_data.panel_section_dict)
            }
            $('#repository_details').replaceWith(repository_details_template(data));
            $('#repo_info_tab').click();
            require(["libs/jquery/jstree"], function() {
                $('#repository_deps').jstree();
            });
            $('#repository_installation').ready(function() {
                bind_repository_events();
            });
        });
        $('#repository_contents').click();
    });
}
function bind_repository_events() {
    var current_changeset = get_current_changeset();
    var current_metadata = repository_data.repository.metadata[current_changeset];
    $('.show_tool_tps_selector').click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_selector(tool_guid, changeset);
    });
    $('#changeset').change(changeset_metadata);
    $('.toggle_folder').click(function() {
        toggle_folder($(this));
    });
    $('#queue_install').click(function() {
        var changeset = get_current_changeset();
        var repository_metadata = repository_data.current_metadata;
        repository_metadata.install_tool_dependencies = $("#install_tool_dependencies").val();
        repository_metadata.install_repository_dependencies = $("#install_repository_dependencies").val();
        repository_metadata.install_resolver_dependencies = $("#install_resolver_dependencies").val();
        repository_metadata.tool_panel_section = JSON.stringify(select_tps({}));
        repository_metadata.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        var queue_key = get_queue_key(repository_metadata, changeset);
        var queued_repos = new Object();
        if (localStorage.repositories) {
            queued_repos = get_repository_queue();
        }
        if (!queued_repos.hasOwnProperty(queue_key)) {
            queued_repos[queue_key] = repository_metadata;
        }
        save_repository_queue(queued_repos);
        check_if_installed(repository_metadata.repository.name, repository_metadata.repository.owner, current_changeset.split(':')[1]);
        check_queue();
    });
    $('#create_new').click(show_global_tps_create);
    $('#install_repository').click(function() {
        var form = $('#repository_installation');
        var params = {};
        params.repositories = JSON.stringify([[$('#install_repository').attr('data-tsrid'), $('#changeset').find("option:selected").val()]]);
        params.tool_shed_repository_ids = JSON.stringify([$('#install_repository').attr('data-tsrid')]);
        params.tool_shed_url = $('#tab_contents').attr('data-shedurl');
        params.install_tool_dependencies = $("#install_tool_dependencies").val();
        params.install_repository_dependencies = $("#install_repository_dependencies").val();
        params.install_resolver_dependencies = $("#install_resolver_dependencies").val();
        params.tool_panel_section = JSON.stringify(select_tps(params));
        params.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        params.changeset = $('#changeset').find("option:selected").val();
        url = $('#repository_installation').attr('action');
        prepare_installation(params, url);
    });
    check_if_installed(current_metadata.repository.name, current_metadata.repository.owner, current_changeset.split(':')[1]);
}
function bind_shed_events() {
    $('.category-selector').click(function() {
        var tabsw = $('#category_list_tab');
        $('#list_repositories').replaceWith('<div id="list_repositories" class="tab-pane"><img src="/static/images/jstree/throbber.gif" alt="Loading repositories..." /></div>');
        var category_id = $(this).attr('data-categoryid');
        var shed_url = $('#tab_contents').attr('data-shedurl');
        var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_category")}'
        var params = {'tool_shed_url': shed_url, 'category_id': category_id};
        $.get(api_url, params, function(data) {
            $('#list_repositories').replaceWith(repositories_in_category(data));
            $('#repo_list_tab').click();
            bind_category_events();
        });
    });
}
function changeset_metadata() {
    repository_data.current_changeset = get_current_changeset();
    repository_data.current_metadata = repository_data.repository.metadata[changeset];
    repository_information = repository_data.repository;
    $('#repository_details').replaceWith(repository_details_template(repository_data));
    check_if_installed(repository_information.name, repository_information.owner, changeset.split(':')[1]);
    bind_repository_events();
}
function check_if_installed(name, owner, changeset) {
    params = {name: name, owner: owner}
    var already_installed = false;
    var queued = repository_in_queue();
    $.get('${h.url_for(controller='/api/tool_shed_repositories')}', params, function(data) {
        for (var index = 0; index < data.length; index++) {
            var repository = data[index];
            var installed = !repository.deleted && !repository.uninstalled;
            var changeset_match = repository.changeset_revision == changeset ||
                                  repository.installed_changeset_revision == changeset;
            if (repository.name == name && repository.owner == owner && installed && changeset_match) {
                already_installed = true;
            }
            if (already_installed && !repository_in_queue()) {
                $('#install_repository').prop('disabled', true);
                $('#install_repository').val('This revision is already installed');
                $('#queue_install').prop('disabled', true);
                $('#queue_install').val('This revision is already installed');
            }
            else {
                $('#install_repository').prop('disabled', false);
                $('#install_repository').val('Install this revision');
                $('#queue_install').prop('disabled', false);
                $('#queue_install').val('Install this revision later');
            }
        }
    });
    if (repository_in_queue() && !already_installed) {
        $('#queue_install').prop('disabled', true);
        $('#queue_install').val('This revision has been queued');
    }
    else {
        $('#queue_install').prop('disabled', false);
        $('#queue_install').val('Install this revision later');
    }
}
function check_queue() {
    if (localStorage.hasOwnProperty('repositories')) {
        repository_queue = JSON.parse(localStorage.repositories);
        queue_keys = Object.keys(repository_queue);
        queue = Array();
        for (var i = 0; i < queue_keys.length; i++) {
            queue_key = queue_keys[i];
            repository_metadata = repository_queue[queue_key];
            repository = repository_metadata.repository;
            key_parts = queue_key.split('|');
            tool_shed_url = key_parts[0];
            repository.queue_key = queue_key;
            repository.changeset = repository_metadata.changeset_revision;
            repository.tool_shed_url = tool_shed_url;
            queue.push(repository);
        }
        $('#repository_queue').replaceWith(repository_queue_template({'repositories': queue}));
        $('.install_one').click(function() {
            var repository_metadata = get_repository_from_queue($(this).attr('data-repokey'));
            install_from_queue(repository_metadata, $(this).attr('data-repokey'));
        });
        $('.remove_one').click(function(){
            queue_key = $(this).attr('data-repokey');
            repository_metadata = get_repository_from_queue(queue_key);
            repository_id = repository_metadata.repository.id;
            selector = "#queued_repository_" + repository_id;
            $(selector).remove();
            remove_from_queue(undefined, undefined, queue_key);
        });
        $('#clear_queue').click(function() {
            localStorage.removeItem('repositories');
        });
        $('#install_all').click(process_queue);
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
function get_current_changeset() {
    return $('#changeset').find("option:selected").text();
}
function get_queue_key(repository_metadata, changeset, shed_url = undefined) {
    if (shed_url === undefined) {
        shed_url = $("#tab_contents").attr('data-shedurl');
    }
    return shed_url + '|' + repository_metadata.id + '|' + changeset;
}
function get_queued_repositories(current_ids = null, processed_ids = null, metadata = null) {
    if (processed_ids === null) {
        processed_ids = Array();
    }
    if (current_ids === null) {
        current_ids = Array();
    }
    if (metadata === null) {
        var changeset = get_current_changeset();
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
function get_repository_queue() {
    return JSON.parse(localStorage.repositories);
}
function get_repository_from_queue(queue_key) {
    repository_queue = get_repository_queue();
    if (repository_queue.hasOwnProperty(queue_key)) {
        return repository_queue[queue_key];
    }
    return undefined;
}
function install_repository(data) {
    var params = data;
    $.post("${h.url_for( controller='admin_toolshed', action='manage_repositories' )}", params, function(data) {
        console.log( "Initializing repository installation succeeded" );
        window.location.assign('${h.url_for(controller='admin_toolshed', action='monitor_repository_installation')}');
    })
}
function install_from_queue(repository_metadata, queue_key) {
    var params = Object();
    params.install_tool_dependencies = repository_metadata.install_tool_dependencies;
    params.install_repository_dependencies = repository_metadata.install_repository_dependencies;
    params.install_resolver_dependencies = repository_metadata.install_resolver_dependencies;
    params.tool_panel_section = repository_metadata.tool_panel_section;
    params.shed_tool_conf = repository_metadata.shed_tool_conf;
    params.repositories = JSON.stringify([[repository_metadata.repository.id, repository_metadata.changeset_revision]]);
    params.tool_shed_repository_ids = JSON.stringify([repository_metadata.repository.id]);
    params.tool_shed_url = queue_key.split('|')[0];
    params.changeset = repository_metadata.changeset_revision;
    var url = '${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}';
    $('#queued_repository_' + repository_metadata.repository.id).remove();
    remove_from_queue(undefined, undefined, queue_key);
    prepare_installation(params, url);
}
function prepare_installation(params, api_url) {
    $.post(api_url, params, function(data) {
        iri_parameters = JSON.parse(data);
        install_repository(iri_parameters);
    });
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
function process_queue() {
    if (!localStorage.repositories) {
        return;
    }
    var toolsheds = Array();
    var queue = Object();
    var queued_repositories = get_repository_queue();
    var queue_keys = Object.keys(queued_repositories);
    for (var i = 0; i < queue_keys.length; i++) {
        queue_key = queue_keys[i];
        toolshed = queue_key.split('|')[0];
        if (toolsheds.indexOf(toolshed) === -1) {
            toolsheds.push(toolshed);
            queue[toolshed] = Array();
        }
        repository_metadata = queued_repositories[queue_key]
        repository_metadata.queue_key = queue_key
        queue[toolshed].push(repository_metadata);
    }
    for (i = 0; i < toolsheds.length; i++) {
        for (var j = 0; j < queue[toolsheds[i]].length; j++) {
            repository = queue[toolsheds[i]][j];
            install_from_queue(repository, repository.queue_key);
        }
    }
}
function remove_from_queue(repository_metadata, changeset, queue_key=undefined) {
    if (!localStorage.repositories) {
        return;
    }
    if (queue_key === undefined) {
        queue_key = get_queue_key(repository_metadata, changeset);
    }
    repository_queue = get_repository_queue();
    if (repository_queue.hasOwnProperty(queue_key)) {
        delete repository_queue[queue_key];
        save_repository_queue(repository_queue);
    }
}
function repository_in_queue() {
    if (!localStorage.repositories) {
        return;
    }
    repository_queue = get_repository_queue();
    changeset = get_current_changeset();
    var repository_metadata = repository_data.current_metadata;
    var queue_key = get_queue_key(repository_metadata, changeset);
    if (localStorage.repositories) {
        queued_repos = get_repository_queue();
    }
    if (queued_repos.hasOwnProperty(queue_key)) {
        return true;
    }
    return false;
}
function save_repository_queue(repository_queue) {
    localStorage.repositories = JSON.stringify(repository_queue);
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
function show_panel_button(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(tps_picker_template({tool: tool}));
    $('#select_tps_button_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_selector(tool_guid, changeset);
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
function show_tool_create(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(create_tps_template({tool: tool}));
    $('#per_tool_select_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_select(tool_guid, changeset);
    });
    $('#cancel_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_button(tool_guid, changeset);
    });
}
function show_tool_select(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(select_tps_template({tool: tool}));
    $('#per_tool_create_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_create(tool_guid, changeset);
    });
    $('#cancel_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_panel_button(tool_guid, changeset);
    });
}
function toggle_folder(folder) {
    target_selector = '#' + folder.attr('data_target');
    $(target_selector).toggle();
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
$(document).ready(function() {
    $('#list_toolsheds').replaceWith(tool_sheds_template({tool_sheds: tool_sheds}));
    $('#shed_list_tab').click();
    check_queue();
    $('.shed-selector').click(function() {
        $('#list_categories').replaceWith('<div id="list_categories" class="nav-tab"><img src="/static/images/jstree/throbber.gif" alt="Loading categories..." /></div>');
        shed_url = $(this).attr('data-shedurl');
        $('#tab_contents').attr('data-shedurl', shed_url);
        api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_categories")}'
        $.get(api_url, { tool_shed_url: shed_url }, function(data) {
            $('#list_categories').replaceWith(categories_in_shed(data));
            $('#category_list_tab').click();
            bind_shed_events();
        });
    });
});
</script>
<div class="container" role="navigation">
    <ul class="nav nav-tabs" id="browse_toolsheds">
        <li class="nav-tab tab_toolsheds" role="presentation" id="toolshed_list">
            <a id="shed_list_tab" href="#list_toolsheds" data-toggle="tab">Toolsheds</a>
        </li>
        <li class="nav-tab tab_categories" role="presentation" id="category_list">
            <a id="category_list_tab" href="#list_categories" data-toggle="tab">Categories</a>
        </li>
        <li class="nav-tab tab_repositories" role="presentation" id="repository_list">
            <a id="repo_list_tab" href="#list_repositories" data-toggle="tab">Repositories</a>
        </li>
        <li class="nav-tab tab_repository_details" role="presentation" id="repository_contents">
            <a id="repo_info_tab" href="#repository_details" data-toggle="tab">Repository</a>
        </li>
        <li class="nav-tab" role="presentation" id="repository_installation_queue">
            <a href="#repository_queue" data-toggle="tab">Repository Installation Queue</a>
        </li>
    </ul>
    <div id="tab_contents" class="tab-content clearfix">
        <div class="tab-pane active" id="list_toolsheds">Loading...</div>
        <div class="tab-pane" id="list_categories">Select a toolshed in the previous tab to see a list of its categories.</div>
        <div class="tab-pane" id="list_repositories">Select a category in the previous tab to see a list of its repositories.</div>
        <div class="tab-pane" id="repository_details">Select a repository in the previous tab.</div>
        <div class="tab-pane" id="repository_queue">There are no repositories queued for installation.</div>
    </div>
</div>
