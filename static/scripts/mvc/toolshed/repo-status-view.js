define("mvc/toolshed/repo-status-view", ["exports", "utils/localization", "mvc/toolshed/toolshed-model", "mvc/toolshed/util"], function(exports, _localization, _toolshedModel, _util) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _toolshedModel2 = _interopRequireDefault(_toolshedModel);

    var _util2 = _interopRequireDefault(_util);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var ToolShedRepoStatusView = Backbone.View.extend({
        el: "#center",

        initialize: function initialize(options) {
            var self = this;
            this.options = _.defaults(this.options || [{}], options, this.defaults);
            this.model = new _toolshedModel2.default.RepoStatus();
            this.listenTo(this.model, "sync", this.render);
            this.model.url += "?repositories=" + this.options.repositories.join("|");
            this.model.fetch();
            this.timer = setInterval(function(self) {
                var terminal_states = ["installed", "error"];
                var all_done = true;
                _.some(self.model.models, function(repository) {
                    repo_id = repository.get("id");
                    var repo_status = repository.get("status").toLowerCase();
                    if (terminal_states.indexOf(repo_status) === -1) {
                        all_done = false;
                        return true;
                    }
                });
                if (all_done) {
                    clearInterval(self.timer);
                } else {
                    self.model.fetch();
                }
            }, 2000, this);
        },

        close: function close() {
            clearInterval(this.timer);
        },

        render: function render(options) {
            this.options = _.extend(this.options, options);
            var repo_status_template = this.templateRepoStatus;
            this.$el.html(repo_status_template({
                title: (0, _localization2.default)("Repository Status"),
                repositories: this.model.models,
                queue: _util2.default.queueLength()
            }));
            $("#center").css("overflow", "auto");
            this.bindEvents();
        },

        bindEvents: function bindEvents() {
            var that = this;
        },

        reDraw: function reDraw(options) {
            this.$el.empty();
            this.initialize(options);
        },

        templateRepoStatus: _.template(['<div class="unified-panel-header" id="panel_header" unselectable="on">', '<div class="unified-panel-header-inner"><%= title %></div>', '<div class="unified-panel-header-inner" style="position: absolute; right: 5px; top: 0px;"><a href="#/queue">Repository Queue (<%= queue %>)</a></div>', "</div>", '<style type="text/css">', ".state-color-new,", ".state-color-deactivated,", ".state-color-uninstalled { border-color:#bfbfbf; background:#eee }", ".state-color-cloning,", ".state-color-setting-tool-versions,", ".state-color-installing-repository-dependencies,", ".state-color-installing-tool-dependencies,", ".state-color-loading-proprietary-datatypes { border-color:#AAAA66; background:#FFFFCC }", ".state-color-installed { border-color:#20b520; background:#b0f1b0 }", ".state-color-error { border-color:#dd1b15; background:#f9c7c5 }", "</style>", '<table id="grid-table" class="grid">', '<thead id="grid-table-header">', "<tr>", '<th id="null-header">Name<span class="sort-arrow"></span></th>', '<th id="null-header">Description<span class="sort-arrow"></span></th>', '<th id="null-header">Owner<span class="sort-arrow"></span></th>', '<th id="null-header">Revision<span class="sort-arrow"></span></th>', '<th id="null-header">Installation Status<span class="sort-arrow"></span></th>', "</tr>", "</thead>", '<tbody id="grid-table-body">', "<% _.each(repositories, function(repository) { %>", "<tr>", "<td>", '<div id="" class="">', '<label id="repo-name-<%= repository.get("id") %>" for="<%= repository.get("id") %>">', '<%= repository.get("name") %>', "</label>", "</div>", "</td>", "<td>", '<div id="" class="">', '<label id="repo-desc-<%= repository.get("id") %>" for="<%= repository.get("id") %>">', '<%= repository.get("description") %>', "</label>", "</div>", "</td>", "<td>", '<div id="" class="">', '<label id="repo-user-<%= repository.get("id") %>" for="<%= repository.get("id") %>">', '<%= repository.get("owner") %>', "</label>", "</div>", "</td>", "<td>", '<div id="" class="">', '<label id="repo-changeset-<%= repository.get("id") %>" for="<%= repository.get("id") %>">', '<%= repository.get("changeset_revision") %>', "</label>", "</div>", "</td>", "<td>", '<div id="" class="">', '<label id="RepositoryStatus-<%= repository.get("id") %>" for="<%= repository.get("id") %>">', '<div class="repo-status count-box state-color-<%= repository.get("status").toLowerCase().replace(/ /g, "-") %>" id="RepositoryStatus-<%= repository.get("id") %>">', '<%= repository.get("status") %>', "</div>", "</label>", "</div>", "</td>", "</tr>", "<% }); %>", "</tbody>", '<tfoot id="grid-table-footer"></tfoot>', "</table>"].join(""))
    });

    exports.default = {
        RepoStatus: ToolShedRepoStatusView
    };
});
//# sourceMappingURL=../../../maps/mvc/toolshed/repo-status-view.js.map
