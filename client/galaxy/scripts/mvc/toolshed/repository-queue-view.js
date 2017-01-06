define(['mvc/toolshed/toolshed-model', 'mvc/toolshed/util'], function(toolshed_model, toolshed_util) {

    var ToolShedRepoQueueView = Backbone.View.extend({

        el: '#center',

        defaults: {
            tool_shed: "https://toolshed.g2.bx.psu.edu/"
        },

        initialize: function(options) {
            var self = this;
            this.options = _.defaults(this.options || options, this.defaults);
            this.model = new toolshed_model.RepoQueue();
            this.listenTo(this.model, 'sync', this.render);
            this.model.url = this.model.url + '?tool_shed_url=' + this.options.tool_shed;
            this.model.fetch();
        },

        render: function(options) {
            this.options = _.extend(this.options, options);
            this.options.categories = this.model.models;
            var category_list_template = this.templateCategoryList;
            this.$el.html(category_list_template(this.options));
            $("#center").css('overflow', 'auto');
            this.bindEvents();
        },

        bindEvents: function() {
            // toolshed_util.initSearch('search_box');
        },

        reDraw: function(options) {
            this.$el.empty();
            this.model.url = this.model.url + '?tool_shed_url=' + this.options.tool_shed;
            this.initialize(options);
            // this.model.fetch();
            // this.render(options);
        },
        templateRepoQueue: _.template([
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
                        '<% _.each(repositories, function(repository) { %>',
                            '<tr id="queued_repository_<%= repository.id %>">',
                                '<td class="datasetRow">',
                                    '<input class="btn btn-primary install_one" data-repokey="<%= repository.queue_key %>" type="submit" id="install_repository_<%= repository.id %>" name="install_repository" value="Install now" />',
                                '</td>',
                                '<td class="datasetRow">',
                                    '<input class="btn btn-primary remove_one" data-repokey="<%= repository.queue_key %>" type="submit" id="unqueue_repository_<%= repository.id %>" name="unqueue_repository" value="Remove from queue" />',
                                '</td>',
                                '<td class="datasetRow"><%= repository.tool_shed_url %></td>',
                                '<td class="datasetRow"><%= repository.name %></td>',
                                '<td class="datasetRow"><%= repository.owner %></td>',
                                '<td class="datasetRow"><%= repository.changeset %></td>',
                            '</tr>',
                        '<% }); %>',
                    '</tbody>',
                '</table>',
                '<input type="button" class="btn btn-primary" id="from_workflow" value="Add from workflow" />',
            '</div>',
            ].join(''));
    });

    return {
        RepoQueue: ToolShedRepoQueueView,
    };

});