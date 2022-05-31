import Vue from "vue";
import VueRouter from "vue-router";

import Analysis from "entry/app/modules/Analysis";
import { CloudAuth } from "components/User/CloudAuth";
import DatasetDetails from "components/DatasetInformation/DatasetDetails";
import DatasetError from "components/DatasetInformation/DatasetError";
import { ExternalIdentities } from "components/User/ExternalIdentities";
import HistoryImport from "components/HistoryImport";
import InteractiveTools from "components/InteractiveTools/InteractiveTools";
import NewUserConfirmation from "components/login/NewUserConfirmation";
import ToolsJson from "components/ToolsView/ToolsSchemaJson/ToolsJson";
import ToolsView from "components/ToolsView/ToolsView";
import UserPreferences from "components/User/UserPreferences";
import WorkflowEditorModule from "entry/app/modules/WorkflowEditor";
import CenterPanel from "entry/app/modules/CenterPanel";
import { StorageDashboardRouter } from "components/User/DiskUsage";

Vue.use(VueRouter);

// patches $router.push() to trigger an event and hide duplication warnings
const originalPush = VueRouter.prototype.push;
VueRouter.prototype.push = function push(location) {
    // always emit event when a route is pushed
    this.app.$emit("router-push");
    // avoid console warning when user clicks to revisit same route
    return originalPush.call(this, location).catch((err) => {
        if (err.name !== "NavigationDuplicated") {
            throw err;
        }
    });
};

// produces the client router
export function getRouter(Galaxy) {
    return new VueRouter({
        routes: [
            {
                path: "/",
                component: Analysis,
                children: [
                    {
                        path: "",
                        component: CenterPanel,
                        props: { src: "welcome" },
                    },
                    {
                        path: "datasets/:datasetId/details",
                        component: DatasetDetails,
                        props: true,
                    },
                    {
                        path: "datasets/:datasetId/error",
                        component: DatasetError,
                        props: true,
                    },
                    {
                        path: "histories/import",
                        component: HistoryImport,
                    },
                    {
                        path: "interactivetool_entry_points/list",
                        component: InteractiveTools,
                    },
                    {
                        path: "login/confirm",
                        component: NewUserConfirmation,
                    },
                    {
                        path: "storage",
                        component: StorageDashboardRouter,
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
                        path: "user",
                        component: UserPreferences,
                        props: {
                            enableQuotas: Galaxy.config.enable_quotas,
                            userId: Galaxy.user.id,
                        },
                    },
                    {
                        path: "user/cloud_auth",
                        component: CloudAuth,
                    },
                    {
                        path: "user/external_ids",
                        component: ExternalIdentities,
                    },
                ],
            },
            { path: "/workflows/edit", component: WorkflowEditorModule },
        ],
    });
}
