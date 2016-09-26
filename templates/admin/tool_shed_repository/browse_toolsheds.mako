<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
<style type="text/css">
.modal-dialog {
    width: 70%;
}
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
#queue_install {
    margin: 5px;
}
.container-table {
    padding-top: 1em;
}
ul.jstree-container-ul {
    margin-top: 1em;
}
ul.workflow_tools, ul.workflow_names {
    padding-left: 0px;
    list-style-type: none
}
</style>
</%def>
<%def name="javascripts()">
    ${parent.javascripts()}
</%def>
<link rel="stylesheet" href="http://code.jquery.com/ui/1.12.0/themes/base/jquery-ui.css">
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
var tool_sheds = ${tool_sheds};
categories_in_shed = _.template([
    '<div class="tab-pane" id="list_categories">',
        '<div id="standard-search" style="height: 2em; margin: 1em;">',
            '<span class="ui-widget" >',
                '<input class="search-box-input" id="repository_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />',
            '</span>',
        '</div>',
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
repository_details_template = _.template([
    '<div class="tab-pane" id="repository_details" data-shedurl="<\%= tool_shed_url \%>" data-tsrid="<\%= current_metadata.repository.id \%>">',
        '<h2 style="font-weight: normal;">Repository information for <strong><\%= repository.name \%></strong> from <strong><\%= repository.owner \%></strong></h2>',
        '<form id="repository_installation" name="install_repository" method="post" action="${h.url_for(controller='/api/tool_shed_repositories', action='install', async=True)}">',
            '<input type="hidden" id="repositories" name="<\%= current_metadata.repository.id \%>" value="ID" />',
            '<input type="hidden" id="tool_shed_url" name="tool_shed_url" value="<\%= tool_shed_url \%>" />',
            '<div class="toolForm">',
                '<div class="toolFormTitle">Changeset</div>',
                '<div class="toolFormBody changeset">',
                    '<select id="changeset" name="changeset" style="margin: 5px;">',
                        '<\% _.each(Object.keys(repository.metadata), function(changeset) { \%>',
                            '<\% if (changeset == current_changeset) { var selected = "selected "; } else { var selected = ""; } \%>',
                            '<option <\%= selected \%>data-changeset="<\%= changeset \%>" value="<\%= changeset.split(":")[1] \%>"><\%= changeset \%></option>',
                        '<\% }); \%>',
                    '</select>',
                    '<input class="btn btn-primary preview-button" data-tsrid="<\%= current_metadata.repository.id \%>" type="submit" id="install_repository" name="install_repository" value="Install this revision now" />',
                    '<input class="btn btn-primary preview-button" type="button" id="queue_install" name="queue_install" value="Install this revision later" />',
                    '<div class="toolParamHelp" style="clear: both;">Please select a revision and review the settings below before installing.</div>',
                '</div>',
            '</div>',
            '<\%= shed_tool_conf \%>',
            '<div class="toolFormTitle">Dependencies of this repository at revision <strong id="current_changeset"><\%= current_changeset \%></strong></div>',
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
                                    '<th><\%= tps_template_global_select({tps: panel_section_dict}) \%></tr>',
                            '</thead>',
                            '<tbody id="tools_in_repo">',
                                    '<\% _.each(tools[current_changeset], function(tool) { \%>',
                                        '<tr id="libraryItem-<\%= tool.clean \%>" class="tool_row" style="display: table-row;" style="width: 15%">',
                                            '<td style="padding-left: 40px;">',
                                                '<div id="tool-<\%= tool.clean \%>" class="menubutton split popup" style="float: left;">',
                                                    '<a class="tool_form view-info" data-toggle="modal" data-target="toolform_<\%= tool.clean \%>" data-clean="<\%= tool.clean \%>" data-guid="<\%= tool.guid \%>" data-name="<\%= tool.name \%>" data-desc="<\%= tool.description \%>"><\%= tool.name \%></a>',
                                                '</div>',
                                            '</td>',
                                            '<td><\%= tool.description \%></td>',
                                            '<td style="width: 15%"><\%= tool.version \%></td>',
                                            '<td style="width: 35%" id="tool_tps_<\%= tool.clean \%>">',
                                                '<\%= tps_template_tool_select({tool: tool, tps: panel_section_dict}) \%>',
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
        '<input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />',
    '</div>',
].join(''));
repositories_in_category = _.template([
    '<div class="tab-pane" id="list_repositories">',
        '<div id="standard-search" style="height: 2em; margin: 1em;">',
            '<span class="ui-widget" >',
                '<input class="search-box-input" id="category_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />',
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
shed_tool_conf = _.template([
    '<div class="toolFormTitle">Shed tool configuration file:</div>',
    '<div class="toolFormBody">',
    '<div class="form-row">',
        '<\%= stc_html \%>',
        '<div class="toolParamHelp" style="clear: both;">Select the file whose <b>tool_path</b> setting you want used for installing repositories.</div>',
    '</div>',
].join(''));
tool_dependency_template = _.template([
    '<\% if (has_repository_dependencies) { \%>',
        '<\% _.each(repository_dependencies, function(dependency) { \%>',
            '<\% if (dependency.includes_tool_dependencies) { \%>',
                '<\% dependency.tool_dependency_template = tool_dependency_template \%>',
                '<\%= tool_dependency_template(dependency) \%>',
            '<\% } \%>',
        '<\% }); \%>',
    '<\% } \%>',
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
tps_template_global_create = _.template([
    '<div id="tool_panel_section">',
        '<div class="toolFormTitle">Tool Panel Section</div>',
        '<div class="toolFormBody">',
            '<div class="form-row" id="new_tps">',
                '<input id="new_tool_panel_section" name="new_tool_panel_section" type="textfield" value="" size="40"/>',
                '<input class="btn btn-primary" type="button" id="select_existing" value="Select existing" />',
                '<div class="toolParamHelp" style="clear: both;">',
                    'Add a new tool panel section to contain the installed tools (optional).',
                '</div>',
            '</div>',
        '</div>',
    '</div>',
].join(''));
tps_template_global_select = _.template([
    '<div id="tool_panel_section">',
        '<div class="toolFormTitle">Tool Panel Section</div>',
        '<div class="toolFormBody">',
            '<div class="tab-pane" id="select_tps">',
                '<select name="<\%= name \%>" id="<\%= tps.id \%>">',
                    '<\%= tps_select_options({sections: tps.sections}) \%>',
                '</select>',
                '<input class="btn btn-primary" type="button" id="create_new" value="Create new" />',
                '<div class="toolParamHelp" style="clear: both;">',
                    'Select an existing tool panel section to contain the installed tools (optional).',
                '</div>',
            '</div>',
        '</div>',
    '</div>',
].join(''));
tps_template_tool_create = _.template([
    '<div id="new_tps_<\%= tool.clean \%>" data-clean="<\%= tool.clean \%>" class="form-row">',
        '<input data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" size="40" name="new_tool_panel_section" id="new_tool_panel_section_<\%= tool.clean \%>" type="text">',
        '<input id="per_tool_select_<\%= tool.clean \%>" class="btn btn-primary" data-toolguid="<\%= tool.guid \%>" value="Select existing" id="select_existing_<\%= tool.clean \%>" type="button">',
    '</div>',
].join(''));
tps_template_tool_select = _.template([
    '<div id="select_tps_<\%= tool.clean \%>" data-clean="<\%= tool.clean \%>" class="tps_creator">',
        '<select default="active" style="width: 30em;" data-toolguid="<\%= tool.guid \%>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<\%= tool.clean \%>">',
            '<\%= tps_select_options({sections: tps.sections}) \%>',
        '</select>',
        '<input id="per_tool_create_<\%= tool.clean \%>" data-clean="<\%= tool.clean \%>" class="btn btn-primary create-tps-button" data-toolguid="<\%= tool.guid \%>" value="Create new" id="create_new_<\%= tool.clean \%>" type="button">',
        '<div style="clear: both;" class="toolParamHelp"></div>',
    '</div>',
].join(''));
tps_select_options = _.template([
    '<\% _.each(sections, function(section) { \%>',
        '<option value="<\%= section.id \%>"><\%= section.name \%></option>',
    '<\% }); \%>',
].join(''));
workflows_missing_tools = _.template([
    '<table id="workflows_missing_tools" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">',
        '<thead id="grid-table-header">',
            '<tr>',
                '<th class="datasetRow">Workflows</th>',
                '<th class="datasetRow">Tool IDs</th>',
                '<th class="datasetRow">Shed</th>',
                '<th class="datasetRow">Name</th>',
                '<th class="datasetRow">Owner</th>',
                '<th class="datasetRow">Actions</th>',
            '</tr>',
        '</thead>',
        '<tbody>',
            '<\% _.each(Object.keys(workflows), function(workflow_key) { \%>',
                '<\% var workflow_details = workflow_key.split("/"); \%>',
                '<\% var workflow = workflows[workflow_key]; \%>',
                '<tr>',
                    '<td class="datasetRow">',
                        '<ul class="workflow_names">',
                            '<\% _.each(workflow.workflows.sort(), function(wf) { \%>',
                                '<li class="workflow_names"><\%= wf \%></li>',
                            '<\% }); \%>',
                        '</ul>',
                    '</td>',
                    '<td class="datasetRow">',
                        '<ul class="workflow_tools">',
                            '<\% _.each(workflow.tools.sort(), function(tool) { \%>',
                                '<li class="workflow_tools"><\%= tool \%></li>',
                            '<\% }); \%>',
                        '</ul>',
                    '</td>',
                    '<td class="datasetRow"><\%= workflow_details[0] \%></td>',
                    '<td class="datasetRow"><\%= workflow_details[2] \%></td>',
                    '<td class="datasetRow"><\%= workflow_details[1] \%></td>',
                    '<td class="datasetRow">',
                        '<ul class="workflow_tools">',
                            '<li class="workflow_tools"><input type="button" class="show_wf_repo btn btn-primary" data-shed="<\%= workflow_details[0] \%>" data-owner="<\%= workflow_details[1] \%>" data-repo="<\%= workflow_details[2] \%>" data-toolids="<\%= workflow.tools.join(",") \%>" value="Preview" /></li>',
                            '<li><input type="button" class="queue_wf_repo btn btn-primary" data-shed="<\%= workflow_details[0] \%>" data-owner="<\%= workflow_details[1] \%>" data-repo="<\%= workflow_details[2] \%>" data-toolids="<\%= workflow.tools.join(",") \%>" value="Add to queue" /></li>',
                        '</ul>',
                    '</td>',
                '</tr>',
            '<\% }); \%>',
        '</ul>',
    '</div>',
].join(''));

function bind_category_events() {
    $('.repository-selector').click(function() {
        $('#repository_details').replaceWith('<div class="tab-pane" id="repository_details"><p><img src="/static/images/jstree/throbber.gif" alt="Loading repository..." /></p></div>');
        tsr_id = $(this).attr('data-tsrid');
        shed_url = $('#tab_contents').attr('data-shedurl');
        load_repository(shed_url, tsr_id);
    });
    setup_repo_search('#category_search');
}
function bind_repository_events() {
    var current_changeset = get_current_changeset();
    var current_metadata = repository_data.repository.metadata[current_changeset];
    bind_tps_propagation();
    $('.create-tps-button').click(function() {
        var changeset = get_current_changeset();
        var guid = $(this).attr('data-toolguid');
        show_tool_tps_create(guid, changeset);
    });
    $('#changeset').change(changeset_metadata);
    $('.toggle_folder').click(function() {
        toggle_folder($(this));
    });
    $('#queue_install').click(function() {
        var changeset = get_current_changeset();
        var repository_metadata = current_metadata;
        repository_metadata.install_tool_dependencies = $("#install_tool_dependencies").val();
        repository_metadata.install_repository_dependencies = $("#install_repository_dependencies").val();
        repository_metadata.install_resolver_dependencies = $("#install_resolver_dependencies").val();
        repository_metadata.tool_panel_section = JSON.stringify(select_tps({}));
        repository_metadata.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        repository_metadata.tool_shed_url = $("#repository_details").attr('data-shedurl');
        var queue_key = get_queue_key(repository_metadata);
        var queued_repos = new Object();
        if (localStorage.repositories) {
            queued_repos = get_repository_queue();
        }
        if (!queued_repos.hasOwnProperty(queue_key)) {
            queued_repos[queue_key] = repository_metadata;
        }
        save_repository_queue(queued_repos);
        check_if_installed(repository_metadata);
        check_queue();
    });
    $('#create_new').click(show_global_tps_create);
    $('#install_repository').click(function() {
        var form = $('#repository_installation');
        var params = {};
        params.repositories = JSON.stringify([[$('#install_repository').attr('data-tsrid'), $('#changeset').find("option:selected").val()]]);
        params.tool_shed_repository_ids = JSON.stringify([$('#install_repository').attr('data-tsrid')]);
        params.tool_shed_url = $('#repository_details').attr('data-shedurl');
        params.install_tool_dependencies = $("#install_tool_dependencies").val();
        params.install_repository_dependencies = $("#install_repository_dependencies").val();
        params.install_resolver_dependencies = $("#install_resolver_dependencies").val();
        params.tool_panel_section = JSON.stringify(select_tps(params));
        params.shed_tool_conf = $("select[name='shed_tool_conf']").find('option:selected').val()
        params.changeset = $('#changeset').find("option:selected").val();
        url = $('#repository_installation').attr('action');
        prepare_installation(params, url);
    });
    check_if_installed(current_metadata);
    $(document).on('click', '.tool_form', function() {
        var guid = $(this).attr('data-guid');
        var clean = $(this).attr('data-clean');
        var name = $(this).attr('data-name');
        var desc = $(this).attr('data-desc');
        var tool_shed_url = $('#repository_details').attr('data-shedurl');
        var tsr_id = $('#repository_details').attr('data-tsrid');
        var changeset = get_current_changeset();
        var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action='shed_tool_json')}';
        var params = {'guid': guid, 'tool_shed_url': tool_shed_url, 'tsr_id': tsr_id, 'changeset': changeset};
        $.get(api_url, params, function(data) {
            console.log(data);
            require(["utils/utils", "mvc/ui/ui-modal", "mvc/form/form-view"], function (Utils, Modal, FormView) {
                $(function() {
                    data.cls = 'ui-portlet-plain';
                    var toolform = new FormView(data);
                    Utils.deepeach(data.inputs, function( input ) {
                        if (input.type) {
                            if (['data', 'data_collection'].indexOf(input.type) != -1) {
                                input.type = 'hidden';
                                input.info = 'Data input \'' + input.name + '\' (' + Utils.textify(input.extensions) + ')';
                            }
                        }
                    });
                    var modal = new Modal.View();
                    var modal_title = '<u>' + name + '</u> ' + desc;
                    modal.show({'title': modal_title, 'body': toolform.$el, 'buttons': { 'Close': function() { modal.hide(); }}});

                });
            });
        });
    });
}
function bind_shed_events() {
    $('.category-selector').click(function() {
        $('#list_repositories').replaceWith('<div id="list_repositories" class="tab-pane"><img src="/static/images/jstree/throbber.gif" alt="Loading repositories..." /></div>');
        var category_id = $(this).attr('data-categoryid');
        var shed_url = $('#tab_contents').attr('data-shedurl');
        load_category(shed_url, category_id);
    });
}
function bind_tps_propagation() {
    $('#tool_panel_section_select').change(function() {
        new_tps = $('#tool_panel_section_select').find('option:selected').val();
        $('.tool_panel_section_picker[default="active"]').each(function() {
            $(this).val(new_tps);
        });
    });
    tool_tps_selection_events();
}
function bind_workflow_events() {
    $('.show_wf_repo').click(function() {
        var tool_ids = $(this).attr('data-toolids');
        var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action='shed_repository')}';
        var params = {'tool_ids': tool_ids};
        $.get(api_url, params, function(data) {
            data.current_metadata = data.repository.metadata[data.current_changeset];
            data.repository_dependencies_template = repository_dependencies_template;
            data.repository_dependency_template = repository_dependency_template;
            data.tps_template_global_select = tps_template_global_select;
            repository_data = data;
            repository_data.shed_tool_conf = shed_tool_conf({'stc_html': repository_data.shed_conf});
            repository_data.tool_panel_section = '';
            if (repository_data.repository.metadata[data.current_changeset].includes_tools_for_display_in_tool_panel) {
                tps_dict = {'current_changeset': data.current_changeset, 'tps': repository_data.panel_section_dict};
                repository_data.tool_panel_section = tps_template_global_select(tps_dict);
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
    });
    $('.queue_wf_repo').click(function() {
        var tool_ids = $(this).attr('data-toolids');
        var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action='shed_repository')}';
        var params = {'tool_ids': tool_ids};
        $.get(api_url, params, function(data) {
            var repository_metadata = data.repository.metadata[data.current_changeset];
            $('#repository_details').attr('data-shedurl', data.tool_shed_url);
            var queue_key = get_queue_key(repository_metadata);
            var queued_repos = new Object();
            if (localStorage.repositories) {
                queued_repos = get_repository_queue();
            }
            if (!queued_repos.hasOwnProperty(queue_key)) {
                queued_repos[queue_key] = repository_metadata;
            }
            save_repository_queue(queued_repos);
            check_if_installed(repository_metadata);
            check_queue();
        });
    });
}
function bind_wf_button() {
    $('#from_workflow').click(load_from_workflow);
}
function changeset_metadata() {
    repository_data.current_changeset = get_current_changeset();
    repository_data.current_metadata = repository_data.repository.metadata[changeset];
    repository_information = repository_data.repository;
    $('#repository_details').replaceWith(repository_details_template(repository_data));
    check_if_installed(repository_data.current_metadata);
    bind_repository_events();
}
function check_if_installed(repository_metadata) {
    params = {name: repository_metadata.name, owner: repository_metadata.owner}
    var already_installed = false;
    var queued = repository_in_queue(repository_metadata);
    $.get('${h.url_for(controller='/api/tool_shed_repositories')}', params, function(data) {
        for (var index = 0; index < data.length; index++) {
            var repository = data[index];
            var installed = !repository.deleted && !repository.uninstalled;
            var changeset_match = repository.changeset_revision == repository_metadata.changeset_revision ||
                                  repository.installed_changeset_revision == repository_metadata.changeset_revision;
            if (repository.name == repository_metadata.name && repository.owner == repository_metadata.owner && installed && changeset_match) {
                already_installed = true;
            }
            if (already_installed) {
                $('#install_repository').prop('disabled', true);
                $('#install_repository').val('This revision is already installed');
            }
            else {
                $('#install_repository').prop('disabled', false);
                $('#install_repository').val('Install this revision');
            }
        }
    });
    if (repository_in_queue(repository_metadata) || already_installed) {
        $('#queue_install').hide();
        $('#queue_install').val('This revision is already in the queue');
    }
    else {
        $('#queue_install').show();
        $('#queue_install').val('Install this revision later');
    }
}
function check_queue() {
    var was_active = $('#repository_queue').attr('class');
    if (localStorage.hasOwnProperty('repositories')) {
        var repository_queue = JSON.parse(localStorage.repositories);
        var queue_keys = Object.keys(repository_queue);
        var queue = Array();
        for (var i = 0; i < queue_keys.length; i++) {
            var queue_key = queue_keys[i];
            var repository_metadata = repository_queue[queue_key];
            var repository = repository_metadata.repository;
            var key_parts = queue_key.split('|');
            var tool_shed_url = key_parts[0];
            repository.queue_key = queue_key;
            repository.changeset = repository_metadata.changeset_revision;
            repository.tool_shed_url = tool_shed_url;
            queue.push(repository);
        }
        $('#repository_queue').replaceWith(repository_queue_template({'repositories': queue}));
        $('#repository_queue').attr('class', was_active);
    }
    $('.install_one').click(function() {
        var repository_metadata = get_repository_from_queue($(this).attr('data-repokey'));
        install_from_queue(repository_metadata, $(this).attr('data-repokey'));
    });
    $('.remove_one').click(function(){
        var queue_key = $(this).attr('data-repokey');
        var repository_metadata = get_repository_from_queue(queue_key);
        var repository_id = repository_metadata.repository.id;
        var selector = "#queued_repository_" + repository_id;
        $(selector).remove();
        remove_from_queue(undefined, undefined, queue_key);
    });
    $('#clear_queue').click(function() {
        $('#repository_queue').replaceWith('<div class="tab-pane" id="repository_queue"><p>There are no repositories queued for installation.</p><input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" /></div>');
        $('#repository_queue').attr('class', was_active);
        localStorage.removeItem('repositories');
    });
    $('#install_all').click(process_queue);
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
function get_queue_key(repository_metadata) {
    if (repository_metadata.tool_shed_url === undefined) {
        repository_metadata.tool_shed_url = $("#repository_details").attr('data-shedurl');
    }
    // Make sure there is never a trailing slash on the shed URL.
    if (repository_metadata.tool_shed_url.substr(-1) == '/') {
        repository_metadata.tool_shed_url = repository_metadata.tool_shed_url.substr(0, repository_metadata.tool_shed_url.length - 1);
    }
    return repository_metadata.tool_shed_url + '|' + repository_metadata.repository_id + '|' + repository_metadata.changeset_revision;
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
function install_repository(params) {
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
function load_category(shed_url, category_id) {
    var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_category")}'
    var params = {'tool_shed_url': shed_url, 'category_id': category_id};
    $.get(api_url, params, function(data) {
        $('#list_repositories').replaceWith(repositories_in_category(data));
        $('#repo_list_tab').click();
        bind_category_events();
        window.location.hash = 'tab=list_repositories&tool_shed_url=' + shed_url + '&category_id=' + category_id;
    });
}
function load_from_workflow() {
    api_url = '${h.url_for(controller='api', action='workflows', missing_tools=True)}';
    $.get(api_url, function(data) {
        $('#workflows_missing_tools').remove();
        $('#repository_queue').append(workflows_missing_tools({'workflows': data}));
        bind_workflow_events();
    });
}
function load_repository(shed_url, tsr_id) {
    api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_repository")}';
    params = {"tool_shed_url": shed_url, "tsr_id": tsr_id};
    load_repository_contents(tsr_id, shed_url, api_url, params);
}
function load_repository_contents(tsr_id, shed_url, api_url, params) {
    $.get(api_url, params, function(data) {
        var changesets = Object.keys(data.repository.metadata);
        data.tool_shed_url = shed_url;
        data.current_changeset = changesets[changesets.length - 1];
        data.current_metadata = data.repository.metadata[data.current_changeset];
        data.repository_dependencies_template = repository_dependencies_template;
        data.repository_dependency_template = repository_dependency_template;
        data.tps_template_global_select = tps_template_global_select;
        // data.tps = repository_data.panel_section_dict;
        repository_data = data;
        repository_data.shed_tool_conf = shed_tool_conf({'stc_html': repository_data.shed_conf});
        repository_data.tool_panel_section = '';
        if (repository_data.repository.metadata[data.current_changeset].includes_tools_for_display_in_tool_panel) {
            tps_dict = {'current_changeset': data.current_changeset, 'tps': repository_data.panel_section_dict};
            repository_data.tool_panel_section = tps_template_global_select(tps_dict)
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
    window.location.hash = 'tab=repository_details&tool_shed_url=' + shed_url + '&tsr_id=' + tsr_id;
}
function load_toolshed(shed_url) {
    api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_categories")}'
    $.get(api_url, { tool_shed_url: shed_url }, function(data) {
        $('#list_categories').replaceWith(categories_in_shed(data));
        $('#category_list_tab').click();
        bind_shed_events();
        setup_repo_search('#category_search');
        window.location.hash = 'tab=list_categories&tool_shed_url=' + shed_url;
    });
}
function load_toolshed_list(tool_sheds) {
    $('#list_toolsheds').replaceWith(tool_sheds_template({tool_sheds: tool_sheds}));
    $('.shed-selector').click(function() {
        $('#list_categories').replaceWith('<div id="list_categories" class="nav-tab"><img src="/static/images/jstree/throbber.gif" alt="Loading categories..." /></div>');
        shed_url = $(this).attr('data-shedurl');
        $('#tab_contents').attr('data-shedurl', shed_url);
        load_toolshed(shed_url);
        window.location.hash = 'tab=list_categories&tool_shed_url=' + shed_url;
    });
}
function parse_shed_response(data) {
    var results = [];
    var hits = data.hits;
    $.each(hits, function(hit) {
        var record = hits[hit];
        var label = record.repository.name + ' by ' + record.repository.repo_owner_username + ': ' + record.repository.description;
        result = {value: record.repository.id, label: label};
        results.push(result);
    });
    return results;
}
function prepare_installation(params, api_url) {
    $.post(api_url, params, function(data) {
        iri_parameters = JSON.parse(data);
        install_repository(iri_parameters);
    });
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
        queue_key = get_queue_key(repository_metadata);
    }
    repository_queue = get_repository_queue();
    if (repository_queue.hasOwnProperty(queue_key)) {
        delete repository_queue[queue_key];
        save_repository_queue(repository_queue);
    }
}
function repository_in_queue(repository_metadata) {
    if (!localStorage.repositories) {
        return;
    }
    var repository_queue = get_repository_queue();
    var changeset = repository_metadata.changeset_revision;
    // changeset = get_current_changeset();
    var queue_key = get_queue_key(repository_metadata);
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
function search_in_shed(request, response) {
    var shed_url = $('#tab_contents').attr('data-shedurl');
    var base_url = '${h.url_for(controller='/api/tool_shed_repositories', action='shed_search')}';
    $.get(base_url, {term: request.term, tool_shed_url: shed_url}, function(data) {
        result_list = parse_shed_response(data);
        response(result_list);
    });
}
function setup_repo_search(selector) {
    $(selector).autocomplete({
        source: search_in_shed,
        minLength: 3,
        select: function(event, ui) {
            var tsr_id = ui.item.value;
            var shed_url = $('#tab_contents').attr('data-shedurl');
            var api_url = '${h.url_for(controller='/api/tool_shed_repositories', action="shed_repository")}';
            var params = {"tool_shed_url": shed_url, "tsr_id": tsr_id};
            load_repository_contents(tsr_id, shed_url, api_url, params);
        },
    });
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
    tps_dict = {'current_changeset': repository_data.current_changeset, 'tps': repository_data.panel_section_dict};
    $('#tool_panel_section').replaceWith(tps_template_global_select(tps_dict));
    bind_tps_propagation();
    $('#create_new').click(show_global_tps_create);
}
function show_global_tps_create() {
    $('#tool_panel_section').replaceWith(tps_template_global_create(repository_data));
    $('#select_existing').click(show_global_tps_select);
}
function show_panel_button(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#per_tool_tps_container_' + tool.clean;
    $(selector).empty();
    $(selector).append(tps_template_tool_select({tool: tool}));
    $('#select_tps_button_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_tps_select(tool_guid, changeset);
    });
}
function show_tool_tps_select(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#tool_tps_' + tool.clean;
    $(selector).empty();
    $(selector).append(tps_template_tool_select({tool: tool, tps: repository_data.panel_section_dict}));
    $('#per_tool_create_' + tool.clean).click(function() {
        show_tool_tps_create(tool_guid, changeset);
    });
    $('#select_tps_' + tool.clean).find('select').removeAttr('default');
    tool_tps_selection_events();
}
function show_tool_tps_create(tool_guid, changeset) {
    var tool = find_tool_by_guid(tool_guid, changeset);
    var selector = '#tool_tps_' + tool.clean;
    $(selector).empty();
    $(selector).append(tps_template_tool_create({tool: tool}));
    $('#per_tool_select_' + tool.clean).click(function() {
        var changeset = get_current_changeset();
        var tool_guid = $(this).attr('data-toolguid');
        show_tool_tps_select(tool_guid, changeset);
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
function tool_tps_selection_events() {
    $('.tool_panel_section_picker').change(function() {
        new_value = $(this).find('option:selected').val();
        default_tps = $('#tool_panel_section_select').find('option:selected').val();
        if (new_value == default_tps) {
            $(this).attr('default', 'active');
        }
        else {
            $(this).removeAttr('default');
        }
    });
}
$(document).ready(function() {
    var urlhash = String(window.location.hash);
    urlhash = urlhash.replace(/^#/, '');
    var page_params = {};
    if (urlhash.length > 0) {
        var parts = urlhash.split('&');
        for (var i = 0; i < parts.length; i++) {
            var kv = parts[i].split('=');
            page_params[kv[0]] = kv[1];
        }
    }
    load_toolshed_list(tool_sheds);
    if (page_params.tab == 'list_categories') {
        load_toolshed(page_params.tool_shed_url);
        $('#tab_contents').attr('data-shedurl', page_params.tool_shed_url);
        return;
    }
    else if (page_params.tab == 'list_repositories') {
        load_category(page_params.tool_shed_url, page_params.category_id);
        $('#tab_contents').attr('data-shedurl', page_params.tool_shed_url);
        return;
    }
    else if (page_params.tab == 'repository_details') {
        load_repository(page_params.tool_shed_url, page_params.tsr_id);
        $('#tab_contents').attr('data-shedurl', page_params.tool_shed_url);
        return;
    }
    $('#shed_list_tab').click();
    check_queue();
    $('#repository_installation_queue').click(bind_wf_button);
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
        <div class="tab-pane" id="list_categories"><p>Select a toolshed in the previous tab to see a list of its categories.</p></div>
        <div class="tab-pane" id="list_repositories"><p>Select a category in the previous tab to see a list of its repositories.</p></div>
        <div class="tab-pane" id="repository_details"><p>Select a repository in the previous tab.</p></div>
        <div class="tab-pane" id="repository_queue">
            <p>There are no repositories queued for installation.</p>
            <input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />
        </div>
    </div>
</div>
