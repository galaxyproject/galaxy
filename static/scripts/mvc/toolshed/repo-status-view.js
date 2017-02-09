define([ "mvc/toolshed/toolshed-model" ], function(toolshed_model) {
    var ToolShedRepoStatusView = Backbone.View.extend({
        el: "#center",
        initialize: function(options) {
            this.options = _.defaults(this.options || [ {} ], options, this.defaults), this.model = new toolshed_model.RepoStatus(), 
            this.listenTo(this.model, "sync", this.render), this.model.url += "?repositories=" + this.options.repositories.join("|"), 
            this.model.fetch(), this.timer = setInterval(function(self) {
                var terminal_states = [ "installed", "error" ], all_done = !0;
                _.some(self.model.models, function(repository) {
                    return repo_id = repository.get("id"), repo_status = repository.get("status").toLowerCase(), 
                    -1 === terminal_states.indexOf(repo_status) ? (all_done = !1, !0) : void 0;
                }), all_done ? clearInterval(self.timer) : self.model.fetch();
            }, 2e3, this);
        },
        close: function() {
            clearInterval(this.timer);
        },
        render: function(options) {
            this.options = _.extend(this.options, options);
            var repo_status_template = this.templateRepoStatus;
            this.$el.html(repo_status_template({
                repositories: this.model.models
            })), $("#center").css("overflow", "auto"), this.bindEvents();
        },
        bindEvents: function() {
        },
        reDraw: function(options) {
            this.$el.empty(), this.initialize(options);
        },
        templateRepoStatus: _.template([ '<table id="grid-table" class="grid">', '<thead id="grid-table-header">', "<tr>", '<th id="null-header">Name<span class="sort-arrow"></span></th>', '<th id="null-header">Description<span class="sort-arrow"></span></th>', '<th id="null-header">Owner<span class="sort-arrow"></span></th>', '<th id="null-header">Revision<span class="sort-arrow"></span></th>', '<th id="null-header">Installation Status<span class="sort-arrow"></span></th>', "</tr>", "</thead>", '<tbody id="grid-table-body">', "<% _.each(repositories, function(repository) { %>", "<tr>", '<td><div id="" class=""><label id="repo-name-<%= repository.get("id") %>" for="<%= repository.get("id") %>"><%= repository.get("name") %></label></div></td>', '<td><div id="" class=""><label id="repo-desc-<%= repository.get("id") %>" for="<%= repository.get("id") %>"><%= repository.get("description") %></label></div></td>', '<td><div id="" class=""><label id="repo-user-<%= repository.get("id") %>" for="<%= repository.get("id") %>"><%= repository.get("owner") %></label></div></td>', '<td><div id="" class=""><label id="repo-changeset-<%= repository.get("id") %>" for="<%= repository.get("id") %>"><%= repository.get("changeset_revision") %></label></div></td>', '<td><div id="" class=""><label id="RepositoryStatus-<%= repository.get("id") %>" for="<%= repository.get("id") %>"><div class="repo-status count-box state-color-<%= repository.get("status").toLowerCase() %>" id="RepositoryStatus-<%= repository.get("id") %>"><%= repository.get("status") %></div></label></div></td>', "</tr>", "<% }); %>", "</tbody>", '<tfoot id="grid-table-footer"></tfoot>', "</table>" ].join(""))
    });
    return {
        RepoStatus: ToolShedRepoStatusView
    };
});