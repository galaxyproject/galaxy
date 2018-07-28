import _l from "utils/localization";
import jQuery from "jquery";
var $ = jQuery;
import GalaxyApp from "galaxy";
import AdminPanel from "./panels/admin-panel";
import FormWrapper from "mvc/form/form-wrapper";
import GridView from "mvc/grid/grid-view";
import QueryStringParsing from "utils/query-string-parsing";
import Router from "layout/router";
import Utils from "utils/utils";
import Page from "layout/page";
import DataTables from "components/admin/DataTables.vue";
import DataTypes from "components/admin/DataTypes.vue";
import Vue from "vue";

window.app = function app(options, bootstrapped) {
    window.Galaxy = new GalaxyApp.GalaxyApp(options, bootstrapped);
    Galaxy.debug("admin app");

    /** Routes */
    var AdminRouter = Router.extend({
        routes: {
            "(/)admin(/)" : "home",
            "(/)admin(/)users": "show_users",
            "(/)admin(/)roles": "show_roles",
            "(/)admin(/)groups": "show_groups",
            "(/)admin(/)tool_versions": "show_tool_versions",
            "(/)admin(/)quotas": "show_quotas",
            "(/)admin(/)repositories": "show_repositories",
            "(/)admin(/)forms": "show_forms",
            "(/)admin(/)form(/)(:form_id)": "show_form",
            "(/)admin/data_tables": "show_data_tables",
            "(/)admin/data_types": "show_data_types",
            "*notFound": "not_found"
        },

        authenticate: function() {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get("is_admin");
        },

        not_found: function() {
            window.location.href = `${Galaxy.root}${Backbone.history.getFragment()}`;
        },

        home: function() {
            this.page
                .$("#galaxy_main")
                .prop("src", `${Galaxy.root}admin/center?message=${options.message}&status=${options.status}`);
        },

        show_users: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin/users_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_roles: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin/roles_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_groups: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin/groups_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_repositories: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin_toolshed/browse_repositories`,
                    url_data: Galaxy.params
                })
            );
        },

        show_tool_versions: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin/tool_versions_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_quotas: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}admin/quotas_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_data_tables: function() {
            var vueMount = document.createElement("div");
            this.page.display(vueMount);
            new Vue(DataTables).$mount(vueMount);
        },

        show_data_types: function() {
            var vueMount = document.createElement("div");
            this.page.display(vueMount);
            new Vue(DataTypes).$mount(vueMount);
        },

        show_forms: function() {
            this.page.display(
                new GridView({
                    url_base: `${Galaxy.root}forms/forms_list`,
                    url_data: Galaxy.params
                })
            );
        },

        show_form: function(form_id) {
            var id = `?id=${QueryStringParsing.get("id")}`;
            var form_defs = {
                reset_user_password: {
                    title: _l("Reset passwords"),
                    url: `admin/reset_user_password${id}`,
                    icon: "fa-user",
                    submit_title: "Save new password",
                    redirect: "admin/users"
                },
                manage_roles_and_groups_for_user: {
                    url: `admin/manage_roles_and_groups_for_user${id}`,
                    icon: "fa-users",
                    redirect: "admin/users"
                },
                manage_users_and_groups_for_role: {
                    url: `admin/manage_users_and_groups_for_role${id}`,
                    redirect: "admin/roles"
                },
                manage_users_and_roles_for_group: {
                    url: `admin/manage_users_and_roles_for_group${id}`,
                    redirect: "admin/groups"
                },
                manage_users_and_groups_for_quota: {
                    url: `admin/manage_users_and_groups_for_quota${id}`,
                    redirect: "admin/quotas"
                },
                create_role: {
                    url: "admin/create_role",
                    redirect: "admin/roles"
                },
                create_group: {
                    url: "admin/create_group",
                    redirect: "admin/groups"
                },
                create_quota: {
                    url: "admin/create_quota",
                    redirect: "admin/quotas"
                },
                rename_role: {
                    url: `admin/rename_role${id}`,
                    redirect: "admin/roles"
                },
                rename_group: {
                    url: `admin/rename_group${id}`,
                    redirect: "admin/groups"
                },
                rename_quota: {
                    url: `admin/rename_quota${id}`,
                    redirect: "admin/quotas"
                },
                edit_quota: {
                    url: `admin/edit_quota${id}`,
                    redirect: "admin/quotas"
                },
                set_quota_default: {
                    url: `admin/set_quota_default${id}`,
                    redirect: "admin/quotas"
                },
                create_form: {
                    url: "forms/create_form",
                    redirect: "admin/forms"
                },
                edit_form: {
                    url: `forms/edit_form${id}`,
                    redirect: "admin/forms"
                }
            };
            this.page.display(new FormWrapper.View(form_defs[form_id]));
        }
    });

    $(() => {
        _.extend(options.config, { active_view: "admin" });
        Utils.setWindowTitle("Administration");
        Galaxy.page = new Page.View(
            _.extend(options, {
                Left: AdminPanel,
                Router: AdminRouter
            })
        );
    });
};
