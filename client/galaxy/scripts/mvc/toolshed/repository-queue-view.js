define(['mvc/toolshed/toolshed-model', 'mvc/toolshed/util'], function(toolshed_model, toolshed_util) {

    var View = Backbone.View.extend({

        el: '#center',

        defaults: {},

        initialize: function(options) {
            var that = this;
            this.model = new toolshed_model.RepoQueue();
            this.listenTo(this.model, 'sync', this.render);
            this.model.fetch();
            that.render();
        },

        render: function(options) {
            var that = this;
            var repo_queue_template = that.templateRepoQueue;
            console.log({model: that.model.models[0].attributes});
            var repositories = that.model.models;
            console.log(repositories);
            that.$el.html(repo_queue_template({repositories: repositories}));
            $("#center").css('overflow', 'auto');
            that.bindEvents();
        },

        bindEvents: function() {
            // toolshed_util.initSearch('search_box');
        },

        reDraw: function(options) {
            this.$el.empty();
            this.initialize(options);
            // this.model.fetch();
            // this.render(options);
        },

        templateRepoQueue: _.template([
            '<div class="tab-pane" id="panel_header" id="repository_queue">',
                '<table id="queued_repositories" class="grid" border="0" cellpadding="2" cellspacing="2" width="100%">',
                    '<thead id="grid-table-header">',
                        '<tr>',
                            '<th class="datasetRow">Name</th>',
                            '<th class="datasetRow">Owner</th>',
                            '<th class="datasetRow">Revision</th>',
                            '<th class="datasetRow">ToolShed</th>',
                            '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="install_all" name="install_all" value="Install all" /></th>',
                            '<th class="datasetRow"><input class="btn btn-primary" type="submit" id="clear_queue" name="clear_queue" value="Clear queue" /></th>',
                        '</tr>',
                    '</thead>',
                    '<tbody>',
                        '<% _.each(repositories, function(repository) { %>',
                                '<tr id="queued_repository_<%= repository.get("id") %>">',
                                    '<td class="datasetRow"><%= repository.get("repository").name %></td>',
                                    '<td class="datasetRow"><%= repository.get("repository").owner %></td>',
                                    '<td class="datasetRow"><%= repository.get("changeset_revision") %></td>',
                                    '<td class="datasetRow"><%= repository.get("tool_shed_url") %></td>',
                                    '<td class="datasetRow">',
                                        '<input class="btn btn-primary install_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="install_repository_<%= repository.get("id") %>" name="install_repository" value="Install now" />',
                                    '</td>',
                                    '<td class="datasetRow">',
                                        '<input class="btn btn-primary remove_one" data-repokey="<%= repository.get("queue_key") %>" type="submit" id="unqueue_repository_<%= repository.get("id") %>" name="unqueue_repository" value="Remove from queue" />',
                                    '</td>',
                                '</tr>',
                        '<% }); %>',
                    '</tbody>',
                '</table>',
                '<input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />',
            '</div>',
            ].join(''))
    });

    return {
        RepoQueueView: View,
    };

});