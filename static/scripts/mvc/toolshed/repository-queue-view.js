define([ "mvc/toolshed/toolshed-model", "mvc/toolshed/util" ], function(toolshed_model, toolshed_util) {
    var View = Backbone.View.extend({
        el: "#center",
        defaults: [ {} ],
        initialize: function() {
            var that = this;
            this.model = new toolshed_model.RepoQueue(), this.listenTo(this.model, "sync", this.render), 
            this.model.fetch(), that.render();
        },
        render: function() {
            var that = this, repo_queue_template = that.templateRepoQueue, repositories = that.model.models;
            that.$el.html(repo_queue_template({
                repositories: repositories
            })), $("#center").css("overflow", "auto"), that.bindEvents();
        },
        bindEvents: function() {
            var that = this;
            $(".install_one").on("click", function() {
                var repository_metadata = that.loadFromQueue($(this).attr("data-repokey"));
                that.installFromQueue(repository_metadata, $(this).attr("data-repokey"));
            }), $("#from_workflow").on("click", function() {
                Backbone.history.navigate("workflows", {
                    trigger: !0,
                    replace: !0
                });
            });
        },
        installFromQueue: function(repository_metadata, queue_key) {
            var params = Object();
            params.install_tool_dependencies = repository_metadata.install_tool_dependencies, 
            params.install_repository_dependencies = repository_metadata.install_repository_dependencies, 
            params.install_resolver_dependencies = repository_metadata.install_resolver_dependencies, 
            params.tool_panel_section = repository_metadata.tool_panel_section, params.shed_tool_conf = repository_metadata.shed_tool_conf, 
            params.repositories = JSON.stringify([ [ repository_metadata.repository.id, repository_metadata.changeset_revision ] ]), 
            params.tool_shed_repository_ids = JSON.stringify([ repository_metadata.repository.id ]), 
            params.tool_shed_url = queue_key.split("|")[0], params.changeset = repository_metadata.changeset_revision;
            var url = Galaxy.root + "api/tool_shed_repositories/install?async=True";
            $("#queued_repository_" + repository_metadata.repository.id).remove(), localStorage.repositories && (void 0 === queue_key && (queue_key = toolshed_util.queueKey(repository_metadata)), 
            repository_queue = JSON.parse(localStorage.repositories), repository_queue.hasOwnProperty(queue_key) && (delete repository_queue[queue_key], 
            localStorage.repositories = JSON.stringify(repository_queue))), $.post(url, params, function(data) {
                var iri_params = JSON.parse(data), repositories = iri_params.repositories, new_route = "status/r/" + repositories.join("|");
                $.post(Galaxy.root + "admin_toolshed/manage_repositories", iri_params, function() {
                    console.log("Initializing repository installation succeeded");
                }), Backbone.history.navigate(new_route, {
                    trigger: !0,
                    replace: !0
                });
            });
        },
        loadWorkflows: function() {
            var that = this;
            api_url = Galaxy.root + "api/workflows?missing_tools=True";
            var workflows_missing_tools = that.templateWorkflows;
            $.get(api_url, function(data) {
                $("#workflows_missing_tools").remove(), $("#center").append(workflows_missing_tools({
                    workflows: data
                })), bind_workflow_events();
            });
        },
        loadFromQueue: function(queue_key) {
            return repository_queue = JSON.parse(localStorage.repositories), repository_queue.hasOwnProperty(queue_key) ? repository_queue[queue_key] : void 0;
        },
        reDraw: function(options) {
            this.$el.empty(), this.initialize(options), this.model.fetch(), this.render(options);
        },
        templateRepoQueue: _.template([ '<div class="tab-pane" id="panel_header" id="repository_queue">', '<table id="queued_repositories" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">', '<thead id="grid-table-header">', "<tr>", '<th class="datasetRow">Name</th>', '<th class="datasetRow">Owner</th>', '<th class="datasetRow">Revision</th>', '<th class="datasetRow">ToolShed</th>', '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="install_all" name="install_all" value="Install all" /></th>', '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="clear_queue" name="clear_queue" value="Clear queue" /></th>', "</tr>", "</thead>", "<tbody>", "<% _.each(repositories, function(repository) { %>", '<tr id="queued_repository_<%= repository.get("id") %>">', '<td class="datasetRow"><%= repository.get("repository").name %></td>', '<td class="datasetRow"><%= repository.get("repository").owner %></td>', '<td class="datasetRow"><%= repository.get("changeset_revision") %></td>', '<td class="datasetRow"><%= repository.get("tool_shed_url") %></td>', '<td class="datasetRow">', '<input class="btn btn-primary install_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="install_repository_<%= repository.get("id") %>" name="install_repository" value="Install now" />', "</td>", '<td class="datasetRow">', '<input class="btn btn-primary remove_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="unqueue_repository_<%= repository.get("id") %>" name="unqueue_repository" value="Remove from queue" />', "</td>", "</tr>", "<% }); %>", "</tbody>", "</table>", '<input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />', "</div>" ].join("")),
        templateWorkflows: _.template([ '<table id="workflows_missing_tools" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">', '<thead id="grid-table-header">', "<tr>", '<th class="datasetRow">Workflows</th>', '<th class="datasetRow">Tool IDs</th>', '<th class="datasetRow">Shed</th>', '<th class="datasetRow">Name</th>', '<th class="datasetRow">Owner</th>', '<th class="datasetRow">Actions</th>', "</tr>", "</thead>", "<tbody>", "<% _.each(Object.keys(workflows), function(workflow_key) { %>", '<% var workflow_details = workflow_key.split("/"); %>', "<% var workflow = workflows[workflow_key]; %>", "<tr>", '<td class="datasetRow">', '<ul class="workflow_names">', "<% _.each(workflow.workflows.sort(), function(wf) { %>", '<li class="workflow_names"><%= wf %></li>', "<% }); %>", "</ul>", "</td>", '<td class="datasetRow">', '<ul class="workflow_tools">', "<% _.each(workflow.tools.sort(), function(tool) { %>", '<li class="workflow_tools"><%= tool %></li>', "<% }); %>", "</ul>", "</td>", '<td class="datasetRow"><%= workflow_details[0] %></td>', '<td class="datasetRow"><%= workflow_details[2] %></td>', '<td class="datasetRow"><%= workflow_details[1] %></td>', '<td class="datasetRow">', '<ul class="workflow_tools">', '<li class="workflow_tools"><input type="button" class="show_wf_repo btn btn-primary" data-shed="<%= workflow_details[0] %>" data-owner="<%= workflow_details[1] %>" data-repo="<%= workflow_details[2] %>" data-toolids="<%= workflow.tools.join(",") %>" value="Preview" /></li>', '<li><input type="button" class="queue_wf_repo btn btn-primary" data-shed="<%= workflow_details[0] %>" data-owner="<%= workflow_details[1] %>" data-repo="<%= workflow_details[2] %>" data-toolids="<%= workflow.tools.join(",") %>" value="Add to queue" /></li>', "</ul>", "</td>", "</tr>", "<% }); %>", "</ul>", "</div>" ].join(""))
    });
    return {
        RepoQueueView: View
    };
});