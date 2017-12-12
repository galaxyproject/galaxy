define("admin.toolshed", ["exports", "mvc/toolshed/shed-list-view", "mvc/toolshed/categories-view", "mvc/toolshed/repositories-view", "mvc/toolshed/repository-view", "mvc/toolshed/repository-queue-view", "mvc/toolshed/repo-status-view", "mvc/toolshed/workflows-view"], function(exports, _shedListView, _categoriesView, _repositoriesView, _repositoryView, _repositoryQueueView, _repoStatusView, _workflowsView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _shedListView2 = _interopRequireDefault(_shedListView);

    var _categoriesView2 = _interopRequireDefault(_categoriesView);

    var _repositoriesView2 = _interopRequireDefault(_repositoriesView);

    var _repositoryView2 = _interopRequireDefault(_repositoryView);

    var _repositoryQueueView2 = _interopRequireDefault(_repositoryQueueView);

    var _repoStatusView2 = _interopRequireDefault(_repoStatusView);

    var _workflowsView2 = _interopRequireDefault(_workflowsView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var AdminToolshedRouter = Backbone.Router.extend({
        initialize: function initialize() {
            this.routesHit = 0;
            // keep count of number of routes handled by the application
            Backbone.history.on("route", function() {
                this.routesHit++;
            }, this);
            this.bind("route", this.trackPageview);
        },

        routes: {
            "": "toolsheds",
            sheds: "toolsheds",
            queue: "queue",
            workflows: "workflows",
            "status/r/:repositories": "status",
            status: "status",
            "categories/s/:tool_shed": "categories",
            "category/s/:tool_shed/c/:cateory_id": "repositories",
            "repository/s/:tool_shed/r/:repository_id": "repository"
        },

        /**
         * If more than one route has been hit the user did not land on current
         * page directly so we can go back safely. Otherwise go to the home page.
         * Use replaceState if available so the navigation doesn't create an
         * extra history entry
         */
        back: function back() {
            if (this.routesHit > 1) {
                window.history.back();
            } else {
                this.navigate("#", {
                    trigger: true,
                    replace: true
                });
            }
        }
    });

    var GalaxyAdminToolshedApp = Backbone.View.extend({
        app_config: {
            known_views: ["toolsheds", "queue", "status", "categories", "repositories", "repoository"]
        },

        initialize: function initialize() {
            Galaxy.admintoolshedapp = this;
            this.admin_toolshed_router = new AdminToolshedRouter();

            this.admin_toolshed_router.on("route:queue", function() {
                if (Galaxy.admintoolshedapp.adminRepoQueueView) {
                    Galaxy.admintoolshedapp.adminRepoQueueView.reDraw();
                } else {
                    Galaxy.admintoolshedapp.adminRepoQueueView = new _repositoryQueueView2.default.RepoQueueView();
                }
            });
            this.admin_toolshed_router.on("route:toolsheds", function() {
                if (Galaxy.admintoolshedapp.adminShedListView) {
                    Galaxy.admintoolshedapp.adminShedListView.reDraw();
                } else {
                    Galaxy.admintoolshedapp.adminShedListView = new _shedListView2.default.ShedListView();
                }
            });
            this.admin_toolshed_router.on("route:categories", function(tool_shed) {
                if (Galaxy.admintoolshedapp.adminShedCategoriesView) {
                    Galaxy.admintoolshedapp.adminShedCategoriesView.reDraw({
                        tool_shed: tool_shed.replace(/\//g, "%2f")
                    });
                } else {
                    Galaxy.admintoolshedapp.adminShedCategoriesView = new _categoriesView2.default.CategoryView({
                        tool_shed: tool_shed.replace(/\//g, "%2f")
                    });
                }
            });
            this.admin_toolshed_router.on("route:repositories", function(tool_shed, category_id) {
                if (Galaxy.admintoolshedapp.adminShedCategoryView) {
                    Galaxy.admintoolshedapp.adminShedCategoryView.reDraw({
                        tool_shed: tool_shed.replace(/\//g, "%2f"),
                        category_id: category_id
                    });
                } else {
                    Galaxy.admintoolshedapp.adminShedCategoryView = new _repositoriesView2.default.Category({
                        tool_shed: tool_shed.replace(/\//g, "%2f"),
                        category_id: category_id
                    });
                }
            });
            this.admin_toolshed_router.on("route:repository", function(tool_shed, repository_id) {
                if (Galaxy.admintoolshedapp.adminRepositoryView) {
                    Galaxy.admintoolshedapp.adminRepositoryView.reDraw({
                        tool_shed: tool_shed.replace(/\//g, "%2f"),
                        repository_id: repository_id
                    });
                } else {
                    Galaxy.admintoolshedapp.adminRepositoryView = new _repositoryView2.default.RepoDetails({
                        tool_shed: tool_shed.replace(/\//g, "%2f"),
                        repository_id: repository_id
                    });
                }
            });
            this.admin_toolshed_router.on("route:status", function(repositories) {
                if (Galaxy.admintoolshedapp.adminRepoStatusView) {
                    Galaxy.admintoolshedapp.adminRepoStatusView.reDraw({
                        repositories: repositories.split("|")
                    });
                } else {
                    Galaxy.admintoolshedapp.adminRepoStatusView = new _repoStatusView2.default.RepoStatus({
                        repositories: repositories.split("|")
                    });
                }
            });
            this.admin_toolshed_router.on("route:workflows", function() {
                if (Galaxy.admintoolshedapp.adminWorkflowsView) {
                    Galaxy.admintoolshedapp.adminWorkflowsView.reDraw();
                } else {
                    Galaxy.admintoolshedapp.adminWorkflowsView = new _workflowsView2.default.Workflows();
                }
            });

            Backbone.history.start({
                pushState: false
            });
        }
    });

    exports.default = {
        GalaxyApp: GalaxyAdminToolshedApp
    };
});
//# sourceMappingURL=../maps/admin.toolshed.js.map
