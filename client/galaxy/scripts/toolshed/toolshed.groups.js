// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN TOOLSHED GROUP MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

import Backbone from "backbone";
import mod_group_list from "toolshed/groups/group-list-view";
import mod_group_detail from "toolshed/groups/group-detail-view";

// ============================================================================
// ROUTER
const ToolshedRouter = Backbone.Router.extend({
    routes: {
        "": "groups",
        ":group_id": "group_page"
    }
});

const ToolshedGroups = Backbone.View.extend({
    groupListView: null,
    groupDetailView: null,
    collection: null,

    initialize: function() {
        window.globalTS.groups = this;

        this.ts_router = new ToolshedRouter();
        this.ts_router.on("route:groups", () => {
            window.globalTS.groups.groupListView = new mod_group_list.GroupListView();
        });

        this.ts_router.on("route:group_page", group_id => {
            window.globalTS.groups.groupDetailView = new mod_group_detail.GroupDetailView({
                group_id: group_id
            });
        });

        Backbone.history.start({ pushState: false });
    }
});

export default {
    ToolshedGroups: ToolshedGroups
};
