import _l from "utils/localization";
import toolshed_model from "mvc/toolshed/toolshed-model";
import toolshed_util from "mvc/toolshed/util";
var View = Backbone.View.extend({
    el: "#center",

    defaults: [],

    initialize: function(options) {
        var that = this;
        this.model = new toolshed_model.RepoQueue();
        this.listenTo(this.model, "sync", this.render);
        this.model.fetch();
        that.render();
    },

    render: function(options) {
        var that = this;
        var repo_queue_template = that.templateRepoQueue;
        var repositories = that.model.models;
        that.$el.html(
            repo_queue_template({
                title: _l("Repository Installation Queue"),
                repositories: repositories,
                empty: _l("No repositories in queue."),
                queue: toolshed_util.queueLength()
            })
        );
        $("#center").css("overflow", "auto");
        that.bindEvents();
    },

    bindEvents: function() {
        var that = this;
        $(".install_one").on("click", function() {
            var repository_metadata = that.loadFromQueue($(this).attr("data-repokey"));
            that.installFromQueue(repository_metadata, $(this).attr("data-repokey"));
        });
        $(".remove_one").on("click", function() {
            var queue_key = $(this).attr("data-repokey");
            var repo_queue = JSON.parse(localStorage.repositories);
            if (repo_queue.hasOwnProperty(queue_key)) {
                var repository_id = repo_queue[queue_key].repository.id;
                delete repo_queue[queue_key];
                $(`#queued_repository_${repository_id}`).remove();
            }
            localStorage.repositories = JSON.stringify(repo_queue);
        });
        $("#clear_queue").on("click", () => {
            localStorage.repositories = "{}";
        });
        $("#from_workflow").on("click", () => {
            Backbone.history.navigate("workflows", {
                trigger: true,
                replace: true
            });
        });
    },

    installFromQueue: function(repository_metadata, queue_key) {
        var that = this;
        var params = Object();
        params.install_tool_dependencies = repository_metadata.install_tool_dependencies;
        params.install_repository_dependencies = repository_metadata.install_repository_dependencies;
        params.install_resolver_dependencies = repository_metadata.install_resolver_dependencies;
        params.tool_panel_section = repository_metadata.tool_panel_section;
        params.shed_tool_conf = repository_metadata.shed_tool_conf;
        params.repositories = JSON.stringify([
            [repository_metadata.repository.id, repository_metadata.changeset_revision]
        ]);
        params.tool_shed_repository_ids = JSON.stringify([repository_metadata.repository.id]);
        params.tool_shed_url = queue_key.split("|")[0];
        params.changeset = repository_metadata.changeset_revision;
        var url = `${Galaxy.root}api/tool_shed_repositories/install?async=True`;
        $(`#queued_repository_${repository_metadata.repository.id}`).remove();
        if (localStorage.repositories) {
            if (queue_key === undefined) {
                queue_key = toolshed_util.queueKey(repository_metadata);
            }
            var repository_queue = JSON.parse(localStorage.repositories);
            if (repository_queue.hasOwnProperty(queue_key)) {
                delete repository_queue[queue_key];
                localStorage.repositories = JSON.stringify(repository_queue);
            }
        }

        $.post(url, params, data => {
            var iri_params = JSON.parse(data);
            var repositories = iri_params.repositories;
            var new_route = `status/r/${repositories.join("|")}`;
            $.post(`${Galaxy.root}admin_toolshed/install_repositories`, iri_params, data => {
                console.log("Initializing repository installation succeeded");
            });
            Backbone.history.navigate(new_route, {
                trigger: true,
                replace: true
            });
        });
    },

    loadFromQueue: function(queue_key) {
        var repository_queue = JSON.parse(localStorage.repositories);
        if (repository_queue.hasOwnProperty(queue_key)) {
            return repository_queue[queue_key];
        }
        return this.defaults;
    },

    reDraw: function(options) {
        this.$el.empty();
        this.initialize(options);
        this.model.fetch();
        this.render(options);
    },

    templateRepoQueue: _.template(
        [
            '<div class="unified-panel-header" id="panel_header" unselectable="on">',
            '<div class="unified-panel-header-inner"><%= title %></div>',
            '<div class="unified-panel-header-inner" style="position: absolute; right: 5px; top: 0px;"><a href="#/queue">Repository Queue (<%= queue %>)</a></div>',
            "</div>",
            '<div class="tab-pane" id="panel_header" id="repository_queue">',
            '<table id="queued_repositories" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">',
            '<thead id="grid-table-header">',
            "<tr>",
            '<th class="datasetRow">Name</th>',
            '<th class="datasetRow">Owner</th>',
            '<th class="datasetRow">Revision</th>',
            '<th class="datasetRow">ToolShed</th>',
            '<th class="datasetRow">Install</th>',
            '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="clear_queue" name="clear_queue" value="Clear queue" /></th>',
            "</tr>",
            "</thead>",
            "<tbody>",
            "<% if (repositories.length > 0) { %>",
            "<% _.each(repositories, function(repository) { %>",
            '<tr id="queued_repository_<%= repository.get("id") %>">',
            '<td class="datasetRow"><%= repository.get("repository").name %></td>',
            '<td class="datasetRow"><%= repository.get("repository").owner %></td>',
            '<td class="datasetRow"><%= repository.get("changeset_revision") %></td>',
            '<td class="datasetRow"><%= repository.get("tool_shed_url") %></td>',
            '<td class="datasetRow">',
            '<input class="btn btn-primary install_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="install_repository_<%= repository.get("id") %>" name="install_repository" value="Install now" />',
            "</td>",
            '<td class="datasetRow">',
            '<input class="btn btn-primary remove_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="unqueue_repository_<%= repository.get("id") %>" name="unqueue_repository" value="Remove from queue" />',
            "</td>",
            "</tr>",
            "<% }); %>",
            "<% } else { %>",
            '<tr><td colspan="6"><%= empty %></td></tr>',
            "<% } %>",
            "</tbody>",
            "</table>",
            '<input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />',
            "</div>"
        ].join("")
    )
});

export default {
    RepoQueueView: View
};
