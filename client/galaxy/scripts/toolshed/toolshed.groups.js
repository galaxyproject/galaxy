// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN TOOLSHED GROUP MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

import mod_group_list from "groups/group-list-view";
import mod_group_detail from "groups/group-detail-view";
import mod_group_model from "groups/group-model";

// ============================================================================
// ROUTER
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

    initialize: function() {
        window.globalTS.groups = this;

        this.ts_router = new ToolshedRouter();
        this.ts_router.on("route:groups", function() {
            window.globalTS.groups.groupListView = new mod_group_list.GroupListView();
        });

        this.ts_router.on("route:group_page", function(group_id) {
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
