import Vue from "vue";
import VueRouter from "vue-router";

import Analysis from "entry/app/modules/Analysis";
import DatasetDetails from "components/DatasetInformation/DatasetDetails";
import HistoryImport from "components/HistoryImport";
import InteractiveTools from "components/InteractiveTools/InteractiveTools";
import NewUserConfirmation from "components/login/NewUserConfirmation";
import ToolsJson from "components/ToolsView/ToolsSchemaJson/ToolsJson";
import ToolsView from "components/ToolsView/ToolsView";
import WorkflowEditorModule from "entry/app/modules/WorkflowEditor";

Vue.use(VueRouter);

// patches $router.push() to trigger an event and hide duplication warnings
const originalPush = VueRouter.prototype.push;
VueRouter.prototype.push = function push(location) {
    return originalPush.call(this, location).catch((err) => {
        // always emit event when a route is pushed
        this.app.$emit("router-push");
        // avoid console warning when user clicks to revisit same route
        if (err.name !== "NavigationDuplicated") {
            throw err;
        }
    });
};

const router = new VueRouter({
    routes: [
        {
            path: "/",
            component: Analysis,
            children: [
                {
                    path: "datasets/:datasetId/details",
                    component: DatasetDetails,
                    props: true,
                },
                {
                    path: "login/confirm",
                    component: NewUserConfirmation,
                },
                {
                    path: "tools/view",
                    component: ToolsView,
                },
                {
                    path: "tools/json",
                    component: ToolsJson,
                },
                {
                    path: "interactivetool_entry_points/list",
                    component: InteractiveTools,
                },
                {
                    path: "histories/import",
                    component: HistoryImport,
                },
            ],
        },
        { path: "/workflows/edit", component: WorkflowEditorModule },
    ],
});

export default router;
