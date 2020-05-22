import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import _l from "utils/localization";
import FormWrapper from "mvc/form/form-wrapper";
import GridView from "mvc/grid/grid-view";
import QueryStringParsing from "utils/query-string-parsing";
import Router from "layout/router";
import DataTables from "components/admin/DataTables.vue";
import DataTypes from "components/admin/DataTypes.vue";
import Jobs from "components/admin/Jobs.vue";
import ActiveInvocations from "components/admin/ActiveInvocations.vue";
import Landing from "components/admin/Dependencies/Landing.vue";
import AdminHome from "components/admin/Home.vue";
import DataManagerView from "components/admin/DataManager/DataManagerView.vue";
import DataManagerRouter from "components/admin/DataManager/DataManagerRouter.vue";
import Register from "components/login/Register.vue";
import ErrorStack from "components/admin/ErrorStack.vue";
import DisplayApplications from "components/admin/DisplayApplications.vue";
import ResetMetadata from "components/admin/ResetMetadata.vue";
import Toolshed from "components/Toolshed/Index.vue";
import Vue from "vue";
import store from "store";

export const getAdminRouter = (Galaxy, options) => {
    const galaxyRoot = getAppRoot();

    return Router.extend({
        routes: {
            "(/)admin(/)": "show_home",
            "(/)admin(/)users": "show_users",
            "(/)admin(/)users(/)create": "show_users_create",
            "(/)admin(/)roles": "show_roles",
            "(/)admin(/)groups": "show_groups",
            "(/)admin(/)toolshed": "show_toolshed",
            "(/)admin(/)error_stack": "show_error_stack",
            "(/)admin(/)display_applications": "show_display_applications",
            "(/)admin(/)tool_versions": "show_tool_versions",
            "(/)admin(/)quotas": "show_quotas",
            "(/)admin(/)forms": "show_forms",
            "(/)admin(/)form(/)(:form_id)": "show_form",
            "(/)admin/data_tables": "show_data_tables",
            "(/)admin/data_types": "show_data_types",
            "(/)admin/jobs": "show_jobs",
            "(/)admin/invocations": "show_invocations",
            "(/)admin/toolbox_dependencies": "show_toolbox_dependencies",
            "(/)admin/data_manager*path": "show_data_manager",
            "(/)admin(/)reset_metadata": "show_reset_metadata",
            "*notFound": "not_found",
        },

        authenticate: function () {
            const Galaxy = getGalaxyInstance();
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get("is_admin");
        },

        not_found: function () {
            window.location.reload(); // = window.location.href;
        },

        show_home: function () {
            this._display_vue_helper(AdminHome, {
                isRepoInstalled: options.settings.is_repo_installed,
                isToolShedInstalled: options.settings.is_tool_shed_installed,
            });
        },

        show_users: function () {
            this._show_grid_view("admin/users_list");
        },

        show_users_create: function () {
            this._display_vue_helper(Register, {
                redirect: "/admin/users",
                registration_warning_message: options.config.registration_warning_message,
                mailing_join_addr: options.config.mailing_join_addr,
                server_mail_configured: options.config.server_mail_configured,
            });
        },

        show_roles: function () {
            this._show_grid_view("admin/roles_list");
        },

        show_groups: function () {
            this._show_grid_view("admin/groups_list");
        },

        show_toolshed: function () {
            this._display_vue_helper(Toolshed);
        },

        show_tool_versions: function () {
            this._show_grid_view("admin/tool_versions_list");
        },

        show_quotas: function () {
            this._show_grid_view("admin/quotas_list");
        },

        _show_grid_view: function (urlSuffix) {
            const Galaxy = getGalaxyInstance();
            this.page.display(
                new GridView({
                    url_base: `${galaxyRoot}${urlSuffix}`,
                    url_data: Galaxy.params,
                })
            );
        },

        _display_vue_helper: function (component, propsData = {}) {
            const instance = Vue.extend(component);
            const container = document.createElement("div");
            this.page.display(container);
            new instance({ store, propsData }).$mount(container);
        },

        show_data_tables: function () {
            this._display_vue_helper(DataTables);
        },

        show_data_types: function () {
            this._display_vue_helper(DataTypes);
        },

        show_jobs: function () {
            this._display_vue_helper(Jobs);
        },

        show_invocations: function () {
            this._display_vue_helper(ActiveInvocations);
        },

        show_toolbox_dependencies: function () {
            this._display_vue_helper(Landing);
        },

        show_error_stack: function () {
            this._display_vue_helper(ErrorStack);
        },

        show_display_applications: function () {
            this._display_vue_helper(DisplayApplications);
        },

        show_reset_metadata: function () {
            this._display_vue_helper(ResetMetadata);
        },

        show_data_manager: function (path) {
            const Galaxy = getGalaxyInstance();
            console.log("show_data_manager");
            const vueMount = document.createElement("div");
            this.page.display(vueMount);
            // always set the route back to the base, i.e.
            // `${galaxyRoot}admin/data_manager`
            Galaxy.debug("show_data_manager: path='" + path + "'");
            DataManagerRouter.replace(path || "/");
            new Vue({ router: DataManagerRouter, render: (h) => h(DataManagerView) }).$mount(vueMount);
        },

        show_forms: function () {
            this._show_grid_view("forms/forms_list");
        },

        show_form: function (form_id) {
            const id = `?id=${QueryStringParsing.get("id")}`;
            const form_defs = {
                reset_user_password: {
                    title: _l("Reset passwords"),
                    url: `admin/reset_user_password${id}`,
                    icon: "fa-user",
                    submit_title: "Save new password",
                    redirect: "admin/users",
                },
                manage_roles_and_groups_for_user: {
                    url: `admin/manage_roles_and_groups_for_user${id}`,
                    icon: "fa-users",
                    redirect: "admin/users",
                },
                manage_users_and_groups_for_role: {
                    url: `admin/manage_users_and_groups_for_role${id}`,
                    redirect: "admin/roles",
                },
                manage_users_and_roles_for_group: {
                    url: `admin/manage_users_and_roles_for_group${id}`,
                    redirect: "admin/groups",
                },
                manage_users_and_groups_for_quota: {
                    url: `admin/manage_users_and_groups_for_quota${id}`,
                    redirect: "admin/quotas",
                },
                create_role: {
                    url: "admin/create_role",
                    redirect: "admin/roles",
                },
                create_group: {
                    url: "admin/create_group",
                    redirect: "admin/groups",
                },
                create_quota: {
                    url: "admin/create_quota",
                    redirect: "admin/quotas",
                },
                rename_role: {
                    url: `admin/rename_role${id}`,
                    redirect: "admin/roles",
                },
                rename_group: {
                    url: `admin/rename_group${id}`,
                    redirect: "admin/groups",
                },
                rename_quota: {
                    url: `admin/rename_quota${id}`,
                    redirect: "admin/quotas",
                },
                edit_quota: {
                    url: `admin/edit_quota${id}`,
                    redirect: "admin/quotas",
                },
                set_quota_default: {
                    url: `admin/set_quota_default${id}`,
                    redirect: "admin/quotas",
                },
                create_form: {
                    url: "forms/create_form",
                    redirect: "admin/forms",
                },
                edit_form: {
                    url: `forms/edit_form${id}`,
                    redirect: "admin/forms",
                },
            };
            this.page.display(new FormWrapper.View(form_defs[form_id]));
        },
    });
};
