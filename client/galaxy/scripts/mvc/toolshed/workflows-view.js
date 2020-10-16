import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import toolshed_model from "mvc/toolshed/toolshed-model";
import toolshed_util from "mvc/toolshed/util";

var View = Backbone.View.extend({
    el: "#center",

    defaults: [{}],

    initialize: function(options) {
        this.model = new toolshed_model.WorkflowTools();
        this.listenTo(this.model, "sync", this.render);
        this.model.fetch();
        this.render();
    },

    render: function(options) {
        var workflows_missing_tools = this.templateWorkflows;
        var workflows = this.model.models;
        this.$el.html(
            workflows_missing_tools({
                title: _l("Workflows Missing Tools"),
                workflows: workflows,
                queue: toolshed_util.queueLength()
            })
        );
        $("#center").css("overflow", "auto");
        this.bindEvents();
    },

    bindEvents: function() {
        var repository_id;
        $(".show_wf_repo").on("click", ev => {
            var tool_ids = $(ev.target).attr("data-toolids");
            var toolshed = $(ev.target).attr("data-shed");
            var api_url = `${getAppRoot()}api/tool_shed/repository`;
            var params = { tool_ids: tool_ids };
            $.get(api_url, params, data => {
                repository_id = data.repository.id;
                var new_route = `repository/s/${toolshed.replace(/:/g, "%3a").replace(/\//g, "%2f")}/r/${
                    data.repository.id
                }`;
                Backbone.history.navigate(new_route, {
                    trigger: true,
                    replace: true
                });
            });
        });
        $(".queue_wf_repo").on("click", ev => {
            var elem = $(ev.target);
            var tool_ids = elem.attr("data-toolids");
            var toolshed = elem.attr("data-shed");
            var api_url = `${getAppRoot()}api/tool_shed/repository`;
            var params = { tool_ids: tool_ids };
            $.get(api_url, params, data => {
                repository_id = data.repository.id;
                params = {
                    tool_shed_url: toolshed,
                    repository_id: repository_id
                };
                $.get(api_url, params, data => {
                    var changesets = Object.keys(data.repository.metadata);
                    var current_changeset = changesets[0];
                    var current_metadata = data.repository.metadata[current_changeset];
                    current_metadata.tool_shed_url = toolshed;
                    toolshed_util.addToQueue(current_metadata);
                    elem.remove();
                });
            });
        });
        $("#from_workflow").on("click", this.loadWorkflows);
    },

    templateWorkflows: _.template(
        [
            '<div class="unified-panel-header" id="panel_header" unselectable="on">',
            '<div class="unified-panel-header-inner"><%= title %><a class="ml-auto" href="#/queue">Repository Queue (<%= queue %>)</a></div>',
            "</div>",
            '<style type="text/css">',
            ".workflow_names, .workflow_tools { list-style-type: none; } ul.workflow_tools, ul.workflow_names {  padding-left: 0px; }",
            "</style>",
            '<table id="workflows_missing_tools" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">',
            '<thead id="grid-table-header">',
            "<tr>",
            '<th class="datasetRow">Workflows</th>',
            '<th class="datasetRow">Tool IDs</th>',
            '<th class="datasetRow">Shed</th>',
            '<th class="datasetRow">Name</th>',
            '<th class="datasetRow">Owner</th>',
            '<th class="datasetRow">Actions</th>',
            "</tr>",
            "</thead>",
            "<tbody>",
            "<% _.each(workflows, function(workflow) { %>",
            "<tr>",
            '<td class="datasetRow">',
            '<ul class="workflow_names">',
            '<% _.each(workflow.get("workflows"), function(name) { %>',
            '<li class="workflow_names"><%= name %></li>',
            "<% }); %>",
            "</ul>",
            "</td>",
            '<td class="datasetRow">',
            '<ul class="workflow_tools">',
            '<% _.each(workflow.get("tools"), function(tool) { %>',
            '<li class="workflow_tools"><%= tool %></li>',
            "<% }); %>",
            "</ul>",
            "</td>",
            '<td class="datasetRow"><%= workflow.get("shed") %></td>',
            '<td class="datasetRow"><%= workflow.get("repository") %></td>',
            '<td class="datasetRow"><%= workflow.get("owner") %></td>',
            '<td class="datasetRow">',
            '<ul class="workflow_tools">',
            '<li class="workflow_tools">',
            '<input type="button" class="show_wf_repo btn btn-primary" data-shed="<%= workflow.get("shed") %>" data-owner="<%= workflow.get("owner") %>" data-repo="<%= workflow.get("repository") %>" data-toolids="<%= workflow.get("tools").join(",") %>" value="Show Repository" /></li>',
            "</ul>",
            "</td>",
            "</tr>",
            "<% }); %>",
            "</ul>",
            "</div>"
        ].join("")
    )
});

export default {
    Workflows: View
};
