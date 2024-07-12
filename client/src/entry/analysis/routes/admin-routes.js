import { getGalaxyInstance } from "app";
import DataManager from "components/admin/DataManager/DataManager";
import DataManagerJob from "components/admin/DataManager/DataManagerJob";
import DataManagerJobs from "components/admin/DataManager/DataManagerJobs";
import DataManagerTable from "components/admin/DataManager/DataManagerTable";
import DataManagerView from "components/admin/DataManager/DataManagerView";
import DataTables from "components/admin/DataTables";
import DataTypes from "components/admin/DataTypes";
import ToolboxDependencies from "components/admin/Dependencies/Landing";
import DisplayApplications from "components/admin/DisplayApplications";
import ErrorStack from "components/admin/ErrorStack";
import Home from "components/admin/Home";
import JobsList from "components/admin/JobsList";
import BroadcastForm from "components/admin/Notifications/BroadcastForm";
import NotificationForm from "components/admin/Notifications/NotificationForm";
import NotificationsManagement from "components/admin/Notifications/NotificationsManagement";
import ResetMetadata from "components/admin/ResetMetadata";
import SanitizeAllow from "components/admin/SanitizeAllow";
import FormGeneric from "components/Form/FormGeneric";
import adminFormsGridConfig from "components/Grid/configs/adminForms";
import adminGroupsGridConfig from "components/Grid/configs/adminGroups";
import adminQuotasGridConfig from "components/Grid/configs/adminQuotas";
import adminRolesGridConfig from "components/Grid/configs/adminRoles";
import adminUsersGridConfig from "components/Grid/configs/adminUsers";
import GridInvocation from "components/Grid/GridInvocation";
import GridList from "components/Grid/GridList";
import RegisterForm from "components/Login/RegisterForm";
import Toolshed from "components/Toolshed/Index";
import Admin from "entry/analysis/modules/Admin";

export default [
    {
        path: "/admin",
        component: Admin,
        meta: { requiresAdmin: true }, // All children of this route require admin
        children: [
            {
                path: "",
                component: Home,
                props: () => {
                    const config = getGalaxyInstance().config;
                    return {
                        isToolShedInstalled: config.tool_shed_urls && config.tool_shed_urls.length > 0,
                    };
                },
            },
            { path: "data_tables", component: DataTables },
            { path: "data_types", component: DataTypes },
            { path: "display_applications", component: DisplayApplications },
            { path: "error_stack", component: ErrorStack },
            {
                path: "invocations",
                component: GridInvocation,
                props: () => {
                    return {
                        headerMessage:
                            "Workflow invocations that are still being scheduled are displayed on this page.",
                        noInvocationsMessage: "There are no scheduling workflow invocations to show currently.",
                        ownerGrid: false,
                    };
                },
            },
            { path: "jobs", component: JobsList },
            { path: "reset_metadata", component: ResetMetadata },
            { path: "sanitize_allow", component: SanitizeAllow },
            { path: "toolbox_dependencies", component: ToolboxDependencies },
            { path: "toolshed", component: Toolshed },

            // user registration route
            {
                path: "users/create",
                component: RegisterForm,
                props: () => {
                    const Galaxy = getGalaxyInstance();
                    return {
                        redirect: "/admin/users",
                        registrationWarningMessage: Galaxy.config.registration_warning_message,
                        mailingJoinAddr: Galaxy.config.mailing_join_addr,
                        serverMailConfigured: Galaxy.config.server_mail_configured,
                        sessionCsrfToken: Galaxy.session_csrf_token,
                    };
                },
            },

            // data managers
            {
                path: "data_manager",
                component: DataManagerView,
                children: [
                    {
                        path: "",
                        name: "DataManager",
                        component: DataManager,
                    },
                    {
                        path: "jobs/:id",
                        name: "DataManagerJobs",
                        component: DataManagerJobs,
                        props: true,
                    },
                    {
                        path: "job/:id",
                        name: "DataManagerJob",
                        component: DataManagerJob,
                        props: true,
                    },
                    {
                        path: "table/:name",
                        name: "DataManagerTable",
                        component: DataManagerTable,
                        props: true,
                    },
                ],
            },

            // notifications and broadcasts
            {
                path: "notifications",
                component: NotificationsManagement,
            },

            {
                path: "notifications/create_new_broadcast",
                name: "NewBroadcast",
                component: BroadcastForm,
            },

            {
                path: "notifications/edit_broadcast/:id",
                name: "EditBroadcast",
                component: BroadcastForm,
                props: true,
            },

            {
                path: "notifications/create_new_notification",
                name: "NewNotification",
                component: NotificationForm,
            },

            // grids
            {
                path: "forms",
                component: GridList,
                props: (route) => ({
                    gridConfig: adminFormsGridConfig,
                    gridMessage: route.query.message,
                }),
            },
            {
                path: "groups",
                component: GridList,
                props: (route) => ({
                    gridConfig: adminGroupsGridConfig,
                    gridMessage: route.query.message,
                }),
            },
            {
                path: "quotas",
                component: GridList,
                props: (route) => ({
                    gridConfig: adminQuotasGridConfig,
                    gridMessage: route.query.message,
                }),
            },
            {
                path: "roles",
                component: GridList,
                props: (route) => ({
                    gridConfig: adminRolesGridConfig,
                    gridMessage: route.query.message,
                }),
            },
            {
                path: "users",
                component: GridList,
                props: (route) => ({
                    gridConfig: adminUsersGridConfig,
                    gridMessage: route.query.message,
                }),
            },
            // forms
            {
                path: "form/reset_user_password",
                component: FormGeneric,
                props: (route) => ({
                    title: "Reset passwords",
                    url: `/admin/reset_user_password?id=${route.query.id}`,
                    icon: "fa-user",
                    submitTitle: "Save new password",
                    redirect: "/admin/users",
                }),
            },
            {
                path: "form/manage_roles_and_groups_for_user",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/manage_roles_and_groups_for_user?id=${route.query.id}`,
                    icon: "fa-users",
                    redirect: "/admin/users",
                }),
            },
            {
                path: "form/manage_users_and_groups_for_role",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/manage_users_and_groups_for_role?id=${route.query.id}`,
                    redirect: "/admin/roles",
                }),
            },
            {
                path: "form/manage_users_and_roles_for_group",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/manage_users_and_roles_for_group?id=${route.query.id}`,
                    redirect: "/admin/groups",
                }),
            },
            {
                path: "form/manage_users_and_groups_for_quota",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/manage_users_and_groups_for_quota?id=${route.query.id}`,
                    redirect: "/admin/quotas",
                }),
            },
            {
                path: "form/create_role",
                component: FormGeneric,
                props: {
                    url: "/admin/create_role",
                    redirect: "/admin/roles",
                },
            },
            {
                path: "form/create_group",
                component: FormGeneric,
                props: {
                    url: "/admin/create_group",
                    redirect: "/admin/groups",
                },
            },
            {
                path: "form/create_quota",
                component: FormGeneric,
                props: {
                    url: "/admin/create_quota",
                    redirect: "/admin/quotas",
                },
            },
            {
                path: "form/rename_role",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/rename_role?id=${route.query.id}`,
                    redirect: "/admin/roles",
                }),
            },
            {
                path: "form/rename_group",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/rename_group?id=${route.query.id}`,
                    redirect: "/admin/groups",
                }),
            },
            {
                path: "form/rename_quota",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/rename_quota?id=${route.query.id}`,
                    redirect: "/admin/quotas",
                }),
            },
            {
                path: "form/edit_quota",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/edit_quota?id=${route.query.id}`,
                    redirect: "/admin/quotas",
                }),
            },
            {
                path: "form/set_quota_default",
                component: FormGeneric,
                props: (route) => ({
                    url: `/admin/set_quota_default?id=${route.query.id}`,
                    redirect: "/admin/quotas",
                }),
            },
            {
                path: "form/create_form",
                component: FormGeneric,
                props: {
                    url: "/forms/create_form",
                    redirect: "/admin/forms",
                },
            },
            {
                path: "form/edit_form",
                component: FormGeneric,
                props: (route) => ({
                    url: `/forms/edit_form?id=${route.query.id}`,
                    redirect: "/admin/forms",
                }),
            },
        ],
    },
];
