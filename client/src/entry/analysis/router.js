import { getGalaxyInstance } from "app";
import CitationsList from "components/Citation/CitationsList";
import ClientError from "components/ClientError";
import CollectionEditView from "components/Collections/common/CollectionEditView";
import DatasetList from "components/Dataset/DatasetList";
import DatasetAttributes from "components/DatasetInformation/DatasetAttributes";
import DatasetDetails from "components/DatasetInformation/DatasetDetails";
import DatasetError from "components/DatasetInformation/DatasetError";
import FormGeneric from "components/Form/FormGeneric";
import GalaxyWizard from "components/GalaxyWizard";
import HelpTerm from "components/Help/HelpTerm";
import HistoryExportTasks from "components/History/Export/HistoryExport";
import HistoryPublished from "components/History/HistoryPublished";
import HistoryView from "components/History/HistoryView";
import HistoryMultipleView from "components/History/Multiple/MultipleView";
import { HistoryExport } from "components/HistoryExport/index";
import HistoryImport from "components/HistoryImport";
import InteractiveTools from "components/InteractiveTools/InteractiveTools";
import JobDetails from "components/JobInformation/JobDetails";
import CarbonEmissionsCalculations from "components/JobMetrics/CarbonEmissions/CarbonEmissionsCalculations";
import ToolLanding from "components/Landing/ToolLanding";
import WorkflowLanding from "components/Landing/WorkflowLanding";
import PageDisplay from "components/PageDisplay/PageDisplay";
import PageForm from "components/PageDisplay/PageForm";
import PageEditor from "components/PageEditor/PageEditor";
import ToolSuccess from "components/Tool/ToolSuccess";
import ToolsList from "components/ToolsList/ToolsList";
import ToolsJson from "components/ToolsView/ToolsSchemaJson/ToolsJson";
import TourList from "components/Tour/TourList";
import TourRunner from "components/Tour/TourRunner";
import { APIKey } from "components/User/APIKey";
import CustomBuilds from "components/User/CustomBuilds";
import { ExternalIdentities } from "components/User/ExternalIdentities";
import NotificationsPreferences from "components/User/Notifications/NotificationsPreferences";
import UserPreferences from "components/User/UserPreferences";
import UserPreferencesForm from "components/User/UserPreferencesForm";
import VisualizationsList from "components/Visualizations/Index";
import VisualizationCreate from "components/Visualizations/VisualizationCreate";
import VisualizationFrame from "components/Visualizations/VisualizationFrame";
import VisualizationPublished from "components/Visualizations/VisualizationPublished";
import HistoryInvocations from "components/Workflow/HistoryInvocations";
import TrsImport from "components/Workflow/Import/TrsImport";
import TrsSearch from "components/Workflow/Import/TrsSearch";
import InvocationReport from "components/Workflow/InvocationReport";
import WorkflowList from "components/Workflow/List/WorkflowList";
import StoredWorkflowInvocations from "components/Workflow/StoredWorkflowInvocations";
import WorkflowCreate from "components/Workflow/WorkflowCreate";
import WorkflowExport from "components/Workflow/WorkflowExport";
import WorkflowImport from "components/Workflow/WorkflowImport";
import Analysis from "entry/analysis/modules/Analysis";
import CenterFrame from "entry/analysis/modules/CenterFrame";
import Home from "entry/analysis/modules/Home";
import Login from "entry/analysis/modules/Login";
import WorkflowEditorModule from "entry/analysis/modules/WorkflowEditor";
import AdminRoutes from "entry/analysis/routes/admin-routes";
import LibraryRoutes from "entry/analysis/routes/library-routes";
import StorageDashboardRoutes from "entry/analysis/routes/storageDashboardRoutes";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";

import AvailableDatatypes from "@/components/AvailableDatatypes/AvailableDatatypes";
import CreateFileSourceInstance from "@/components/FileSources/Instances/CreateInstance";
import GridHistory from "@/components/Grid/GridHistory";
import GridPage from "@/components/Grid/GridPage";
import CreateObjectStoreInstance from "@/components/ObjectStore/Instances/CreateInstance";
import { requireAuth } from "@/router/guards";
import { parseBool } from "@/utils/utils";

import { patchRouterPush } from "./router-push";

import AboutGalaxy from "@/components/AboutGalaxy.vue";
import EditFileSourceInstance from "@/components/FileSources/Instances/EditInstance.vue";
import ManageFileSourceIndex from "@/components/FileSources/Instances/ManageIndex.vue";
import UpgradeFileSourceInstance from "@/components/FileSources/Instances/UpgradeInstance.vue";
import CreateUserFileSource from "@/components/FileSources/Templates/CreateUserFileSource.vue";
import GridInvocation from "@/components/Grid/GridInvocation.vue";
import GridVisualization from "@/components/Grid/GridVisualization.vue";
import HistoryArchiveWizard from "@/components/History/Archiving/HistoryArchiveWizard.vue";
import HistoryDatasetPermissions from "@/components/History/HistoryDatasetPermissions.vue";
import NotificationsList from "@/components/Notifications/NotificationsList.vue";
import EditObjectStoreInstance from "@/components/ObjectStore/Instances/EditInstance.vue";
import ManageObjectStoreIndex from "@/components/ObjectStore/Instances/ManageIndex.vue";
import UpgradeObjectStoreInstance from "@/components/ObjectStore/Instances/UpgradeInstance.vue";
import CreateUserObjectStore from "@/components/ObjectStore/Templates/CreateUserObjectStore.vue";
import Sharing from "@/components/Sharing/SharingPage.vue";
import HistoryStorageOverview from "@/components/User/DiskUsage/Visualizations/HistoryStorageOverview.vue";
import UserDatasetPermissions from "@/components/User/UserDatasetPermissions.vue";
import WorkflowPublished from "@/components/Workflow/Published/WorkflowPublished.vue";
import WorkflowInvocationState from "@/components/WorkflowInvocationState/WorkflowInvocationState.vue";

Vue.use(VueRouter);

// patches $router.push() to trigger an event and hide duplication warnings
patchRouterPush(VueRouter);

// redirect anon users
function redirectAnon(redirect = "") {
    const Galaxy = getGalaxyInstance();
    if (!Galaxy.user || !Galaxy.user.id) {
        if (redirect !== "") {
            return redirect;
        } else {
            return "/login/start";
        }
    }
}

// redirect logged in users
function redirectLoggedIn() {
    const Galaxy = getGalaxyInstance();
    if (Galaxy.user.id) {
        return "/";
    }
}

function redirectIf(condition, path) {
    if (condition) {
        return path;
    }
}

// produces the client router
export function getRouter(Galaxy) {
    const router = new VueRouter({
        base: getAppRoot(),
        mode: "history",
        routes: [
            /** Login entry route */
            {
                path: "/login/start",
                component: Login,
                redirect: redirectLoggedIn(),
            },
            /** Workflow editor */
            {
                path: "/workflows/edit",
                component: WorkflowEditorModule,
                redirect: redirectAnon(),
            },
            /** Published resources routes */
            {
                path: "/published/history",
                component: HistoryPublished,
                props: (route) => ({ id: route.query.id }),
            },
            {
                path: "/published/page",
                component: PageDisplay,
                props: (route) => ({ pageId: route.query.id }),
            },
            {
                path: "/published/visualization",
                component: VisualizationPublished,
                props: (route) => ({ id: route.query.id }),
            },
            {
                path: "/published/workflow",
                component: WorkflowPublished,
                props: (route) => ({
                    id: route.query.id,
                    zoom: route.query.zoom ? parseFloat(route.query.zoom) : undefined,
                    embed: route.query.embed ? parseBool(route.query.embed) : undefined,
                    showButtons: route.query.buttons ? parseBool(route.query.buttons) : undefined,
                    showAbout: route.query.about ? parseBool(route.query.about) : undefined,
                    showHeading: route.query.heading ? parseBool(route.query.heading) : undefined,
                    showMinimap: route.query.minimap ? parseBool(route.query.minimap) : undefined,
                    showZoomControls: route.query.zoom_controls ? parseBool(route.query.zoom_controls) : undefined,
                    initialX: route.query.initialX ? parseInt(route.query.initialX) : undefined,
                    initialY: route.query.initialY ? parseInt(route.query.initialY) : undefined,
                }),
            },
            {
                name: "error",
                path: "/client-error/",
                component: ClientError,
                props: true,
            },
            /** Analysis routes */
            {
                path: "/",
                component: Analysis,
                children: [
                    ...AdminRoutes,
                    ...LibraryRoutes,
                    ...StorageDashboardRoutes,
                    {
                        path: "",
                        alias: "root",
                        component: Home,
                        props: (route) => ({ config: Galaxy.config, query: route.query }),
                    },
                    {
                        path: "about",
                        component: AboutGalaxy,
                    },
                    {
                        path: "help/terms/:term",
                        component: HelpTerm,
                        props: true,
                    },
                    {
                        path: "carbon_emissions_calculations",
                        component: CarbonEmissionsCalculations,
                    },
                    {
                        path: "custom_builds",
                        component: CustomBuilds,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "collection/:collectionId/edit",
                        component: CollectionEditView,
                        props: true,
                    },
                    {
                        path: "datasets/:datasetId/edit",
                        component: DatasetAttributes,
                        props: true,
                    },
                    {
                        path: "datasets/list",
                        component: DatasetList,
                    },
                    {
                        path: "datasets/:datasetId/details",
                        name: "DatasetDetails",
                        component: DatasetDetails,
                        props: true,
                    },
                    {
                        path: "datasets/:datasetId/preview",
                        component: CenterFrame,
                        props: (route) => ({
                            src: `/datasets/${route.params.datasetId}/display/?preview=True`,
                            isPreview: true,
                        }),
                    },
                    {
                        // legacy route, potentially used by 3rd parties
                        path: "datasets/:datasetId/show_params",
                        component: DatasetDetails,
                        props: true,
                    },
                    {
                        path: "datasets/:datasetId/error",
                        component: DatasetError,
                        props: true,
                    },
                    {
                        path: "datatypes",
                        component: AvailableDatatypes,
                    },
                    {
                        path: "histories/import",
                        component: HistoryImport,
                    },
                    {
                        path: "histories/citations",
                        component: CitationsList,
                        props: (route) => ({
                            id: route.query.id,
                            source: "histories",
                        }),
                    },
                    {
                        path: "histories/rename",
                        component: FormGeneric,
                        props: (route) => ({
                            url: `/history/rename?id=${route.query.id}`,
                            redirect: "/histories/list",
                        }),
                    },
                    {
                        path: "histories/sharing",
                        component: Sharing,
                        props: (route) => ({
                            id: route.query.id,
                            pluralName: "Histories",
                            modelClass: "History",
                        }),
                    },
                    {
                        path: "histories/permissions",
                        component: HistoryDatasetPermissions,
                        props: (route) => ({
                            historyId: route.query.id,
                        }),
                    },
                    {
                        path: "histories/view",
                        component: HistoryView,
                        props: (route) => ({
                            id: route.query.id,
                        }),
                    },
                    {
                        path: "histories/view_multiple",
                        component: HistoryMultipleView,
                        props: true,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "histories/list_published",
                        component: GridHistory,
                        props: (route) => ({
                            activeList: "published",
                            username: route.query["f-username"],
                        }),
                    },
                    {
                        path: "histories/archived",
                        component: GridHistory,
                        props: {
                            activeList: "archived",
                        },
                        redirect: redirectAnon(),
                    },
                    {
                        path: "histories/list",
                        component: GridHistory,
                        props: {
                            activeList: "my",
                        },
                        redirect: redirectAnon("/histories/list_published"),
                    },
                    {
                        path: "histories/list_shared",
                        component: GridHistory,
                        props: {
                            activeList: "shared",
                        },
                        redirect: redirectAnon(),
                    },
                    {
                        path: "histories/:historyId/export",
                        get component() {
                            return Galaxy.config.enable_celery_tasks ? HistoryExportTasks : HistoryExport;
                        },
                        props: true,
                    },
                    {
                        path: "histories/:historyId/archive",
                        component: HistoryArchiveWizard,
                        props: true,
                    },
                    {
                        path: "histories/:historyId/invocations",
                        component: HistoryInvocations,
                        props: true,
                    },
                    {
                        path: "interactivetool_entry_points/list",
                        component: InteractiveTools,
                    },
                    {
                        path: "jobs/submission/success",
                        component: ToolSuccess,
                        props: true,
                    },
                    {
                        path: "jobs/:jobId/view",
                        component: JobDetails,
                        props: true,
                    },
                    {
                        path: "object_store_instances/create",
                        component: CreateUserObjectStore,
                    },
                    {
                        path: "object_store_instances/index",
                        component: ManageObjectStoreIndex,
                        props: (route) => {
                            return { message: route.query["message"] };
                        },
                    },
                    {
                        path: "object_store_instances/:instanceId/edit",
                        component: EditObjectStoreInstance,
                        props: true,
                    },
                    {
                        path: "object_store_instances/:instanceId/upgrade",
                        component: UpgradeObjectStoreInstance,
                        props: true,
                    },
                    {
                        path: "object_store_templates/:templateId/new",
                        component: CreateObjectStoreInstance,
                        props: true,
                    },
                    {
                        path: "file_source_instances/create",
                        component: CreateUserFileSource,
                        props: (route) => {
                            return {
                                error: route.params.error,
                            };
                        },
                    },
                    {
                        path: "file_source_instances/index",
                        component: ManageFileSourceIndex,
                        props: (route) => {
                            return { message: route.query["message"] };
                        },
                    },
                    {
                        path: "file_source_instances/:instanceId/edit",
                        component: EditFileSourceInstance,
                        props: true,
                    },
                    {
                        path: "file_source_instances/:instanceId/upgrade",
                        component: UpgradeFileSourceInstance,
                        props: true,
                    },
                    {
                        path: "file_source_templates/:templateId/new",
                        component: CreateFileSourceInstance,
                        props: (route) => ({
                            templateId: route.params.templateId,
                            uuid: route.query.uuid,
                        }),
                    },
                    {
                        path: "pages/create",
                        component: PageForm,
                        props: (route) => ({
                            invocationId: route.query.invocation_id,
                            mode: "create",
                        }),
                    },
                    {
                        path: "pages/edit",
                        component: PageForm,
                        props: (route) => ({
                            id: route.query.id,
                            mode: "edit",
                        }),
                    },
                    {
                        path: "/pages/editor",
                        component: PageEditor,
                        props: (route) => ({
                            pageId: route.query.id,
                        }),
                    },
                    {
                        path: "pages/sharing",
                        component: Sharing,
                        props: (route) => ({
                            id: route.query.id,
                            pluralName: "Pages",
                            modelClass: "Page",
                        }),
                    },
                    {
                        path: "pages/list",
                        component: GridPage,
                        props: {
                            activeList: "my",
                        },
                        redirect: redirectAnon("/pages/list_published"),
                    },
                    {
                        path: "pages/list_published",
                        component: GridPage,
                        props: (route) => ({
                            activeList: "published",
                            username: route.query["f-username"],
                        }),
                    },
                    {
                        path: "storage/history/:historyId",
                        name: "HistoryOverviewInAnalysis",
                        component: HistoryStorageOverview,
                        props: true,
                    },
                    {
                        path: "tours",
                        component: TourList,
                    },
                    {
                        path: "wizard",
                        component: GalaxyWizard,
                    },
                    {
                        path: "tours/:tourId",
                        component: TourRunner,
                        props: true,
                    },
                    {
                        path: "tools/list",
                        component: ToolsList,
                        props: (route) => {
                            return {
                                ...route.query,
                            };
                        },
                    },
                    {
                        path: "tools/json",
                        component: ToolsJson,
                    },
                    {
                        path: "tool_landings/:uuid",
                        component: ToolLanding,
                        props: true,
                    },
                    {
                        path: "workflow_landings/:uuid",
                        component: WorkflowLanding,
                        props: (route) => ({
                            uuid: route.params.uuid,
                            public: route.query.public.toLowerCase() === "true",
                            secret: route.query.client_secret,
                        }),
                        beforeEnter: requireAuth,
                    },
                    {
                        path: "user",
                        component: UserPreferences,
                        props: {
                            enableQuotas: Galaxy.config.enable_quotas,
                            userId: Galaxy.user.id,
                        },
                        redirect: redirectAnon(),
                    },
                    {
                        path: "user/api_key",
                        component: APIKey,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "user/external_ids",
                        component: ExternalIdentities,
                        redirect: redirectIf(Galaxy.config.fixed_delegated_auth, "/") || redirectAnon(),
                    },
                    {
                        path: "user/notifications",
                        component: NotificationsList,
                        redirect: redirectIf(!Galaxy.config.enable_notification_system, "/") || redirectAnon(),
                        props: (route) => ({
                            shouldOpenPreferences: Boolean(route.query.preferences),
                        }),
                    },
                    {
                        path: "user/notifications/preferences",
                        component: NotificationsPreferences,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "user/permissions",
                        component: UserDatasetPermissions,
                        redirect: redirectAnon(),
                        props: {
                            userId: Galaxy.user.id,
                        },
                    },
                    {
                        path: "user/:formId",
                        component: UserPreferencesForm,
                        props: true,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "visualizations",
                        component: VisualizationsList,
                        props: (route) => ({
                            datasetId: route.query.dataset_id,
                        }),
                    },
                    {
                        path: "visualizations/create/:visualization",
                        component: VisualizationCreate,
                        name: "VisualizationsCreate",
                        props: (route) => ({
                            visualization: route.params.visualization,
                        }),
                    },
                    {
                        path: "visualizations/display",
                        component: VisualizationFrame,
                        name: "VisualizationsDisplay",
                        props: (route) => ({
                            datasetId: route.query.dataset_id,
                            visualization: route.query.visualization,
                            visualizationId: route.query.visualization_id,
                        }),
                    },
                    {
                        path: "visualizations/edit",
                        component: FormGeneric,
                        props: (route) => ({
                            url: `/visualization/edit?id=${route.query.id}`,
                            redirect: "/visualizations/list",
                            active_tab: "visualization",
                        }),
                    },
                    {
                        path: "visualizations/sharing",
                        component: Sharing,
                        props: (route) => ({
                            id: route.query.id,
                            pluralName: "Visualizations",
                            modelClass: "Visualization",
                        }),
                    },
                    {
                        path: "visualizations/list",
                        component: GridVisualization,
                        props: {
                            activeList: "my",
                        },
                        redirect: redirectAnon(),
                    },
                    {
                        path: "visualizations/list_published",
                        component: GridVisualization,
                        props: {
                            activeList: "published",
                        },
                    },
                    {
                        path: "workflows/create",
                        component: WorkflowCreate,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "workflows/export",
                        component: WorkflowExport,
                        props: (route) => ({
                            id: route.query.id,
                        }),
                    },
                    {
                        path: "workflows/import",
                        component: WorkflowImport,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "workflows/invocations",
                        component: GridInvocation,
                        redirect: redirectAnon(),
                    },
                    {
                        path: "workflows/invocations/import",
                        component: HistoryImport,
                        props: {
                            invocationImport: true,
                        },
                    },
                    {
                        path: "workflows/invocations/report",
                        component: InvocationReport,
                        props: (route) => ({
                            invocationId: route.query.id,
                        }),
                    },
                    {
                        path: "workflows/invocations/:invocationId",
                        component: WorkflowInvocationState,
                        props: (route) => ({
                            invocationId: route.params.invocationId,
                            isFullPage: true,
                            success: route.query.success,
                        }),
                    },
                    {
                        path: "workflows/list",
                        component: WorkflowList,
                        redirect: redirectAnon("/workflows/list_published"),
                    },
                    {
                        path: "workflows/list_published",
                        component: WorkflowList,
                        props: (route) => ({
                            activeList: "published",
                            query: { ...route.query },
                        }),
                    },
                    {
                        path: "workflows/list_shared_with_me",
                        component: WorkflowList,
                        redirect: redirectAnon(),
                        props: (route) => ({
                            activeList: "shared_with_me",
                            query: { ...route.query },
                        }),
                    },
                    {
                        path: "workflows/run",
                        component: Home,
                        redirect: redirectAnon(),
                        props: (route) => ({
                            config: Galaxy.config,
                            query: {
                                workflow_id: route.query.id,
                                version: route.query.version,
                            },
                        }),
                    },
                    {
                        path: "workflows/sharing",
                        component: Sharing,
                        props: (route) => ({
                            id: route.query.id,
                            pluralName: "Workflows",
                            modelClass: "Workflow",
                        }),
                    },
                    {
                        path: "workflows/trs_import",
                        component: TrsImport,
                        props: (route) => ({
                            queryTrsServer: route.query.trs_server,
                            queryTrsId: route.query.trs_id,
                            queryTrsVersionId: route.query.trs_version,
                            queryTrsUrl: route.query.trs_url,
                            isRun: route.query.run_form == "true",
                        }),
                    },
                    {
                        path: "workflows/trs_search",
                        component: TrsSearch,
                    },
                    {
                        path: "workflows/:storedWorkflowId/invocations",
                        component: StoredWorkflowInvocations,
                        props: true,
                    },
                ],
            },
        ],
    });

    function checkAdminAccessRequired(to) {
        // Check parent route hierarchy to see if we require admin access here.
        // Access is required if *any* component in the hierarchy requires it.
        if (to.matched.some((record) => record.meta.requiresAdmin === true)) {
            const isAdmin = getGalaxyInstance()?.user?.isAdmin();
            return !isAdmin;
        }
        return false;
    }

    function checkRegisteredUserAccessRequired(to) {
        // Check parent route hierarchy to see if we require registered user access here.
        // Access is required if *any* component in the hierarchy requires it.
        if (to.matched.some((record) => record.meta.requiresRegisteredUser === true)) {
            const isAnonymous = getGalaxyInstance()?.user?.isAnonymous();
            return isAnonymous;
        }
        return false;
    }

    router.beforeEach(async (to, from, next) => {
        // TODO: merge anon redirect functionality here for more standard handling

        const isAdminAccessRequired = checkAdminAccessRequired(to);
        if (isAdminAccessRequired) {
            const error = new Error(`Admin access required for '${to.path}'.`);
            error.name = "AdminRequired";
            next(error);
        }

        const isRegisteredUserAccessRequired = checkRegisteredUserAccessRequired(to);
        if (isRegisteredUserAccessRequired) {
            const error = new Error(`Registered user access required for '${to.path}'.`);
            error.name = "RegisteredUserRequired";
            next(error);
        }
        next();
    });

    router.onError((error) => {
        router.push({ name: "error", params: { error: error } });
    });

    return router;
}
