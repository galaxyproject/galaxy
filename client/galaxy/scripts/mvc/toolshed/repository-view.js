import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import "libs/jquery/jstree";
import toolshed_model from "mvc/toolshed/toolshed-model";
import Utils from "utils/utils";
import Modal from "mvc/ui/ui-modal";
import FormView from "mvc/form/form-view";
import toolshed_util from "mvc/toolshed/util";

var ToolShedRepositoryView = Backbone.View.extend({
    el: "#center",

    initialize: function(params) {
        this.options = _.defaults(this.options || {}, this.defaults);
        this.model = new toolshed_model.RepositoryCollection();
        this.listenTo(this.model, "sync", this.render);
        var shed = params.tool_shed.replace(/\//g, "%2f");
        this.model.url += `?tool_shed_url=${shed}&repository_id=${params.repository_id}`;
        this.model.tool_shed_url = params.tool_shed.replace(/%2f/g, "/");
        this.model.tool_shed = shed;
        this.model.category = params.repository_id;
        this.model.fetch();
    },

    render: function(options) {
        var repo_details_template = this.templateRepoDetails;
        var models = this.model.models[0];
        this.options = {
            repository: models.get("repository"),
            tool_shed: this.model.tool_shed,
            queue: toolshed_util.queueLength()
        };
        var changesets = Object.keys(this.options.repository.metadata).sort(function(a, b) {
            return parseInt(a.split(":")[0] - b.split(":")[0]);
        });
        var ordered_metadata = {};
        var unordered_metadata = this.options.repository.metadata;
        changesets.forEach(function(key) {
            ordered_metadata[key] = unordered_metadata[key];
        });
        this.options.repository.metadata = ordered_metadata;
        this.options.current_changeset = this.options.current_changeset || changesets[changesets.length - 1];
        this.options.current_metadata = this.options.repository.metadata[this.options.current_changeset];
        this.options.current_metadata.tool_shed_url = this.model.tool_shed_url;
        this.options.tools = this.options.current_metadata.tools;
        this.options.repository_dependencies_template = this.templateRepoDependencies;
        this.options.repository_dependency_template = this.templateRepoDependency;
        this.options.tps_template_global_select = this.templateGlobalSectionSelect;
        this.options.tps_template_global_create = this.templateGlobalSectionCreate;
        this.options.tps_template_tool_select = this.templateToolSectionSelect;
        this.options.tps_template_tool_create = this.templateToolSectionCreate;
        this.options.panel_section_options = this.templatePanelSelectOptions;
        this.options.tool_dependencies = models.get("tool_dependencies");
        this.options.shed_tool_conf = this.templateShedToolConf({
            shed_tool_confs: models.get("shed_conf")
        });
        this.options.panel_section_dict = models.get("panel_section_dict");
        this.options.api_url = `${getAppRoot()}api/tool_shed_repositories/install?async=True`;
        this.options = _.extend(this.options, options);
        this.$el.html(repo_details_template(this.options));
        this.checkInstalled(this.options.current_metadata);
        this.bindEvents();
        $("#center").css("overflow", "auto");
    },

    bindEvents: function() {
        $("#changeset").on("change", () => {
            this.options.current_changeset = $("#changeset")
                .find("option:selected")
                .text();
            this.options.current_metadata = this.options.repository.metadata[this.options.current_changeset];
            this.checkInstalled(this.options.current_metadata);
            this.reDraw(this.options);
        });
        $("#tool_panel_section_select").on("change", () => {
            this.tpsSelection();
        });
        $("#install_repository").on("click", ev => {
            ev.preventDefault();
            var params = {};
            params.repositories = JSON.stringify([
                [
                    $("#install_repository").attr("data-tsrid"),
                    $("#changeset")
                        .find("option:selected")
                        .val()
                ]
            ]);
            params.tool_shed_repository_ids = JSON.stringify([$("#install_repository").attr("data-tsrid")]);
            params.tool_shed_url = this.model.tool_shed_url;
            params.install_tool_dependencies = $("#install_tool_dependencies").val();
            params.install_repository_dependencies = $("#install_repository_dependencies").val();
            params.install_resolver_dependencies = $("#install_resolver_dependencies").val();
            params.tool_panel_section = JSON.stringify(this.panelSelect(params));
            params.shed_tool_conf = $("select[name='shed_tool_conf']")
                .find("option:selected")
                .val();
            params.changeset = $("#changeset")
                .find("option:selected")
                .val();
            var url = $("#repository_installation").attr("action");
            this.prepareInstall(params, url);
        });
        $("#queue_install").on("click", ev => {
            this.options.current_changeset = $("#changeset")
                .find("option:selected")
                .text();
            this.options.current_metadata = this.options.repository.metadata[this.options.current_changeset];
            var repository_metadata = {};
            _.each(Object.keys(this.options.current_metadata), key => {
                if (!repository_metadata[key]) {
                    repository_metadata[key] = this.options.current_metadata[key];
                }
            });
            repository_metadata.install_tool_dependencies = $("#install_tool_dependencies").val();
            repository_metadata.install_repository_dependencies = $("#install_repository_dependencies").val();
            repository_metadata.install_resolver_dependencies = $("#install_resolver_dependencies").val();
            repository_metadata.tool_panel_section = JSON.stringify(this.panelSelect({}));
            repository_metadata.shed_tool_conf = $("select[name='shed_tool_conf']")
                .find("option:selected")
                .val();
            repository_metadata.tool_shed_url = this.model.tool_shed_url;
            if (repository_metadata.tool_shed_url.substr(-1) == "/") {
                repository_metadata.tool_shed_url = repository_metadata.tool_shed_url.substr(
                    0,
                    repository_metadata.tool_shed_url.length - 1
                );
            }
            toolshed_util.addToQueue(repository_metadata);
            this.checkInstalled(repository_metadata);
        });
        this.toolTPSSelectionEvents();
        $(() => {
            $("#repository_dependencies").jstree();
        });
        $(".tool_form").on("click", ev => {
            var guid = $(ev.target).attr("data-guid");
            var name = $(ev.target).attr("data-name");
            var desc = $(ev.target).attr("data-desc");
            var tool_shed_url = this.model.tool_shed_url;
            var tsr_id = $("#repository_details").attr("data-tsrid");
            var changeset = $("#changeset")
                .find("option:selected")
                .val();
            var api_url = `${getAppRoot()}api/tool_shed/tool_json`;
            var params = {
                guid: guid,
                tool_shed_url: tool_shed_url,
                tsr_id: tsr_id,
                changeset: changeset
            };
            $.get(api_url, params, data => {
                var toolform = new FormView(data);
                Utils.deepeach(data.inputs, input => {
                    if (input.type) {
                        if (["data", "data_collection"].indexOf(input.type) != -1) {
                            input.type = "hidden";
                            input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                        }
                    }
                });
                var modal = new Modal.View();
                var modal_title = `<u>${name}</u> ${desc}`;
                modal.show({
                    closing_events: true,
                    title: modal_title,
                    body: toolform.$el,
                    buttons: {
                        Close: function() {
                            modal.hide();
                        }
                    }
                });
            });
        });
        $(".select-tps-button").on("click", params => {
            var changeset = this.selectedChangeset();
            var guid = params.target.attributes.getNamedItem("data-toolguid");
            this.showToolTPSSelect(guid, changeset);
        });
        $(".create-tps-button").on("click", params => {
            var changeset = this.selectedChangeset();
            var guid = params.target.attributes.getNamedItem("data-toolguid");
            this.showToolTPSCreate(guid, changeset);
        });
        $(".global-select-tps-button").on("click", () => {
            $("#tool_panel_section").replaceWith(this.options.tps_template_global_select(this.options));
            this.propagateTPS();
            this.bindEvents();
        });
        $(".global-create-tps-button").on("click", () => {
            $("#tool_panel_section").replaceWith(this.options.tps_template_global_create());
            this.bindEvents();
        });
    },

    checkInstalled: function(metadata) {
        var params = { name: metadata.name, owner: metadata.owner };
        var already_installed = false;
        $.get(`${getAppRoot()}api/tool_shed_repositories`, params, data => {
            for (var index = 0; index < data.length; index++) {
                var repository = data[index];
                var installed = !repository.deleted && !repository.uninstalled;
                var changeset_match =
                    repository.changeset_revision == metadata.changeset_revision ||
                    repository.installed_changeset_revision == metadata.changeset_revision;
                if (
                    repository.name == metadata.repository.name &&
                    repository.owner == metadata.repository.owner &&
                    installed &&
                    changeset_match
                ) {
                    already_installed = true;
                }
                if (already_installed) {
                    $("#install_repository").prop("disabled", true);
                    $("#install_repository").val("This revision is already installed");
                } else {
                    $("#install_repository").prop("disabled", false);
                    $("#install_repository").val("Install this revision");
                }
            }
            if (this.repoQueued(metadata) || already_installed) {
                $("#queue_install").hide();
                $("#queue_install").val("This revision is already in the queue");
            } else {
                $("#queue_install").show();
                $("#queue_install").val("Install this revision later");
            }
        });
    },

    panelSelect: function(params) {
        var tool_panel_section = {};
        if ($("#tool_panel_section_select").length) {
            params.tool_panel_section_id = $("#tool_panel_section_select")
                .find("option:selected")
                .val();
        } else {
            params.new_tool_panel_section = $("#new_tool_panel_section").val();
        }
        $(".tool_panel_section_picker").each(function() {
            var element_name = $(this).attr("name");
            var tool_guid = $(this).attr("data-toolguid");
            if (element_name === "tool_panel_section_id") {
                tool_panel_section[tool_guid] = {
                    tool_panel_section: $(this)
                        .find("option:selected")
                        .val(),
                    action: "append"
                };
            } else {
                tool_panel_section[tool_guid] = {
                    tool_panel_section: $(this).val(),
                    action: "create"
                };
            }
        });
        return tool_panel_section;
    },

    reDraw: function(options) {
        this.$el.empty();
        this.render(options);
    },

    repoQueued: function(metadata) {
        if (!window.localStorage.repositories) {
            return;
        }
        var queue_key = this.queueKey(metadata);
        var queued_repos;
        if (window.localStorage.repositories) {
            queued_repos = JSON.parse(window.localStorage.repositories);
        }
        if (queued_repos && queued_repos.hasOwnProperty(queue_key)) {
            return true;
        }
        return false;
    },

    queueKey: function(metadata) {
        var shed_url = this.model.tool_shed_url;
        // Make sure there is never a trailing slash on the shed URL.
        if (shed_url.substr(-1) == "/") {
            shed_url = shed_url.substr(0, shed_url.length - 1);
        }
        return `${shed_url}|${metadata.repository_id}|${metadata.changeset_revision}`;
    },

    tpsSelection: function() {
        var new_tps = $("#tool_panel_section_select")
            .find("option:selected")
            .val();
        $('.tool_panel_section_picker[default="active"]').each(function() {
            $(this).val(new_tps);
        });
    },

    prepareInstall: function(params, api_url) {
        $.post(api_url, params, data => {
            var iri_parameters = JSON.parse(data);
            this.doInstall(iri_parameters);
        });
    },

    doInstall: function(params) {
        var controller_url = `${getAppRoot()}admin_toolshed/install_repositories`;
        var repositories = params.repositories;
        var new_route = `status/r/${repositories.join("|")}`;
        $.post(controller_url, params, data => {
            console.log("Initializing repository installation succeeded");
        });
        Backbone.history.navigate(new_route, {
            trigger: true,
            replace: true
        });
    },

    selectedChangeset: function() {
        var changeset = $("#changeset")
            .find("option:selected")
            .val();
        return changeset;
    },

    showToolTPSCreate: function(guid, changeset) {
        var metadata = this.options.current_metadata;
        var tools = metadata.tools;
        var tool = toolshed_util.toolByGuid(guid, changeset, tools);
        var selector = "#tool_tps_" + tool.clean;
        $(selector).empty();
        $(selector).append(this.options.tps_template_tool_create({ tool: tool }));
        $(".select-tps-button").click(ev => {
            var changeset = this.selectedChangeset();
            var guid = ev.target.attributes.getNamedItem("data-toolguid");
            this.showToolTPSSelect(guid, changeset);
        });
        this.bindEvents();
    },

    showToolTPSSelect: function(guid, changeset) {
        var metadata = this.options.current_metadata;
        var tools = metadata.tools;
        var tool = toolshed_util.toolByGuid(guid, changeset, tools);
        var selector = "#tool_tps_" + tool.clean;
        $(selector).empty();
        $(selector).append(
            this.options.tps_template_tool_select({
                tool: tool,
                panel_section_dict: this.options.panel_section_dict,
                panel_section_options: this.options.panel_section_options
            })
        );
        $(".create-tps-button").click(ev => {
            var changeset = this.selectedChangeset();
            var guid = ev.target.attributes.getNamedItem("data-toolguid");
            this.showToolTPSCreate(guid, changeset);
        });
        this.bindEvents();
    },

    propagateTPS: function() {
        $("#tool_panel_section_select").change(() => {
            var new_tps = $("#tool_panel_section_select")
                .find("option:selected")
                .val();
            $('.tool_panel_section_picker[default="active"]').each(obj => {
                obj.val(new_tps);
            });
        });
        this.toolTPSSelectionEvents();
    },

    toolTPSSelectionEvents: function() {
        $(".tool_panel_section_picker").on("change", ev => {
            let element = $(ev.target);
            var new_value = element.find("option:selected").val();
            var default_tps = $("#tool_panel_section_select")
                .find("option:selected")
                .val();
            if (new_value == default_tps) {
                element.attr("default", "active");
            } else {
                element.removeAttr("default");
            }
        });
    },

    templateRepoDetails: _.template(
        [
            '<div class="unified-panel-header" id="panel_header" unselectable="on">',
            '<div class="unified-panel-header-inner">Repository information for&nbsp;<strong><%= repository.name %></strong>&nbsp;from&nbsp;<strong><%= repository.owner %></strong><a class="ml-auto" href="#/queue">Repository Queue (<%= queue %>)</a></div>',
            "</div>",
            '<div class="unified-panel-body" id="repository_details" data-tsrid="<%= repository.id %>">',
            '<form id="repository_installation" name="install_repository" method="post" action="<%= api_url %>">',
            '<input type="hidden" id="repositories" name="<%= repository.id %>" value="ID" />',
            '<input type="hidden" id="tool_shed_url" name="tool_shed_url" value="<%= tool_shed %>" />',
            '<div class="toolForm">',
            '<div class="toolFormTitle">Changeset</div>',
            '<div class="toolFormBody changeset">',
            '<select id="changeset" name="changeset" style="margin: 5px;">',
            "<% _.each(Object.keys(repository.metadata), function(changeset) { %>",
            '<% if (changeset == current_changeset) { var selected = "selected "; } else { var selected = ""; } %>',
            '<option <%= selected %>value="<%= changeset.split(":")[1] %>"><%= changeset %></option>',
            "<% }); %>",
            "</select>",
            '<input class="btn btn-primary preview-button" data-tsrid="<%= current_metadata.repository.id %>" type="submit" id="install_repository" name="install_repository" value="Install this revision now" />',
            '<input class="btn btn-primary preview-button" type="button" id="queue_install" name="queue_install" value="Install this revision later" />',
            '<div class="toolParamHelp" style="clear: both;">Please select a revision and review the settings below before installing.</div>',
            "</div>",
            "</div>",
            "<%= shed_tool_conf %>",
            "<% if (current_metadata.has_repository_dependencies) { %>",
            '<div class="toolFormTitle">Repository dependencies for <strong id="current_changeset"><%= current_changeset %></strong></div>',
            '<div class="toolFormBody">',
            '<p id="install_repository_dependencies_checkbox">',
            '<input type="checkbox" checked id="install_repository_dependencies" />',
            '<label for="install_repository_dependencies">Install repository dependencies</label>',
            "</p>",
            "<% current_metadata.repository_dependency_template = repository_dependency_template; %>",
            '<div class="tables container-table" id="repository_dependencies">',
            '<div class="expandLink">',
            '<a class="toggle_folder" data_target="repository_dependencies_table">',
            "Repository dependencies &ndash; <em>installation of these additional repositories is required</em>",
            "</a>",
            "</div>",
            "<%= repository_dependencies_template(current_metadata) %>",
            "</div>",
            "</div>",
            "<% } %>",
            "<% if (current_metadata.includes_tool_dependencies) { %>",
            '<div class="toolFormTitle">Tool dependencies</div>',
            '<div class="toolFormBody">',
            '<p id="install_resolver_dependencies_checkbox">',
            '<input type="checkbox" checked id="install_resolver_dependencies" />',
            '<label for="install_resolver_dependencies">Install resolver dependencies</label>',
            "</p>",
            '<p id="install_tool_dependencies_checkbox">',
            '<input type="checkbox" checked id="install_tool_dependencies" />',
            '<label for="install_tool_dependencies">Install tool dependencies</label>',
            "</p>",
            '<div class="tables container-table" id="tool_dependencies">',
            '<div class="expandLink">',
            '<a class="toggle_folder" data_target="tool_dependencies_table">',
            "Tool dependencies &ndash; <em>repository tools require handling of these dependencies</em>",
            "</a>",
            "</div>",
            '<table class="tables container-table" id="tool_dependencies_table" border="0" cellpadding="2" cellspacing="2" width="100%">',
            "<thead>",
            '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
            '<th style="padding-left: 40px;">Name</th>',
            "<th>Version</th>",
            "<th>Type</th>",
            "</tr>",
            "</thead>",
            '<tbody id="tool_deps">',
            "<% _.each(tool_dependencies[current_changeset], function(dependency) { %>",
            '<tr class="datasetRow tool_dependency_row" style="display: table-row;">',
            '<td style="padding-left: 40px;">',
            "<%= dependency.name %></td>",
            "<td><%= dependency.version %></td>",
            "<td><%= dependency.type %></td>",
            "</tr>",
            "<% }); %>",
            "</tbody>",
            "</table>",
            "</div>",
            "</div>",
            "<% } %>",
            "<% if (current_metadata.includes_tools_for_display_in_tool_panel) { %>",
            '<div class="toolFormTitle">Tools &ndash; <em>click the name to preview the tool and use the pop-up menu to inspect all metadata</em></div>',
            '<div class="toolFormBody">',
            '<div class="tables container-table" id="tools_toggle">',
            '<table class="tables container-table" id="valid_tools" border="0" cellpadding="2" cellspacing="2" width="100%">',
            "<thead>",
            '<tr style="display: table-row;" class="datasetRow" parent="0" id="libraryItem-rt-f9cad7b01a472135">',
            '<th style="padding-left: 40px;">Name</th>',
            "<th>Description</th>",
            "<th>Version</th>",
            "<th><%= tps_template_global_select({panel_section_dict: panel_section_dict, panel_section_options: panel_section_options}) %></tr>",
            "</thead>",
            '<tbody id="tools_in_repo">',
            "<% _.each(current_metadata.tools, function(tool) { %>",
            '<tr id="libraryItem-<%= tool.clean %>" class="tool_row" style="display: table-row;" style="width: 15%">',
            '<td style="padding-left: 40px;">',
            '<div id="tool-<%= tool.clean %>" class="menubutton split popup" style="float: left;">',
            '<a class="tool_form view-info" data-toggle="modal" data-target="toolform_<%= tool.clean %>" data-clean="<%= tool.clean %>" data-guid="<%= tool.guid %>" data-name="<%= tool.name %>" data-desc="<%= tool.description %>"><%= tool["name"] %></a>',
            "</div>",
            "</td>",
            "<td><%= tool.description %></td>",
            '<td style="width: 15%"><%= tool.version %></td>',
            '<td style="width: 35%" id="tool_tps_<%= tool.clean %>">',
            "<%= tps_template_tool_select({tool: tool, panel_section_dict: panel_section_dict, panel_section_options: panel_section_options}) %>",
            "</td>",
            "</tr>",
            "<% }); %>",
            "</tbody>",
            "</table>",
            "</div>",
            "</div>",
            "<% } %>",
            "</form>",
            "</div>"
        ].join("")
    ),

    templateRepoDependencies: _.template(
        [
            '<div class="toolFormTitle">Repository Dependencies</div>',
            '<div class="toolFormBody tables container-table" id="repository_dependencies">',
            "<ul>",
            "<li>Repository installation requires the following",
            "<% if (has_repository_dependencies) { %>",
            "<% _.each(repository_dependencies, function(dependency) { %>",
            "<% dependency.repository_dependency_template = repository_dependency_template; %>",
            "<%= repository_dependency_template(dependency) %>",
            "<% }); %>",
            "<% } %>",
            "</li>",
            "</ul>",
            "</div>"
        ].join("")
    ),

    templateRepoDependency: _.template(
        [
            '<li id="metadata_<%= id %>" class="datasetRow repository_dependency_row">',
            "Repository <b><%= repository.name %></b> revision <b><%= changeset_revision %></b> owned by <b><%= repository.owner %></b>",
            "<% if (has_repository_dependencies) { %>",
            '<ul class="child_dependencies">',
            "<% _.each(repository_dependencies, function(dependency) { %>",
            "<% dependency.repository_dependency_template = repository_dependency_template; %>",
            "<%= repository_dependency_template(dependency) %>",
            "<% }); %>",
            "</ul>",
            "<% } %>",
            "</li>"
        ].join("")
    ),

    templateShedToolConf: _.template(
        [
            '<div class="toolFormTitle">Shed tool configuration file:</div>',
            '<div class="toolFormBody">',
            '<div class="form-row">',
            '<select name="shed_tool_conf">',
            "<% _.each(shed_tool_confs.options, function(conf) { %>",
            '<option value="<%= conf.value %>"><%= conf.label %></option>',
            "<% }); %>",
            "</select>",
            '<div class="toolParamHelp" style="clear: both;">Select the file whose <b>tool_path</b> setting you want used for installing repositories.</div>',
            "</div>",
            "</div>"
        ].join("")
    ),

    templateToolDependency: _.template(
        [
            "<% if (has_repository_dependencies) { %>",
            "<% _.each(repository_dependencies, function(dependency) { %>",
            "<% if (dependency.includes_tool_dependencies) { %>",
            "<% dependency.tool_dependency_template = tool_dependency_template %>",
            "<%= tool_dependency_template(dependency) %>",
            "<% } %>",
            "<% }); %>",
            "<% } %>"
        ].join("")
    ),

    templateGlobalSectionCreate: _.template(
        [
            '<div id="tool_panel_section">',
            '<div class="form-row" id="new_tps">',
            '<input id="new_tool_panel_section" name="new_tool_panel_section" type="textfield" value="" size="40"/>',
            '<input class="btn btn-primary global-select-tps-button" type="button" id="select_existing" value="Select existing" />',
            '<div class="toolParamHelp" style="clear: both;">',
            "Add a new tool panel section to contain the installed tools (optional).",
            "</div>",
            "</div>",
            "</div>"
        ].join("")
    ),

    templateGlobalSectionSelect: _.template(
        [
            '<div id="tool_panel_section">',
            '<div class="toolFormTitle">Tool Panel Section</div>',
            '<div class="toolFormBody">',
            '<div class="tab-pane" id="select_tps">',
            '<select name="<%= name %>" id="<%= panel_section_dict.id %>">',
            "<%= panel_section_options({sections: panel_section_dict.sections}) %>",
            "</select>",
            '<input class="btn btn-primary global-create-tps-button" type="button" id="create_new" value="Create new" />',
            '<div class="toolParamHelp" style="clear: both;">',
            "Select an existing tool panel section to contain the installed tools (optional).",
            "</div>",
            "</div>",
            "</div>",
            "</div>"
        ].join("")
    ),

    templateToolSectionCreate: _.template(
        [
            '<div id="new_tps_<%= tool.clean %>" data-clean="<%= tool.clean %>" class="form-row">',
            '<input data-toolguid="<%= tool.guid %>" class="tool_panel_section_picker" size="40" name="new_tool_panel_section" id="new_tool_panel_section_<%= tool.clean %>" type="text">',
            '<input id="per_tool_select_<%= tool.clean %>" class="btn btn-primary select-tps-button" data-toolguid="<%= tool.guid %>" value="Select existing" id="select_existing_<%= tool.clean %>" type="button">',
            "</div>"
        ].join("")
    ),

    templateToolSectionSelect: _.template(
        [
            '<div id="select_tps_<%= tool.clean %>" data-clean="<%= tool.clean %>" class="tps_creator">',
            '<select default="active" style="width: 30em;" data-toolguid="<%= tool.guid %>" class="tool_panel_section_picker" name="tool_panel_section_id" id="tool_panel_section_select_<%= tool.clean %>">',
            "<%= panel_section_options({sections: panel_section_dict.sections}) %>",
            "</select>",
            '<input id="per_tool_create_<%= tool.clean %>" data-clean="<%= tool.clean %>" class="btn btn-primary create-tps-button" data-toolguid="<%= tool.guid %>" value="Create new" id="create_new_<%= tool.clean %>" type="button">',
            '<div style="clear: both;" class="toolParamHelp"></div>',
            "</div>"
        ].join("")
    ),

    templatePanelSelectOptions: _.template(
        [
            "<% _.each(sections, function(section) { %>",
            '<option value="<%= section.id %>"><%= section.name %></option>',
            "<% }); %>"
        ].join("")
    )
});

export default {
    RepoDetails: ToolShedRepositoryView
};
