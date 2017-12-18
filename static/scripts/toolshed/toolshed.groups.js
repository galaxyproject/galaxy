define("toolshed/toolshed.groups", ["exports", "toolshed/groups/group-list-view", "toolshed/groups/group-detail-view"], function(exports, _groupListView, _groupDetailView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _groupListView2 = _interopRequireDefault(_groupListView);

    var _groupDetailView2 = _interopRequireDefault(_groupDetailView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // ============================================================================
    // ROUTER
    // MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
    // === MAIN TOOLSHED GROUP MODULE ====
    // MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

    var ToolshedRouter = Backbone.Router.extend({
        routes: {
            "": "groups",
            ":group_id": "group_page"
        }
    });

    var ToolshedGroups = Backbone.View.extend({
        groupListView: null,
        groupDetailView: null,
        collection: null,

        initialize: function initialize() {
            window.globalTS.groups = this;

            this.ts_router = new ToolshedRouter();
            this.ts_router.on("route:groups", function() {
                window.globalTS.groups.groupListView = new _groupListView2.default.GroupListView();
            });

            this.ts_router.on("route:group_page", function(group_id) {
                window.globalTS.groups.groupDetailView = new _groupDetailView2.default.GroupDetailView({
                    group_id: group_id
                });
            });

            Backbone.history.start({
                pushState: false
            });
        }
    });

    exports.default = {
        ToolshedGroups: ToolshedGroups
    };
});
//# sourceMappingURL=../../maps/toolshed/toolshed.groups.js.map
